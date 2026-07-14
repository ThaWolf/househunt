"""Auth routes."""

from __future__ import annotations

import secrets
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, Response
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import service
from app.auth.deps import get_current_user
from app.auth.service import user_dto
from app.config import get_settings
from app.db.base import get_db
from app.db.models import User
from app.errors import AppError
from app.schemas.auth import (
    AuthResponse,
    AuthTokens,
    LoginRequest,
    LogoutRequest,
    RefreshRequest,
    RegisterRequest,
    UserDTO,
)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=AuthResponse)
async def register(body: RegisterRequest, db: AsyncSession = Depends(get_db)) -> AuthResponse:
    return await service.register_user(
        db,
        email=str(body.email),
        password=body.password,
        display_name=body.display_name,
    )


@router.post("/login", response_model=AuthResponse)
async def login(body: LoginRequest, db: AsyncSession = Depends(get_db)) -> AuthResponse:
    return await service.login_user(db, email=str(body.email), password=body.password)


@router.post("/refresh", response_model=AuthTokens)
async def refresh(body: RefreshRequest, db: AsyncSession = Depends(get_db)) -> AuthTokens:
    return await service.refresh_tokens(db, refresh_token=body.refresh_token)


@router.post("/logout", status_code=204)
async def logout(
    body: LogoutRequest | None = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Response:
    await service.logout_user(
        db, user_id=user.id, refresh_token=body.refresh_token if body else None
    )
    return Response(status_code=204)


@router.get("/me", response_model=UserDTO)
async def me(user: User = Depends(get_current_user)) -> UserDTO:
    return user_dto(user)


@router.get("/google")
async def google_start() -> RedirectResponse:
    state = secrets.token_urlsafe(16)
    url = service.google_authorize_url(state=state)
    return RedirectResponse(url=url, status_code=302)


@router.get("/google/callback")
async def google_callback(
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
    db: AsyncSession = Depends(get_db),
) -> RedirectResponse:
    settings = get_settings()
    if error or not code:
        raise AppError(401, "unauthorized", error or "Missing authorization code")
    auth = await service.google_callback(db, code=code)
    # Fragment redirect to FE (API_CONTRACT MVP option)
    fragment = urlencode(
        {
            "accessToken": auth.access_token,
            "refreshToken": auth.refresh_token,
            "expiresIn": str(auth.expires_in),
            "tokenType": auth.token_type,
        }
    )
    return RedirectResponse(
        url=f"{settings.frontend_url.rstrip('/')}/auth/callback#{fragment}",
        status_code=302,
    )
