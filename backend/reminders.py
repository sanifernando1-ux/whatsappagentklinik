from datetime import date, timedelta, datetime
from database import db
from config import get_settings
import gateway_client as gw


async def run_reminders(force: bool = False):
    settings = await get_settings()
    rem = settings.get("reminders", {})
    if not force and not rem.get("enabled", False):
        return {"sent": 0, "skipped": "disabled"}

    tomorrow = (date.today() + timedelta(days=1)).isoformat()
    appts = await db.appointments.find({
        "appointment_date": tomorrow,
        "reminder_sent": False,
        "status": {"$in": ["pending", "confirmed"]},
    }).to_list(500)

    clinic = settings.get("clinic", {})
    sent = 0
    for a in appts:
        jid = None
        if a.get("conversation_id"):
            conv = await db.conversations.find_one({"id": a["conversation_id"]})
            if conv:
                jid = conv["wa_jid"]
        if not jid and a.get("patient_phone"):
            phone = "".join(ch for ch in str(a["patient_phone"]) if ch.isdigit())
            if phone:
                jid = f"{phone}@s.whatsapp.net"
        if not jid:
            continue
        d = datetime.fromisoformat(a["appointment_date"]).strftime("%d-%m-%Y")
        msg = (f"🔔 *Pengingat Janji Temu*\n\nHalo {a.get('patient_name', 'Bapak/Ibu')}, kami mengingatkan janji temu Anda besok:\n"
               f"🗓️ {d}   ⏰ {a['appointment_time']}\n🏥 {clinic.get('name', 'Klinik')}\n\n"
               "Mohon hadir 15 menit lebih awal. Balas *BATAL* bila ingin membatalkan. Terima kasih! 🙏")
        r = await gw.send_message(jid, msg)
        if r.get("ok"):
            await db.appointments.update_one({"id": a["id"]}, {"$set": {"reminder_sent": True}})
            sent += 1
    return {"sent": sent, "total_due": len(appts)}
