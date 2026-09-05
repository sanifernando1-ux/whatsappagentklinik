import uuid
from datetime import datetime, timezone, date, timedelta
from database import db
from rag import retrieve
from llm_service import generate_reply

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


def _intents(settings):
    return [i for i in settings.get("workflow", {}).get("intents", []) if i.get("enabled", True)]


def build_system_prompt(settings, rag_context=""):
    clinic = settings.get("clinic", {})
    base = settings.get("ai", {}).get("system_prompt") or (
        "Anda adalah asisten digital resmi Klinik Kimia Farma Sepinggan yang ramah, empatik, cerdas, dan natural. "
        "Berpikirlah dengan rapi: pahami maksud pasien, pertimbangkan konteks percakapan, lalu jawab singkat, jelas, dan hangat dalam Bahasa Indonesia. "
        "Tunjukkan empati saat pasien cemas atau mengeluh. Jangan kaku atau seperti robot. "
        "Jika pertanyaan ambigu, ajukan satu pertanyaan klarifikasi yang sopan. "
        "JANGAN memberi diagnosis medis pasti atau meresepkan obat — untuk hal medis arahkan ke dokter. "
        "Jika informasi tidak ada pada konteks/pengetahuan klinik dan Anda tidak yakin, akui dengan jujur dan tawarkan menghubungkan ke staf klinik."
    )
    info = (
        f"\n\nINFORMASI KLINIK:\n"
        f"Nama: {clinic.get('name', 'Klinik Kimia Farma Sepinggan')}\n"
        f"Alamat: {clinic.get('address', '-')}\n"
        f"Telepon: {clinic.get('phone', '-')}\n"
        f"Jam Operasional: {clinic.get('hours', '-')}\n"
    )
    ctx = (f"\n\nKONTEKS PENGETAHUAN KLINIK (gunakan bila relevan, sampaikan seolah info resmi klinik):\n{rag_context}"
           if rag_context else "")
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
                if a > 31:
                    return date(a, b, c)
                year = c if c > 999 else (2000 + c if c < 100 else today.year)
                return date(year, b, a)
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
    negatives = settings.get("negative_words", [])
    tl = text.lower()
    return -0.7 if any(n in tl for n in negatives) else 0.0


def menu_text(settings):
    clinic = settings.get("clinic", {})
    lines = [f"🏥 *Selamat datang di {clinic.get('name', 'Klinik Kimia Farma Sepinggan')}!*",
             "Saya asisten digital yang siap membantu Anda. Silakan pilih layanan:", ""]
    items = sorted([i for i in _intents(settings) if i.get("menu_key")], key=lambda x: x["menu_key"])
    for m in items:
        lines.append(f"{m['menu_key']}️⃣ {m['name']}")
    extra = settings.get("workflow", {}).get("welcome_extra")
    lines.append("")
    if extra:
        lines.append(extra)
        lines.append("")
    lines.append("_Ketik nomor menu atau tulis pertanyaan Anda langsung._")
    return "\n".join(lines)


async def services_text(settings):
    services = settings.get("services", [])
    clinic = settings.get("clinic", {})
    lines = ["*Layanan & Informasi Klinik*", "",
             f"🕐 Jam Operasional: {clinic.get('hours', '-')}",
             f"📍 Alamat: {clinic.get('address', '-')}",
             f"☎️ Telepon: {clinic.get('phone', '-')}"]
    if services:
        lines += ["", "*Daftar Layanan:*"]
        for s in services:
            price = f" — Rp{s['price']:,}".replace(",", ".") if s.get("price") else ""
            lines.append(f"• {s.get('name')}{price}")
    lines += ["", "_Ketik MENU untuk kembali ke menu utama._"]
    return "\n".join(lines)


def doctors_text(settings):
    doctors = settings.get("doctors", [])
    if not doctors:
        return "Mohon maaf, jadwal dokter belum tersedia. Silakan hubungi staf klinik.\n\n_Ketik MENU untuk kembali._"
    lines = ["*Jadwal Dokter*", ""]
    for d in doctors:
        lines.append(f"👨‍⚕️ {d.get('name')} ({d.get('specialty', 'Umum')})")
        lines.append(f"   🗓️ {d.get('schedule', '-')}")
    lines += ["", "_Ketik 3 untuk membuat janji temu, atau MENU untuk kembali._"]
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
           "1. Konsultasi Umum\n2. Pemeriksaan Lab\n3. Layanan Farmasi\n4. Vaksinasi\n\n_Ketik nomor atau nama layanan._")
    return flow, msg


async def continue_booking(conv, flow, text, settings):
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
        flow.update(step="date", data=data)
        return [f"Anda memilih *{SERVICE_LABEL[svc]}*.\n\nUntuk tanggal berapa? (contoh: *besok* atau *12-06-2026*)"], flow, None

    if step == "date":
        d = parse_date(text)
        if not d or d < date.today():
            return ["Format tanggal belum tepat atau sudah lewat. Contoh: *besok*, *lusa*, atau *15-06-2026*."], flow, None
        slots = await available_slots(settings, d)
        if not slots:
            return [f"Mohon maaf, tidak ada slot tersedia pada {d.strftime('%d-%m-%Y')}. Silakan pilih tanggal lain."], flow, None
        data["appointment_date"] = d.isoformat()
        data["_slots"] = slots
        flow.update(step="time", data=data)
        slot_lines = "\n".join([f"{i+1}. {s}" for i, s in enumerate(slots)])
        return [f"Slot tersedia pada *{d.strftime('%d-%m-%Y')}*:\n{slot_lines}\n\n_Ketik nomor atau jam (contoh: 09:00)._"], flow, None

    if step == "time":
        slots = data.get("_slots", [])
        chosen = None
        if t.isdigit() and 1 <= int(t) <= len(slots):
            chosen = slots[int(t) - 1]
        else:
            for s in slots:
                if s in text or s.replace(":", ".") in text:
                    chosen = s
                    break
        if not chosen:
            return ["Maaf, jam tidak dikenali. Ketik nomor slot atau jam persis seperti daftar."], flow, None
        data["appointment_time"] = chosen
        if conv.get("patient_name"):
            data["patient_name"] = conv["patient_name"]
            flow.update(step="confirm", data=data)
            return [_confirm_text(data)], flow, None
        flow.update(step="name", data=data)
        return ["Atas nama siapa janji temu ini? Mohon ketik nama lengkap pasien."], flow, None

    if step == "name":
        data["patient_name"] = text.strip().title()
        flow.update(step="confirm", data=data)
        return [_confirm_text(data)], flow, None

    if step == "confirm":
        if t in CONFIRM_YES:
            appt = {
                "id": str(uuid.uuid4()), "conversation_id": conv["id"],
                "patient_name": data.get("patient_name") or conv.get("patient_name") or "-",
                "patient_phone": conv["wa_jid"].split("@")[0],
                "service_type": data["service_type"], "doctor_id": None,
                "appointment_date": data["appointment_date"], "appointment_time": data["appointment_time"],
                "status": "confirmed", "reminder_sent": False, "created_at": now_iso(),
            }
            await db.appointments.insert_one(dict(appt))
            d = datetime.fromisoformat(data["appointment_date"]).strftime("%d-%m-%Y")
            msg = (f"✅ *Janji temu Anda telah dikonfirmasi!*\n\n👤 Pasien: {appt['patient_name']}\n"
                   f"🩺 Layanan: {SERVICE_LABEL[appt['service_type']]}\n🗓️ Tanggal: {d}\n⏰ Jam: {appt['appointment_time']}\n\n"
                   f"Kami akan mengirimkan pengingat H-1. Mohon datang 15 menit lebih awal. Terima kasih! 🙏\n\n_Ketik MENU untuk layanan lain._")
            return [msg], None, appt
        if t in CONFIRM_NO:
            return ["Baik, janji temu dibatalkan. Ketik MENU untuk kembali. 😊"], None, None
        return ["Mohon konfirmasi dengan mengetik *YA* untuk menyimpan atau *TIDAK* untuk membatalkan."], flow, None

    return ["Ketik MENU untuk memulai kembali."], None, None


def _confirm_text(data):
    d = datetime.fromisoformat(data["appointment_date"]).strftime("%d-%m-%Y")
    return (f"Mohon konfirmasi data janji temu berikut:\n\n👤 Pasien: {data.get('patient_name')}\n"
            f"🩺 Layanan: {SERVICE_LABEL[data['service_type']]}\n🗓️ Tanggal: {d}\n⏰ Jam: {data['appointment_time']}\n\n"
            f"Ketik *YA* untuk konfirmasi atau *TIDAK* untuk membatalkan.")


async def recent_history(conv, limit=8):
    msgs = await db.messages.find({"conversation_id": conv["id"]}).sort("created_at", -1).to_list(limit)
    msgs = list(reversed(msgs))
    lines = []
    for m in msgs:
        who = {"patient": "Pasien", "ai": "Asisten", "agent": "Staf"}.get(m["sender_type"], "?")
        lines.append(f"{who}: {m['content']}")
    return "Riwayat percakapan:\n" + "\n".join(lines) if lines else ""


async def rag_answer(conv, text, settings):
    results, top = await retrieve(text)
    threshold = settings.get("rag_relevant_threshold", 0.08)
    use_rag = settings.get("modules", {}).get("rag", True)
    context = "\n\n".join([f"[{r['source']}] {r['text']}" for r in results if r["score"] >= threshold]) if use_rag else ""
    history = await recent_history(conv)
    sys = build_system_prompt(settings, context)
    prompt = f"{history}\nPasien: {text}\nAsisten:"
    try:
        reply = await generate_reply(sys, prompt, conv["id"], settings)
    except Exception:
        reply = ("Mohon maaf, sedang terjadi gangguan teknis pada layanan AI. "
                 "Silakan coba lagi sebentar lagi atau ketik *6* untuk terhubung dengan staf klinik.")
    return reply, top


async def llm_route(text, history, settings):
    """Smart semantic router: pick the best-matching configured intent id or 'none'."""
    intents = _intents(settings)
    if not intents:
        return None
    catalog = "\n".join(
        [f"- {i['id']}: {i['name']}. Contoh: {'; '.join(i.get('examples', [])[:3])}" for i in intents])
    sys = (
        "Anda adalah router intent yang cerdas untuk chatbot klinik. Berdasarkan pesan pasien dan konteks, "
        "pilih SATU id intent paling sesuai dari daftar. Jika tidak ada yang cocok atau ini pertanyaan bebas, jawab 'none'. "
        "Jawab HANYA dengan id (satu kata), tanpa penjelasan.\n\nDaftar intent:\n" + catalog)
    try:
        out = await generate_reply(sys, f"{history}\nPesan pasien: {text}\nId intent:", f"router-{hash(text) % 100000}", settings)
        word = out.strip().split()[0].lower().strip(".,:'\"")
        ids = {i["id"] for i in intents}
        return word if word in ids else None
    except Exception:
        return None


def _keyword_route(t, settings):
    for i in _intents(settings):
        for kw in i.get("keywords", []):
            if kw and kw.lower() in t:
                return i
    return None


def _find_intent(settings, intent_id):
    for i in _intents(settings):
        if i["id"] == intent_id:
            return i
    return None


async def execute_intent(intent, conv, text, settings, result):
    action = intent.get("action", "rag")
    modules = settings.get("modules", {})
    if action == "static":
        result["replies"] = [intent.get("response") or "Baik, mohon tunggu sebentar."]
    elif action == "services":
        result["replies"] = [await services_text(settings)]
    elif action == "doctors":
        result["replies"] = [doctors_text(settings)]
    elif action == "queue":
        result["replies"] = [await queue_text(settings)]
    elif action == "booking" and modules.get("booking", True):
        new_flow, msg = await start_booking(settings)
        result["flow"] = new_flow
        result["replies"] = [msg]
    elif action == "handoff" and modules.get("handoff", True):
        result["handoff"] = True
        result["replies"] = [intent.get("response") or "Baik, saya hubungkan Anda dengan staf klinik. Mohon tunggu sebentar. 🙏"]
    else:  # rag / faq / fallback
        reply, top = await rag_answer(conv, text, settings)
        result["confidence"] = top
        result["replies"] = [reply]
    return result


async def handle_incoming(conv, text, msg_type, settings):
    """Data-driven, smart & natural workflow engine."""
    modules = settings.get("modules", {})
    wf = settings.get("workflow", {})
    result = {"replies": [], "handoff": False, "intent": None, "confidence": None,
              "sentiment": 0.0, "flow": conv.get("flow"), "appointment": None, "resolved_flow": False}

    if conv.get("status") == "handoff" and conv.get("ai_paused"):
        return result

    if msg_type != "text":
        if modules.get("handoff", True):
            result["handoff"] = True
            result["replies"] = ["Saya menerima lampiran media dari Anda. Mohon tunggu, saya hubungkan dengan staf klinik untuk membantu. 🙏"]
        else:
            result["replies"] = ["Mohon maaf, saya belum dapat memproses lampiran. Silakan kirim dalam bentuk teks."]
        return result

    t = text.lower().strip()
    result["sentiment"] = detect_sentiment(text, settings)

    handoff_kw = settings.get("handoff_keywords", [])
    if modules.get("handoff", True) and any(k in t for k in handoff_kw):
        result["handoff"] = True
        result["intent"] = "staf"
        result["replies"] = ["Baik, saya akan menghubungkan Anda dengan staf klinik kami. Mohon tunggu sebentar. 🙏"]
        return result

    if modules.get("handoff", True) and result["sentiment"] < 0:
        streak = conv.get("negative_streak", 0) + 1
        result["negative_streak"] = streak
        if streak >= 2:
            result["handoff"] = True
            result["intent"] = "eskalasi_sentimen"
            result["replies"] = ["Saya turut prihatin atas ketidaknyamanan Anda. 🙏 Izinkan saya menghubungkan Anda dengan staf klinik agar dapat dibantu lebih baik."]
            return result
    else:
        result["negative_streak"] = 0

    # Active booking flow
    flow = conv.get("flow")
    if flow and flow.get("name") == "booking" and modules.get("booking", True):
        if t == "menu":
            result["flow"] = None
            result["resolved_flow"] = True
            result["replies"] = [menu_text(settings)]
            return result
        replies, new_flow, appt = await continue_booking(conv, flow, text, settings)
        result.update(replies=replies, flow=new_flow, resolved_flow=new_flow is None, appointment=appt, intent="booking")
        return result

    # Welcome / menu
    is_first = await db.messages.count_documents({"conversation_id": conv["id"], "sender_type": "patient"}) <= 1
    if t in WELCOME_KEYWORDS or is_first:
        result["replies"] = [menu_text(settings)]
        result["intent"] = "welcome"
        return result

    # 1) menu number
    intent = None
    if t.isdigit():
        for i in _intents(settings):
            if i.get("menu_key") == t:
                intent = i
                break
    # 2) keyword route
    if not intent:
        intent = _keyword_route(t, settings)
    # 3) smart LLM semantic route
    if not intent and wf.get("use_llm_router", True):
        history = await recent_history(conv, 6)
        rid = await llm_route(text, history, settings)
        if rid:
            intent = _find_intent(settings, rid)

    if intent:
        result["intent"] = intent["id"]
        return await execute_intent(intent, conv, text, settings, result)

    # 4) fallback
    fb = wf.get("fallback", "rag")
    if fb == "handoff" and modules.get("handoff", True):
        result["handoff"] = True
        result["intent"] = "fallback_handoff"
        result["replies"] = ["Mohon maaf, saya belum sepenuhnya memahami. Saya hubungkan Anda dengan staf klinik ya. 🙏"]
        return result
    result["intent"] = "faq"
    reply, top = await rag_answer(conv, text, settings)
    result["confidence"] = top
    result["replies"] = [reply]
    return result
