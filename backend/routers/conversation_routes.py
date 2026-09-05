import uuid
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from database import db, clean, clean_list
from auth import get_current_user
from workflow import now_iso
import gateway_client as gw

router = APIRouter(prefix="/api/conversations", tags=["conversations"])


class SendReq(BaseModel):
    text: str


@router.get("")
async def list_conversations(status: str = None, user=Depends(get_current_user)):
    q = {}
    if status and status != "all":
        q["status"] = status
    convs = await db.conversations.find(q).sort("updated_at", -1).to_list(200)
    return clean_list(convs)


@router.get("/{conv_id}")
async def get_conversation(conv_id: str, user=Depends(get_current_user)):
    conv = await db.conversations.find_one({"id": conv_id})
    if not conv:
        raise HTTPException(404, "Percakapan tidak ditemukan")
    msgs = await db.messages.find({"conversation_id": conv_id}).sort("created_at", 1).to_list(1000)
    await db.conversations.update_one({"id": conv_id}, {"$set": {"unread": 0}})
    return {"conversation": clean(conv), "messages": clean_list(msgs)}


@router.post("/{conv_id}/send")
async def staff_send(conv_id: str, req: SendReq, user=Depends(get_current_user)):
    conv = await db.conversations.find_one({"id": conv_id})
    if not conv:
        raise HTTPException(404, "Percakapan tidak ditemukan")
    await gw.send_message(conv["wa_jid"], req.text)
    msg = {
        "id": str(uuid.uuid4()),
        "conversation_id": conv_id,
        "sender_type": "agent",
        "content": req.text,
        "message_type": "text",
        "wa_message_id": None,
        "intent_detected": None,
        "confidence": None,
        "created_at": now_iso(),
    }
    await db.messages.insert_one(dict(msg))
    await db.conversations.update_one({"id": conv_id}, {"$set": {
        "status": "handoff", "ai_paused": True, "assigned_agent": user["id"],
        "last_message": req.text, "updated_at": now_iso()}})
    return clean(msg)


@router.post("/{conv_id}/takeover")
async def takeover(conv_id: str, user=Depends(get_current_user)):
    conv = await db.conversations.find_one({"id": conv_id})
    if not conv:
        raise HTTPException(404, "Percakapan tidak ditemukan")
    await db.conversations.update_one({"id": conv_id}, {"$set": {
        "status": "handoff", "ai_paused": True, "assigned_agent": user["id"], "updated_at": now_iso()}})
    return {"ok": True}


@router.post("/{conv_id}/resume")
async def resume(conv_id: str, user=Depends(get_current_user)):
    conv = await db.conversations.find_one({"id": conv_id})
    if not conv:
        raise HTTPException(404, "Percakapan tidak ditemukan")
    resume_msg = "Terima kasih telah menghubungi kami. 😊 Ada lagi yang bisa saya bantu? Ketik *MENU* untuk melihat layanan."
    await gw.send_message(conv["wa_jid"], resume_msg)
    await db.messages.insert_one({
        "id": str(uuid.uuid4()), "conversation_id": conv_id, "sender_type": "ai",
        "content": resume_msg, "message_type": "text", "wa_message_id": None,
        "intent_detected": "resume", "confidence": None, "created_at": now_iso()})
    await db.conversations.update_one({"id": conv_id}, {"$set": {
        "status": "active", "ai_paused": False, "assigned_agent": None,
        "flow": None, "negative_streak": 0, "updated_at": now_iso()}})
    return {"ok": True}


@router.post("/{conv_id}/close")
async def close_conv(conv_id: str, user=Depends(get_current_user)):
    await db.conversations.update_one({"id": conv_id}, {"$set": {
        "status": "closed", "ai_paused": False, "updated_at": now_iso()}})
    return {"ok": True}
