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
    want_type = (
        filters.property_type.value
        if hasattr(filters.property_type, "value")
        else str(filters.property_type)
    )
    out: list[RawProperty] = []
    for item in items:
        # iter-7: fuera de scope de tipo (depto/oficina/cochera/…) → descarta. Ver analysis/RCA.md.
        item_type = (
            item.property_type.value
            if hasattr(item.property_type, "value")
            else str(item.property_type)
        )
        if item_type != want_type:
            continue
        # iter-6: dato faltante (precio/ambientes) NO descarta — coverage. Ver analysis/RCA.md.
        if filters.price and (
            filters.price.min is not None or filters.price.max is not None
        ):
            if item.price_amount is not None:
                currency = (item.price_currency or "USD").upper()
                want = filters.price.currency.value if filters.price.currency else "USD"
                if currency != want:
                    continue
                if filters.price.min is not None and item.price_amount < filters.price.min:
                    continue
                if filters.price.max is not None and item.price_amount > filters.price.max:
                    continue
            # price_amount None → se mantiene (UI marca "precio a confirmar")
        if filters.rooms and filters.rooms.min is not None:
            if item.rooms is not None and item.rooms < filters.rooms.min:
                continue
            # rooms None → se mantiene (ML/C21 rara vez exponen ambientes en la card)
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


def _count_rooms_drops(
    items: list[RawProperty], filters: SearchFilters
) -> tuple[int, list[str]]:
    """Count items excluded by rooms.min. iter-6: rooms null se MANTIENE (no cuenta como drop).

    Solo cuenta `rooms` conocido y < min (rooms_below_min). Los nulls kept se informan
    aparte como `rooms_null` en reasons (para diagnóstico) sin sumar a dropped.
    """
    if filters.rooms is None or filters.rooms.min is None:
        return 0, []
    min_rooms = filters.rooms.min
    dropped = 0
    reasons: list[str] = []
    for item in items:
        if item.rooms is None:
            if "rooms_null" not in reasons:
                reasons.append("rooms_null")
        elif item.rooms < min_rooms:
            dropped += 1
            if "rooms_below_min" not in reasons:
                reasons.append("rooms_below_min")
    return dropped, reasons


def _maturity_for(
    portal: PortalId,
    *,
    status: AdapterStatus,
    filtered: list[RawProperty],
    error: AdapterError | None,
) -> str:
    from app.schemas.common import AdapterMaturity

    if error and error.code == AdapterErrorCode.not_implemented:
        return AdapterMaturity.not_implemented.value
    if error and error.code == AdapterErrorCode.auth_required:
        return AdapterMaturity.broken.value
    if filtered:
        return AdapterMaturity.live_ok.value
    if status == AdapterStatus.skipped:
        return AdapterMaturity.not_implemented.value
    if status == AdapterStatus.error and error and error.code in (
        AdapterErrorCode.bot_wall,
        AdapterErrorCode.network,
        AdapterErrorCode.parse,
    ):
        return AdapterMaturity.live_partial.value
    return AdapterMaturity.live_partial.value


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
    maturity: str | None = None,
) -> AdapterResult:
    max_pages, page_size = _pagination_knobs(filters, settings)
    unsupported = unsupported_from_filters(filters, SUPPORTED_FILTERS)
    err = AdapterError(code=code, message=message, retryable=retryable)
    mat = maturity or _maturity_for(portal, status=status, filtered=[], error=err)
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
        error=err,
        raw_count=0,
        rooms_dropped=0,
        rooms_filter_wiped=False,
        maturity=mat,
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
            raw_count=pagination.listings_raw,
            rooms_dropped=0,
            rooms_filter_wiped=False,
            maturity="live_partial",
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
        maturity="not_implemented",
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
    rooms_dropped, drop_reasons = _count_rooms_drops(items, filters)
    filtered = filter_raw_items(items, filters)
    for item in filtered:
        item.data_source = DataSource.live

    rooms_min_set = filters.rooms is not None and filters.rooms.min is not None
    rooms_wipe = (
        rooms_min_set
        and len(items) > 0
        and len(filtered) == 0
        and rooms_dropped == len(items)
    )

    error = None
    if rooms_wipe:
        error = AdapterError(
            code=AdapterErrorCode.filtered_rooms_null,
            message=(
                f"{portal.value}: scraped {len(items)} listings but rooms.min "
                f"filter dropped all (null or below min)"
            ),
            retryable=False,
        )

    status = AdapterStatus.ok if filtered else AdapterStatus.partial
    mat = _maturity_for(portal, status=status, filtered=filtered, error=error)
    return AdapterResult(
        portal=portal,
        status=status,
        items=filtered,
        unsupported_filters=unsupported,
        pagination=AdapterPaginationMeta(
            pages_fetched=pages_fetched if items else 0,
            listings_raw=len(items),
            listings_after_filter=len(filtered),
            max_pages=max_pages,
            page_size_hint=page_size,
            mode="live",
            data_source_hint=DataSource.live.value if filtered else None,
        ),
        error=error,
        raw_count=len(items),
        rooms_dropped=rooms_dropped,
        rooms_filter_wiped=rooms_wipe,
        maturity=mat,
        drop_reasons=drop_reasons,
    )
