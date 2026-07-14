"""Image proxy (feature-flagged)."""

from __future__ import annotations

from urllib.parse import urlparse

import httpx
from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response

from app.adapters.veracity import is_banned_image_host
from app.auth.deps import get_current_user
from app.config import get_settings
from app.db.models import User
from app.errors import AppError

router = APIRouter(prefix="/media", tags=["media"])

ALLOWED_HOST_SUFFIXES = (
    "zonaprop.com.ar",
    "zonapropcdn.com",
    "naventcdn.com",
    "argenprop.com",
    "mercadolibre.com.ar",
    "mlstatic.com",
    "remax.com.ar",
    "cloudfront.net",
    "imgs.remax.com.ar",
    "century21.com.ar",
    "21online.lat",
)


def _host_allowed(url: str) -> bool:
    if is_banned_image_host(url):
        return False
    host = urlparse(url).hostname or ""
    host = host.lower()
    return any(host == s or host.endswith("." + s) for s in ALLOWED_HOST_SUFFIXES)


@router.get("/proxy")
async def media_proxy(
    u: str = Query(..., description="Encoded image URL"),
    user: User = Depends(get_current_user),
) -> Response:
    _ = user
    settings = get_settings()
    if not settings.feature_image_proxy:
        raise AppError(501, "feature_disabled", "Image proxy disabled")
    if not _host_allowed(u):
        raise AppError(400, "validation_error", "URL host not allowlisted")
    try:
        async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
            resp = await client.get(u)
    except httpx.HTTPError:
        raise AppError(502, "error", "Failed to fetch image") from None
    if resp.status_code >= 400:
        raise AppError(resp.status_code if resp.status_code in (404, 403) else 502, "error", "Upstream image error")
    content_type = resp.headers.get("content-type", "image/jpeg")
    return Response(
        content=resp.content,
        media_type=content_type,
        headers={"Cache-Control": "public, max-age=3600"},
    )
