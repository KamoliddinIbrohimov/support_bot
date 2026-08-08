"""JWT auth dependency for protected admin endpoints."""
from __future__ import annotations

from fastapi import Depends, HTTPException, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from api.admin.auth import decode_token
from config.settings import settings

_bearer = HTTPBearer()


def get_current_admin(
    creds: HTTPAuthorizationCredentials = Security(_bearer),
) -> int:
    user_id = decode_token(creds.credentials)
    if user_id not in settings.ADMIN_IDS:
        raise HTTPException(status_code=403, detail="Admin emas")
    return user_id
