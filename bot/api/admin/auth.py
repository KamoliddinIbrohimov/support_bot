"""Telegram Login Widget verification + JWT issuance for admin panel."""
from __future__ import annotations

import hashlib
import hmac
import time
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from config.settings import settings

router = APIRouter(prefix="/admin/auth", tags=["admin-auth"])

_ALGORITHM = "HS256"
_TOKEN_EXPIRE_HOURS = 24


# ── Schemas ───────────────────────────────────────────────────────────────────

class TelegramAuthData(BaseModel):
    id: int
    first_name: str
    last_name: str | None = None
    username: str | None = None
    photo_url: str | None = None
    auth_date: int
    hash: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: int
    first_name: str
    username: str | None


# ── Helpers ───────────────────────────────────────────────────────────────────

def _verify_telegram_hash(data: TelegramAuthData) -> bool:
    """Verify Telegram Login Widget data with HMAC-SHA256."""
    bot_token = settings.BOT_TOKEN
    secret_key = hashlib.sha256(bot_token.encode()).digest()

    fields = {
        "id": str(data.id),
        "first_name": data.first_name,
        "auth_date": str(data.auth_date),
    }
    if data.last_name:
        fields["last_name"] = data.last_name
    if data.username:
        fields["username"] = data.username
    if data.photo_url:
        fields["photo_url"] = data.photo_url

    check_string = "\n".join(f"{k}={v}" for k, v in sorted(fields.items()))
    computed = hmac.new(secret_key, check_string.encode(), hashlib.sha256).hexdigest()
    return computed == data.hash


def create_access_token(user_id: int) -> str:
    expire = datetime.now(timezone.utc) + timedelta(hours=_TOKEN_EXPIRE_HOURS)
    payload = {"sub": str(user_id), "exp": expire}
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=_ALGORITHM)


def decode_token(token: str) -> int:
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[_ALGORITHM])
        return int(payload["sub"])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token muddati tugagan")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Token noto'g'ri")


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("/telegram", response_model=TokenResponse)
async def login_with_telegram(data: TelegramAuthData):
    # 1. Auth date fresh (5 daqiqadan eski bo'lmasin)
    if time.time() - data.auth_date > 300:
        raise HTTPException(status_code=400, detail="Auth data eskirgan")

    # 2. HMAC tekshiruv
    if not _verify_telegram_hash(data):
        raise HTTPException(status_code=401, detail="Telegram imzo noto'g'ri")

    # 3. Admin ekanligini tekshirish
    if data.id not in settings.ADMIN_IDS:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Siz admin emassiz",
        )

    token = create_access_token(data.id)
    return TokenResponse(
        access_token=token,
        user_id=data.id,
        first_name=data.first_name,
        username=data.username,
    )


@router.get("/me")
async def get_me(user_id: int = 0):
    """Token validity check (deps.py dan chaqiriladi)."""
    return {"user_id": user_id, "is_admin": True}
