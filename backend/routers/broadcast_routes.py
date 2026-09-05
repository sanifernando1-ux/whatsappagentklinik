import uuid
import asyncio
from fastapi import APIRouter, Depends
from pydantic import BaseModel

from database import db, clean_list
from auth import get_current_user
from workflow import now_iso
import gateway_client as gw

router = APIRouter(prefix="/api/broadcast", tags=["broadcast"])


class BroadcastReq(BaseModel):
    message: str
    target: str = "all"  # all | active | handoff


def _query(target):
    if target == "active":
        return {"status": "active"}
    if target == "handoff":
        return {"status": "handoff"}
    return {"status": {"$ne": "closed"}}  # all except closed


@router.get("/audience")
async def audience(target: str = "all", user=Depends(get_current_user)):
    return {"target": target, "count": await db.conversations.count_documents(_query(target))}


@router.get("")
async def history(user=Depends(get_current_user)):
    items = await db.broadcasts.find().sort("created_at", -1).to_list(100)
    return clean_list(items)


@router.post("")
async def send_broadcast(req: BroadcastReq, user=Depends(get_current_user)):
    convs = await db.conversations.find(_query(req.target)).to_list(5000)
    sent, failed = 0, 0
    for c in convs:
        r = await gw.send_message(c["wa_jid"], req.message)
        if r.get("ok"):
            sent += 1
            await db.messages.insert_one({
                "id": str(uuid.uuid4()), "conversation_id": c["id"], "sender_type": "agent",
                "content": req.message, "message_type": "text", "wa_message_id": None,
                "intent_detected": "broadcast", "confidence": None, "created_at": now_iso()})
            await db.conversations.update_one({"id": c["id"]}, {"$set": {"last_message": req.message, "updated_at": now_iso()}})
        else:
            failed += 1
        await asyncio.sleep(0.25)  # throttle to reduce WhatsApp ban risk

    rec = {
        "id": str(uuid.uuid4()), "message": req.message, "target": req.target,
        "total": len(convs), "sent": sent, "failed": failed,
        "sent_by": user.get("username"), "created_at": now_iso(),
    }
    await db.broadcasts.insert_one(dict(rec))
    rec.pop("_id", None)
    return rec
