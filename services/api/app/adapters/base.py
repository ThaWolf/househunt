"""PortalAdapter protocol + registry helpers."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from app.adapters.types import AdapterResult
from app.schemas.common import PortalId
from app.schemas.property import SearchFilters


@runtime_checkable
class PortalAdapter(Protocol):
    portal: PortalId
    analysis_status: str

    async def fetch(self, filters: SearchFilters) -> AdapterResult:
        ...


def unsupported_from_filters(filters: SearchFilters, supported: set[str]) -> list[str]:
    """Return filter keys present but not supported by this portal."""
    present: list[str] = []
    if filters.price and (filters.price.min is not None or filters.price.max is not None):
        present.append("price")
    if filters.rooms and filters.rooms.min is not None:
        present.append("rooms")
    if filters.bathrooms and filters.bathrooms.min is not None:
        present.append("bathrooms")
    if filters.area and (
        filters.area.covered_m2_min is not None or filters.area.total_m2_min is not None
    ):
        present.append("area")
    if filters.parking and filters.parking.min is not None:
        present.append("parking")
    if filters.query:
        present.append("query")
    if filters.location is not None:
        present.append("location")
    elif filters.geo.mode.value == "custom":
        present.append("geo.custom")
    return [f for f in present if f not in supported]

