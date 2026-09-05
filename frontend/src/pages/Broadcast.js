import React, { useEffect, useState } from "react";
import { Megaphone, Send, Users, History, CheckCircle2, AlertTriangle } from "lucide-react";
import api from "../lib/api";

const TARGETS = [
  { v: "all", label: "Semua pasien (kecuali ditutup)" },
  { v: "active", label: "Percakapan aktif (dilayani AI)" },
  { v: "handoff", label: "Sedang ditangani staf" },
];

export default function Broadcast() {
  const [message, setMessage] = useState("");
  const [target, setTarget] = useState("all");
  const [count, setCount] = useState(0);
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState(null);
  const [history, setHistory] = useState([]);

  const loadCount = (t) => api.get("/broadcast/audience", { params: { target: t } }).then((r) => setCount(r.data.count)).catch(() => {});
  const loadHistory = () => api.get("/broadcast").then((r) => setHistory(r.data)).catch(() => {});
  useEffect(() => { loadCount(target); }, [target]);
  useEffect(() => { loadHistory(); }, []);

  const send = async () => {
    if (!message.trim()) return;
    setBusy(true); setResult(null);
    try {
      const r = await api.post("/broadcast", { message, target });
      setResult(r.data); setMessage(""); loadHistory();
    } catch { setResult({ error: true }); } finally { setBusy(false); }
  };

  return (
    <div className="grid grid-cols-1 gap-6 lg:grid-cols-[1fr_360px]">
      <div className="space-y-4">
        <div className="card p-5">
          <div className="flex items-center gap-2"><Megaphone className="text-kf-orange" size={20} /><h3 className="font-bold text-kf-ink">Kirim Pesan Massal</h3></div>
          <p className="mt-1 text-sm text-slate-500">Kirim promo, pengumuman, atau informasi penting ke pasien via WhatsApp.</p>

          <div className="mt-4">
            <label className="label">Penerima</label>
            <select className="input" value={target} onChange={(e) => setTarget(e.target.value)} data-testid="broadcast-target">
              {TARGETS.map((t) => <option key={t.v} value={t.v}>{t.label}</option>)}
            </select>
            <div className="mt-2 inline-flex items-center gap-1.5 rounded-lg bg-kf-blueLight px-3 py-1.5 text-sm font-semibold text-kf-blueDark">
              <Users size={15} /> {count} penerima
            </div>
          </div>

          <div className="mt-4">
            <label className="label">Isi Pesan</label>
            <textarea rows={6} className="input" placeholder="Tulis pesan promo/pengumuman di sini…" value={message} onChange={(e) => setMessage(e.target.value)} data-testid="broadcast-message" />
            <p className="mt-1 text-xs text-slate-400">Gunakan *tebal* untuk penekanan. Hindari spam agar nomor WhatsApp klinik tetap aman.</p>
          </div>

          <button className="btn-orange mt-4" onClick={send} disabled={busy || !message.trim()} data-testid="broadcast-send-btn">
            <Send size={18} /> {busy ? "Mengirim…" : `Kirim ke ${count} pasien`}
          </button>

          {result && !result.error && (
            <div className="mt-4 flex items-start gap-2 rounded-lg bg-emerald-50 p-4 text-sm text-emerald-700" data-testid="broadcast-result">
              <CheckCircle2 size={18} className="mt-0.5" />
              <span>Broadcast selesai: <b>{result.sent}</b> terkirim, <b>{result.failed}</b> gagal dari {result.total} penerima.
              {result.failed > 0 && " (Kegagalan biasanya karena WhatsApp belum tersambung.)"}</span>
            </div>
          )}
          {result && result.error && (
            <div className="mt-4 flex items-center gap-2 rounded-lg bg-red-50 p-4 text-sm text-red-600"><AlertTriangle size={18} /> Gagal mengirim broadcast.</div>
          )}
        </div>
      </div>

      <div className="card p-5">
        <div className="mb-3 flex items-center gap-2"><History size={18} className="text-kf-blue" /><h3 className="font-bold text-kf-ink">Riwayat Broadcast</h3></div>
        {history.length === 0 ? (
          <p className="py-8 text-center text-sm text-slate-400">Belum ada broadcast</p>
        ) : (
          <div className="space-y-3">
            {history.map((h) => (
              <div key={h.id} className="rounded-lg border border-slate-100 p-3" data-testid={`broadcast-history-${h.id}`}>
                <p className="line-clamp-2 text-sm text-kf-ink">{h.message}</p>
                <p className="mt-1 text-xs text-slate-400">{h.sent}/{h.total} terkirim · {(TARGETS.find((t) => t.v === h.target) || {}).label || h.target} · {new Date(h.created_at).toLocaleString("id-ID")}</p>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
