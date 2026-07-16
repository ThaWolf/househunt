from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.deps import get_current_user
from app.config import get_settings
from app.db import models
from app.db.base import get_db
from app.db.models import User
from app.errors import AppError
from app.interest.deps import resolve_list_id
from app.schemas.common import Visit, VisitStatus
from app.schemas.interest import (
    CalendarEvent,
    CalendarResponse,
    CalendarSyncRequest,
    CalendarSyncResponse,
)

router = APIRouter(prefix="/calendar", tags=["calendar"])


@router.get("", response_model=CalendarResponse)
async def calendar_feed(
    from_: datetime | None = Query(default=None, alias="from"),
    to: datetime | None = None,
    list_id: UUID | None = Query(default=None, alias="listId"),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CalendarResponse:
    resolved_list_id = await resolve_list_id(db, user, list_id)
    q = select(models.Visit).where(
        models.Visit.list_id == resolved_list_id,
        models.Visit.status.in_([VisitStatus.scheduled.value, VisitStatus.visited.value]),
    )
    if from_:
        q = q.where(models.Visit.at >= from_)
    if to:
        q = q.where(models.Visit.at <= to)

    visits = list((await db.execute(q.order_by(models.Visit.at.asc()))).scalars().all())
    events: list[CalendarEvent] = []
    for v in visits:
        interest = (
            await db.execute(
                select(models.InterestItem).where(
                    models.InterestItem.list_id == resolved_list_id,
                    models.InterestItem.property_id == v.property_id,
                )
            )
        ).scalar_one_or_none()
        if interest is None:
            continue
        prop = await db.get(models.Property, v.property_id)
        if prop is None:
            continue
        events.append(
            CalendarEvent(
                interest_id=interest.id,
                property_id=v.property_id,
                title=prop.title,
                source_url=prop.source_url,
                visit=Visit(
                    status=VisitStatus(v.status),
                    at=v.at.isoformat() if v.at else None,
                ),
                google_event_id=v.google_event_id,
            )
        )
    return CalendarResponse(events=events)


@router.post("/sync", response_model=CalendarSyncResponse)
async def calendar_sync(
    body: CalendarSyncRequest | None = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CalendarSyncResponse:
    settings = get_settings()
    if not settings.effective_google_calendar():
        raise AppError(
            501,
            "feature_disabled",
            "Google Calendar sync is disabled (missing flag or OAuth secrets)",
        )
    if body and body.list_id is not None:
        await resolve_list_id(db, user, body.list_id)
    # Placeholder for real Google Calendar API sync
    _ = (body, user, db)
    return CalendarSyncResponse(synced=0, failed=0, errors=[])
