import React, { useEffect, useState } from "react";
import { QrCode, Smartphone, Power, RefreshCw, CheckCircle2, AlertTriangle, Loader2 } from "lucide-react";
import api from "../lib/api";

const STATUS_META = {
  open: { label: "Terhubung", cls: "bg-emerald-50 text-emerald-600", icon: CheckCircle2 },
  qr: { label: "Menunggu Scan QR", cls: "bg-blue-50 text-kf-blue", icon: QrCode },
  pairing: { label: "Menunggu Pairing Code", cls: "bg-blue-50 text-kf-blue", icon: Smartphone },
  connecting: { label: "Menghubungkan…", cls: "bg-amber-50 text-amber-600", icon: Loader2 },
  disconnected: { label: "Tidak Terhubung", cls: "bg-slate-100 text-slate-500", icon: Power },
  gateway_down: { label: "Gateway Tidak Aktif", cls: "bg-red-50 text-red-600", icon: AlertTriangle },
};

export default function Connection() {
  const [st, setSt] = useState({ status: "disconnected" });
  const [mode, setMode] = useState("qr");
  const [phone, setPhone] = useState("");
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState("");

  const load = () => api.get("/whatsapp/status").then((r) => setSt(r.data)).catch(() => {});
  useEffect(() => {
    load();
    const t = setInterval(load, 3000);
    return () => clearInterval(t);
  }, []);

  const connectQR = async () => {
    setBusy(true); setMsg(""); setMode("qr");
    try { await api.post("/whatsapp/connect"); } catch (e) { setMsg("Gagal memulai koneksi."); }
    setBusy(false);
  };

  const requestPairing = async () => {
    if (!phone) { setMsg("Masukkan nomor WhatsApp klinik (contoh: 628123456789)."); return; }
    setBusy(true); setMsg(""); setMode("pairing");
    try {
      const r = await api.post("/whatsapp/pairing-code", { phone });
      if (!r.data.ok) setMsg(r.data.error || "Gagal meminta pairing code.");
    } catch (e) { setMsg(e.response?.data?.detail || "Gagal meminta pairing code."); }
    setBusy(false);
  };

  const logout = async () => {
    setBusy(true);
    try { await api.post("/whatsapp/logout"); } catch (e) {}
    setBusy(false); load();
  };

  const meta = STATUS_META[st.status] || STATUS_META.disconnected;
  const StatusIcon = meta.icon;
  const connected = st.status === "open";

  return (
    <div className="mx-auto max-w-4xl space-y-6">
      <div className="card flex flex-col items-start justify-between gap-4 p-5 sm:flex-row sm:items-center" data-testid="connection-status">
        <div>
          <p className="text-sm font-semibold text-slate-500">Status Koneksi WhatsApp</p>
          <div className="mt-2 flex items-center gap-2">
            <span className={`badge ${meta.cls}`}>
              <StatusIcon size={14} className={st.status === "connecting" ? "animate-spin" : ""} /> {meta.label}
            </span>
          </div>
          {connected && st.me && <p className="mt-2 text-sm text-slate-500">Nomor: <b>{st.me.id?.split(":")[0]?.replace("@s.whatsapp.net", "")}</b> {st.me.name ? `· ${st.me.name}` : ""}</p>}
          {st.lastError && <p className="mt-2 text-xs text-red-500">{st.lastError}</p>}
        </div>
        <div className="flex gap-2">
          <button className="btn-ghost" onClick={load} data-testid="refresh-status-btn"><RefreshCw size={16} /> Segarkan</button>
          {connected && <button className="btn-ghost !text-red-600 !border-red-200 hover:!bg-red-50" onClick={logout} disabled={busy} data-testid="logout-wa-btn"><Power size={16} /> Putuskan</button>}
        </div>
      </div>

      {!connected && (
        <div className="card p-6">
          <div className="mb-5 flex gap-2 rounded-lg bg-slate-100 p-1">
            <button onClick={() => setMode("qr")} data-testid="tab-qr" className={`flex-1 rounded-md py-2 text-sm font-semibold transition ${mode === "qr" ? "bg-white text-kf-blue shadow-card" : "text-slate-500"}`}>Scan QR Code</button>
            <button onClick={() => setMode("pairing")} data-testid="tab-pairing" className={`flex-1 rounded-md py-2 text-sm font-semibold transition ${mode === "pairing" ? "bg-white text-kf-blue shadow-card" : "text-slate-500"}`}>Pairing Code</button>
          </div>

          {mode === "qr" ? (
            <div className="flex flex-col items-center text-center">
              <div className="grid h-64 w-64 place-items-center rounded-xl border-2 border-dashed border-slate-200 bg-slate-50">
                {st.qr ? (
                  <img src={st.qr} alt="QR WhatsApp" className="h-60 w-60" data-testid="wa-qr" />
                ) : st.status === "connecting" ? (
                  <Loader2 className="animate-spin text-kf-blue" size={40} />
                ) : (
                  <QrCode className="text-slate-300" size={64} />
                )}
              </div>
              <p className="mt-4 max-w-md text-sm text-slate-500">
                Klik <b>Tampilkan QR</b>, lalu buka WhatsApp di ponsel klinik → <b>Perangkat Tertaut</b> → <b>Tautkan Perangkat</b> dan scan kode di atas.
              </p>
              <button className="btn-primary mt-4" onClick={connectQR} disabled={busy} data-testid="show-qr-btn">
                <QrCode size={18} /> {st.qr ? "Segarkan QR" : "Tampilkan QR"}
              </button>
            </div>
          ) : (
            <div className="mx-auto max-w-md text-center">
              <Smartphone className="mx-auto text-kf-blue" size={40} />
              <p className="mt-3 text-sm text-slate-500">Masukkan nomor WhatsApp klinik (format internasional tanpa +, contoh: <b>628123456789</b>). Kode 8-digit akan muncul untuk dimasukkan di WhatsApp ponsel.</p>
              <input className="input mt-4 text-center" placeholder="628123456789" value={phone} onChange={(e) => setPhone(e.target.value)} data-testid="pairing-phone" />
              <button className="btn-primary mt-4 w-full" onClick={requestPairing} disabled={busy} data-testid="request-pairing-btn">
                <Smartphone size={18} /> Minta Pairing Code
              </button>
              {st.pairingCode && (
                <div className="mt-5 rounded-xl bg-kf-blueLight p-5" data-testid="pairing-code">
                  <p className="text-sm font-semibold text-kf-blueDark">Kode Pairing Anda:</p>
                  <p className="mt-1 text-3xl font-extrabold tracking-widest text-kf-blueDark">{st.pairingCode}</p>
                  <p className="mt-1 text-xs text-kf-blue">Berlaku 60 detik. Masukkan di WhatsApp ponsel.</p>
                </div>
              )}
            </div>
          )}

          {msg && <p className="mt-4 text-center text-sm text-red-500" data-testid="connection-msg">{msg}</p>}
        </div>
      )}

      {connected && (
        <div className="card flex items-center gap-3 p-6 text-emerald-700">
          <CheckCircle2 size={24} /> <span className="font-semibold">WhatsApp berhasil terhubung. Agen AI siap menerima pesan pasien.</span>
        </div>
      )}
    </div>
  );
}
