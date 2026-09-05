import os
import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Request, Header
from pydantic import BaseModel
from dotenv import load_dotenv

from database import db, clean
from auth import get_current_user
from config import get_settings
from workflow import handle_incoming, now_iso
import gateway_client as gw
from ws_manager import manager

load_dotenv()
WEBHOOK_TOKEN = os.environ.get("WEBHOOK_TOKEN")
router = APIRouter(prefix="/api/whatsapp", tags=["whatsapp"])


class PairingReq(BaseModel):
    phone: str


class WebhookMsg(BaseModel):
    sender: str
    text: str = ""
    messageType: str = "text"
    waMessageId: str = ""
    pushName: str = ""


async def _get_or_create_conversation(wa_jid, push_name=""):
    conv = await db.conversations.find_one({"wa_jid": wa_jid})
    if conv:
        return clean(conv)
    conv = {
        "id": str(uuid.uuid4()),
        "wa_jid": wa_jid,
        "patient_name": push_name or None,
        "status": "active",
        "assigned_agent": None,
        "ai_paused": False,
        "sentiment_score": 0.0,
        "negative_streak": 0,
        "flow": None,
        "unread": 0,
        "last_message": "",
        "created_at": now_iso(),
        "updated_at": now_iso(),
    }
    await db.conversations.insert_one(dict(conv))
    return conv


async def _save_message(conv_id, sender_type, content, message_type="text",
                        wa_message_id=None, intent=None, confidence=None):
    msg = {
        "id": str(uuid.uuid4()),
        "conversation_id": conv_id,
        "sender_type": sender_type,
        "content": content,
        "message_type": message_type,
        "wa_message_id": wa_message_id,
        "intent_detected": intent,
        "confidence": confidence,
        "created_at": now_iso(),
    }
    await db.messages.insert_one(dict(msg))
    return clean(msg)


@router.post("/webhook")
async def webhook(payload: WebhookMsg, x_webhook_token: str = Header(default="")):
    if x_webhook_token != WEBHOOK_TOKEN:
        raise HTTPException(401, "Invalid webhook token")

    wa_jid = payload.sender
    settings = await get_settings()
    conv = await _get_or_create_conversation(wa_jid, payload.pushName)

    if payload.pushName and not conv.get("patient_name"):
        conv["patient_name"] = payload.pushName
        await db.conversations.update_one({"id": conv["id"]}, {"$set": {"patient_name": payload.pushName}})

    await _save_message(conv["id"], "patient", payload.text or "[media]",
                        payload.messageType, payload.waMessageId)

    result = await handle_incoming(conv, payload.text, payload.messageType, settings)

    updates = {
        "updated_at": now_iso(),
        "last_message": payload.text or "[media]",
        "sentiment_score": result.get("sentiment", conv.get("sentiment_score", 0.0)),
        "flow": result.get("flow"),
        "negative_streak": result.get("negative_streak", 0),
    }

    if result.get("handoff"):
        updates["status"] = "handoff"
        updates["ai_paused"] = True
        updates["unread"] = conv.get("unread", 0) + 1
        await db.notifications.insert_one({
            "id": str(uuid.uuid4()),
            "type": "handoff",
            "conversation_id": conv["id"],
            "patient_name": conv.get("patient_name") or wa_jid.split("@")[0],
            "message": f"Percakapan membutuhkan staf: {payload.text[:60]}",
            "read": False,
            "created_at": now_iso(),
        })

    await db.conversations.update_one({"id": conv["id"]}, {"$set": updates})

    patient_label = conv.get("patient_name") or wa_jid.split("@")[0]
    await manager.broadcast({
        "type": "handoff" if result.get("handoff") else "message",
        "conversation_id": conv["id"],
        "patient_name": patient_label,
        "preview": (payload.text or "[media]")[:80],
        "handoff": result.get("handoff", False),
    })

    # Send AI replies via gateway and persist them
    for reply in result.get("replies", []):
        if not reply:
            continue
        await gw.send_message(wa_jid, reply)
        await _save_message(conv["id"], "ai", reply, "text",
                            intent=result.get("intent"), confidence=result.get("confidence"))

    return {"ok": True, "handoff": result.get("handoff", False), "replies": result.get("replies", [])}


@router.get("/status")
async def status(user=Depends(get_current_user)):
    return await gw.get_status()


@router.post("/connect")
async def connect(user=Depends(get_current_user)):
    return await gw.connect()


@router.post("/pairing-code")
async def pairing_code(req: PairingReq, user=Depends(get_current_user)):
    phone = "".join(ch for ch in req.phone if ch.isdigit())
    if len(phone) < 8:
        raise HTTPException(400, "Nomor telepon tidak valid")
    return await gw.request_pairing_code(phone)


@router.post("/logout")
async def logout(user=Depends(get_current_user)):
    return await gw.logout()
