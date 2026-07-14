"""Map ORM Property rows ↔ canonical Property DTO."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID, uuid4

from app.db import models
from app.schemas.common import (
    Address,
    Agent,
    Area,
    Currency,
    GeoPoint,
    ImageRef,
    InterestFlags,
    InterestState,
    Money,
    Operation,
    PortalId,
    PropertyType,
    ScoreBreakdown,
    Visit,
    VisitStatus,
)
from app.schemas.property import PropertyDTO
from app.adapters.types import RawProperty


def _dt(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


def property_to_dto(row: models.Property) -> PropertyDTO:
    breakdown = None
    if row.score_breakdown:
        breakdown = ScoreBreakdown.model_validate(row.score_breakdown)

    images = [ImageRef.model_validate(img) for img in (row.images or [])]
    price = None
    if row.price_amount is not None or row.price_currency:
        price = Money(
            amount=row.price_amount,
            currency=Currency(row.price_currency) if row.price_currency else None,
            period=None,
        )

    return PropertyDTO(
        id=row.id,
        portal=PortalId(row.portal),
        external_id=row.external_id,
        source_url=row.source_url,
        title=row.title,
        description=row.description,
        operation=Operation(row.operation),
        property_type=PropertyType(row.property_type),
        price=price,
        address=Address(
            raw=row.address_raw,
            province=row.address_province,
            locality=row.address_locality,
            neighborhood=row.address_neighborhood,
        ),
        geo=GeoPoint(lat=row.geo_lat, lng=row.geo_lng),
        rooms=row.rooms,
        bathrooms=row.bathrooms,
        parking=row.parking,
        area=Area(covered_m2=row.area_covered_m2, total_m2=row.area_total_m2),
        amenities=list(row.amenities or []),
        images=images,
        agent=Agent(name=row.agent_name, phone=row.agent_phone),
        listed_at=_dt(row.listed_at),
        scraped_at=_dt(row.scraped_at) or datetime.now(timezone.utc),
        app_score=row.app_score,
        score_breakdown=breakdown,
    )


def raw_property_to_model(
    raw: RawProperty,
    *,
    property_id: UUID | None = None,
    app_score: int | None = None,
    score_breakdown: dict | None = None,
) -> models.Property:
    scraped = raw.scraped_at or datetime.now(timezone.utc)
    return models.Property(
        id=property_id or uuid4(),
        portal=raw.portal.value if hasattr(raw.portal, "value") else str(raw.portal),
        external_id=raw.external_id,
        source_url=raw.source_url,
        title=raw.title,
        description=raw.description,
        operation=raw.operation.value if hasattr(raw.operation, "value") else raw.operation,
        property_type=(
            raw.property_type.value if hasattr(raw.property_type, "value") else raw.property_type
        ),
        price_amount=raw.price_amount,
        price_currency=raw.price_currency,
        address_raw=raw.address_raw,
        address_province=raw.address_province,
        address_locality=raw.address_locality,
        address_neighborhood=raw.address_neighborhood,
        geo_lat=raw.geo_lat,
        geo_lng=raw.geo_lng,
        rooms=raw.rooms,
        bathrooms=raw.bathrooms,
        parking=raw.parking,
        area_covered_m2=raw.area_covered_m2,
        area_total_m2=raw.area_total_m2,
        amenities=raw.amenities or [],
        images=raw.images or [],
        agent_name=raw.agent_name,
        agent_phone=raw.agent_phone,
        listed_at=raw.listed_at,
        scraped_at=scraped,
        app_score=app_score,
        score_breakdown=score_breakdown,
        raw_hints=raw.raw_hints,
    )


def apply_raw_to_row(
    row: models.Property,
    raw: RawProperty,
    *,
    app_score: int | None,
    score_breakdown: dict | None,
) -> None:
    row.source_url = raw.source_url
    row.title = raw.title
    row.description = raw.description
    row.operation = raw.operation.value if hasattr(raw.operation, "value") else raw.operation
    row.property_type = (
        raw.property_type.value if hasattr(raw.property_type, "value") else raw.property_type
    )
    row.price_amount = raw.price_amount
    row.price_currency = raw.price_currency
    row.address_raw = raw.address_raw
    row.address_province = raw.address_province
    row.address_locality = raw.address_locality
    row.address_neighborhood = raw.address_neighborhood
    row.geo_lat = raw.geo_lat
    row.geo_lng = raw.geo_lng
    row.rooms = raw.rooms
    row.bathrooms = raw.bathrooms
    row.parking = raw.parking
    row.area_covered_m2 = raw.area_covered_m2
    row.area_total_m2 = raw.area_total_m2
    row.amenities = raw.amenities or []
    row.images = raw.images or []
    row.agent_name = raw.agent_name
    row.agent_phone = raw.agent_phone
    row.listed_at = raw.listed_at
    row.scraped_at = raw.scraped_at or datetime.now(timezone.utc)
    row.app_score = app_score
    row.score_breakdown = score_breakdown
    row.raw_hints = raw.raw_hints


def interest_flags(
    *,
    state: str | None,
    user_score: int | None,
    comments: str | None,
    visit_status: str | None = None,
    visit_at: datetime | None = None,
) -> InterestFlags:
    visit = None
    if visit_status is not None:
        visit = Visit(
            status=VisitStatus(visit_status),
            at=visit_at.isoformat() if visit_at else None,
        )
    return InterestFlags(
        state=InterestState(state) if state else None,
        user_score=user_score,
        visit=visit,
        comments=comments,
        comment_flag=bool(comments and comments.strip()),
    )
