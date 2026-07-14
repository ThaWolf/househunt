"""Property and search DTOs."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import Field, field_validator, model_validator

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
    score_breakdown: ScoreBreakdown | None = None


class GeoFilters(CamelModel):
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


class ReportStub(CamelModel):
    summary: str | None = None
    risk_hits: list[str] = Field(default_factory=list)
    generated_at: datetime | None = None


class PropertyDetailResponse(CamelModel):
    property: PropertyDTO
    interest: InterestFlags
    report: ReportStub | None = None
    user_fields_enabled: bool
