import React, { useEffect, useState } from "react";
import { Save, Plus, Trash2, Building2, Bot, Stethoscope, ListChecks, SlidersHorizontal, KeyRound } from "lucide-react";
import api from "../lib/api";

const MODELS = {
  openai: ["gpt-4o", "gpt-5.4", "gpt-4o-mini", "gpt-5.4-mini"],
  anthropic: ["claude-sonnet-4-6", "claude-haiku-4-5-20251001", "claude-opus-4-6"],
  gemini: ["gemini-3.1-pro-preview", "gemini-2.5-flash", "gemini-3-flash-preview"],
};

const TABS = [
  { id: "klinik", label: "Klinik", icon: Building2 },
  { id: "ai", label: "AI & Model", icon: Bot },
  { id: "layanan", label: "Layanan & Dokter", icon: Stethoscope },
  { id: "menu", label: "Menu & Handoff", icon: ListChecks },
  { id: "lanjutan", label: "Lanjutan", icon: SlidersHorizontal },
];

export default function Settings() {
  const [s, setS] = useState(null);
  const [tab, setTab] = useState("klinik");
  const [saved, setSaved] = useState(false);
  const [saving, setSaving] = useState(false);
  const [useOwnKey, setUseOwnKey] = useState(false);
  const [ownKey, setOwnKey] = useState("");

  useEffect(() => { api.get("/settings").then((r) => setS(r.data)).catch(() => {}); }, []);

  const save = async () => {
    setSaving(true); setSaved(false);
    const payload = { ...s };
    payload.ai = { ...s.ai };
    if (useOwnKey && ownKey) payload.ai.api_key = ownKey; else delete payload.ai.api_key;
    delete payload.ai.has_api_key;
    try {
      const r = await api.put("/settings", payload);
      setS(r.data); setSaved(true); setOwnKey(""); setUseOwnKey(false);
      setTimeout(() => setSaved(false), 2500);
    } catch { /* noop */ } finally { setSaving(false); }
  };

  if (!s) return <div className="text-slate-400">Memuat pengaturan…</div>;

  const setC = (k, v) => setS({ ...s, clinic: { ...s.clinic, [k]: v } });
  const setAI = (k, v) => setS({ ...s, ai: { ...s.ai, [k]: v } });
  const setBH = (k, v) => setS({ ...s, business_hours: { ...s.business_hours, [k]: v } });

  const listEdit = (field, blank) => ({
    add: () => setS({ ...s, [field]: [...(s[field] || []), blank] }),
    remove: (i) => setS({ ...s, [field]: s[field].filter((_, idx) => idx !== i) }),
    update: (i, k, v) => setS({ ...s, [field]: s[field].map((it, idx) => idx === i ? { ...it, [k]: v } : it) }),
  });
  const svc = listEdit("services", { name: "", type: "umum", price: 0 });
  const doc = listEdit("doctors", { name: "", specialty: "Dokter Umum", schedule: "" });

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex flex-wrap gap-1 rounded-lg bg-white p-1 shadow-card">
          {TABS.map((t) => (
            <button key={t.id} onClick={() => setTab(t.id)} data-testid={`settings-tab-${t.id}`}
              className={`flex items-center gap-1.5 rounded-md px-3 py-1.5 text-sm font-semibold transition ${tab === t.id ? "bg-kf-blueLight text-kf-blueDark" : "text-slate-500 hover:bg-slate-50"}`}>
              <t.icon size={16} /> {t.label}
            </button>
          ))}
        </div>
        <button className="btn-primary" onClick={save} disabled={saving} data-testid="settings-save-btn">
          <Save size={18} /> {saving ? "Menyimpan…" : saved ? "Tersimpan ✓" : "Simpan Perubahan"}
        </button>
      </div>

      <div className="card p-6">
        {tab === "klinik" && (
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2" data-testid="tab-klinik">
            <div className="sm:col-span-2"><label className="label">Nama Klinik</label><input className="input" value={s.clinic.name} onChange={(e) => setC("name", e.target.value)} data-testid="clinic-name" /></div>
            <div className="sm:col-span-2"><label className="label">Alamat</label><input className="input" value={s.clinic.address} onChange={(e) => setC("address", e.target.value)} data-testid="clinic-address" /></div>
            <div><label className="label">Telepon</label><input className="input" value={s.clinic.phone} onChange={(e) => setC("phone", e.target.value)} data-testid="clinic-phone" /></div>
            <div><label className="label">Jam Operasional</label><input className="input" value={s.clinic.hours} onChange={(e) => setC("hours", e.target.value)} data-testid="clinic-hours" /></div>
            <div className="sm:col-span-2"><label className="label">Deskripsi</label><textarea rows={3} className="input" value={s.clinic.description} onChange={(e) => setC("description", e.target.value)} /></div>
          </div>
        )}

        {tab === "ai" && (
          <div className="space-y-4" data-testid="tab-ai">
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
              <div>
                <label className="label">Provider AI</label>
                <select className="input" value={s.ai.provider} onChange={(e) => setAI("provider", e.target.value)} data-testid="ai-provider">
                  <option value="openai">OpenAI (GPT)</option>
                  <option value="anthropic">Anthropic (Claude)</option>
                  <option value="gemini">Google (Gemini)</option>
                </select>
              </div>
              <div>
                <label className="label">Model</label>
                <input list="models" className="input" value={s.ai.model} onChange={(e) => setAI("model", e.target.value)} data-testid="ai-model" />
                <datalist id="models">
                  {(MODELS[s.ai.provider] || []).map((mm) => <option key={mm} value={mm} />)}
                </datalist>
              </div>
            </div>
            <div className="rounded-lg bg-kf-blueLight/60 p-4">
              <label className="flex cursor-pointer items-center gap-2 text-sm font-semibold text-kf-blueDark">
                <input type="checkbox" checked={useOwnKey} onChange={(e) => setUseOwnKey(e.target.checked)} data-testid="ai-use-own-key" />
                <KeyRound size={16} /> Gunakan API Key sendiri (opsi custom)
              </label>
              <p className="mt-1 text-xs text-slate-500">Secara default menggunakan Emergent Universal Key. {s.ai.has_api_key ? "Saat ini: API Key custom aktif." : "Saat ini: Universal Key."}</p>
              {useOwnKey && <input className="input mt-2" placeholder="Masukkan API key provider Anda" value={ownKey} onChange={(e) => setOwnKey(e.target.value)} data-testid="ai-own-key" />}
            </div>
            <div>
              <label className="label">System Prompt (Kepribadian AI)</label>
              <textarea rows={6} className="input" placeholder="Kosongkan untuk menggunakan prompt empatik bawaan klinik" value={s.ai.system_prompt} onChange={(e) => setAI("system_prompt", e.target.value)} data-testid="ai-system-prompt" />
            </div>
          </div>
        )}

        {tab === "layanan" && (
          <div className="space-y-6" data-testid="tab-layanan">
            <div>
              <div className="mb-2 flex items-center justify-between"><h4 className="font-bold text-kf-ink">Daftar Layanan & Harga</h4><button className="btn-ghost !py-1.5" onClick={svc.add} data-testid="add-service"><Plus size={16} /> Tambah</button></div>
              <div className="space-y-2">
                {(s.services || []).map((it, i) => (
                  <div key={i} className="flex flex-wrap items-center gap-2" data-testid={`service-row-${i}`}>
                    <input className="input flex-1 min-w-[160px]" placeholder="Nama layanan" value={it.name} onChange={(e) => svc.update(i, "name", e.target.value)} />
                    <select className="input w-32" value={it.type} onChange={(e) => svc.update(i, "type", e.target.value)}>
                      <option value="umum">Umum</option><option value="lab">Lab</option><option value="farmasi">Farmasi</option><option value="vaksinasi">Vaksinasi</option>
                    </select>
                    <input type="number" className="input w-32" placeholder="Harga" value={it.price} onChange={(e) => svc.update(i, "price", Number(e.target.value))} />
                    <button className="rounded-md p-2 text-red-500 hover:bg-red-50" onClick={() => svc.remove(i)}><Trash2 size={16} /></button>
                  </div>
                ))}
              </div>
            </div>
            <div>
              <div className="mb-2 flex items-center justify-between"><h4 className="font-bold text-kf-ink">Jadwal Dokter</h4><button className="btn-ghost !py-1.5" onClick={doc.add} data-testid="add-doctor"><Plus size={16} /> Tambah</button></div>
              <div className="space-y-2">
                {(s.doctors || []).map((it, i) => (
                  <div key={i} className="flex flex-wrap items-center gap-2" data-testid={`doctor-row-${i}`}>
                    <input className="input flex-1 min-w-[140px]" placeholder="Nama dokter" value={it.name} onChange={(e) => doc.update(i, "name", e.target.value)} />
                    <input className="input w-40" placeholder="Spesialisasi" value={it.specialty} onChange={(e) => doc.update(i, "specialty", e.target.value)} />
                    <input className="input flex-1 min-w-[160px]" placeholder="Jadwal praktik" value={it.schedule} onChange={(e) => doc.update(i, "schedule", e.target.value)} />
                    <button className="rounded-md p-2 text-red-500 hover:bg-red-50" onClick={() => doc.remove(i)}><Trash2 size={16} /></button>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        {tab === "menu" && (
          <div className="space-y-6" data-testid="tab-menu">
            <div>
              <h4 className="mb-2 font-bold text-kf-ink">Label Menu Utama</h4>
              <div className="space-y-2">
                {(s.menu || []).map((it, i) => (
                  <div key={i} className="flex items-center gap-2">
                    <span className="grid h-9 w-9 shrink-0 place-items-center rounded-lg bg-kf-blueLight font-bold text-kf-blueDark">{it.key}</span>
                    <input className="input flex-1" value={it.label} onChange={(e) => setS({ ...s, menu: s.menu.map((mm, idx) => idx === i ? { ...mm, label: e.target.value } : mm) })} data-testid={`menu-label-${i}`} />
                  </div>
                ))}
              </div>
            </div>
            <div>
              <label className="label">Kata Kunci Handoff (pisahkan dengan koma)</label>
              <input className="input" value={(s.handoff_keywords || []).join(", ")} onChange={(e) => setS({ ...s, handoff_keywords: e.target.value.split(",").map((x) => x.trim()).filter(Boolean) })} data-testid="handoff-keywords" />
              <p className="mt-1 text-xs text-slate-400">Jika pasien mengetik salah satu kata ini, percakapan langsung dialihkan ke staf.</p>
            </div>
          </div>
        )}

        {tab === "lanjutan" && (
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2" data-testid="tab-lanjutan">
            <div><label className="label">Jam Buka (slot mulai)</label><input className="input" value={s.business_hours.start} onChange={(e) => setBH("start", e.target.value)} data-testid="bh-start" /></div>
            <div><label className="label">Jam Tutup (slot akhir)</label><input className="input" value={s.business_hours.end} onChange={(e) => setBH("end", e.target.value)} data-testid="bh-end" /></div>
            <div><label className="label">Durasi Slot (menit)</label><input type="number" className="input" value={s.business_hours.slot_minutes} onChange={(e) => setBH("slot_minutes", Number(e.target.value))} data-testid="bh-slot" /></div>
            <div><label className="label">Ambang Relevansi RAG (0-1)</label><input type="number" step="0.01" className="input" value={s.rag_relevant_threshold} onChange={(e) => setS({ ...s, rag_relevant_threshold: Number(e.target.value) })} data-testid="rag-threshold" /></div>
          </div>
        )}
      </div>
    </div>
  );
}
