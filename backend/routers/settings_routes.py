from fastapi import APIRouter, Depends
from typing import Any, Dict

from database import db
from auth import get_current_user
from config import get_settings

router = APIRouter(prefix="/api/settings", tags=["settings"])


def _mask(settings: dict) -> dict:
    s = dict(settings)
    ai = dict(s.get("ai", {}))
    ai["has_api_key"] = bool(ai.get("api_key"))
    ai["api_key"] = ""
    s["ai"] = ai
    return s


@router.get("")
async def read_settings(user=Depends(get_current_user)):
    return _mask(await get_settings())


@router.put("")
async def update_settings(payload: Dict[str, Any], user=Depends(get_current_user)):
    current = await get_settings()
    incoming_ai = payload.get("ai", {})
    # keep existing api_key if not explicitly provided
    if "ai" in payload:
        new_key = incoming_ai.get("api_key", "")
        if not new_key:
            incoming_ai["api_key"] = current.get("ai", {}).get("api_key", "")
        payload["ai"] = {**current.get("ai", {}), **incoming_ai}

    merged = {**current, **payload, "id": "singleton"}
    await db.settings.update_one({"id": "singleton"}, {"$set": merged}, upsert=True)
    return _mask(merged)
