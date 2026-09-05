import React, { useEffect, useRef, useState } from "react";
import { Upload, FileText, Trash2, Plus, BookOpen } from "lucide-react";
import api from "../lib/api";

export default function Knowledge() {
  const [docs, setDocs] = useState([]);
  const [showText, setShowText] = useState(false);
  const [tdoc, setTdoc] = useState({ source: "", content: "" });
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState("");
  const fileRef = useRef();

  const load = () => api.get("/knowledge").then((r) => setDocs(r.data)).catch(() => {});
  useEffect(() => { load(); }, []);

  const upload = async (e) => {
    const file = e.target.files[0];
    if (!file) return;
    setBusy(true); setMsg("");
    const fd = new FormData();
    fd.append("file", file);
    try {
      await api.post("/knowledge/upload", fd, { headers: { "Content-Type": "multipart/form-data" } });
      setMsg(`"${file.name}" berhasil diproses.`); load();
    } catch (e) { setMsg(e.response?.data?.detail || "Gagal mengunggah dokumen."); }
    finally { setBusy(false); if (fileRef.current) fileRef.current.value = ""; }
  };

  const addText = async (e) => {
    e.preventDefault();
    setBusy(true);
    try { await api.post("/knowledge/text", tdoc); setShowText(false); setTdoc({ source: "", content: "" }); load(); }
    catch { setMsg("Gagal menyimpan."); } finally { setBusy(false); }
  };

  const del = async (id) => { await api.delete(`/knowledge/${id}`); load(); };

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <div className="card flex flex-col items-center justify-center gap-2 p-6 text-center">
          <div className="grid h-12 w-12 place-items-center rounded-xl bg-kf-blueLight text-kf-blue"><Upload size={22} /></div>
          <p className="font-bold text-kf-ink">Unggah Dokumen</p>
          <p className="text-xs text-slate-400">SOP, daftar layanan, FAQ (.pdf, .docx, .txt, .md)</p>
          <input ref={fileRef} type="file" accept=".pdf,.docx,.txt,.md" className="hidden" onChange={upload} data-testid="kb-file-input" />
          <button className="btn-primary mt-2" onClick={() => fileRef.current?.click()} disabled={busy} data-testid="kb-upload-btn">
            <Upload size={16} /> {busy ? "Memproses…" : "Pilih File"}
          </button>
        </div>
        <div className="card flex flex-col items-center justify-center gap-2 p-6 text-center">
          <div className="grid h-12 w-12 place-items-center rounded-xl bg-orange-50 text-kf-orange"><Plus size={22} /></div>
          <p className="font-bold text-kf-ink">Tambah Teks Manual</p>
          <p className="text-xs text-slate-400">Ketik langsung informasi ke knowledge base</p>
          <button className="btn-orange mt-2" onClick={() => setShowText(true)} data-testid="kb-add-text-btn"><Plus size={16} /> Tulis Teks</button>
        </div>
      </div>

      {msg && <div className="rounded-lg bg-kf-blueLight px-4 py-3 text-sm font-medium text-kf-blueDark" data-testid="kb-msg">{msg}</div>}

      <div className="card overflow-hidden">
        <div className="border-b border-slate-100 px-4 py-3 font-bold text-kf-ink">Dokumen Tersimpan ({docs.length})</div>
        {docs.length === 0 ? (
          <p className="p-10 text-center text-sm text-slate-400"><BookOpen className="mx-auto mb-2 text-slate-200" size={40} />Belum ada dokumen. Unggah SOP klinik agar AI dapat menjawab akurat.</p>
        ) : docs.map((d) => (
          <div key={d.id} className="flex items-center gap-3 border-b border-slate-50 px-4 py-3" data-testid={`kb-doc-${d.id}`}>
            <FileText className="text-kf-blue" size={20} />
            <div className="flex-1 min-w-0">
              <p className="truncate font-semibold text-kf-ink">{d.source}</p>
              <p className="text-xs text-slate-400">{d.chunk_count} chunk · {d.chars} karakter</p>
            </div>
            <button onClick={() => del(d.id)} className="rounded-md p-2 text-red-500 hover:bg-red-50" data-testid={`kb-del-${d.id}`}><Trash2 size={16} /></button>
          </div>
        ))}
      </div>

      {showText && (
        <div className="fixed inset-0 z-50 grid place-items-center bg-black/40 p-4" onClick={() => setShowText(false)}>
          <form onClick={(e) => e.stopPropagation()} onSubmit={addText} className="w-full max-w-lg rounded-xl bg-white p-6 shadow-xl" data-testid="kb-text-form">
            <h3 className="mb-4 text-lg font-bold text-kf-ink">Tambah Teks ke Knowledge Base</h3>
            <div><label className="label">Judul / Sumber</label><input required className="input" placeholder="mis. SOP Pendaftaran BPJS" value={tdoc.source} onChange={(e) => setTdoc({ ...tdoc, source: e.target.value })} data-testid="kb-text-source" /></div>
            <div className="mt-3"><label className="label">Isi</label><textarea required rows={8} className="input" value={tdoc.content} onChange={(e) => setTdoc({ ...tdoc, content: e.target.value })} data-testid="kb-text-content" /></div>
            <div className="mt-5 flex gap-2">
              <button type="button" className="btn-ghost flex-1" onClick={() => setShowText(false)}>Batal</button>
              <button type="submit" className="btn-primary flex-1" disabled={busy} data-testid="kb-text-submit">Simpan</button>
            </div>
          </form>
        </div>
      )}
    </div>
  );
}
