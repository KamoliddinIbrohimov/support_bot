"""Simple username/password auth + JWT for admin panel."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import jwt
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from config.settings import settings

router = APIRouter(prefix="/admin/auth", tags=["admin-auth"])

_ALGORITHM = "HS256"
_TOKEN_EXPIRE_HOURS = 24


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


def create_access_token() -> str:
    expire = datetime.now(timezone.utc) + timedelta(hours=_TOKEN_EXPIRE_HOURS)
    return jwt.encode({"sub": "admin", "exp": expire}, settings.JWT_SECRET, algorithm=_ALGORITHM)


def decode_token(token: str) -> str:
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[_ALGORITHM])
        return payload["sub"]
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token muddati tugagan")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Token noto'g'ri")


@router.post("/login", response_model=TokenResponse)
async def login(data: LoginRequest):
    if data.username != settings.ADMIN_USERNAME or data.password != settings.ADMIN_PASSWORD:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Login yoki parol noto'g'ri")
    return TokenResponse(access_token=create_access_token())
