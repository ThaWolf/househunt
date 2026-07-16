"""Shared enums, camelCase helpers, error envelope."""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


def to_camel(name: str) -> str:
    parts = name.split("_")
    return parts[0] + "".join(p.capitalize() for p in parts[1:])


class CamelModel(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
    )


class PortalId(str, Enum):
    zonaprop = "zonaprop"
    argenprop = "argenprop"
    mercadolibre = "mercadolibre"
    remax = "remax"
    century21 = "century21"
    # iter-9: publicación agregada por el usuario desde una URL de host no reconocido
    external = "external"


class Operation(str, Enum):
    buy = "buy"


class PropertyType(str, Enum):
    house = "house"
    apartment = "apartment"
    land = "land"
    other = "other"


class Currency(str, Enum):
    USD = "USD"
    ARS = "ARS"


class InterestState(str, Enum):
    active = "active"
    archived = "archived"


class ListMemberRole(str, Enum):
    owner = "owner"
    collaborator = "collaborator"


class VisitStatus(str, Enum):
    none = "none"
    scheduled = "scheduled"
    visited = "visited"


class GeoMode(str, Enum):
    gba = "gba"
    custom = "custom"


class AdapterStatus(str, Enum):
    ok = "ok"
    partial = "partial"
    error = "error"
    skipped = "skipped"


class AdapterErrorCode(str, Enum):
    bot_wall = "bot_wall"
    rate_limit = "rate_limit"
    parse = "parse"
    network = "network"
    not_implemented = "not_implemented"
    fixtures_only = "fixtures_only"
    auth_required = "auth_required"
    filtered_rooms_null = "filtered_rooms_null"


class AdapterMaturity(str, Enum):
    live_ok = "live_ok"
    live_partial = "live_partial"
    not_implemented = "not_implemented"
    broken = "broken"


class EmptyStateKind(str, Enum):
    ok = "ok"
    no_inventory = "no_inventory"
    rooms_filter_wipe = "rooms_filter_wipe"
    all_partial = "all_partial"
    all_skipped = "all_skipped"
    all_error = "all_error"


class SearchModeHint(str, Enum):
    fixtures = "fixtures"
    live = "live"
    hybrid = "hybrid"


class PriceStance(str, Enum):
    low = "low"
    fair = "fair"
    high = "high"
    unknown = "unknown"


class ZonePlaceSource(str, Enum):
    seed = "seed"
    places = "places"
    stub = "stub"


class ZoneProvider(str, Enum):
    none = "none"
    seed = "seed"
    google_places = "google_places"


class GeocodeStatus(str, Enum):
    exact = "exact"
    approximate = "approximate"
    missing = "missing"
    stub = "stub"


class GeocodeSource(str, Enum):
    portal = "portal"
    seed_locality = "seed_locality"
    places = "places"
    manual = "manual"


class MapPinKind(str, Enum):
    listing = "listing"
    poi = "poi"
    commerce = "commerce"
    transit = "transit"


class MapProvider(str, Enum):
    google_embed = "google_embed"
    external_only = "external_only"


class ErrorResponse(CamelModel):
    code: str
    message: str
    details: dict[str, Any] | None = None


class PageMeta(CamelModel):
    total: int
    limit: int
    offset: int


class Money(CamelModel):
    amount: float | None = None
    currency: Currency | None = None
    period: None = None


class Address(CamelModel):
    raw: str | None = None
    province: str | None = None
    locality: str | None = None
    neighborhood: str | None = None


class GeoPoint(CamelModel):
    lat: float | None = None
    lng: float | None = None


class Area(CamelModel):
    covered_m2: float | None = None
    total_m2: float | None = None


class ImageKind(str, Enum):
    source = "source"
    proxied = "proxied"
    placeholder = "placeholder"


class DataSource(str, Enum):
    live = "live"
    fixture_curated = "fixture_curated"
    demo_stub = "demo_stub"
    # iter-9: publicación agregada por el usuario vía URL (extracción externa)
    external = "external"


class ImageRef(CamelModel):
    url: str
    order: int
    kind: ImageKind  # E19 — required; no silent default to source


class Agent(CamelModel):
    name: str | None = None
    phone: str | None = None


class ScoreBreakdown(CamelModel):
    attrs: float = 0
    area: float = 0
    zone: float = 0
    price_fit: float = 0
    risk_penalty: float = 0
    weights: dict[str, float] = Field(default_factory=dict)
    risk_hits: list[str] = Field(default_factory=list)


class Visit(CamelModel):
    status: VisitStatus
    at: str | None = None  # ISO datetime


class InterestFlags(CamelModel):
    state: InterestState | None = None
    user_score: int | None = None
    visit: Visit | None = None
    comments: str | None = None
    comment_flag: bool = False
