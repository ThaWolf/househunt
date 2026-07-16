from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.adapters.amenities_parse import parse_amenities
from app.adapters.external import ExternalExtractError, extract_listing
from app.auth.deps import get_current_user
from app.config import get_settings
from app.db import models
from app.db.base import get_db
from app.db.models import User
from app.errors import AppError
from app.interest.amenities import amenities_highlight
from app.interest.deps import require_membership, resolve_list_id
from app.mappers import apply_raw_to_row, property_to_dto, raw_property_to_model
from app.schemas.common import InterestState, PageMeta, Visit, VisitStatus
from app.schemas.interest import (
    AddedByUser,
    CreateInterestRequest,
    ExternalInterestRequest,
    InterestItem,
    InterestListResponse,
    PatchInterestRequest,
)
from app.scoring.appscore import compute_appscore

router = APIRouter(prefix="/interest", tags=["interest"])


def _added_by_dto(user: User | None) -> AddedByUser | None:
    if user is None:
        return None
    return AddedByUser(
        user_id=user.id,
        display_name=user.display_name,
        email=user.email,
    )


def _to_item(
    interest: models.InterestItem,
    visit: models.Visit | None,
    added_by: User | None = None,
) -> InterestItem:
    prop = interest.property
    v = Visit(
        status=VisitStatus(visit.status) if visit else VisitStatus.none,
        at=visit.at.isoformat() if visit and visit.at else None,
    )
    author = added_by or getattr(interest, "added_by", None)
    ams = list(prop.amenities or []) if prop else []
    if not ams and prop is not None:
        # Soft infer for stale rows until re-extract (iter-10)
        ams = parse_amenities(prop.title, prop.description)
    return InterestItem(
        id=interest.id,
        property=property_to_dto(prop),
        state=InterestState(interest.state),
        rooms=prop.rooms if prop else None,
        amenities_highlight=amenities_highlight(ams),
        user_score=interest.user_score,
        visit=v,
        comments=interest.comments,
        comment_flag=bool(interest.comments and interest.comments.strip()),
        added_by=_added_by_dto(author),
        created_at=interest.created_at,
        updated_at=interest.updated_at,
        archived_at=interest.archived_at,
    )


async def _visits_for_list(
    db: AsyncSession, list_id: UUID, property_ids: list[UUID]
) -> dict[UUID, models.Visit]:
    if not property_ids:
        return {}
    vres = await db.execute(
        select(models.Visit).where(
            models.Visit.list_id == list_id,
            models.Visit.property_id.in_(property_ids),
        )
    )
    return {v.property_id: v for v in vres.scalars().all()}


@router.get("", response_model=InterestListResponse)
async def list_interest(
    state: InterestState = Query(default=InterestState.active),
    list_id: UUID | None = Query(default=None, alias="listId"),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> InterestListResponse:
    resolved_list_id = await resolve_list_id(db, user, list_id)
    base = select(models.InterestItem).where(
        models.InterestItem.list_id == resolved_list_id,
        models.InterestItem.state == state.value,
    )
    total = (
        await db.execute(select(func.count()).select_from(base.subquery()))
    ).scalar_one()
    result = await db.execute(
        base.options(
            selectinload(models.InterestItem.property),
            selectinload(models.InterestItem.added_by),
        )
        .order_by(models.InterestItem.updated_at.desc())
        .limit(limit)
        .offset(offset)
    )
    rows = list(result.scalars().all())
    visits_map = await _visits_for_list(db, resolved_list_id, [r.property_id for r in rows])
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
    resolved_list_id = await resolve_list_id(db, user, body.list_id)
    prop = await db.get(models.Property, body.property_id)
    if prop is None:
        raise AppError(404, "not_found", "Property not found")

    existing = (
        await db.execute(
            select(models.InterestItem).where(
                models.InterestItem.list_id == resolved_list_id,
                models.InterestItem.property_id == body.property_id,
            )
        )
    ).scalar_one_or_none()
    if existing:
        raise AppError(409, "interest_exists", "Interest already active or archived")

    interest = models.InterestItem(
        list_id=resolved_list_id,
        added_by_user_id=user.id,
        property_id=body.property_id,
        state=InterestState.active.value,
    )
    db.add(interest)
    await db.flush()
    interest.property = prop
    interest.added_by = user
    return _to_item(interest, None)


@router.post("/external", response_model=InterestItem)
async def create_external_interest(
    body: ExternalInterestRequest,
    response: Response,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> InterestItem:
    """iter-9: pegar la URL de una publicación externa → Property + interés."""
    resolved_list_id = await resolve_list_id(db, user, body.list_id)
    settings = get_settings()
    try:
        raw = await extract_listing(body.url)
    except ExternalExtractError as exc:
        raise AppError(422, exc.code, exc.message)

    portal_val = raw.portal.value if hasattr(raw.portal, "value") else str(raw.portal)
    prop = (
        await db.execute(
            select(models.Property).where(
                models.Property.portal == portal_val,
                models.Property.external_id == raw.external_id,
            )
        )
    ).scalar_one_or_none()
    score = compute_appscore(raw, poi_enabled=settings.feature_poi)
    breakdown = score.breakdown.model_dump(by_alias=False)
    if prop is None:
        prop = raw_property_to_model(
            raw,
            app_score=score.score,
            score_breakdown=breakdown,
        )
        db.add(prop)
        await db.flush()
    else:
        # iter-10: refresh stale external/live rows when user re-pastes URL
        apply_raw_to_row(
            prop,
            raw,
            app_score=score.score,
            score_breakdown=breakdown,
        )
        await db.flush()

    existing = (
        await db.execute(
            select(models.InterestItem).where(
                models.InterestItem.list_id == resolved_list_id,
                models.InterestItem.property_id == prop.id,
            )
        )
    ).scalar_one_or_none()
    if existing:
        # Still refresh property above; return existing interest (not silent stale 409)
        await db.refresh(existing)
        existing.property = prop
        existing.added_by = await db.get(User, existing.added_by_user_id)
        visit = (
            await db.execute(
                select(models.Visit).where(
                    models.Visit.list_id == existing.list_id,
                    models.Visit.property_id == existing.property_id,
                )
            )
        ).scalar_one_or_none()
        response.status_code = 200
        return _to_item(existing, visit)

    interest = models.InterestItem(
        list_id=resolved_list_id,
        added_by_user_id=user.id,
        property_id=prop.id,
        state=InterestState.active.value,
    )
    db.add(interest)
    await db.flush()
    interest.property = prop
    interest.added_by = user
    response.status_code = 201
    return _to_item(interest, None)


async def _patchable_interest(
    db: AsyncSession, user: User, interest_id: UUID
) -> models.InterestItem:
    interest = await db.get(models.InterestItem, interest_id)
    if interest is None:
        raise AppError(404, "not_found", "Interest not found")
    await require_membership(db, user.id, interest.list_id)
    return interest


@router.patch("/{interest_id}", response_model=InterestItem)
async def patch_interest(
    interest_id: UUID,
    body: PatchInterestRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> InterestItem:
    interest = await _patchable_interest(db, user, interest_id)
    data = body.model_dump(exclude_unset=True)
    if "user_score" in data:
        interest.user_score = data["user_score"]
    if "comments" in data:
        interest.comments = data["comments"]
    interest.updated_at = datetime.now(timezone.utc)
    await db.flush()
    prop = await db.get(models.Property, interest.property_id)
    interest.property = prop  # type: ignore[assignment]
    added_by = await db.get(User, interest.added_by_user_id)
    visit = (
        await db.execute(
            select(models.Visit).where(
                models.Visit.list_id == interest.list_id,
                models.Visit.property_id == interest.property_id,
            )
        )
    ).scalar_one_or_none()
    return _to_item(interest, visit, added_by)


@router.post("/{interest_id}/archive", response_model=InterestItem)
async def archive_interest(
    interest_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> InterestItem:
    interest = await _patchable_interest(db, user, interest_id)
    interest.state = InterestState.archived.value
    interest.archived_at = datetime.now(timezone.utc)
    interest.updated_at = datetime.now(timezone.utc)
    await db.flush()
    interest.property = await db.get(models.Property, interest.property_id)  # type: ignore[assignment]
    added_by = await db.get(User, interest.added_by_user_id)
    visit = (
        await db.execute(
            select(models.Visit).where(
                models.Visit.list_id == interest.list_id,
                models.Visit.property_id == interest.property_id,
            )
        )
    ).scalar_one_or_none()
    return _to_item(interest, visit, added_by)


@router.post("/{interest_id}/restore", response_model=InterestItem)
async def restore_interest(
    interest_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> InterestItem:
    interest = await _patchable_interest(db, user, interest_id)
    interest.state = InterestState.active.value
    interest.archived_at = None
    interest.updated_at = datetime.now(timezone.utc)
    await db.flush()
    interest.property = await db.get(models.Property, interest.property_id)  # type: ignore[assignment]
    added_by = await db.get(User, interest.added_by_user_id)
    visit = (
        await db.execute(
            select(models.Visit).where(
                models.Visit.list_id == interest.list_id,
                models.Visit.property_id == interest.property_id,
            )
        )
    ).scalar_one_or_none()
    return _to_item(interest, visit, added_by)
