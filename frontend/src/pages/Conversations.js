import React, { useEffect, useRef, useState } from "react";
import { Send, UserCog, Bot, User, Headphones, CheckCheck, X, Search } from "lucide-react";
import api from "../lib/api";
import { useWS } from "../context/WSContext";

const STATUS_BADGE = {
  active: "bg-emerald-50 text-emerald-600",
  handoff: "bg-orange-50 text-kf-orangeDark",
  closed: "bg-slate-100 text-slate-500",
};

function timefmt(iso) {
  try { return new Date(iso).toLocaleTimeString("id-ID", { hour: "2-digit", minute: "2-digit" }); }
  catch { return ""; }
}

export default function Conversations() {
  const [convs, setConvs] = useState([]);
  const [filter, setFilter] = useState("all");
  const [q, setQ] = useState("");
  const [sel, setSel] = useState(null);
  const [detail, setDetail] = useState(null);
  const [text, setText] = useState("");
  const [sending, setSending] = useState(false);
  const bottomRef = useRef(null);

  const loadList = () => api.get(`/conversations`, { params: { status: filter } }).then((r) => setConvs(r.data)).catch(() => {});
  useEffect(() => { loadList(); const t = setInterval(loadList, 6000); return () => clearInterval(t); }, [filter]);

  const loadDetail = (id) => api.get(`/conversations/${id}`).then((r) => setDetail(r.data)).catch(() => {});
  useEffect(() => {
    if (!sel) return;
    loadDetail(sel);
    const t = setInterval(() => loadDetail(sel), 4000);
    return () => clearInterval(t);
  }, [sel]);

  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior: "smooth" }); }, [detail?.messages?.length]);

  const ws = useWS();
  useEffect(() => {
    if (!ws) return;
    return ws.subscribe((d) => {
      loadList();
      if (d.conversation_id && d.conversation_id === sel) loadDetail(sel);
    });
  }, [ws, sel]);

  const send = async () => {
    if (!text.trim() || !sel) return;
    setSending(true);
    try { await api.post(`/conversations/${sel}/send`, { text }); setText(""); await loadDetail(sel); loadList(); }
    catch { /* noop */ } finally { setSending(false); }
  };

  const act = async (action) => { await api.post(`/conversations/${sel}/${action}`); await loadDetail(sel); loadList(); };

  const filtered = convs.filter((c) =>
    !q || (c.patient_name || "").toLowerCase().includes(q.toLowerCase()) || c.wa_jid.includes(q));

  const conv = detail?.conversation;

  return (
    <div className="grid h-[calc(100vh-7rem)] grid-cols-1 gap-4 lg:grid-cols-[360px_1fr]">
      {/* List */}
      <div className="card flex flex-col overflow-hidden">
        <div className="border-b border-slate-100 p-3">
          <div className="relative">
            <Search size={16} className="absolute left-3 top-3 text-slate-400" />
            <input className="input pl-9" placeholder="Cari pasien / nomor…" value={q} onChange={(e) => setQ(e.target.value)} data-testid="conv-search" />
          </div>
          <div className="mt-2 flex gap-1">
            {["all", "active", "handoff", "closed"].map((f) => (
              <button key={f} onClick={() => setFilter(f)} data-testid={`filter-${f}`}
                className={`flex-1 rounded-md py-1.5 text-xs font-semibold capitalize transition ${filter === f ? "bg-kf-blueLight text-kf-blueDark" : "text-slate-500 hover:bg-slate-50"}`}>
                {f === "all" ? "Semua" : f}
              </button>
            ))}
          </div>
        </div>
        <div className="flex-1 overflow-y-auto">
          {filtered.length === 0 ? (
            <p className="p-6 text-center text-sm text-slate-400">Belum ada percakapan</p>
          ) : filtered.map((c) => (
            <button key={c.id} onClick={() => setSel(c.id)} data-testid={`conv-item-${c.id}`}
              className={`flex w-full items-center gap-3 border-b border-slate-50 px-4 py-3 text-left transition hover:bg-slate-50 ${sel === c.id ? "bg-kf-blueLight/50" : ""}`}>
              <div className="grid h-10 w-10 shrink-0 place-items-center rounded-full bg-kf-blueLight text-sm font-bold text-kf-blueDark">
                {(c.patient_name || "P").charAt(0).toUpperCase()}
              </div>
              <div className="min-w-0 flex-1">
                <div className="flex items-center justify-between">
                  <p className="truncate text-sm font-bold text-kf-ink">{c.patient_name || c.wa_jid.split("@")[0]}</p>
                  {c.unread > 0 && <span className="ml-2 grid h-5 min-w-5 place-items-center rounded-full bg-kf-orange px-1 text-[10px] font-bold text-white">{c.unread}</span>}
                </div>
                <p className="truncate text-xs text-slate-400">{c.last_message}</p>
              </div>
              <span className={`badge ${STATUS_BADGE[c.status]}`}>{c.status}</span>
            </button>
          ))}
        </div>
      </div>

      {/* Chat */}
      <div className="card flex flex-col overflow-hidden">
        {!conv ? (
          <div className="flex h-full flex-col items-center justify-center text-slate-400">
            <Headphones size={48} className="mb-3 text-slate-200" />
            Pilih percakapan untuk melihat detail
          </div>
        ) : (
          <>
            <div className="flex items-center justify-between border-b border-slate-100 p-4">
              <div className="flex items-center gap-3">
                <div className="grid h-10 w-10 place-items-center rounded-full bg-kf-blueLight text-sm font-bold text-kf-blueDark">
                  {(conv.patient_name || "P").charAt(0).toUpperCase()}
                </div>
                <div>
                  <p className="font-bold text-kf-ink">{conv.patient_name || conv.wa_jid.split("@")[0]}</p>
                  <p className="text-xs text-slate-400">{conv.wa_jid.split("@")[0]} · <span className="capitalize">{conv.status}</span></p>
                </div>
              </div>
              <div className="flex gap-2">
                {conv.status !== "handoff" ? (
                  <button className="btn-ghost !py-2 !px-3" onClick={() => act("takeover")} data-testid="takeover-btn"><UserCog size={16} /> Ambil Alih</button>
                ) : (
                  <button className="btn-orange !py-2 !px-3" onClick={() => act("resume")} data-testid="resume-btn"><CheckCheck size={16} /> Selesai (Kembalikan ke AI)</button>
                )}
                {conv.status !== "closed" && <button className="btn-ghost !py-2 !px-3" onClick={() => act("close")} data-testid="close-btn"><X size={16} /> Tutup</button>}
              </div>
            </div>

            <div className="flex-1 space-y-3 overflow-y-auto bg-kf-panel p-4" data-testid="chat-window">
              {detail.messages.map((m) => {
                const isPatient = m.sender_type === "patient";
                return (
                  <div key={m.id} className={`flex ${isPatient ? "justify-start" : "justify-end"}`}>
                    <div className={`max-w-[75%] rounded-2xl px-4 py-2.5 text-sm shadow-card ${
                      isPatient ? "rounded-tl-sm bg-white text-kf-ink"
                      : m.sender_type === "ai" ? "rounded-tr-sm bg-kf-blue text-white"
                      : "rounded-tr-sm bg-kf-orange text-white"}`}>
                      <div className="mb-1 flex items-center gap-1.5 text-[10px] font-bold opacity-80">
                        {isPatient ? <><User size={11} /> Pasien</> : m.sender_type === "ai" ? <><Bot size={11} /> AI</> : <><Headphones size={11} /> Staf</>}
                      </div>
                      <p className="whitespace-pre-wrap break-words">{m.content}</p>
                      <p className={`mt-1 text-right text-[10px] ${isPatient ? "text-slate-400" : "text-white/70"}`}>{timefmt(m.created_at)}</p>
                    </div>
                  </div>
                );
              })}
              <div ref={bottomRef} />
            </div>

            <div className="border-t border-slate-100 p-3">
              {conv.status !== "handoff" && (
                <p className="mb-2 text-center text-xs text-slate-400">AI sedang menangani percakapan ini. Kirim pesan untuk mengambil alih.</p>
              )}
              <div className="flex items-center gap-2">
                <input className="input" placeholder="Ketik balasan sebagai staf…" value={text}
                  onChange={(e) => setText(e.target.value)} onKeyDown={(e) => e.key === "Enter" && send()} data-testid="chat-input" />
                <button className="btn-primary !px-4" onClick={send} disabled={sending} data-testid="chat-send-btn"><Send size={18} /></button>
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
