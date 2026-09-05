import React, { useEffect, useState } from "react";
import {
  MessageSquareText, ShieldAlert, HeartPulse, ListTree, CalendarPlus,
  Stethoscope, Info, Users, BrainCircuit, Headphones, ArrowDown, ToggleLeft, ToggleRight,
} from "lucide-react";
import api from "../lib/api";

function Node({ icon: Icon, title, desc, tone = "blue", testid }) {
  const tones = {
    blue: "border-kf-blue/30 bg-kf-blueLight text-kf-blueDark",
    orange: "border-kf-orange/30 bg-orange-50 text-kf-orangeDark",
    slate: "border-slate-200 bg-white text-slate-600",
    red: "border-red-200 bg-red-50 text-red-600",
  };
  return (
    <div className={`rounded-xl border p-4 shadow-card ${tones[tone]}`} data-testid={testid}>
      <div className="flex items-center gap-2">
        <Icon size={18} />
        <p className="font-bold">{title}</p>
      </div>
      {desc && <p className="mt-1 text-xs opacity-80">{desc}</p>}
    </div>
  );
}

const Arrow = () => <div className="flex justify-center py-1 text-slate-300"><ArrowDown size={20} /></div>;

export default function Workflow() {
  const [settings, setSettings] = useState(null);
  const [saving, setSaving] = useState(false);

  const load = () => api.get("/settings").then((r) => setSettings(r.data)).catch(() => {});
  useEffect(() => { load(); }, []);

  const toggle = async (key) => {
    setSaving(true);
    const modules = { ...settings.modules, [key]: !settings.modules[key] };
    setSettings({ ...settings, modules });
    try { await api.put("/settings", { modules }); } catch { /* noop */ }
    setSaving(false);
  };

  if (!settings) return <div className="text-slate-400">Memuat…</div>;
  const m = settings.modules || {};

  return (
    <div className="space-y-6">
      <div className="card p-5">
        <div className="flex items-center gap-2">
          <BrainCircuit className="text-kf-blue" size={20} />
          <h3 className="font-bold text-kf-ink">Modul Aktif</h3>
          {saving && <span className="text-xs text-slate-400">menyimpan…</span>}
        </div>
        <p className="mt-1 text-sm text-slate-500">Aktif/nonaktifkan modul untuk mengatur bagaimana AI menjalankan alur percakapan.</p>
        <div className="mt-4 grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
          {[
            { key: "faq", label: "FAQ & Tanya Jawab", desc: "Jawab pertanyaan umum" },
            { key: "booking", label: "Booking Janji Temu", desc: "Alur penjadwalan" },
            { key: "rag", label: "RAG Knowledge Base", desc: "Jawaban dari dokumen" },
            { key: "handoff", label: "Handoff ke Staf", desc: "Eskalasi ke manusia" },
          ].map((mod) => (
            <button key={mod.key} onClick={() => toggle(mod.key)} data-testid={`toggle-${mod.key}`}
              className={`flex items-start justify-between rounded-xl border p-4 text-left transition ${m[mod.key] ? "border-kf-blue/30 bg-kf-blueLight" : "border-slate-200 bg-white"}`}>
              <div>
                <p className="text-sm font-bold text-kf-ink">{mod.label}</p>
                <p className="text-xs text-slate-500">{mod.desc}</p>
              </div>
              {m[mod.key] ? <ToggleRight className="text-kf-blue" size={22} /> : <ToggleLeft className="text-slate-300" size={22} />}
            </button>
          ))}
        </div>
      </div>

      <div className="card p-6">
        <h3 className="mb-1 font-bold text-kf-ink">Alur Eksekusi AI</h3>
        <p className="mb-5 text-sm text-slate-500">Setiap pesan pasien diproses berurutan melalui node berikut agar jawaban selalu rapi & terkontrol.</p>

        <div className="mx-auto max-w-2xl">
          <Node icon={MessageSquareText} title="1. Pesan Masuk (WhatsApp)" desc="Pesan pasien diterima via Baileys gateway" tone="slate" testid="wf-node-incoming" />
          <Arrow />
          <Node icon={ShieldAlert} title="2. Deteksi Permintaan Staf" desc={`Kata kunci: ${(settings.handoff_keywords || []).slice(0, 4).join(", ")}… → Handoff`} tone={m.handoff ? "red" : "slate"} testid="wf-node-handoff-kw" />
          <Arrow />
          <Node icon={HeartPulse} title="3. Analisis Sentimen" desc="2+ pesan negatif berturut-turut → eskalasi ke staf" tone={m.handoff ? "orange" : "slate"} testid="wf-node-sentiment" />
          <Arrow />
          <Node icon={ListTree} title="4. Router Intent & Menu" desc="Kenali menu (1-6) atau maksud pesan" tone="blue" testid="wf-node-router" />
          <Arrow />
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
            <Node icon={Info} title="Info Layanan" tone="slate" testid="wf-branch-layanan" />
            <Node icon={Stethoscope} title="Jadwal Dokter" tone="slate" testid="wf-branch-dokter" />
            <Node icon={CalendarPlus} title="Booking" tone={m.booking ? "orange" : "slate"} testid="wf-branch-booking" />
            <Node icon={Users} title="Cek Antrian" tone="slate" testid="wf-branch-antrian" />
            <Node icon={BrainCircuit} title="FAQ + RAG + LLM" tone={m.rag || m.faq ? "blue" : "slate"} testid="wf-branch-rag" />
            <Node icon={Headphones} title="Handoff Staf" tone={m.handoff ? "red" : "slate"} testid="wf-branch-staf" />
          </div>
          <Arrow />
          <Node icon={MessageSquareText} title="5. Balasan Terkirim ke Pasien" desc="Empatik, terstruktur, dengan citation bila dari knowledge base" tone="blue" testid="wf-node-reply" />
        </div>
      </div>
    </div>
  );
}
