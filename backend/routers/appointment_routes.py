import uuid
from datetime import date, datetime
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from database import db, clean, clean_list
from auth import get_current_user
from config import get_settings
from workflow import available_slots, now_iso
from reminders import run_reminders

router = APIRouter(prefix="/api/appointments", tags=["appointments"])


class StatusReq(BaseModel):
    status: str


class CreateReq(BaseModel):
    patient_name: str
    patient_phone: str
    service_type: str
    appointment_date: str
    appointment_time: str


@router.get("")
async def list_appointments(status: str = None, on_date: str = None, user=Depends(get_current_user)):
    q = {}
    if status and status != "all":
        q["status"] = status
    if on_date:
        q["appointment_date"] = on_date
    appts = await db.appointments.find(q).sort("appointment_date", -1).to_list(500)
    return clean_list(appts)


@router.get("/slots")
async def slots(on_date: str, user=Depends(get_current_user)):
    settings = await get_settings()
    try:
        d = datetime.fromisoformat(on_date).date()
    except Exception:
        raise HTTPException(400, "Format tanggal salah (YYYY-MM-DD)")
    return {"date": on_date, "slots": await available_slots(settings, d)}


@router.post("")
async def create_appointment(req: CreateReq, user=Depends(get_current_user)):
    appt = {
        "id": str(uuid.uuid4()),
        "conversation_id": None,
        "patient_name": req.patient_name,
        "patient_phone": req.patient_phone,
        "service_type": req.service_type,
        "doctor_id": None,
        "appointment_date": req.appointment_date,
        "appointment_time": req.appointment_time,
        "status": "confirmed",
        "reminder_sent": False,
        "created_at": now_iso(),
    }
    await db.appointments.insert_one(dict(appt))
    return clean(appt)


@router.post("/send-reminders")
async def send_reminders(user=Depends(get_current_user)):
    return await run_reminders(force=True)


@router.patch("/{appt_id}")
async def update_status(appt_id: str, req: StatusReq, user=Depends(get_current_user)):
    r = await db.appointments.update_one({"id": appt_id}, {"$set": {"status": req.status}})
    if r.matched_count == 0:
        raise HTTPException(404, "Janji temu tidak ditemukan")
    return {"ok": True}
