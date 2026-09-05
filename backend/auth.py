import os
import uuid
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from passlib.context import CryptContext
from jose import jwt, JWTError
from pydantic import BaseModel
from dotenv import load_dotenv
from database import db, clean

load_dotenv()

pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")
SECRET = os.environ["JWT_SECRET"]
ALGO = "HS256"
security = HTTPBearer()
router = APIRouter(prefix="/api/auth", tags=["auth"])


class LoginReq(BaseModel):
    username: str
    password: str


def create_token(user):
    payload = {
        "sub": user["id"],
        "username": user["username"],
        "role": user.get("role", "admin"),
        "exp": datetime.now(timezone.utc) + timedelta(days=7),
    }
    return jwt.encode(payload, SECRET, algorithm=ALGO)


async def get_current_user(cred: HTTPAuthorizationCredentials = Depends(security)):
    try:
        payload = jwt.decode(cred.credentials, SECRET, algorithms=[ALGO])
    except JWTError:
        raise HTTPException(401, "Token tidak valid atau kadaluarsa")
    user = await db.users.find_one({"id": payload["sub"]})
    if not user:
        raise HTTPException(401, "Pengguna tidak ditemukan")
    return clean(user)


@router.post("/login")
async def login(req: LoginReq):
    user = await db.users.find_one({"username": req.username})
    if not user or not pwd_ctx.verify(req.password, user["password_hash"]):
        raise HTTPException(401, "Username atau password salah")
    return {
        "token": create_token(user),
        "user": {"username": user["username"], "role": user.get("role"), "name": user.get("name")},
    }


@router.get("/me")
async def me(user=Depends(get_current_user)):
    return {"username": user["username"], "role": user.get("role"), "name": user.get("name")}


async def seed_admin():
    if not await db.users.find_one({"username": "admin"}):
        await db.users.insert_one({
            "id": str(uuid.uuid4()),
            "username": "admin",
            "password_hash": pwd_ctx.hash("admin123"),
            "role": "admin",
            "name": "Administrator Klinik",
            "created_at": datetime.now(timezone.utc).isoformat(),
        })
