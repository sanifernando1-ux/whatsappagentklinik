from datetime import datetime, timezone, timedelta, date
from fastapi import APIRouter, Depends

from database import db, clean_list
from auth import get_current_user

router = APIRouter(prefix="/api", tags=["dashboard"])


@router.get("/dashboard/stats")
async def stats(user=Depends(get_current_user)):
    total_conv = await db.conversations.count_documents({})
    active = await db.conversations.count_documents({"status": "active"})
    handoff = await db.conversations.count_documents({"status": "handoff"})
    closed = await db.conversations.count_documents({"status": "closed"})
    today = date.today().isoformat()
    appt_today = await db.appointments.count_documents(
        {"appointment_date": today, "status": {"$in": ["pending", "confirmed"]}})
    total_appt = await db.appointments.count_documents({})
    total_msg = await db.messages.count_documents({})

    # Containment: conversations never escalated to handoff
    ever_handoff = await db.conversations.count_documents({"status": {"$in": ["handoff"]}})
    containment = round((1 - (ever_handoff / total_conv)) * 100) if total_conv else 0

    # 7-day message trend
    trend = []
    now = datetime.now(timezone.utc)
    for i in range(6, -1, -1):
        day = (now - timedelta(days=i)).date()
        start = datetime(day.year, day.month, day.day, tzinfo=timezone.utc).isoformat()
        end = datetime(day.year, day.month, day.day, 23, 59, 59, tzinfo=timezone.utc).isoformat()
        cnt = await db.messages.count_documents({"created_at": {"$gte": start, "$lte": end}})
        conv_cnt = await db.conversations.count_documents({"created_at": {"$gte": start, "$lte": end}})
        trend.append({"date": day.strftime("%d/%m"), "messages": cnt, "conversations": conv_cnt})

    # intent distribution
    pipeline = [{"$match": {"sender_type": "ai", "intent_detected": {"$ne": None}}},
                {"$group": {"_id": "$intent_detected", "count": {"$sum": 1}}}]
    intents = await db.messages.aggregate(pipeline).to_list(50)
    intent_dist = [{"intent": i["_id"], "count": i["count"]} for i in intents]

    return {
        "conversations": {"total": total_conv, "active": active, "handoff": handoff, "closed": closed},
        "appointments": {"today": appt_today, "total": total_appt},
        "messages_total": total_msg,
        "containment_rate": containment,
        "trend": trend,
        "intent_distribution": intent_dist,
    }


@router.get("/notifications")
async def notifications(user=Depends(get_current_user)):
    notifs = await db.notifications.find({"read": False}).sort("created_at", -1).to_list(50)
    return clean_list(notifs)


@router.post("/notifications/{notif_id}/read")
async def mark_read(notif_id: str, user=Depends(get_current_user)):
    await db.notifications.update_one({"id": notif_id}, {"$set": {"read": True}})
    return {"ok": True}


@router.post("/notifications/read-all")
async def mark_all_read(user=Depends(get_current_user)):
    await db.notifications.update_many({"read": False}, {"$set": {"read": True}})
    return {"ok": True}
