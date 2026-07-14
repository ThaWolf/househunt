"""Shared adapter helpers: fixtures + optional live probe."""

from __future__ import annotations

import logging

import httpx

from app.adapters.base import unsupported_from_filters
from app.adapters.fixtures.loader import load_fixture_properties
from app.adapters.types import AdapterError, AdapterResult, RawProperty
from app.config import Settings, get_settings
from app.schemas.common import AdapterErrorCode, AdapterStatus, PortalId
from app.schemas.property import SearchFilters

logger = logging.getLogger(__name__)

PROBE_URLS: dict[PortalId, str] = {
    PortalId.zonaprop: "https://www.zonaprop.com.ar/casas-venta.html",
    PortalId.argenprop: "https://www.argenprop.com/",
    PortalId.mercadolibre: "https://inmuebles.mercadolibre.com.ar/",
    PortalId.remax: "https://www.remax.com.ar/",
    PortalId.century21: "https://century21.com.ar/busqueda/tipo_casa/operacion_venta",
}

SUPPORTED_FILTERS = {
    "price",
    "rooms",
    "bathrooms",
    "area",
    "parking",
    "query",
    "geo.custom",
    "location",
}


def filter_raw_items(items: list[RawProperty], filters: SearchFilters) -> list[RawProperty]:
    """Light adapter-side filter. Merge post-filter is authoritative for geo/price/rooms."""
    from app.geo.match import location_matches_listing
    from app.search.postfilter import resolve_location

    location = resolve_location(filters)
    out: list[RawProperty] = []
    for item in items:
        if filters.price:
            currency = (item.price_currency or "USD").upper()
            want = filters.price.currency.value if filters.price.currency else "USD"
            if currency != want:
                continue
            if filters.price.min is not None and (
                item.price_amount is None or item.price_amount < filters.price.min
            ):
                continue
            if filters.price.max is not None and (
                item.price_amount is None or item.price_amount > filters.price.max
            ):
                continue
        if filters.rooms and filters.rooms.min is not None:
            if item.rooms is None or item.rooms < filters.rooms.min:
                continue
        if location is not None:
            if not location_matches_listing(
                location,
                address_locality=item.address_locality,
                address_neighborhood=item.address_neighborhood,
                address_raw=item.address_raw,
                title=item.title,
            ):
                continue
        if filters.query:
            q = filters.query.lower()
            hay = f"{item.title} {item.description or ''}".lower()
            if q not in hay:
                continue
        out.append(item)
    return out


async def probe_url(url: str, timeout: float) -> tuple[bool, str | None]:
    """Return (ok, error_code)."""
    try:
        async with httpx.AsyncClient(
            timeout=timeout,
            follow_redirects=True,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                )
            },
        ) as client:
            resp = await client.get(url)
            if resp.status_code == 403:
                return False, "bot_wall"
            if resp.status_code == 429:
                return False, "rate_limit"
            if resp.status_code >= 500:
                return False, "network"
            if resp.status_code >= 400:
                return False, "network"
            return True, None
    except httpx.TimeoutException:
        return False, "network"
    except httpx.HTTPError:
        return False, "network"


async def fetch_with_fixtures(
    portal: PortalId,
    filters: SearchFilters,
    *,
    settings: Settings | None = None,
    analysis_status: str = "needs_probe",
    try_live: bool = False,
) -> AdapterResult:
    settings = settings or get_settings()
    unsupported = unsupported_from_filters(filters, SUPPORTED_FILTERS)

    if settings.adapter_use_fixtures or not try_live:
        items = filter_raw_items(load_fixture_properties(portal), filters)
        # fixtures_only is informational when flag on — still status ok for MVP UX
        return AdapterResult(
            portal=portal,
            status=AdapterStatus.ok if items else AdapterStatus.partial,
            items=items,
            unsupported_filters=unsupported,
            error=AdapterError(
                code=AdapterErrorCode.fixtures_only,
                message="Serving fixture listings (ADAPTER_USE_FIXTURES or live scrape deferred)",
                retryable=True,
            )
            if settings.adapter_use_fixtures
            else None,
        )

    # Live probe path (minimal): check entrypoint; on success still fall back to fixtures parse
    url = PROBE_URLS[portal]
    ok, err = await probe_url(url, settings.adapter_timeout_seconds)
    items = filter_raw_items(load_fixture_properties(portal), filters)
    if not ok:
        code = AdapterErrorCode(err or "network")
        # Degrade to fixtures with partial
        return AdapterResult(
            portal=portal,
            status=AdapterStatus.partial if items else AdapterStatus.error,
            items=items,
            unsupported_filters=unsupported,
            error=AdapterError(
                code=code,
                message=f"Live probe failed for {portal.value}; returning fixtures",
                retryable=code in (AdapterErrorCode.network, AdapterErrorCode.rate_limit),
            ),
        )
    return AdapterResult(
        portal=portal,
        status=AdapterStatus.ok,
        items=items,
        unsupported_filters=unsupported,
        error=None,
    )
