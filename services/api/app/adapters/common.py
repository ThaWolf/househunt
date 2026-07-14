"""Shared adapter helpers: optional curated fixtures + honest live/hybrid."""

from __future__ import annotations

import logging

import httpx

from app.adapters.base import unsupported_from_filters
from app.adapters.fixtures.loader import load_fixture_properties
from app.adapters.types import AdapterError, AdapterPaginationMeta, AdapterResult, RawProperty
from app.adapters.veracity import normalize_data_source
from app.config import Settings, get_settings
from app.schemas.common import AdapterErrorCode, AdapterStatus, DataSource, PortalId
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


def curated_fixture_slice(
    portal: PortalId,
    filters: SearchFilters,
    *,
    max_pages: int,
    page_size: int,
    mode: str,
) -> tuple[list[RawProperty], AdapterPaginationMeta]:
    """Return curated fixtures only (may be empty). Never invent listings."""
    raw_all = load_fixture_properties(portal)
    for item in raw_all:
        item.data_source = normalize_data_source(
            (item.raw_hints or {}).get("dataSource") or DataSource.fixture_curated
        )
    filtered = filter_raw_items(raw_all, filters)
    cap = max(page_size * max_pages, page_size)
    items = filtered[:cap]
    pages_fetched = 0
    if items:
        pages_fetched = min(max_pages, max(1, (len(items) + page_size - 1) // page_size))
    hint = DataSource.fixture_curated.value if items else None
    pagination = AdapterPaginationMeta(
        pages_fetched=pages_fetched,
        listings_raw=len(raw_all),
        listings_after_filter=len(items),
        max_pages=max_pages,
        page_size_hint=page_size,
        mode=mode,
        data_source_hint=hint,
    )
    return items, pagination


# Back-compat alias
dense_fixture_slice = curated_fixture_slice


def empty_result(
    portal: PortalId,
    filters: SearchFilters,
    *,
    settings: Settings,
    code: AdapterErrorCode,
    message: str,
    status: AdapterStatus = AdapterStatus.error,
    retryable: bool = True,
    mode: str = "live",
) -> AdapterResult:
    max_pages, page_size = _pagination_knobs(filters, settings)
    unsupported = unsupported_from_filters(filters, SUPPORTED_FILTERS)
    return AdapterResult(
        portal=portal,
        status=status,
        items=[],
        unsupported_filters=unsupported,
        pagination=AdapterPaginationMeta(
            pages_fetched=0,
            listings_raw=0,
            listings_after_filter=0,
            max_pages=max_pages,
            page_size_hint=page_size,
            mode=mode,
            data_source_hint=None,
        ),
        error=AdapterError(code=code, message=message, retryable=retryable),
    )


async def fetch_with_fixtures(
    portal: PortalId,
    filters: SearchFilters,
    *,
    settings: Settings | None = None,
    analysis_status: str = "needs_probe",
    try_live: bool = False,
) -> AdapterResult:
    """
    Fixtures-only OR honest live-empty path for portals without a live scraper.

    On bot_wall / probe failure: return empty + typed error — never invent listings.
    """
    _ = analysis_status
    _ = try_live
    settings = settings or get_settings()
    unsupported = unsupported_from_filters(filters, SUPPORTED_FILTERS)
    max_pages, page_size = _pagination_knobs(filters, settings)

    if settings.adapter_use_fixtures:
        items, pagination = curated_fixture_slice(
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
                message=(
                    "Serving curated fixtures (ADAPTER_USE_FIXTURES); "
                    f"{len(items)} items — empty set is valid (veracity > density)"
                ),
                retryable=True,
            ),
        )

    # Live preferred but no scraper for this portal → skip inventing
    url = PROBE_URLS[portal]
    ok, err = await probe_url(url, min(settings.adapter_timeout_seconds, 12.0))
    if not ok:
        code = AdapterErrorCode(err or "network")
        return empty_result(
            portal,
            filters,
            settings=settings,
            code=code,
            message=(
                f"Live path unavailable for {portal.value} ({code.value}); "
                "returning empty (no invented listings)"
            ),
            status=AdapterStatus.error,
            mode="live",
        )

    return empty_result(
        portal,
        filters,
        settings=settings,
        code=AdapterErrorCode.not_implemented,
        message=(
            f"Live scrape not implemented for {portal.value}; "
            "omitting results rather than inventing listings"
        ),
        status=AdapterStatus.skipped,
        retryable=False,
        mode="live",
    )


def live_ok_result(
    portal: PortalId,
    filters: SearchFilters,
    items: list[RawProperty],
    *,
    settings: Settings,
    pages_fetched: int = 1,
) -> AdapterResult:
    max_pages, page_size = _pagination_knobs(filters, settings)
    unsupported = unsupported_from_filters(filters, SUPPORTED_FILTERS)
    filtered = filter_raw_items(items, filters)
    for item in filtered:
        item.data_source = DataSource.live
    return AdapterResult(
        portal=portal,
        status=AdapterStatus.ok if filtered else AdapterStatus.partial,
        items=filtered,
        unsupported_filters=unsupported,
        pagination=AdapterPaginationMeta(
            pages_fetched=pages_fetched if filtered else 0,
            listings_raw=len(items),
            listings_after_filter=len(filtered),
            max_pages=max_pages,
            page_size_hint=page_size,
            mode="live",
            data_source_hint=DataSource.live.value if filtered else None,
        ),
        error=None,
    )
