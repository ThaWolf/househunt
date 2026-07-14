"""Post-filter merge: location + price + rooms.min (iter 2)."""

from __future__ import annotations

from app.db import models
from app.geo.match import location_matches_listing
from app.schemas.property import Location, SearchFilters


def resolve_location(filters: SearchFilters) -> Location | None:
    """Canonical location from iter-2 field or legacy geo.custom."""
    if filters.location is not None:
        return filters.location
    if filters.geo.mode.value == "custom" and filters.geo.locality:
        return Location(
            query=filters.geo.locality,
            locality=filters.geo.locality,
            district=None,
            province=filters.geo.province or "Buenos Aires",
            country="AR",
            place_id=None,
        )
    return None


def passes_price(row: models.Property, filters: SearchFilters) -> bool:
    price = filters.price
    if price is None:
        return True
    if price.min is None and price.max is None:
        return True
    if row.price_amount is None:
        return False
    currency = (row.price_currency or "USD").upper()
    want = price.currency.value if price.currency else "USD"
    if currency != want:
        return False
    amount = float(row.price_amount)
    if price.min is not None and amount < price.min:
        return False
    if price.max is not None and amount > price.max:
        return False
    return True


def passes_rooms_min(row: models.Property, filters: SearchFilters) -> bool:
    """E7: rooms null + rooms.min set → exclude."""
    if filters.rooms is None or filters.rooms.min is None:
        return True
    if row.rooms is None:
        return False
    return row.rooms >= filters.rooms.min


def passes_location(row: models.Property, location: Location | None) -> bool:
    if location is None:
        return True
    return location_matches_listing(
        location,
        address_locality=row.address_locality,
        address_neighborhood=row.address_neighborhood,
        address_raw=row.address_raw,
        title=row.title,
    )


def passes_post_filters(row: models.Property, filters: SearchFilters) -> bool:
    location = resolve_location(filters)
    return (
        passes_location(row, location)
        and passes_price(row, filters)
        and passes_rooms_min(row, filters)
    )


def filter_merged(rows: list[models.Property], filters: SearchFilters) -> list[models.Property]:
    return [r for r in rows if passes_post_filters(r, filters)]
