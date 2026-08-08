"""JWT auth dependency for protected admin endpoints."""
from __future__ import annotations

from fastapi import Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from api.admin.auth import decode_token

_bearer = HTTPBearer()


def get_current_admin(
    creds: HTTPAuthorizationCredentials = Security(_bearer),
) -> str:
    return decode_token(creds.credentials)
