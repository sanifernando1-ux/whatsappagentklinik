import os
import asyncio
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Query
from fastapi.middleware.cors import CORSMiddleware
from jose import jwt, JWTError
from dotenv import load_dotenv

from auth import router as auth_router, seed_admin, SECRET, ALGO
from config import seed_settings, seed_knowledge
from ws_manager import manager
from reminders import run_reminders
from routers.whatsapp_routes import router as whatsapp_router
from routers.conversation_routes import router as conversation_router
from routers.appointment_routes import router as appointment_router
from routers.knowledge_routes import router as knowledge_router
from routers.settings_routes import router as settings_router
from routers.dashboard_routes import router as dashboard_router
from routers.broadcast_routes import router as broadcast_router

load_dotenv()

app = FastAPI(title="Klinik KF Sepinggan - WhatsApp AI Agent")

app.add_middleware(
    CORSMiddleware,
    allow_origins=os.environ.get("CORS_ORIGINS", "*").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
async def health():
    return {"status": "ok", "service": "klinik-kf-wa-agent"}


@app.websocket("/api/ws")
async def ws_endpoint(websocket: WebSocket, token: str = Query(default="")):
    try:
        jwt.decode(token, SECRET, algorithms=[ALGO])
    except JWTError:
        await websocket.close(code=1008)
        return
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception:
        manager.disconnect(websocket)


app.include_router(auth_router)
app.include_router(whatsapp_router)
app.include_router(conversation_router)
app.include_router(appointment_router)
app.include_router(knowledge_router)
app.include_router(settings_router)
app.include_router(dashboard_router)
app.include_router(broadcast_router)


async def reminder_loop():
    while True:
        try:
            await run_reminders()
        except Exception:
            pass
        await asyncio.sleep(900)  # every 15 minutes


@app.on_event("startup")
async def startup():
    await seed_admin()
    await seed_settings()
    await seed_knowledge()
    asyncio.create_task(reminder_loop())
