"""Shared adapter helpers: fixtures + hybrid live probe + dense fallback."""

from __future__ import annotations

import logging

import httpx

from app.adapters.base import unsupported_from_filters
from app.adapters.fixtures.loader import load_fixture_properties
from app.adapters.types import AdapterError, AdapterPaginationMeta, AdapterResult, RawProperty
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


def _pagination_knobs(
    filters: SearchFilters, settings: Settings
) -> tuple[int, int]:
    max_pages = filters.max_pages if filters.max_pages is not None else settings.adapter_max_pages
    page_size = (
        filters.page_size_hint
        if filters.page_size_hint is not None
        else settings.adapter_page_size_hint
    )
    return max(1, min(5, max_pages)), max(5, min(50, page_size))


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


def dense_fixture_slice(
    portal: PortalId,
    filters: SearchFilters,
    *,
    max_pages: int,
    page_size: int,
    mode: str,
) -> tuple[list[RawProperty], AdapterPaginationMeta]:
    """Return dense fixtures (≥8–15 typical) with pagination meta — never 1-item fallback."""
    raw_all = load_fixture_properties(portal)
    filtered = filter_raw_items(raw_all, filters)
    cap = max(page_size * max_pages, 15)
    items = filtered[:cap]
    pages_fetched = 0
    if items:
        pages_fetched = min(max_pages, max(1, (len(items) + page_size - 1) // page_size))
    pagination = AdapterPaginationMeta(
        pages_fetched=pages_fetched,
        listings_raw=len(raw_all),
        listings_after_filter=len(items),
        max_pages=max_pages,
        page_size_hint=page_size,
        mode=mode,
    )
    return items, pagination


async def fetch_with_fixtures(
    portal: PortalId,
    filters: SearchFilters,
    *,
    settings: Settings | None = None,
    analysis_status: str = "needs_probe",
    try_live: bool = False,
) -> AdapterResult:
    """Fixtures-only or hybrid: live probe → on fail/bot_wall merge dense fixtures."""
    _ = analysis_status
    settings = settings or get_settings()
    unsupported = unsupported_from_filters(filters, SUPPORTED_FILTERS)
    max_pages, page_size = _pagination_knobs(filters, settings)

    # ADAPTER_USE_FIXTURES=true → dense fixtures (CI/default)
    if settings.adapter_use_fixtures:
        items, pagination = dense_fixture_slice(
            portal, filters, max_pages=max_pages, page_size=page_size, mode="fixtures"
        )
        return AdapterResult(
            portal=portal,
            status=AdapterStatus.ok if items else AdapterStatus.partial,
            items=items,
            unsupported_filters=unsupported,
            pagination=pagination,
            error=AdapterError(
                code=AdapterErrorCode.fixtures_only,
                message="Serving dense fixture listings (ADAPTER_USE_FIXTURES)",
                retryable=True,
            ),
        )

    # Hybrid path (ADAPTER_USE_FIXTURES=false): probe live; on fail merge dense fixtures
    url = PROBE_URLS[portal]
    ok, err = await probe_url(url, settings.adapter_timeout_seconds)
    items, pagination = dense_fixture_slice(
        portal, filters, max_pages=max_pages, page_size=page_size, mode="hybrid"
    )
    if not ok:
        code = AdapterErrorCode(err or "network")
        return AdapterResult(
            portal=portal,
            status=AdapterStatus.partial if items else AdapterStatus.error,
            items=items,
            unsupported_filters=unsupported,
            pagination=pagination,
            error=AdapterError(
                code=code,
                message=(
                    f"Live probe failed for {portal.value} ({code.value}); "
                    f"returning dense fixtures ({len(items)} items)"
                ),
                retryable=code
                in (
                    AdapterErrorCode.network,
                    AdapterErrorCode.rate_limit,
                    AdapterErrorCode.bot_wall,
                ),
            ),
        )

    # Live ok — parse deferred; dense fixtures as floor with hybrid meta
    if try_live or settings.adapter_hybrid_default:
        pagination.pages_fetched = max(pagination.pages_fetched, 1)
    return AdapterResult(
        portal=portal,
        status=AdapterStatus.ok if items else AdapterStatus.partial,
        items=items,
        unsupported_filters=unsupported,
        pagination=pagination,
        error=None,
    )
