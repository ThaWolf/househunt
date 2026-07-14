from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.deps import get_current_user
from app.db.base import get_db
from app.db import models
from app.db.models import User
from app.errors import AppError
from app.mappers import interest_flags, property_to_dto
from app.schemas.property import PropertyDetailResponse
from app.scoring.appscore import compute_appscore
from app.scoring.humanize import build_humanized_report
from app.adapters.types import RawProperty
from app.schemas.common import Operation, PortalId, PropertyType

router = APIRouter(prefix="/properties", tags=["properties"])


def _row_as_raw(row: models.Property) -> RawProperty:
    return RawProperty(
        portal=PortalId(row.portal),
        external_id=row.external_id,
        source_url=row.source_url,
        title=row.title,
        description=row.description,
        operation=Operation(row.operation),
        property_type=PropertyType(row.property_type),
        price_amount=row.price_amount,
        price_currency=row.price_currency,
        address_raw=row.address_raw,
        address_province=row.address_province,
        address_locality=row.address_locality,
        address_neighborhood=row.address_neighborhood,
        geo_lat=row.geo_lat,
        geo_lng=row.geo_lng,
        rooms=row.rooms,
        bathrooms=row.bathrooms,
        parking=row.parking,
        area_covered_m2=row.area_covered_m2,
        area_total_m2=row.area_total_m2,
        amenities=list(row.amenities or []),
        images=list(row.images or []),
        agent_name=row.agent_name,
        agent_phone=row.agent_phone,
        listed_at=row.listed_at,
        scraped_at=row.scraped_at,
    )


@router.get("/{property_id}", response_model=PropertyDetailResponse)
async def get_property(
    property_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PropertyDetailResponse:
    row = await db.get(models.Property, property_id)
    if row is None:
        raise AppError(404, "not_found", "Property not found")

    from sqlalchemy import select

    interest = (
        await db.execute(
            select(models.InterestItem).where(
                models.InterestItem.user_id == user.id,
                models.InterestItem.property_id == property_id,
            )
        )
    ).scalar_one_or_none()
    visit = (
        await db.execute(
            select(models.Visit).where(
                models.Visit.user_id == user.id,
                models.Visit.property_id == property_id,
            )
        )
    ).scalar_one_or_none()

    raw = _row_as_raw(row)
    score = compute_appscore(raw)
    if row.app_score is None:
        row.app_score = score.score
        row.score_breakdown = score.breakdown.model_dump(by_alias=False)
        await db.flush()

    enabled = interest is not None and interest.state in ("active", "archived")
    flags = interest_flags(
        state=interest.state if interest else None,
        user_score=interest.user_score if interest else None,
        comments=interest.comments if interest else None,
        visit_status=visit.status if visit else None,
        visit_at=visit.at if visit else None,
    )
    if not enabled:
        flags.user_score = None
        flags.visit = None
        flags.comments = None
        flags.comment_flag = False

    report = build_humanized_report(raw, score)

    return PropertyDetailResponse(
        property=property_to_dto(row),
        interest=flags,
        report=report,
        user_fields_enabled=enabled,
    )
