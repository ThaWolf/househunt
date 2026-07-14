"""Password hashing and JWT helpers."""

from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.config import Settings, get_settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str | None) -> bool:
    if not hashed:
        return False
    return pwd_context.verify(plain, hashed)


def create_access_token(
    user_id: UUID,
    *,
    settings: Settings | None = None,
    extra: dict[str, Any] | None = None,
) -> tuple[str, int]:
    settings = settings or get_settings()
    expires_in = settings.jwt_access_ttl_minutes * 60
    expire = datetime.now(timezone.utc) + timedelta(seconds=expires_in)
    payload: dict[str, Any] = {
        "sub": str(user_id),
        "type": "access",
        "exp": expire,
    }
    if extra:
        payload.update(extra)
    token = jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)
    return token, expires_in


def create_refresh_token_value() -> str:
    return secrets.token_urlsafe(48)


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def decode_access_token(token: str, *, settings: Settings | None = None) -> UUID:
    settings = settings or get_settings()
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except JWTError as exc:
        raise ValueError("invalid token") from exc
    if payload.get("type") != "access":
        raise ValueError("invalid token type")
    sub = payload.get("sub")
    if not sub:
        raise ValueError("missing sub")
    return UUID(sub)


def refresh_expiry(*, settings: Settings | None = None) -> datetime:
    settings = settings or get_settings()
    return datetime.now(timezone.utc) + timedelta(days=settings.jwt_refresh_ttl_days)
