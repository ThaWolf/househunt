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


class ImageRef(CamelModel):
    url: str
    order: int


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
