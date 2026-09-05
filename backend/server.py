import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from auth import router as auth_router, seed_admin
from config import seed_settings
from routers.whatsapp_routes import router as whatsapp_router
from routers.conversation_routes import router as conversation_router
from routers.appointment_routes import router as appointment_router
from routers.knowledge_routes import router as knowledge_router
from routers.settings_routes import router as settings_router
from routers.dashboard_routes import router as dashboard_router

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


app.include_router(auth_router)
app.include_router(whatsapp_router)
app.include_router(conversation_router)
app.include_router(appointment_router)
app.include_router(knowledge_router)
app.include_router(settings_router)
app.include_router(dashboard_router)


@app.on_event("startup")
async def startup():
    await seed_admin()
    await seed_settings()
