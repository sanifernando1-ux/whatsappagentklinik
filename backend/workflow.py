import uuid
from datetime import datetime, timezone, date, timedelta
from database import db
from rag import retrieve
from llm_service import generate_reply


def _keyword_intent(t, modules):
    """Deterministic keyword routing. Falls back to None (-> RAG/LLM answer)."""
    booking_kw = ["janji", "booking", "buat janji", "daftar berobat", "jadwalkan", "appointment", "reservasi", "mau berobat"]
    doctor_kw = ["jadwal dokter", "dokter siapa", "jadwal praktik", "dokter praktek", "dokter yang", "praktik dokter"]
    service_kw = ["jam buka", "jam operasional", "jam berapa", "alamat", "lokasi", "dimana klinik", "harga", "biaya", "tarif", "berapa biaya"]
    queue_kw = ["antrian", "antre", "ngantri", "nomor antrian"]
    if modules.get("booking", True) and any(k in t for k in booking_kw):
        return "booking"
    if any(k in t for k in doctor_kw):
        return "jadwal_dokter"
    if any(k in t for k in service_kw):
        return "layanan"
    if any(k in t for k in queue_kw):
        return "antrian"
    return None

WELCOME_KEYWORDS = {"halo", "hai", "hi", "menu", "mulai", "start", "assalamualaikum", "p"}
SERVICE_MAP = {"1": "umum", "2": "lab", "3": "farmasi", "4": "vaksinasi",
               "umum": "umum", "lab": "lab", "laboratorium": "lab",
               "farmasi": "farmasi", "obat": "farmasi", "vaksin": "vaksinasi", "vaksinasi": "vaksinasi"}
SERVICE_LABEL = {"umum": "Konsultasi Umum", "lab": "Pemeriksaan Laboratorium",
                 "farmasi": "Layanan Farmasi", "vaksinasi": "Vaksinasi"}
CONFIRM_YES = {"ya", "iya", "yes", "benar", "ok", "oke", "betul", "setuju", "y"}
CONFIRM_NO = {"tidak", "batal", "no", "nggak", "gak", "salah", "cancel", "n"}


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def build_system_prompt(settings, rag_context=""):
    clinic = settings.get("clinic", {})
    base = settings.get("ai", {}).get("system_prompt") or (
        "Anda adalah asisten digital resmi Klinik Kimia Farma Sepinggan. "
        "Jawablah dengan ramah, empatik, profesional, dan singkat dalam Bahasa Indonesia. "
        "Jika pasien menyampaikan keluhan atau kecemasan, tunjukkan empati terlebih dahulu. "
        "JANGAN memberi diagnosis medis atau meresepkan obat — arahkan ke dokter untuk hal medis. "
        "Jika Anda tidak yakin dengan jawaban, katakan Anda akan menghubungkan pasien dengan staf klinik."
    )
    info = (
        f"\n\nINFORMASI KLINIK:\n"
        f"Nama: {clinic.get('name', 'Klinik Kimia Farma Sepinggan')}\n"
        f"Alamat: {clinic.get('address', '-')}\n"
        f"Telepon: {clinic.get('phone', '-')}\n"
        f"Jam Operasional: {clinic.get('hours', '-')}\n"
    )
    ctx = f"\n\nKONTEKS PENGETAHUAN (gunakan bila relevan, sebutkan bahwa info dari SOP/knowledge base klinik):\n{rag_context}" if rag_context else ""
    return base + info + ctx


def parse_date(text):
    t = text.lower().strip()
    today = date.today()
    if "hari ini" in t or t == "sekarang":
        return today
    if "besok" in t:
        return today + timedelta(days=1)
    if "lusa" in t:
        return today + timedelta(days=2)
    for sep in ["-", "/", " "]:
        parts = [p for p in t.replace(".", sep).split(sep) if p.strip().isdigit()]
        if len(parts) >= 3:
            try:
                a, b, c = int(parts[0]), int(parts[1]), int(parts[2])
                if a > 31:  # yyyy-mm-dd
                    return date(a, b, c)
                year = c if c > 999 else (2000 + c if c < 100 else today.year)
                return date(year, b, a)  # dd-mm-yyyy
            except Exception:
                pass
        if len(parts) == 2:
            try:
                return date(today.year, int(parts[1]), int(parts[0]))
            except Exception:
                pass
    return None


async def available_slots(settings, on_date):
    bh = settings.get("business_hours", {})
    start = bh.get("start", "08:00")
    end = bh.get("end", "20:00")
    step = int(bh.get("slot_minutes", 60))
    sh, sm = map(int, start.split(":"))
    eh, em = map(int, end.split(":"))
    cur = datetime(2000, 1, 1, sh, sm)
    stop = datetime(2000, 1, 1, eh, em)
    slots = []
    while cur < stop:
        slots.append(cur.strftime("%H:%M"))
        cur += timedelta(minutes=step)
    booked = await db.appointments.find({
        "appointment_date": on_date.isoformat(),
        "status": {"$in": ["pending", "confirmed"]},
    }).to_list(200)
    taken = {b["appointment_time"] for b in booked}
    return [s for s in slots if s not in taken][:8]


def detect_sentiment(text, settings):
    negatives = settings.get("negative_words", [
        "marah", "kecewa", "buruk", "jelek", "parah", "komplain", "keluhan",
        "lama banget", "lambat", "kesal", "kesel", "menyebalkan", "tidak puas",
        "gagal", "error terus", "nggak becus", "payah", "bohong", "nipu"])
    tl = text.lower()
    hit = any(n in tl for n in negatives)
    return -0.7 if hit else 0.0


def menu_text(settings):
    clinic = settings.get("clinic", {})
    lines = [f"🏥 *Selamat datang di {clinic.get('name', 'Klinik Kimia Farma Sepinggan')}!*",
             "Saya asisten digital yang siap membantu Anda. Silakan pilih layanan:", ""]
    for m in settings.get("menu", []):
        lines.append(f"{m['key']}️⃣ {m['label']}")
    lines.append("")
    lines.append("_Ketik nomor menu atau tulis pertanyaan Anda langsung._")
    return "\n".join(lines)


async def services_text(settings):
    services = settings.get("services", [])
    clinic = settings.get("clinic", {})
    lines = ["*Layanan & Informasi Klinik*", ""]
    lines.append(f"🕐 Jam Operasional: {clinic.get('hours', '-')}")
    lines.append(f"📍 Alamat: {clinic.get('address', '-')}")
    lines.append(f"☎️ Telepon: {clinic.get('phone', '-')}")
    if services:
        lines.append("")
        lines.append("*Daftar Layanan:*")
        for s in services:
            price = f" — Rp{s['price']:,}".replace(",", ".") if s.get("price") else ""
            lines.append(f"• {s.get('name')}{price}")
    lines.append("")
    lines.append("_Ketik MENU untuk kembali ke menu utama._")
    return "\n".join(lines)


def doctors_text(settings):
    doctors = settings.get("doctors", [])
    if not doctors:
        return "Mohon maaf, jadwal dokter belum tersedia. Silakan hubungi staf klinik untuk informasi terbaru.\n\n_Ketik MENU untuk kembali._"
    lines = ["*Jadwal Dokter*", ""]
    for d in doctors:
        lines.append(f"👨‍⚕️ {d.get('name')} ({d.get('specialty', 'Umum')})")
        lines.append(f"   🗓️ {d.get('schedule', '-')}")
    lines.append("")
    lines.append("_Ketik 3 untuk membuat janji temu, atau MENU untuk kembali._")
    return "\n".join(lines)


async def queue_text(settings):
    today = date.today().isoformat()
    count = await db.appointments.count_documents({
        "appointment_date": today, "status": {"$in": ["pending", "confirmed"]}})
    return (f"*Status Antrian Hari Ini*\n\nSaat ini terdapat *{count}* janji temu terjadwal hari ini. "
            "Untuk estimasi antrian real-time, staf kami akan membantu Anda saat tiba di klinik.\n\n"
            "_Ketik MENU untuk kembali._")


async def start_booking(settings):
    flow = {"name": "booking", "step": "service", "data": {}}
    msg = ("*Buat Janji Temu* 📅\n\nSilakan pilih jenis layanan:\n"
           "1. Konsultasi Umum\n2. Pemeriksaan Lab\n3. Layanan Farmasi\n4. Vaksinasi\n\n"
           "_Ketik nomor atau nama layanan._")
    return flow, msg


async def continue_booking(conv, flow, text, settings):
    """Returns (replies:list, new_flow, appointment_or_None)."""
    step = flow["step"]
    data = flow.get("data", {})
    t = text.lower().strip()

    if t in CONFIRM_NO and step != "confirm":
        return ["Baik, proses janji temu dibatalkan. Ketik MENU untuk kembali. 😊"], None, None

    if step == "service":
        svc = SERVICE_MAP.get(t)
        if not svc:
            return ["Maaf, pilihan tidak dikenali. Ketik 1-4 atau nama layanan (umum/lab/farmasi/vaksinasi)."], flow, None
        data["service_type"] = svc
        flow["step"] = "date"
        flow["data"] = data
        return [f"Anda memilih *{SERVICE_LABEL[svc]}*.\n\nUntuk tanggal berapa? (contoh: *besok* atau *12-06-2026*)"], flow, None

    if step == "date":
        d = parse_date(text)
        if not d or d < date.today():
            return ["Format tanggal belum tepat atau sudah lewat. Contoh: *besok*, *lusa*, atau *15-06-2026*."], flow, None
        slots = await available_slots(settings, d)
        if not slots:
            return [f"Mohon maaf, tidak ada slot tersedia pada {d.strftime('%d-%m-%Y')}. Silakan pilih tanggal lain."], flow, None
        data["appointment_date"] = d.isoformat()
        flow["step"] = "time"
        flow["data"] = data
        slot_lines = "\n".join([f"{i+1}. {s}" for i, s in enumerate(slots)])
        flow["data"]["_slots"] = slots
        return [f"Slot tersedia pada *{d.strftime('%d-%m-%Y')}*:\n{slot_lines}\n\n_Ketik nomor atau jam (contoh: 09:00)._"], flow, None

    if step == "time":
        slots = data.get("_slots", [])
        chosen = None
        if t.isdigit() and 1 <= int(t) <= len(slots):
            chosen = slots[int(t) - 1]
        else:
            for s in slots:
                if s in text or s.replace(":", ".") in text or s.replace(":", "") in text.replace(":", "").replace(".", ""):
                    chosen = s
                    break
        if not chosen:
            return ["Maaf, jam tidak dikenali. Ketik nomor slot atau jam persis seperti daftar."], flow, None
        data["appointment_time"] = chosen
        if conv.get("patient_name"):
            data["patient_name"] = conv["patient_name"]
            flow["step"] = "confirm"
            flow["data"] = data
            return [_confirm_text(data, settings)], flow, None
        flow["step"] = "name"
        flow["data"] = data
        return ["Atas nama siapa janji temu ini? Mohon ketik nama lengkap pasien."], flow, None

    if step == "name":
        data["patient_name"] = text.strip().title()
        flow["step"] = "confirm"
        flow["data"] = data
        return [_confirm_text(data, settings)], flow, None

    if step == "confirm":
        if t in CONFIRM_YES:
            appt = {
                "id": str(uuid.uuid4()),
                "conversation_id": conv["id"],
                "patient_name": data.get("patient_name") or conv.get("patient_name") or "-",
                "patient_phone": conv["wa_jid"].split("@")[0],
                "service_type": data["service_type"],
                "doctor_id": None,
                "appointment_date": data["appointment_date"],
                "appointment_time": data["appointment_time"],
                "status": "confirmed",
                "reminder_sent": False,
                "created_at": now_iso(),
            }
            await db.appointments.insert_one(dict(appt))
            d = datetime.fromisoformat(data["appointment_date"]).strftime("%d-%m-%Y")
            msg = (f"✅ *Janji temu Anda telah dikonfirmasi!*\n\n"
                   f"👤 Pasien: {appt['patient_name']}\n"
                   f"🩺 Layanan: {SERVICE_LABEL[appt['service_type']]}\n"
                   f"🗓️ Tanggal: {d}\n⏰ Jam: {appt['appointment_time']}\n\n"
                   f"Kami akan mengirimkan pengingat H-1. Mohon datang 15 menit lebih awal. Terima kasih! 🙏\n\n"
                   f"_Ketik MENU untuk layanan lain._")
            return [msg], None, appt
        if t in CONFIRM_NO:
            return ["Baik, janji temu dibatalkan. Ketik MENU untuk kembali. 😊"], None, None
        return ["Mohon konfirmasi dengan mengetik *YA* untuk menyimpan atau *TIDAK* untuk membatalkan."], flow, None

    return ["Ketik MENU untuk memulai kembali."], None, None


def _confirm_text(data, settings):
    d = datetime.fromisoformat(data["appointment_date"]).strftime("%d-%m-%Y")
    return (f"Mohon konfirmasi data janji temu berikut:\n\n"
            f"👤 Pasien: {data.get('patient_name')}\n"
            f"🩺 Layanan: {SERVICE_LABEL[data['service_type']]}\n"
            f"🗓️ Tanggal: {d}\n⏰ Jam: {data['appointment_time']}\n\n"
            f"Ketik *YA* untuk konfirmasi atau *TIDAK* untuk membatalkan.")


async def rag_answer(conv, text, settings):
    results, top = await retrieve(text)
    threshold = settings.get("rag_relevant_threshold", 0.08)
    context = "\n\n".join([f"[{r['source']}] {r['text']}" for r in results if r["score"] >= threshold]) if settings.get("modules", {}).get("rag", True) else ""
    history = await recent_history(conv)
    sys = build_system_prompt(settings, context)
    prompt = f"{history}\nPasien: {text}\nAsisten:"
    try:
        reply = await generate_reply(sys, prompt, conv["id"], settings)
    except Exception:
        reply = ("Mohon maaf, sedang terjadi gangguan teknis pada layanan AI. "
                 "Silakan coba lagi sebentar lagi atau ketik *6* untuk terhubung dengan staf klinik.")
    return reply, top


async def recent_history(conv, limit=8):
    msgs = await db.messages.find({"conversation_id": conv["id"]}).sort("created_at", -1).to_list(limit)
    msgs = list(reversed(msgs))
    lines = []
    for m in msgs:
        who = {"patient": "Pasien", "ai": "Asisten", "agent": "Staf"}.get(m["sender_type"], "?")
        lines.append(f"{who}: {m['content']}")
    return "Riwayat percakapan:\n" + "\n".join(lines) if lines else ""


async def handle_incoming(conv, text, msg_type, settings):
    """Core workflow engine. Returns dict of replies + metadata + side-effect flags."""
    modules = settings.get("modules", {})
    result = {"replies": [], "handoff": False, "intent": None, "confidence": None,
              "sentiment": 0.0, "flow": conv.get("flow"), "appointment": None, "resolved_flow": False}

    # If a human agent is handling, AI stays silent.
    if conv.get("status") == "handoff" and conv.get("ai_paused"):
        return result

    # Non-text media the AI cannot process -> handoff.
    if msg_type != "text":
        if modules.get("handoff", True):
            result["handoff"] = True
            result["replies"] = ["Saya menerima lampiran media dari Anda. Mohon tunggu, saya hubungkan dengan staf klinik untuk membantu. 🙏"]
            return result
        result["replies"] = ["Mohon maaf, saya belum dapat memproses lampiran. Silakan kirim dalam bentuk teks."]
        return result

    t = text.lower().strip()
    result["sentiment"] = detect_sentiment(text, settings)

    # Explicit handoff keywords
    handoff_kw = settings.get("handoff_keywords", ["staf", "admin", "operator", "manusia", "orang", "cs", "customer service"])
    if modules.get("handoff", True) and (any(k in t for k in handoff_kw) or t == "6"):
        result["handoff"] = True
        result["replies"] = ["Baik, saya akan menghubungkan Anda dengan staf klinik kami. Mohon tunggu sebentar. 🙏"]
        return result

    # Sentiment based escalation (2+ negative in a row)
    if modules.get("handoff", True) and result["sentiment"] < 0:
        streak = conv.get("negative_streak", 0) + 1
        result["negative_streak"] = streak
        if streak >= 2:
            result["handoff"] = True
            result["replies"] = ["Saya turut prihatin atas ketidaknyamanan Anda. 🙏 Izinkan saya menghubungkan Anda dengan staf klinik agar dapat dibantu lebih baik."]
            return result
    else:
        result["negative_streak"] = 0

    # Continue an active booking flow
    flow = conv.get("flow")
    if flow and flow.get("name") == "booking" and modules.get("booking", True):
        if t == "menu":
            result["flow"] = None
            result["resolved_flow"] = True
            result["replies"] = [menu_text(settings)]
            return result
        replies, new_flow, appt = await continue_booking(conv, flow, text, settings)
        result["replies"] = replies
        result["flow"] = new_flow
        result["resolved_flow"] = new_flow is None
        result["appointment"] = appt
        result["intent"] = "booking"
        return result

    # Welcome / menu
    is_first = await db.messages.count_documents({"conversation_id": conv["id"], "sender_type": "patient"}) <= 1
    if t in WELCOME_KEYWORDS or is_first:
        result["replies"] = [menu_text(settings)]
        result["intent"] = "welcome"
        return result

    # Menu number routing (deterministic when user types a menu digit)
    menu_map = {m["key"]: m.get("intent") for m in settings.get("menu", [])}
    intent = menu_map.get(t) if t in menu_map else _keyword_intent(t, modules)
    result["intent"] = intent

    if intent == "layanan":
        result["replies"] = [await services_text(settings)]
        return result
    if intent == "jadwal_dokter":
        result["replies"] = [doctors_text(settings)]
        return result
    if intent == "antrian":
        result["replies"] = [await queue_text(settings)]
        return result
    if intent == "booking" and modules.get("booking", True):
        new_flow, msg = await start_booking(settings)
        result["flow"] = new_flow
        result["replies"] = [msg]
        return result
    if intent == "staf" and modules.get("handoff", True):
        result["handoff"] = True
        result["replies"] = ["Baik, saya hubungkan Anda dengan staf klinik. Mohon tunggu sebentar. 🙏"]
        return result

    # FAQ / general -> RAG + LLM
    if modules.get("faq", True) or modules.get("rag", True):
        reply, top = await rag_answer(conv, text, settings)
        result["confidence"] = top
        result["replies"] = [reply]
        return result

    result["replies"] = ["Maaf, saya belum memahami pertanyaan Anda. Ketik *MENU* untuk melihat pilihan layanan, atau *6* untuk staf klinik."]
    return result
