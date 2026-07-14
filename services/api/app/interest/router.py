from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.auth.deps import get_current_user
from app.db import models
from app.db.base import get_db
from app.db.models import User
from app.errors import AppError
from app.mappers import property_to_dto
from app.schemas.common import InterestState, PageMeta, Visit, VisitStatus
from app.schemas.interest import (
    CreateInterestRequest,
    InterestItem,
    InterestListResponse,
    PatchInterestRequest,
)

router = APIRouter(prefix="/interest", tags=["interest"])


def _to_item(
    interest: models.InterestItem,
    visit: models.Visit | None,
) -> InterestItem:
    v = Visit(
        status=VisitStatus(visit.status) if visit else VisitStatus.none,
        at=visit.at.isoformat() if visit and visit.at else None,
    )
    return InterestItem(
        id=interest.id,
        property=property_to_dto(interest.property),
        state=InterestState(interest.state),
        user_score=interest.user_score,
        visit=v,
        comments=interest.comments,
        comment_flag=bool(interest.comments and interest.comments.strip()),
        created_at=interest.created_at,
        updated_at=interest.updated_at,
        archived_at=interest.archived_at,
    )


@router.get("", response_model=InterestListResponse)
async def list_interest(
    state: InterestState = Query(default=InterestState.active),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> InterestListResponse:
    base = select(models.InterestItem).where(
        models.InterestItem.user_id == user.id,
        models.InterestItem.state == state.value,
    )
    total = (
        await db.execute(select(func.count()).select_from(base.subquery()))
    ).scalar_one()
    result = await db.execute(
        base.options(selectinload(models.InterestItem.property))
        .order_by(models.InterestItem.updated_at.desc())
        .limit(limit)
        .offset(offset)
    )
    rows = list(result.scalars().all())
    prop_ids = [r.property_id for r in rows]
    visits_map: dict[UUID, models.Visit] = {}
    if prop_ids:
        vres = await db.execute(
            select(models.Visit).where(
                models.Visit.user_id == user.id,
                models.Visit.property_id.in_(prop_ids),
            )
        )
        visits_map = {v.property_id: v for v in vres.scalars().all()}

    items = [_to_item(r, visits_map.get(r.property_id)) for r in rows]
    return InterestListResponse(
        items=items, meta=PageMeta(total=total, limit=limit, offset=offset)
    )


@router.post("", response_model=InterestItem, status_code=201)
async def create_interest(
    body: CreateInterestRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> InterestItem:
    prop = await db.get(models.Property, body.property_id)
    if prop is None:
        raise AppError(404, "not_found", "Property not found")

    existing = (
        await db.execute(
            select(models.InterestItem).where(
                models.InterestItem.user_id == user.id,
                models.InterestItem.property_id == body.property_id,
            )
        )
    ).scalar_one_or_none()
    if existing:
        raise AppError(409, "interest_exists", "Interest already active or archived")

    interest = models.InterestItem(
        user_id=user.id,
        property_id=body.property_id,
        state=InterestState.active.value,
    )
    db.add(interest)
    await db.flush()
    await db.refresh(interest, attribute_names=["property"])
    # ensure property loaded
    interest.property = prop
    return _to_item(interest, None)


@router.patch("/{interest_id}", response_model=InterestItem)
async def patch_interest(
    interest_id: UUID,
    body: PatchInterestRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> InterestItem:
    interest = await db.get(models.InterestItem, interest_id)
    if interest is None or interest.user_id != user.id:
        raise AppError(404, "not_found", "Interest not found")
    data = body.model_dump(exclude_unset=True)
    if "user_score" in data:
        interest.user_score = data["user_score"]
    if "comments" in data:
        interest.comments = data["comments"]
    interest.updated_at = datetime.now(timezone.utc)
    await db.flush()
    prop = await db.get(models.Property, interest.property_id)
    interest.property = prop  # type: ignore[assignment]
    visit = (
        await db.execute(
            select(models.Visit).where(
                models.Visit.user_id == user.id,
                models.Visit.property_id == interest.property_id,
            )
        )
    ).scalar_one_or_none()
    return _to_item(interest, visit)


@router.post("/{interest_id}/archive", response_model=InterestItem)
async def archive_interest(
    interest_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> InterestItem:
    interest = await db.get(models.InterestItem, interest_id)
    if interest is None or interest.user_id != user.id:
        raise AppError(404, "not_found", "Interest not found")
    interest.state = InterestState.archived.value
    interest.archived_at = datetime.now(timezone.utc)
    interest.updated_at = datetime.now(timezone.utc)
    await db.flush()
    interest.property = await db.get(models.Property, interest.property_id)  # type: ignore[assignment]
    return _to_item(interest, None)


@router.post("/{interest_id}/restore", response_model=InterestItem)
async def restore_interest(
    interest_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> InterestItem:
    interest = await db.get(models.InterestItem, interest_id)
    if interest is None or interest.user_id != user.id:
        raise AppError(404, "not_found", "Interest not found")
    interest.state = InterestState.active.value
    interest.archived_at = None
    interest.updated_at = datetime.now(timezone.utc)
    await db.flush()
    interest.property = await db.get(models.Property, interest.property_id)  # type: ignore[assignment]
    return _to_item(interest, None)
