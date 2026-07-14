"""Auth service: register, login, refresh, logout, Google OAuth."""

from __future__ import annotations

from datetime import datetime, timezone
from urllib.parse import urlencode
from uuid import UUID

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.security import (
    create_access_token,
    create_refresh_token_value,
    hash_password,
    hash_token,
    refresh_expiry,
    verify_password,
)
from app.config import Settings, get_settings
from app.db.models import RefreshToken, User
from app.errors import AppError
from app.schemas.auth import AuthResponse, AuthTokens, UserDTO


def user_dto(user: User) -> UserDTO:
    return UserDTO(id=user.id, email=user.email, display_name=user.display_name)


async def _issue_tokens(db: AsyncSession, user: User, settings: Settings) -> AuthResponse:
    access, expires_in = create_access_token(user.id, settings=settings)
    refresh = create_refresh_token_value()
    db.add(
        RefreshToken(
            user_id=user.id,
            token_hash=hash_token(refresh),
            expires_at=refresh_expiry(settings=settings),
        )
    )
    await db.flush()
    return AuthResponse(
        access_token=access,
        refresh_token=refresh,
        token_type="Bearer",
        expires_in=expires_in,
        user=user_dto(user),
    )


async def register_user(
    db: AsyncSession,
    *,
    email: str,
    password: str,
    display_name: str | None,
    settings: Settings | None = None,
) -> AuthResponse:
    settings = settings or get_settings()
    email_n = email.strip().lower()
    existing = await db.execute(select(User).where(User.email == email_n))
    if existing.scalar_one_or_none():
        raise AppError(409, "email_taken", "Email already registered")
    user = User(
        email=email_n,
        password_hash=hash_password(password),
        display_name=display_name,
    )
    db.add(user)
    await db.flush()
    return await _issue_tokens(db, user, settings)


async def login_user(
    db: AsyncSession,
    *,
    email: str,
    password: str,
    settings: Settings | None = None,
) -> AuthResponse:
    settings = settings or get_settings()
    email_n = email.strip().lower()
    result = await db.execute(select(User).where(User.email == email_n))
    user = result.scalar_one_or_none()
    if user is None or not verify_password(password, user.password_hash):
        raise AppError(401, "invalid_credentials", "Invalid email or password")
    return await _issue_tokens(db, user, settings)


async def refresh_tokens(
    db: AsyncSession,
    *,
    refresh_token: str,
    settings: Settings | None = None,
) -> AuthTokens:
    settings = settings or get_settings()
    th = hash_token(refresh_token)
    result = await db.execute(select(RefreshToken).where(RefreshToken.token_hash == th))
    row = result.scalar_one_or_none()
    now = datetime.now(timezone.utc)
    if row is None or row.revoked_at is not None or row.expires_at < now:
        raise AppError(401, "invalid_refresh", "Invalid or expired refresh token")
    row.revoked_at = now
    user = await db.get(User, row.user_id)
    if user is None:
        raise AppError(401, "invalid_refresh", "Invalid or expired refresh token")
    access, expires_in = create_access_token(user.id, settings=settings)
    new_refresh = create_refresh_token_value()
    db.add(
        RefreshToken(
            user_id=user.id,
            token_hash=hash_token(new_refresh),
            expires_at=refresh_expiry(settings=settings),
        )
    )
    await db.flush()
    return AuthTokens(
        access_token=access,
        refresh_token=new_refresh,
        token_type="Bearer",
        expires_in=expires_in,
    )


async def logout_user(
    db: AsyncSession,
    *,
    user_id: UUID,
    refresh_token: str | None,
) -> None:
    if not refresh_token:
        return
    th = hash_token(refresh_token)
    result = await db.execute(
        select(RefreshToken).where(
            RefreshToken.token_hash == th, RefreshToken.user_id == user_id
        )
    )
    row = result.scalar_one_or_none()
    if row and row.revoked_at is None:
        row.revoked_at = datetime.now(timezone.utc)
        await db.flush()


def google_authorize_url(settings: Settings | None = None, *, state: str) -> str:
    settings = settings or get_settings()
    if not settings.google_oauth_configured():
        raise AppError(501, "feature_disabled", "Google OAuth is not configured")
    scopes = ["openid", "email", "profile"]
    if settings.effective_google_calendar():
        scopes.append("https://www.googleapis.com/auth/calendar.events")
    params = {
        "client_id": settings.google_oauth_client_id,
        "redirect_uri": settings.google_oauth_redirect_uri,
        "response_type": "code",
        "scope": " ".join(scopes),
        "access_type": "offline",
        "prompt": "consent",
        "state": state,
    }
    return f"https://accounts.google.com/o/oauth2/v2/auth?{urlencode(params)}"


async def google_callback(
    db: AsyncSession,
    *,
    code: str,
    settings: Settings | None = None,
) -> AuthResponse:
    settings = settings or get_settings()
    if not settings.google_oauth_configured():
        raise AppError(501, "feature_disabled", "Google OAuth is not configured")

    async with httpx.AsyncClient(timeout=20.0) as client:
        token_resp = await client.post(
            "https://oauth2.googleapis.com/token",
            data={
                "code": code,
                "client_id": settings.google_oauth_client_id,
                "client_secret": settings.google_oauth_client_secret,
                "redirect_uri": settings.google_oauth_redirect_uri,
                "grant_type": "authorization_code",
            },
        )
        if token_resp.status_code >= 400:
            raise AppError(401, "unauthorized", "Google token exchange failed")
        tokens = token_resp.json()
        access = tokens.get("access_token")
        if not access:
            raise AppError(401, "unauthorized", "Google token exchange failed")
        userinfo_resp = await client.get(
            "https://www.googleapis.com/oauth2/v3/userinfo",
            headers={"Authorization": f"Bearer {access}"},
        )
        if userinfo_resp.status_code >= 400:
            raise AppError(401, "unauthorized", "Failed to fetch Google userinfo")
        info = userinfo_resp.json()

    sub = info.get("sub")
    email = (info.get("email") or "").lower()
    if not sub or not email:
        raise AppError(401, "unauthorized", "Google account missing email")

    result = await db.execute(select(User).where(User.google_sub == sub))
    user = result.scalar_one_or_none()
    if user is None:
        result = await db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()
        if user:
            user.google_sub = sub
            if not user.display_name:
                user.display_name = info.get("name")
        else:
            user = User(
                email=email,
                google_sub=sub,
                display_name=info.get("name"),
                password_hash=None,
            )
            db.add(user)
        await db.flush()
    return await _issue_tokens(db, user, settings)
