# PRD — Web WhatsApp Agent AI · Klinik Kimia Farma Sepinggan

## Problem Statement
Bangun Web WhatsApp Agent AI untuk Klinik Kimia Farma Sepinggan (Balikpapan): asisten virtual empatik yang menjawab pertanyaan pasien, menjadwalkan janji temu, menjawab dari knowledge base (RAG), dan eskalasi ke staf (handoff) via WhatsApp. Sumber: PRD_WHATSAPP_AGENT_AI_KLINIK_KF_SEPINGGAN.docx.

## User Decisions (dari ask_human)
- Koneksi WhatsApp: **Baileys asli** (Node.js gateway, koneksi WhatsApp nyata seperti WhatsApp Web).
- AI: multi-provider (OpenAI/Anthropic/Gemini via Emergent Universal Key) + opsi API key custom, dikonfigurasi di Settings.
- Fitur: Chat/Menu/FAQ, Booking, RAG, Handoff — semua bisa di-toggle di pengaturan.
- Auth: JWT username + password.
- Tema: mengikuti kimiafarma (biru medis + aksen oranye).
- Workflow engine ala N8N agar AI menjawab rapi & terstruktur.

## Architecture
- **Backend**: FastAPI (port 8001), MongoDB. Orchestrator + workflow engine + AI (emergentintegrations) + RAG (TF-IDF sklearn) + auth (JWT) + dashboard API + WhatsApp webhook/proxy.
- **WhatsApp Gateway**: Node.js + Baileys (port 3001, supervisor `whatsapp-gateway`). QR + pairing code, session persist (useMultiFileAuthState), auto-reconnect, forwards inbound to backend webhook, sends replies via `/send`.
- **Frontend**: React + Tailwind (port 3000). Dashboard admin.
- Data model (MongoDB collections): users, settings(singleton), conversations, messages, appointments, knowledge_docs, knowledge_chunks, notifications.

## Implemented (05 Jun 2026)
- JWT auth + seeded admin (admin/admin123).
- Baileys gateway: /status, /connect, /pairing-code, /logout, /send; webhook to backend.
- Workflow engine: welcome/menu, keyword intent router, booking state machine, FAQ/RAG+LLM, sentiment escalation, handoff (keyword/negative/media), deterministic & orderly.
- RAG: upload .pdf/.docx/.txt/.md + manual text, chunking, TF-IDF retrieval, citation in prompt.
- Dashboard: stats (containment, trend, intent dist), Connection (QR/pairing UI), Conversations (live chat + takeover/resume/close), Appointments (CRUD + status), Knowledge base, Workflow visualizer + module toggles, Settings (clinic/AI/services/doctors/menu/advanced).
- Theme: Kimia Farma blue #0B6FB8 + orange #F58220, Plus Jakarta Sans, flat anti-slop UI.

## Implemented — Iteration 3 (05 Jun 2026)
- Node Kondisional (alur bertingkat): intent action "flow" dengan steps + options; tiap opsi bisa lanjut ke langkah lain (next_step) atau aksi terminal (message/link/booking_link/handoff/services/doctors/queue/booking). Contoh: tanya poli → cabang gigi → tanya darurat → handoff/booking. Editor visual di halaman Workflow (FlowEditor). Guard anti-loop 25 langkah.
- Booking eksternal: action "booking_link" + field clinic.booking_url di Settings; booking internal bisa dimatikan lalu arahkan pasien ke tautan booking milik klinik.
- Broadcast Promo: POST /api/broadcast (target all/active/handoff, throttle 0.25s), GET history & audience; halaman Broadcast di dashboard dengan preview jumlah penerima + riwayat.
- Real-time: WSContext (single WebSocket, subscribe registry) → panel Percakapan & daftar update seketika tanpa refresh; broadcast WS pada aksi staf (takeover/resume/close/send) + pesan masuk.
- Tested: 32/32 backend pytest + full frontend flows PASS.

## Backlog / Next
- P2: Broadcast via BackgroundTask + polling untuk audiens besar; schema validation (Pydantic) untuk settings/workflow PUT.
- P2: RBAC multi-role staff; audit log; retensi data 90 hari.
- P2: Embedding-based RAG (vector DB) upgrade dari TF-IDF.

## Implemented — Iteration 2 (05 Jun 2026)
- Knowledge Base auto-seed: BPJS, Daftar Layanan & Tarif, SOP Pendaftaran, Jam & Lokasi.
- Flexible Workflow engine (data-driven from settings.workflow.intents): editable intents/nodes (name, action, menu_key, keywords, examples, response, enabled, order), toggle AI semantic router, fallback (rag/handoff), welcome_extra. Full editor UI di halaman Workflow.
- Smart & natural routing: menu number → keyword → LLM semantic router (paham bahasa bebas) → fallback RAG/LLM; empathetic system prompt.
- Live notifications: WebSocket /api/ws (JWT), broadcast on inbound/handoff; frontend toast + beep sound + bell badge.
- Auto H-1 appointment reminders: background loop tiap 15 menit + manual "Kirim Pengingat H-1" (POST /api/appointments/send-reminders); toggle di Settings > Lanjutan.
- Tested: 27/27 backend pytest + full frontend flows PASS.

## Notes
- Real WhatsApp pairing needs a physical phone scan (not automatable).
- MongoDB used instead of PostgreSQL/pgvector per platform env constraint.
