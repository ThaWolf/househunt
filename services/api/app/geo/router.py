"""GET /api/geo/suggest"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from app.auth.deps import get_current_user
from app.db.models import User
from app.errors import AppError
from app.geo.suggest import suggest_places
from app.schemas.property import GeoSuggestResponse

router = APIRouter(prefix="/geo", tags=["geo"])


@router.get("/suggest", response_model=GeoSuggestResponse)
async def geo_suggest(
    q: str = Query(..., min_length=1),
    user: User = Depends(get_current_user),
) -> GeoSuggestResponse:
    _ = user
    query = q.strip()
    if not query:
        raise AppError(422, "validation_error", "q is required")
    items = suggest_places(query, limit=8)
    return GeoSuggestResponse(items=items)
