import React, { useEffect, useState } from "react";
import {
  BrainCircuit, ToggleLeft, ToggleRight, Plus, Trash2, Save, GripVertical,
  MessageSquareText, ShieldAlert, HeartPulse, ListTree, ArrowDown, Sparkles, GitBranch, CornerDownRight,
} from "lucide-react";
import api from "../lib/api";

const ACTIONS = [
  { v: "rag", label: "Jawab via AI + Knowledge Base" },
  { v: "flow", label: "Alur Bertingkat (Node Kondisional)" },
  { v: "services", label: "Tampilkan Layanan & Harga" },
  { v: "doctors", label: "Tampilkan Jadwal Dokter" },
  { v: "booking", label: "Mulai Booking Janji Temu (internal)" },
  { v: "booking_link", label: "Arahkan ke Link Booking Eksternal" },
  { v: "queue", label: "Cek Status Antrian" },
  { v: "handoff", label: "Alihkan ke Staf (Handoff)" },
  { v: "link", label: "Kirim Link / Teks + URL" },
  { v: "static", label: "Balasan Teks Tetap" },
];

const OPT_ACTIONS = [
  { v: "next", label: "➡️ Lanjut ke Langkah lain" },
  { v: "message", label: "💬 Balasan Teks (selesai)" },
  { v: "booking_link", label: "🔗 Link Booking Eksternal" },
  { v: "link", label: "🔗 Kirim Link/Teks" },
  { v: "handoff", label: "🎧 Alihkan ke Staf" },
  { v: "services", label: "ℹ️ Info Layanan" },
  { v: "doctors", label: "🩺 Jadwal Dokter" },
  { v: "queue", label: "👥 Cek Antrian" },
  { v: "booking", label: "📅 Booking Internal" },
];

const MODULES = [
  { key: "faq", label: "FAQ & Tanya Jawab", desc: "Jawab pertanyaan umum" },
  { key: "booking", label: "Booking Janji Temu", desc: "Alur penjadwalan internal" },
  { key: "rag", label: "RAG Knowledge Base", desc: "Jawaban dari dokumen" },
  { key: "handoff", label: "Handoff ke Staf", desc: "Eskalasi ke manusia" },
];

let uidc = 0;
const newIntent = () => ({ id: `intent_${Date.now()}_${uidc++}`, name: "Intent Baru", action: "rag", menu_key: "", keywords: [], examples: [], response: "", enabled: true, steps: [] });
const newStep = (n) => ({ id: `langkah${n}`, message: "", options: [] });
const newOpt = () => ({ label: "", keywords: [], action: "message", response: "", next_step: "" });

function FlowEditor({ steps, onChange, idx }) {
  const list = steps || [];
  const stepIds = list.map((s) => s.id);
  const setSteps = (v) => onChange(v);
  const updStep = (si, k, v) => setSteps(list.map((s, i) => i === si ? { ...s, [k]: v } : s));
  const updOpt = (si, oi, k, v) => updStep(si, "options", list[si].options.map((o, i) => i === oi ? { ...o, [k]: v } : o));

  return (
    <div className="mt-3 rounded-lg border border-dashed border-kf-blue/40 bg-kf-blueLight/30 p-3" data-testid={`wf-flow-${idx}`}>
      <div className="mb-2 flex items-center justify-between">
        <span className="flex items-center gap-1.5 text-xs font-bold text-kf-blueDark"><GitBranch size={14} /> Alur Bertingkat — pasien menjawab, lalu diarahkan sesuai pilihan</span>
        <button className="btn-ghost !py-1 !px-2 !text-xs" onClick={() => setSteps([...list, newStep(list.length + 1)])} data-testid={`wf-add-step-${idx}`}><Plus size={13} /> Langkah</button>
      </div>
      {list.length === 0 && <p className="py-2 text-center text-xs text-slate-400">Belum ada langkah. Tambahkan langkah pertama (contoh: "Silakan pilih poli").</p>}
      <div className="space-y-3">
        {list.map((step, si) => (
          <div key={si} className="rounded-lg border border-slate-200 bg-white p-3" data-testid={`wf-step-${idx}-${si}`}>
            <div className="flex items-center gap-2">
              <span className="badge bg-kf-blueLight text-kf-blueDark">{si === 0 ? "Langkah Awal" : `Langkah ${si + 1}`}</span>
              <input className="input !py-1.5 w-40 font-mono text-xs" value={step.id} onChange={(e) => updStep(si, "id", e.target.value)} placeholder="id langkah" data-testid={`wf-step-id-${idx}-${si}`} />
              <button className="ml-auto rounded-md p-1.5 text-red-500 hover:bg-red-50" onClick={() => setSteps(list.filter((_, i) => i !== si))} data-testid={`wf-del-step-${idx}-${si}`}><Trash2 size={14} /></button>
            </div>
            <textarea rows={2} className="input mt-2" placeholder="Pertanyaan yang dikirim ke pasien, mis. 'Silakan pilih poli:\n1. Umum\n2. Gigi'" value={step.message} onChange={(e) => updStep(si, "message", e.target.value)} data-testid={`wf-step-msg-${idx}-${si}`} />
            <div className="mt-2 space-y-2">
              {(step.options || []).map((opt, oi) => (
                <div key={oi} className="rounded-md bg-slate-50 p-2" data-testid={`wf-opt-${idx}-${si}-${oi}`}>
                  <div className="flex flex-wrap items-center gap-2">
                    <CornerDownRight size={14} className="text-slate-400" />
                    <input className="input !py-1.5 w-32" placeholder="Label opsi" value={opt.label} onChange={(e) => updOpt(si, oi, "label", e.target.value)} />
                    <input className="input !py-1.5 flex-1 min-w-[120px]" placeholder="kata kunci (pisah koma), mis: 1, umum" value={(opt.keywords || []).join(", ")} onChange={(e) => updOpt(si, oi, "keywords", e.target.value.split(",").map((x) => x.trim()).filter(Boolean))} />
                    <select className="input !py-1.5 w-48" value={opt.action} onChange={(e) => updOpt(si, oi, "action", e.target.value)} data-testid={`wf-opt-action-${idx}-${si}-${oi}`}>
                      {OPT_ACTIONS.map((a) => <option key={a.v} value={a.v}>{a.label}</option>)}
                    </select>
                    <button className="rounded-md p-1.5 text-red-500 hover:bg-red-50" data-testid={`wf-del-opt-${idx}-${si}-${oi}`} onClick={() => updStep(si, "options", step.options.filter((_, i) => i !== oi))}><Trash2 size={13} /></button>
                  </div>
                  {opt.action === "next" && (
                    <select className="input !py-1.5 mt-2" value={opt.next_step} onChange={(e) => updOpt(si, oi, "next_step", e.target.value)} data-testid={`wf-opt-next-${idx}-${si}-${oi}`}>
                      <option value="">— pilih langkah tujuan —</option>
                      {stepIds.filter((id) => id !== step.id).map((id) => <option key={id} value={id}>{id}</option>)}
                    </select>
                  )}
                  {["message", "link", "booking_link", "handoff"].includes(opt.action) && (
                    <input className="input !py-1.5 mt-2" placeholder="Teks balasan (untuk link, sertakan URL)" value={opt.response} onChange={(e) => updOpt(si, oi, "response", e.target.value)} />
                  )}
                </div>
              ))}
              <button className="btn-ghost !py-1 !px-2 !text-xs" onClick={() => updStep(si, "options", [...(step.options || []), newOpt()])} data-testid={`wf-add-opt-${idx}-${si}`}><Plus size={13} /> Opsi Jawaban</button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

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
      const r = await api.put("/settings", { workflow: wf, clinic: s.clinic });
      setS((prev) => ({ ...prev, workflow: r.data.workflow }));
      setSaved(true); setTimeout(() => setSaved(false), 2500);
    } catch { /* noop */ } finally { setSaving(false); }
  };

  return (
    <div className="space-y-6">
      <div className="card p-5">
        <div className="flex items-center gap-2"><BrainCircuit className="text-kf-blue" size={20} /><h3 className="font-bold text-kf-ink">Modul Aktif</h3></div>
        <p className="mt-1 text-sm text-slate-500">Aktif/nonaktifkan modul inti agen AI. Untuk mengarahkan pasien ke link booking eksternal, matikan "Booking Janji Temu" lalu set aksi intent booking menjadi "Arahkan ke Link Booking Eksternal".</p>
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

      <div className="card p-5">
        <div className="mb-3 flex items-center justify-between">
          <div><h3 className="font-bold text-kf-ink">Intent / Node Percakapan</h3><p className="text-sm text-slate-500">Susun bagaimana AI merespons tiap maksud pasien. Pilih aksi "Alur Bertingkat" untuk membuat cabang tanya-jawab.</p></div>
          <button className="btn-ghost" onClick={() => setIntents([...wf.intents, newIntent()])} data-testid="wf-add-intent"><Plus size={16} /> Tambah Intent</button>
        </div>
        <div className="space-y-3">
          {wf.intents.map((it, i) => (
            <div key={it.id} className="rounded-xl border border-slate-200 p-4" data-testid={`wf-intent-${i}`}>
              <div className="flex flex-wrap items-center gap-2">
                <button onClick={() => move(i, -1)} className="text-slate-300 hover:text-kf-blue"><GripVertical size={14} /></button>
                <input className="input flex-1 min-w-[160px] font-semibold" value={it.name} onChange={(e) => updIntent(i, "name", e.target.value)} data-testid={`wf-name-${i}`} />
                <select className="input w-64" value={it.action} onChange={(e) => updIntent(i, "action", e.target.value)} data-testid={`wf-action-${i}`}>
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
              {["static", "handoff", "link", "booking_link"].includes(it.action) && (
                <div className="mt-2">
                  <label className="label !text-xs">Teks Balasan {["link", "booking_link"].includes(it.action) ? "(URL diambil dari Link Booking di Pengaturan)" : ""}</label>
                  <textarea rows={2} className="input" value={it.response || ""} onChange={(e) => updIntent(i, "response", e.target.value)} data-testid={`wf-response-${i}`} />
                </div>
              )}
              {it.action === "flow" && (
                <FlowEditor idx={i} steps={it.steps || []} onChange={(steps) => updIntent(i, "steps", steps)} />
              )}
            </div>
          ))}
        </div>
      </div>

      <div className="card p-6">
        <h3 className="mb-4 font-bold text-kf-ink">Alur Eksekusi (Ringkasan)</h3>
        <div className="mx-auto max-w-xl space-y-1 text-center">
          {[
            { icon: MessageSquareText, t: "Pesan Masuk (WhatsApp)" },
            { icon: ShieldAlert, t: "Deteksi Permintaan Staf → Handoff" },
            { icon: HeartPulse, t: "Analisis Sentimen (2+ negatif → eskalasi)" },
            { icon: ListTree, t: `Router: Menu → Kata Kunci → ${wf.use_llm_router ? "AI Semantik" : "(AI Router mati)"}` },
            { icon: GitBranch, t: "Jika intent Alur Bertingkat → tanya-jawab bercabang" },
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
