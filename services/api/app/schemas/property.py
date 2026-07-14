"""Property and search DTOs."""

from __future__ import annotations

from datetime import datetime
from typing import Literal  # noqa: F401 — used by ScoreComponent / density hints
from uuid import UUID

from pydantic import Field, model_validator

from app.schemas.common import (
    Address,
    AdapterErrorCode,
    AdapterMaturity,
    AdapterStatus,
    Agent,
    Area,
    CamelModel,
    Currency,
    DataSource,
    EmptyStateKind,
    GeoMode,
    GeoPoint,
    GeocodeSource,
    GeocodeStatus,
    ImageRef,
    InterestFlags,
    MapPinKind,
    MapProvider,
    Money,
    Operation,
    PortalId,
    PriceStance,
    PropertyType,
    ScoreBreakdown,
    SearchModeHint,
    ZonePlaceSource,
    ZoneProvider,
)


class PropertyDTO(CamelModel):
    id: UUID
    portal: PortalId
    external_id: str
    source_url: str
    data_source: DataSource
    title: str
    description: str | None = None
    description_excerpt: str | None = None
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
    max_pages: int | None = Field(default=3, ge=1, le=5)
    page_size_hint: int | None = Field(default=20, ge=5, le=50)


class PortalSearchError(CamelModel):
    code: AdapterErrorCode
    message: str
    retryable: bool = False


class AdapterPaginationMetaDTO(CamelModel):
    pages_fetched: int = 0
    listings_raw: int = 0
    listings_after_filter: int = 0
    max_pages: int = 3
    page_size_hint: int = 20
    mode: SearchModeHint | None = None
    data_source_hint: DataSource | Literal["mixed"] | None = None


class PortalDiagnostics(CamelModel):
    raw_count: int = 0
    after_filter_count: int = 0
    rooms_dropped: int = 0
    rooms_filter_wiped: bool = False
    maturity: AdapterMaturity = AdapterMaturity.live_partial
    drop_reasons: list[
        Literal["rooms_null", "rooms_below_min", "geo", "price", "other"]
    ] = Field(default_factory=list)


class PortalSearchResult(CamelModel):
    portal: PortalId
    status: AdapterStatus
    count: int = 0
    unsupported_filters: list[str] = Field(default_factory=list)
    pagination: AdapterPaginationMetaDTO | None = None
    diagnostics: PortalDiagnostics | None = None
    maturity: AdapterMaturity | None = None
    error: PortalSearchError | None = None


class SearchDensity(CamelModel):
    total_items: int
    portals_with_multi_page: int = 0
    mode: SearchModeHint = SearchModeHint.hybrid
    data_source_hint: DataSource | Literal["mixed"] | None = None


class EmptyStateHint(CamelModel):
    kind: EmptyStateKind
    title: str
    body: str
    hint: str | None = None


class PortalDiagnosticsSlice(CamelModel):
    portal: PortalId
    raw_count: int = 0
    after_filter_count: int = 0
    rooms_dropped: int = 0
    rooms_filter_wiped: bool = False
    maturity: AdapterMaturity = AdapterMaturity.live_partial
    status: AdapterStatus
    error_code: AdapterErrorCode | None = None


class SearchDiagnostics(CamelModel):
    raw_count: int = 0
    after_filter_count: int = 0
    rooms_dropped: int = 0
    rooms_filter_wiped: bool = False
    portals: list[PortalDiagnosticsSlice] = Field(default_factory=list)
    empty_state: EmptyStateHint | None = None


class SearchResultItem(PropertyDTO):
    interest: InterestFlags | None = None


class SearchResponse(CamelModel):
    search_id: UUID
    filters: SearchFilters
    items: list[SearchResultItem]
    portal_results: list[PortalSearchResult]
    diagnostics: SearchDiagnostics
    density: SearchDensity | None = None
    took_ms: int


class ScoreComponent(CamelModel):
    id: Literal["attrs", "area", "zone", "priceFit", "riskSafety", "risk"]
    label: str
    help_text: str
    score: float
    max_score: float = 100
    bar_pct: float
    summary: str | None = None
    note: str | None = None  # legacy alias of summary


class RiskHit(CamelModel):
    keyword: str | None = None
    term: str | None = None  # legacy alias
    weight: float = 1.0
    label: str | None = None

    @model_validator(mode="after")
    def sync_keyword_term(self) -> RiskHit:
        if self.keyword is None and self.term is not None:
            self.keyword = self.term
        if self.term is None and self.keyword is not None:
            self.term = self.keyword
        return self


class PriceNarrative(CamelModel):
    summary: str
    stance: PriceStance
    peers_sample_size: int
    peer_median_amount: float | None = None
    currency: Currency | None = None


class ZonePlace(CamelModel):
    id: str
    name: str
    category: str
    lat: float | None = None
    lng: float | None = None
    distance_m: float | None = None
    source: ZonePlaceSource = ZonePlaceSource.seed


class ZoneGeo(CamelModel):
    lat: float | None = None
    lng: float | None = None
    geocode_status: GeocodeStatus
    geocode_source: GeocodeSource | None = None


class ZoneReport(CamelModel):
    summary: str | None = None
    poi: list[ZonePlace] = Field(default_factory=list)
    commerce: list[ZonePlace] = Field(default_factory=list)
    transit: list[ZonePlace] = Field(default_factory=list)
    geo: ZoneGeo
    generated_at: datetime
    provider: ZoneProvider = ZoneProvider.seed


class MapPin(CamelModel):
    id: str
    lat: float
    lng: float
    label: str
    kind: MapPinKind


class MapEmbed(CamelModel):
    center: GeoPoint
    zoom: int | None = 14
    pins: list[MapPin] = Field(default_factory=list)
    embed_url: str | None = None
    external_url: str
    provider: MapProvider = MapProvider.external_only


class HumanizedReport(CamelModel):
    summary: str | None = None
    app_score: int
    components: list[ScoreComponent] = Field(default_factory=list)
    risk_hits: list[RiskHit] = Field(default_factory=list)
    price_narrative: PriceNarrative | None = None
    zone_report: ZoneReport | None = None
    map: MapEmbed | None = None
    generated_at: datetime


# Backward-compat alias
ReportStub = HumanizedReport


class PropertyDetailResponse(CamelModel):
    property: PropertyDTO
    interest: InterestFlags
    report: HumanizedReport
    user_fields_enabled: bool
