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
    """iter-6: precio desconocido NO descarta (coverage). Estricto solo con dato conocido y misma moneda."""
    price = filters.price
    if price is None:
        return True
    if price.min is None and price.max is None:
        return True
    if row.price_amount is None:
        # Precio no informado (ej. "Consultar precio"): se muestra igual, se marca en UI.
        return True
    currency = (row.price_currency or "USD").upper()
    want = price.currency.value if price.currency else "USD"
    if currency != want:
        # Moneda distinta a la pedida y monto conocido → no comparable, se descarta.
        return False
    amount = float(row.price_amount)
    if price.min is not None and amount < price.min:
        return False
    if price.max is not None and amount > price.max:
        return False
    return True


def passes_rooms_min(row: models.Property, filters: SearchFilters) -> bool:
    """iter-6: rooms desconocido NO descarta (coverage). Solo se excluye si rooms conocido < min.

    Antes (E7) se descartaba `rooms is None`, lo que borraba en seco a ML/C21 (que rara vez
    exponen ambientes en la card) → `raw N→0`. Ver lanes/analysis/RCA.md.
    """
    if filters.rooms is None or filters.rooms.min is None:
        return True
    if row.rooms is None:
        return True
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


def passes_type(row: models.Property, filters: SearchFilters) -> bool:
    """iter-7: MVP scope = casas. Descarta lo que no sea el tipo pedido (default house).

    Choke point único para todos los portales: aunque C21/Remax devuelvan
    departamentos/oficinas/cocheras, acá se filtran. Ver lanes/analysis/RCA.md.
    """
    want = (
        filters.property_type.value
        if hasattr(filters.property_type, "value")
        else str(filters.property_type)
    )
    have = (
        row.property_type.value
        if hasattr(row.property_type, "value")
        else str(row.property_type)
    )
    return have == want


def passes_post_filters(row: models.Property, filters: SearchFilters) -> bool:
    location = resolve_location(filters)
    return (
        passes_type(row, filters)
        and passes_location(row, location)
        and passes_price(row, filters)
        and passes_rooms_min(row, filters)
    )


def filter_merged(rows: list[models.Property], filters: SearchFilters) -> list[models.Property]:
    return [r for r in rows if passes_post_filters(r, filters)]
