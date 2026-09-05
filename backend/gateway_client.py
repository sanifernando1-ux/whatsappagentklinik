import os
import httpx
from dotenv import load_dotenv

load_dotenv()

GATEWAY_URL = os.environ.get("GATEWAY_URL", "http://localhost:3001")


async def _post(path, json=None, timeout=15):
    async with httpx.AsyncClient(timeout=timeout) as c:
        r = await c.post(f"{GATEWAY_URL}{path}", json=json or {})
        r.raise_for_status()
        return r.json()


async def _get(path, timeout=10):
    async with httpx.AsyncClient(timeout=timeout) as c:
        r = await c.get(f"{GATEWAY_URL}{path}")
        r.raise_for_status()
        return r.json()


async def get_status():
    try:
        return await _get("/status")
    except Exception as e:
        return {"status": "gateway_down", "error": str(e), "qr": None, "pairingCode": None, "me": None}


async def connect():
    return await _post("/connect")


async def request_pairing_code(phone):
    return await _post("/pairing-code", {"phone": phone})


async def logout():
    return await _post("/logout")


async def send_message(to, text):
    try:
        return await _post("/send", {"to": to, "text": text})
    except Exception as e:
        return {"ok": False, "error": str(e)}
