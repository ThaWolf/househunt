"""Property and search DTOs."""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import Field, model_validator

from app.schemas.common import (
    Address,
    Agent,
    Area,
    CamelModel,
    Currency,
    GeoMode,
    GeoPoint,
    ImageRef,
    InterestFlags,
    Money,
    Operation,
    PortalId,
    PropertyType,
    ScoreBreakdown,
    AdapterErrorCode,
    AdapterStatus,
)


class PropertyDTO(CamelModel):
    id: UUID
    portal: PortalId
    external_id: str
    source_url: str
    title: str
    description: str | None = None
    operation: Operation
    property_type: PropertyType
    price: Money | None = None
    address: Address | None = None
    geo: GeoPoint | None = None
    rooms: int | None = None
    bathrooms: int | None = None
    parking: int | None = None
    area: Area | None = None
    amenities: list[str] = Field(default_factory=list)
    images: list[ImageRef] = Field(default_factory=list)
    agent: Agent | None = None
    listed_at: datetime | None = None
    scraped_at: datetime
    app_score: int | None = None
    # Deprecated for FE UI — prefer HumanizedReport on detail
    score_breakdown: ScoreBreakdown | None = None


class Location(CamelModel):
    query: str
    locality: str
    district: str | None = None
    province: str
    country: str = "AR"
    place_id: str | None = None


class GeoPlace(Location):
    label: str
    aliases: list[str] = Field(default_factory=list)


class GeoSuggestResponse(CamelModel):
    items: list[GeoPlace]


class GeoFilters(CamelModel):
    """Legacy iter-1 geo. Prefer SearchFilters.location."""

    mode: GeoMode = GeoMode.gba
    province: str | None = None
    locality: str | None = None
    neighborhood: str | None = None

    @model_validator(mode="after")
    def custom_requires_province(self) -> GeoFilters:
        if self.mode == GeoMode.custom and not self.province:
            raise ValueError("province is required when geo.mode=custom")
        return self


class PriceFilters(CamelModel):
    min: float | None = None
    max: float | None = None
    currency: Currency = Currency.USD


class MinIntFilter(CamelModel):
    min: int | None = None


class AreaFilters(CamelModel):
    covered_m2_min: float | None = None
    total_m2_min: float | None = None


class SearchFilters(CamelModel):
    operation: Operation = Operation.buy
    property_type: PropertyType = PropertyType.house
    location: Location | None = None
    geo: GeoFilters = Field(default_factory=GeoFilters)
    price: PriceFilters | None = None
    rooms: MinIntFilter | None = None
    bathrooms: MinIntFilter | None = None
    area: AreaFilters | None = None
    parking: MinIntFilter | None = None
    portals: list[PortalId] | None = None
    query: str | None = None


class PortalSearchError(CamelModel):
    code: AdapterErrorCode
    message: str
    retryable: bool = False


class PortalSearchResult(CamelModel):
    portal: PortalId
    status: AdapterStatus
    count: int = 0
    unsupported_filters: list[str] = Field(default_factory=list)
    error: PortalSearchError | None = None


class SearchResultItem(PropertyDTO):
    interest: InterestFlags | None = None


class SearchResponse(CamelModel):
    search_id: UUID
    filters: SearchFilters
    items: list[SearchResultItem]
    portal_results: list[PortalSearchResult]
    took_ms: int


class ScoreComponent(CamelModel):
    id: Literal["attrs", "area", "zone", "priceFit", "risk"]
    label: str
    score: float
    max_score: float = 100
    bar_pct: float
    note: str | None = None


class RiskHit(CamelModel):
    term: str
    label: str


class HumanizedReport(CamelModel):
    summary: str | None = None
    app_score: int
    components: list[ScoreComponent] = Field(default_factory=list)
    risk_hits: list[RiskHit] = Field(default_factory=list)
    generated_at: datetime


# Backward-compat alias
ReportStub = HumanizedReport


class PropertyDetailResponse(CamelModel):
    property: PropertyDTO
    interest: InterestFlags
    report: HumanizedReport
    user_fields_enabled: bool
