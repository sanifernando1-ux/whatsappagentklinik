import React, { useEffect, useState } from "react";
import {
  BrainCircuit, ToggleLeft, ToggleRight, Plus, Trash2, Save, GripVertical,
  MessageSquareText, ShieldAlert, HeartPulse, ListTree, ArrowDown, Sparkles,
} from "lucide-react";
import api from "../lib/api";

const ACTIONS = [
  { v: "rag", label: "Jawab via AI + Knowledge Base" },
  { v: "services", label: "Tampilkan Layanan & Harga" },
  { v: "doctors", label: "Tampilkan Jadwal Dokter" },
  { v: "booking", label: "Mulai Booking Janji Temu" },
  { v: "queue", label: "Cek Status Antrian" },
  { v: "handoff", label: "Alihkan ke Staf (Handoff)" },
  { v: "static", label: "Balasan Teks Tetap" },
];

const MODULES = [
  { key: "faq", label: "FAQ & Tanya Jawab", desc: "Jawab pertanyaan umum" },
  { key: "booking", label: "Booking Janji Temu", desc: "Alur penjadwalan" },
  { key: "rag", label: "RAG Knowledge Base", desc: "Jawaban dari dokumen" },
  { key: "handoff", label: "Handoff ke Staf", desc: "Eskalasi ke manusia" },
];

let uidc = 0;
const newIntent = () => ({ id: `intent_${Date.now()}_${uidc++}`, name: "Intent Baru", action: "rag", menu_key: "", keywords: [], examples: [], response: "", enabled: true });

export default function Workflow() {
  const [s, setS] = useState(null);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);

  useEffect(() => { api.get("/settings").then((r) => setS(r.data)).catch(() => {}); }, []);

  if (!s) return <div className="text-slate-400">Memuat…</div>;
  const m = s.modules || {};
  const wf = s.workflow || { intents: [], use_llm_router: true, fallback: "rag", welcome_extra: "" };

  const setWf = (patch) => setS({ ...s, workflow: { ...wf, ...patch } });
  const setIntents = (intents) => setWf({ intents });
  const updIntent = (i, k, v) => setIntents(wf.intents.map((it, idx) => idx === i ? { ...it, [k]: v } : it));

  const toggleModule = async (key) => {
    const modules = { ...m, [key]: !m[key] };
    setS({ ...s, modules });
    try { await api.put("/settings", { modules }); } catch { /* noop */ }
  };

  const move = (i, dir) => {
    const arr = [...wf.intents];
    const j = i + dir;
    if (j < 0 || j >= arr.length) return;
    [arr[i], arr[j]] = [arr[j], arr[i]];
    setIntents(arr);
  };

  const save = async () => {
    setSaving(true); setSaved(false);
    try {
      const r = await api.put("/settings", { workflow: wf });
      setS((prev) => ({ ...prev, workflow: r.data.workflow }));
      setSaved(true); setTimeout(() => setSaved(false), 2500);
    } catch { /* noop */ } finally { setSaving(false); }
  };

  return (
    <div className="space-y-6">
      {/* Modules */}
      <div className="card p-5">
        <div className="flex items-center gap-2"><BrainCircuit className="text-kf-blue" size={20} /><h3 className="font-bold text-kf-ink">Modul Aktif</h3></div>
        <p className="mt-1 text-sm text-slate-500">Aktif/nonaktifkan modul inti agen AI.</p>
        <div className="mt-4 grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
          {MODULES.map((mod) => (
            <button key={mod.key} onClick={() => toggleModule(mod.key)} data-testid={`toggle-${mod.key}`}
              className={`flex items-start justify-between rounded-xl border p-4 text-left transition ${m[mod.key] ? "border-kf-blue/30 bg-kf-blueLight" : "border-slate-200 bg-white"}`}>
              <div><p className="text-sm font-bold text-kf-ink">{mod.label}</p><p className="text-xs text-slate-500">{mod.desc}</p></div>
              {m[mod.key] ? <ToggleRight className="text-kf-blue" size={22} /> : <ToggleLeft className="text-slate-300" size={22} />}
            </button>
          ))}
        </div>
      </div>

      {/* Router settings */}
      <div className="card p-5">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-2"><Sparkles className="text-kf-orange" size={20} /><h3 className="font-bold text-kf-ink">Kecerdasan & Alur Router</h3></div>
          <button className="btn-primary" onClick={save} disabled={saving} data-testid="wf-save-btn"><Save size={18} /> {saving ? "Menyimpan…" : saved ? "Tersimpan ✓" : "Simpan Workflow"}</button>
        </div>
        <div className="mt-4 grid grid-cols-1 gap-4 sm:grid-cols-2">
          <button onClick={() => setWf({ use_llm_router: !wf.use_llm_router })} data-testid="toggle-llm-router"
            className={`flex items-start justify-between rounded-xl border p-4 text-left transition ${wf.use_llm_router ? "border-kf-blue/30 bg-kf-blueLight" : "border-slate-200 bg-white"}`}>
            <div><p className="text-sm font-bold text-kf-ink">Router AI Semantik</p><p className="text-xs text-slate-500">Pahami maksud pasien secara natural (bukan hanya kata kunci)</p></div>
            {wf.use_llm_router ? <ToggleRight className="text-kf-blue" size={22} /> : <ToggleLeft className="text-slate-300" size={22} />}
          </button>
          <div className="rounded-xl border border-slate-200 p-4">
            <label className="label">Fallback bila tidak ada intent cocok</label>
            <select className="input" value={wf.fallback} onChange={(e) => setWf({ fallback: e.target.value })} data-testid="wf-fallback">
              <option value="rag">Jawab via AI + Knowledge Base</option>
              <option value="handoff">Alihkan ke Staf</option>
            </select>
          </div>
        </div>
        <div className="mt-4">
          <label className="label">Teks Tambahan di Menu Sambutan (opsional)</label>
          <input className="input" value={wf.welcome_extra || ""} onChange={(e) => setWf({ welcome_extra: e.target.value })} placeholder="mis. Kami melayani pasien BPJS & umum" data-testid="wf-welcome-extra" />
        </div>
      </div>

      {/* Intent editor */}
      <div className="card p-5">
        <div className="mb-3 flex items-center justify-between">
          <div><h3 className="font-bold text-kf-ink">Intent / Node Percakapan</h3><p className="text-sm text-slate-500">Susun bagaimana AI merespons tiap maksud pasien. Urutan menentukan prioritas kata kunci.</p></div>
          <button className="btn-ghost" onClick={() => setIntents([...wf.intents, newIntent()])} data-testid="wf-add-intent"><Plus size={16} /> Tambah Intent</button>
        </div>
        <div className="space-y-3">
          {wf.intents.map((it, i) => (
            <div key={it.id} className="rounded-xl border border-slate-200 p-4" data-testid={`wf-intent-${i}`}>
              <div className="flex flex-wrap items-center gap-2">
                <div className="flex flex-col">
                  <button onClick={() => move(i, -1)} className="text-slate-300 hover:text-kf-blue"><GripVertical size={14} /></button>
                </div>
                <input className="input flex-1 min-w-[160px] font-semibold" value={it.name} onChange={(e) => updIntent(i, "name", e.target.value)} data-testid={`wf-name-${i}`} />
                <select className="input w-56" value={it.action} onChange={(e) => updIntent(i, "action", e.target.value)} data-testid={`wf-action-${i}`}>
                  {ACTIONS.map((a) => <option key={a.v} value={a.v}>{a.label}</option>)}
                </select>
                <input className="input w-24" placeholder="No. menu" value={it.menu_key || ""} onChange={(e) => updIntent(i, "menu_key", e.target.value)} data-testid={`wf-menukey-${i}`} />
                <button onClick={() => updIntent(i, "enabled", !it.enabled)} title="Aktif/Nonaktif" data-testid={`wf-enabled-${i}`}>
                  {it.enabled ? <ToggleRight className="text-kf-blue" size={26} /> : <ToggleLeft className="text-slate-300" size={26} />}
                </button>
                <button onClick={() => setIntents(wf.intents.filter((_, idx) => idx !== i))} className="rounded-md p-2 text-red-500 hover:bg-red-50" data-testid={`wf-del-${i}`}><Trash2 size={16} /></button>
              </div>
              <div className="mt-2 grid grid-cols-1 gap-2 sm:grid-cols-2">
                <div>
                  <label className="label !text-xs">Kata Kunci (pisah koma)</label>
                  <input className="input" value={(it.keywords || []).join(", ")} onChange={(e) => updIntent(i, "keywords", e.target.value.split(",").map((x) => x.trim()).filter(Boolean))} data-testid={`wf-keywords-${i}`} />
                </div>
                <div>
                  <label className="label !text-xs">Contoh Kalimat (untuk router AI, pisah koma)</label>
                  <input className="input" value={(it.examples || []).join(", ")} onChange={(e) => updIntent(i, "examples", e.target.value.split(",").map((x) => x.trim()).filter(Boolean))} data-testid={`wf-examples-${i}`} />
                </div>
              </div>
              {(it.action === "static" || it.action === "handoff") && (
                <div className="mt-2">
                  <label className="label !text-xs">Teks Balasan</label>
                  <textarea rows={2} className="input" value={it.response || ""} onChange={(e) => updIntent(i, "response", e.target.value)} data-testid={`wf-response-${i}`} />
                </div>
              )}
            </div>
          ))}
        </div>
      </div>

      {/* Visual flow */}
      <div className="card p-6">
        <h3 className="mb-4 font-bold text-kf-ink">Alur Eksekusi (Ringkasan)</h3>
        <div className="mx-auto max-w-xl space-y-1 text-center">
          {[
            { icon: MessageSquareText, t: "Pesan Masuk (WhatsApp)" },
            { icon: ShieldAlert, t: "Deteksi Permintaan Staf → Handoff" },
            { icon: HeartPulse, t: "Analisis Sentimen (2+ negatif → eskalasi)" },
            { icon: ListTree, t: `Router: Menu → Kata Kunci → ${wf.use_llm_router ? "AI Semantik" : "(AI Router mati)"}` },
            { icon: BrainCircuit, t: `Fallback: ${wf.fallback === "handoff" ? "Alihkan ke Staf" : "AI + Knowledge Base"}` },
            { icon: MessageSquareText, t: "Balasan empatik & terstruktur terkirim" },
          ].map((n, idx, arr) => (
            <div key={idx}>
              <div className="inline-flex items-center gap-2 rounded-xl border border-kf-blue/20 bg-kf-blueLight px-4 py-2.5 text-sm font-semibold text-kf-blueDark">
                <n.icon size={16} /> {idx + 1}. {n.t}
              </div>
              {idx < arr.length - 1 && <div className="flex justify-center py-1 text-slate-300"><ArrowDown size={18} /></div>}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
