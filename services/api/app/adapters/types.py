"""Adapter types and RawProperty intermediate."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from app.schemas.common import (
    AdapterErrorCode,
    AdapterStatus,
    DataSource,
    Operation,
    PortalId,
    PropertyType,
)
from app.schemas.property import SearchFilters


@dataclass
class AdapterError:
    code: AdapterErrorCode
    message: str
    retryable: bool = False


@dataclass
class RawProperty:
    """Adapter output before DB id assignment / scoring."""

    portal: PortalId
    external_id: str
    source_url: str
    title: str
    description: str | None = None
    operation: Operation = Operation.buy
    property_type: PropertyType = PropertyType.house
    price_amount: float | None = None
    price_currency: str | None = "USD"
    address_raw: str | None = None
    address_province: str | None = None
    address_locality: str | None = None
    address_neighborhood: str | None = None
    geo_lat: float | None = None
    geo_lng: float | None = None
    rooms: int | None = None
    bathrooms: int | None = None
    parking: int | None = None
    area_covered_m2: float | None = None
    area_total_m2: float | None = None
    amenities: list[str] = field(default_factory=list)
    images: list[dict[str, Any]] = field(default_factory=list)
    agent_name: str | None = None
    agent_phone: str | None = None
    listed_at: datetime | None = None
    scraped_at: datetime | None = None
    data_source: DataSource = DataSource.live
    raw_hints: dict[str, Any] | None = None

    def __post_init__(self) -> None:
        if self.scraped_at is None:
            self.scraped_at = datetime.now(timezone.utc)


@dataclass
class AdapterPaginationMeta:
    pages_fetched: int = 0
    listings_raw: int = 0
    listings_after_filter: int = 0
    max_pages: int = 3
    page_size_hint: int = 20
    mode: str | None = None  # fixtures | live | hybrid
    data_source_hint: str | None = None  # live | fixture_curated | demo_stub | mixed


@dataclass
class AdapterResult:
    portal: PortalId
    status: AdapterStatus
    items: list[RawProperty] = field(default_factory=list)
    unsupported_filters: list[str] = field(default_factory=list)
    pagination: AdapterPaginationMeta | None = None
    error: AdapterError | None = None


# Re-export for convenience
__all__ = [
    "AdapterError",
    "AdapterPaginationMeta",
    "AdapterResult",
    "RawProperty",
    "SearchFilters",
    "PortalId",
    "AdapterStatus",
    "AdapterErrorCode",
]
