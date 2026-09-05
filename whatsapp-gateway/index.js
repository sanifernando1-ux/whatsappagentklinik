const express = require('express');
const axios = require('axios');
const QRCode = require('qrcode');
const pino = require('pino');
const { Boom } = require('@hapi/boom');
const path = require('path');
const fs = require('fs');
const {
  default: makeWASocket,
  useMultiFileAuthState,
  DisconnectReason,
  fetchLatestBaileysVersion,
} = require('@whiskeysockets/baileys');

const PORT = process.env.PORT || process.env.GATEWAY_PORT || 3001;
const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:8001';
const WEBHOOK_TOKEN = process.env.WEBHOOK_TOKEN || 'whk_9c2f7a1e5b8d3046';
const AUTH_DIR = path.join(__dirname, 'auth_info');

const logger = pino({ level: 'silent' });

let sock = null;
let state = {
  status: 'disconnected', // disconnected | connecting | qr | pairing | open
  qr: null,               // data URL
  pairingCode: null,
  me: null,
  lastError: null,
};
let pendingPhone = null;
let reconnectAttempts = 0;
let connecting = false;

async function startSock() {
  if (connecting) return;
  connecting = true;
  state.status = 'connecting';
  state.lastError = null;

  const { state: authState, saveCreds } = await useMultiFileAuthState(AUTH_DIR);
  const { version } = await fetchLatestBaileysVersion();

  sock = makeWASocket({
    version,
    auth: authState,
    printQRInTerminal: false,
    logger,
    browser: ['Klinik KF Sepinggan', 'Chrome', '1.0.0'],
    syncFullHistory: false,
  });

  connecting = false;

  sock.ev.on('creds.update', saveCreds);

  sock.ev.on('connection.update', async (update) => {
    const { connection, lastDisconnect, qr } = update;

    if (qr) {
      state.qr = await QRCode.toDataURL(qr);
      state.status = 'qr';
      // If a phone was requested for pairing and not yet registered, request pairing code
      if (pendingPhone && !sock.authState.creds.registered) {
        try {
          const code = await sock.requestPairingCode(pendingPhone);
          state.pairingCode = code;
          state.status = 'pairing';
        } catch (e) {
          state.lastError = 'Gagal meminta pairing code: ' + (e.message || e);
        }
        pendingPhone = null;
      }
    }

    if (connection === 'open') {
      state.status = 'open';
      state.qr = null;
      state.pairingCode = null;
      state.me = sock.user ? { id: sock.user.id, name: sock.user.name } : null;
      reconnectAttempts = 0;
    }

    if (connection === 'close') {
      const code = (lastDisconnect?.error instanceof Boom)
        ? lastDisconnect.error.output?.statusCode
        : lastDisconnect?.error?.output?.statusCode;
      state.status = 'disconnected';
      state.me = null;
      if (code === DisconnectReason.loggedOut) {
        state.lastError = 'Logged out. Silakan hubungkan ulang.';
        try { fs.rmSync(AUTH_DIR, { recursive: true, force: true }); } catch (e) {}
      } else {
        reconnectAttempts += 1;
        const delay = Math.min(60000, 1000 * Math.pow(2, reconnectAttempts));
        setTimeout(() => startSock().catch(() => {}), delay);
      }
    }
  });

  sock.ev.on('messages.upsert', async ({ messages, type }) => {
    if (type !== 'notify') return;
    for (const msg of messages) {
      if (!msg.message || msg.key.fromMe) continue;
      const jid = msg.key.remoteJid;
      if (!jid || jid.endsWith('@g.us') || jid === 'status@broadcast') continue; // 1-on-1 only

      const m = msg.message;
      let text = m.conversation || m.extendedTextMessage?.text || '';
      let messageType = 'text';
      if (m.imageMessage) { messageType = 'image'; text = m.imageMessage.caption || ''; }
      else if (m.videoMessage) { messageType = 'video'; text = m.videoMessage.caption || ''; }
      else if (m.documentMessage) { messageType = 'document'; text = m.documentMessage.fileName || ''; }
      else if (m.audioMessage) { messageType = 'audio'; }

      try {
        await axios.post(`${BACKEND_URL}/api/whatsapp/webhook`, {
          sender: jid,
          text: text,
          messageType,
          waMessageId: msg.key.id,
          pushName: msg.pushName || '',
        }, { headers: { 'x-webhook-token': WEBHOOK_TOKEN }, timeout: 60000 });
      } catch (e) {
        console.error('Webhook error:', e.message);
      }
    }
  });
}

// ---- HTTP API ----
const app = express();
app.use(express.json());

app.get('/status', (req, res) => {
  res.json(state);
});

app.post('/connect', async (req, res) => {
  try {
    if (state.status === 'open') return res.json(state);
    await startSock();
    res.json({ ok: true, status: state.status });
  } catch (e) {
    res.status(500).json({ ok: false, error: e.message });
  }
});

app.post('/pairing-code', async (req, res) => {
  const { phone } = req.body;
  if (!phone) return res.status(400).json({ ok: false, error: 'phone wajib diisi' });
  try {
    pendingPhone = phone;
    if (!sock || state.status === 'disconnected') {
      await startSock();
    } else if (sock.authState.creds.registered) {
      return res.status(400).json({ ok: false, error: 'Perangkat sudah terhubung.' });
    } else {
      // socket already up waiting; request code directly
      try {
        const code = await sock.requestPairingCode(phone);
        state.pairingCode = code;
        state.status = 'pairing';
        pendingPhone = null;
      } catch (e) { /* will retry on qr event */ }
    }
    res.json({ ok: true, message: 'Pairing code sedang diproses', status: state.status });
  } catch (e) {
    res.status(500).json({ ok: false, error: e.message });
  }
});

app.post('/logout', async (req, res) => {
  try {
    if (sock) {
      try { await sock.logout(); } catch (e) {}
    }
    try { fs.rmSync(AUTH_DIR, { recursive: true, force: true }); } catch (e) {}
    sock = null;
    state = { status: 'disconnected', qr: null, pairingCode: null, me: null, lastError: null };
    res.json({ ok: true });
  } catch (e) {
    res.status(500).json({ ok: false, error: e.message });
  }
});

app.post('/send', async (req, res) => {
  const { to, text } = req.body;
  if (state.status !== 'open' || !sock) {
    return res.status(409).json({ ok: false, error: 'WhatsApp belum terhubung' });
  }
  try {
    await sock.sendMessage(to, { text });
    res.json({ ok: true });
  } catch (e) {
    res.status(500).json({ ok: false, error: e.message });
  }
});

app.listen(PORT, () => {
  console.log(`WhatsApp gateway listening on :${PORT}`);
  // Auto-resume if a saved session exists
  if (fs.existsSync(path.join(AUTH_DIR, 'creds.json'))) {
    startSock().catch((e) => console.error('startSock error:', e.message));
  }
});
