from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.deps import get_current_user
from app.db import models
from app.db.base import get_db
from app.db.models import User
from app.errors import AppError
from app.schemas.common import PageMeta, Visit, VisitStatus
from app.schemas.interest import VisitListItem, VisitListResponse, VisitUpsertRequest

router = APIRouter(tags=["visits"])

ALLOWED = {
    VisitStatus.none: {VisitStatus.scheduled, VisitStatus.visited, VisitStatus.none},
    VisitStatus.scheduled: {VisitStatus.visited, VisitStatus.none, VisitStatus.scheduled},
    VisitStatus.visited: {VisitStatus.scheduled, VisitStatus.none, VisitStatus.visited},
}


async def _require_interest(db: AsyncSession, user_id: UUID, property_id: UUID) -> models.InterestItem:
    interest = (
        await db.execute(
            select(models.InterestItem).where(
                models.InterestItem.user_id == user_id,
                models.InterestItem.property_id == property_id,
            )
        )
    ).scalar_one_or_none()
    if interest is None or interest.state not in ("active", "archived"):
        raise AppError(
            403,
            "forbidden",
            "User fields require interest (active or archived)",
        )
    return interest


@router.put("/properties/{property_id}/visit", response_model=Visit)
async def upsert_visit(
    property_id: UUID,
    body: VisitUpsertRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Visit:
    await _require_interest(db, user.id, property_id)
    prop = await db.get(models.Property, property_id)
    if prop is None:
        raise AppError(404, "not_found", "Property not found")

    if body.status in (VisitStatus.scheduled, VisitStatus.visited) and body.at is None:
        raise AppError(400, "visit_at_required", "Visit datetime required for scheduled/visited")

    existing = (
        await db.execute(
            select(models.Visit).where(
                models.Visit.user_id == user.id,
                models.Visit.property_id == property_id,
            )
        )
    ).scalar_one_or_none()

    current = VisitStatus(existing.status) if existing else VisitStatus.none
    if body.status not in ALLOWED[current]:
        raise AppError(400, "validation_error", f"Invalid visit transition {current} → {body.status}")

    if existing is None:
        existing = models.Visit(
            user_id=user.id,
            property_id=property_id,
            status=body.status.value,
            at=body.at,
        )
        db.add(existing)
    else:
        existing.status = body.status.value
        existing.at = body.at if body.status != VisitStatus.none else None
    await db.flush()
    return Visit(
        status=VisitStatus(existing.status),
        at=existing.at.isoformat() if existing.at else None,
    )


@router.get("/visits", response_model=VisitListResponse)
async def list_visits(
    status: VisitStatus | None = None,
    from_: datetime | None = Query(default=None, alias="from"),
    to: datetime | None = None,
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> VisitListResponse:
    q = select(models.Visit).where(models.Visit.user_id == user.id)
    if status:
        q = q.where(models.Visit.status == status.value)
    if from_:
        q = q.where(models.Visit.at >= from_)
    if to:
        q = q.where(models.Visit.at <= to)

    total = (await db.execute(select(func.count()).select_from(q.subquery()))).scalar_one()
    rows = list(
        (
            await db.execute(q.order_by(models.Visit.at.desc().nullslast()).limit(limit).offset(offset))
        ).scalars().all()
    )

    items: list[VisitListItem] = []
    for v in rows:
        prop = await db.get(models.Property, v.property_id)
        interest = (
            await db.execute(
                select(models.InterestItem).where(
                    models.InterestItem.user_id == user.id,
                    models.InterestItem.property_id == v.property_id,
                )
            )
        ).scalar_one_or_none()
        items.append(
            VisitListItem(
                property_id=v.property_id,
                interest_id=interest.id if interest else None,
                title=prop.title if prop else None,
                visit=Visit(
                    status=VisitStatus(v.status),
                    at=v.at.isoformat() if v.at else None,
                ),
            )
        )
    return VisitListResponse(
        items=items, meta=PageMeta(total=total, limit=limit, offset=offset)
    )
