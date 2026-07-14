"""Search orchestrator: fan-out adapters, merge, cache upsert."""

from __future__ import annotations

import asyncio
import time
import uuid
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.registry import run_adapter
from app.adapters.types import AdapterResult, RawProperty
from app.config import Settings, get_settings
from app.db import models
from app.mappers import apply_raw_to_row, interest_flags, property_to_dto, raw_property_to_model
from app.schemas.common import (
    AdapterErrorCode,
    AdapterMaturity,
    AdapterStatus,
    EmptyStateKind,
    PortalId,
    SearchModeHint,
)
from app.schemas.property import (
    AdapterPaginationMetaDTO,
    EmptyStateHint,
    PortalDiagnostics,
    PortalDiagnosticsSlice,
    PortalSearchError,
    PortalSearchResult,
    SearchDensity,
    SearchDiagnostics,
    SearchFilters,
    SearchResponse,
    SearchResultItem,
)
from app.scoring.appscore import compute_appscore
from app.search.postfilter import filter_merged, passes_rooms_min

_EMPTY_COPY: dict[EmptyStateKind, tuple[str, str, str | None]] = {
    EmptyStateKind.rooms_filter_wipe: (
        "Sin resultados con ese filtro de ambientes",
        "Encontramos avisos, pero ninguno pasó el mínimo de habitaciones "
        "(faltaba dato o eran menos). Probá bajar ambientes o buscar sin mínimo.",
        "Probá rooms.min=2 o sin mínimo de ambientes",
    ),
    EmptyStateKind.no_inventory: (
        "Sin avisos en esta zona",
        "Los portales no devolvieron inventario para esta búsqueda.",
        None,
    ),
    EmptyStateKind.all_partial: (
        "Búsqueda incompleta",
        "Varios portales respondieron parcial; no hay listados que cumplan los filtros.",
        None,
    ),
    EmptyStateKind.all_skipped: (
        "Portales no disponibles",
        "Los scrapers están deshabilitados o aún no implementados.",
        None,
    ),
    EmptyStateKind.all_error: (
        "No pudimos consultar portales",
        "Errores de red, anti-bot o auth. Reintentá en unos minutos.",
        None,
    ),
}


def _maturity_enum(value: str | None) -> AdapterMaturity:
    if not value:
        return AdapterMaturity.live_partial
    try:
        return AdapterMaturity(value)
    except ValueError:
        return AdapterMaturity.live_partial


def _empty_state_for(
    items_count: int,
    portal_results: list[PortalSearchResult],
    *,
    rooms_filter_wiped: bool,
    raw_count: int,
) -> EmptyStateHint | None:
    if items_count > 0:
        return None
    if rooms_filter_wiped and raw_count > 0:
        kind = EmptyStateKind.rooms_filter_wipe
    else:
        statuses = [pr.status for pr in portal_results]
        if statuses and all(s == AdapterStatus.skipped for s in statuses):
            kind = EmptyStateKind.all_skipped
        elif statuses and all(s == AdapterStatus.error for s in statuses):
            kind = EmptyStateKind.all_error
        elif statuses and all(s in (AdapterStatus.partial, AdapterStatus.error) for s in statuses):
            kind = EmptyStateKind.all_partial
        elif raw_count == 0:
            kind = EmptyStateKind.no_inventory
        else:
            kind = EmptyStateKind.all_partial
    title, body, hint = _EMPTY_COPY[kind]
    return EmptyStateHint(kind=kind, title=title, body=body, hint=hint)


def _merge_rooms_dropped(
    raw_rows: list[models.Property], filters: SearchFilters
) -> int:
    if filters.rooms is None or filters.rooms.min is None:
        return 0
    return sum(1 for r in raw_rows if not passes_rooms_min(r, filters))


def _portal_diagnostics_from_adapter(res: AdapterResult) -> PortalDiagnostics:
    raw = res.raw_count if res.raw_count is not None else (
        res.pagination.listings_raw if res.pagination else len(res.items)
    )
    after = (
        res.pagination.listings_after_filter
        if res.pagination is not None
        else len(res.items)
    )
    rooms_dropped = res.rooms_dropped if res.rooms_dropped is not None else 0
    wiped = bool(res.rooms_filter_wiped)
    maturity = _maturity_enum(res.maturity)
    reasons = []
    for r in res.drop_reasons or []:
        if r in ("rooms_null", "rooms_below_min", "geo", "price", "other"):
            reasons.append(r)
    return PortalDiagnostics(
        raw_count=raw,
        after_filter_count=after,
        rooms_dropped=rooms_dropped,
        rooms_filter_wiped=wiped,
        maturity=maturity,
        drop_reasons=reasons,
    )


async def upsert_property(
    db: AsyncSession, raw: RawProperty, *, poi_enabled: bool
) -> models.Property:
    score = compute_appscore(raw, poi_enabled=poi_enabled)
    breakdown = score.breakdown.model_dump(by_alias=False)

    result = await db.execute(
        select(models.Property).where(
            models.Property.portal == raw.portal.value,
            models.Property.external_id == raw.external_id,
        )
    )
    row = result.scalar_one_or_none()
    if row is None:
        row = raw_property_to_model(
            raw, app_score=score.score, score_breakdown=breakdown
        )
        db.add(row)
    else:
        apply_raw_to_row(row, raw, app_score=score.score, score_breakdown=breakdown)
    await db.flush()
    return row


async def _interest_overlay(
    db: AsyncSession, user_id: UUID, property_ids: list[UUID]
) -> dict[UUID, models.InterestItem]:
    if not property_ids:
        return {}
    result = await db.execute(
        select(models.InterestItem).where(
            models.InterestItem.user_id == user_id,
            models.InterestItem.property_id.in_(property_ids),
        )
    )
    return {i.property_id: i for i in result.scalars().all()}


async def _visits_overlay(
    db: AsyncSession, user_id: UUID, property_ids: list[UUID]
) -> dict[UUID, models.Visit]:
    if not property_ids:
        return {}
    result = await db.execute(
        select(models.Visit).where(
            models.Visit.user_id == user_id,
            models.Visit.property_id.in_(property_ids),
        )
    )
    return {v.property_id: v for v in result.scalars().all()}


def _pagination_dto(res: AdapterResult) -> AdapterPaginationMetaDTO | None:
    if res.pagination is None:
        return None
    p = res.pagination
    mode = None
    if p.mode:
        try:
            mode = SearchModeHint(p.mode)
        except ValueError:
            mode = None
    hint = None
    if p.data_source_hint:
        if p.data_source_hint == "mixed":
            hint = "mixed"
        else:
            try:
                from app.schemas.common import DataSource

                hint = DataSource(p.data_source_hint)
            except ValueError:
                hint = None
    return AdapterPaginationMetaDTO(
        pages_fetched=p.pages_fetched,
        listings_raw=p.listings_raw,
        listings_after_filter=p.listings_after_filter,
        max_pages=p.max_pages,
        page_size_hint=p.page_size_hint,
        mode=mode,
        data_source_hint=hint,
    )


async def run_search(
    db: AsyncSession,
    *,
    user_id: UUID,
    filters: SearchFilters,
    settings: Settings | None = None,
) -> SearchResponse:
    settings = settings or get_settings()
    started = time.perf_counter()
    search_id = uuid.uuid4()

    portals = filters.portals or list(PortalId)
    timeout = settings.adapter_timeout_seconds

    async def _one(portal: PortalId) -> AdapterResult:
        try:
            return await asyncio.wait_for(
                run_adapter(portal, filters, settings=settings), timeout=timeout
            )
        except asyncio.TimeoutError:
            from app.adapters.types import AdapterError, AdapterPaginationMeta

            return AdapterResult(
                portal=portal,
                status=AdapterStatus.error,
                items=[],
                pagination=AdapterPaginationMeta(
                    pages_fetched=0,
                    listings_raw=0,
                    listings_after_filter=0,
                    max_pages=filters.max_pages or settings.adapter_max_pages,
                    page_size_hint=filters.page_size_hint or settings.adapter_page_size_hint,
                    mode="hybrid",
                ),
                error=AdapterError(
                    code=AdapterErrorCode.network,
                    message=f"Adapter timeout after {timeout}s",
                    retryable=True,
                ),
                raw_count=0,
                rooms_dropped=0,
                rooms_filter_wiped=False,
                maturity="live_partial",
            )

    results = await asyncio.gather(*[_one(p) for p in portals], return_exceptions=True)

    portal_results: list[PortalSearchResult] = []
    merged_rows: list[models.Property] = []
    raw_before_merge_filter: list[models.Property] = []
    seen: set[tuple[str, str]] = set()
    modes: list[str] = []
    adapter_raw_by_portal: dict[str, int] = {}
    adapter_rooms_dropped: dict[str, int] = {}

    for portal, res in zip(portals, results, strict=True):
        if isinstance(res, BaseException):
            diag = PortalDiagnostics(
                raw_count=0,
                after_filter_count=0,
                rooms_dropped=0,
                rooms_filter_wiped=False,
                maturity=AdapterMaturity.live_partial,
            )
            portal_results.append(
                PortalSearchResult(
                    portal=portal,
                    status=AdapterStatus.error,
                    count=0,
                    diagnostics=diag,
                    maturity=diag.maturity,
                    error=PortalSearchError(
                        code=AdapterErrorCode.network,
                        message=f"Unexpected: {type(res).__name__}",
                        retryable=True,
                    ),
                )
            )
            continue

        assert isinstance(res, AdapterResult)
        err = None
        if res.error:
            err = PortalSearchError(
                code=res.error.code,
                message=res.error.message,
                retryable=res.error.retryable,
            )
        status = res.status
        if res.error and res.error.code.value == "fixtures_only" and res.items:
            status = AdapterStatus.ok
        pag = _pagination_dto(res)
        if pag and pag.mode:
            modes.append(pag.mode.value)
        diag = _portal_diagnostics_from_adapter(res)
        adapter_raw_by_portal[res.portal.value] = diag.raw_count
        adapter_rooms_dropped[res.portal.value] = diag.rooms_dropped
        portal_results.append(
            PortalSearchResult(
                portal=res.portal,
                status=status,
                count=len(res.items),
                unsupported_filters=res.unsupported_filters,
                pagination=pag,
                diagnostics=diag,
                maturity=diag.maturity,
                error=err,
            )
        )
        for raw in res.items:
            key = (raw.portal.value, raw.external_id)
            if key in seen:
                continue
            seen.add(key)
            row = await upsert_property(db, raw, poi_enabled=settings.feature_poi)
            merged_rows.append(row)
            raw_before_merge_filter.append(row)

    # Authoritative post-filter (geo / price / rooms) — fixtures included
    filtered_rows = filter_merged(merged_rows, filters)

    # Recount portal slices after post-filter + sync pagination.listingsAfterFilter
    counts: dict[str, int] = {}
    for row in filtered_rows:
        counts[row.portal] = counts.get(row.portal, 0) + 1
    merge_rooms_dropped = _merge_rooms_dropped(raw_before_merge_filter, filters)
    for pr in portal_results:
        after = counts.get(pr.portal.value, 0)
        pr.count = after
        if pr.pagination is not None:
            pr.pagination.listings_after_filter = after
        if pr.diagnostics is not None:
            pr.diagnostics.after_filter_count = after
            # Merge-level wipe signal if adapter yielded items but post-filter emptied via rooms
            portal_raw_items = [r for r in raw_before_merge_filter if r.portal == pr.portal.value]
            if (
                filters.rooms
                and filters.rooms.min is not None
                and portal_raw_items
                and after == 0
            ):
                room_fail = sum(1 for r in portal_raw_items if not passes_rooms_min(r, filters))
                if room_fail == len(portal_raw_items):
                    pr.diagnostics.rooms_filter_wiped = True
                    pr.diagnostics.rooms_dropped = max(pr.diagnostics.rooms_dropped, room_fail)
                    if pr.error is None:
                        pr.error = PortalSearchError(
                            code=AdapterErrorCode.filtered_rooms_null,
                            message=(
                                f"{pr.portal.value}: rooms.min wiped all "
                                f"{len(portal_raw_items)} merged listings"
                            ),
                            retryable=False,
                        )
                    if pr.status == AdapterStatus.ok:
                        pr.status = AdapterStatus.partial

    prop_ids = [r.id for r in filtered_rows]
    interests = await _interest_overlay(db, user_id, prop_ids)
    visits = await _visits_overlay(db, user_id, prop_ids)

    items: list[SearchResultItem] = []
    for row in filtered_rows:
        dto = property_to_dto(row)
        interest = interests.get(row.id)
        visit = visits.get(row.id)
        flags = None
        if interest:
            flags = interest_flags(
                state=interest.state,
                user_score=interest.user_score,
                comments=interest.comments,
                visit_status=visit.status if visit else "none",
                visit_at=visit.at if visit else None,
            )
        data = dto.model_dump()
        data["interest"] = flags
        items.append(SearchResultItem.model_validate(data))

    multi_page = sum(
        1
        for pr in portal_results
        if pr.pagination and pr.pagination.pages_fetched >= 2
    )
    if settings.adapter_use_fixtures:
        dens_mode = SearchModeHint.fixtures
    elif "hybrid" in modes:
        dens_mode = SearchModeHint.hybrid
    elif "live" in modes:
        dens_mode = SearchModeHint.live
    else:
        dens_mode = SearchModeHint.live

    sources = {getattr(r, "data_source", None) or "live" for r in filtered_rows}
    if not sources:
        dens_hint = None
    elif len(sources) == 1:
        only = next(iter(sources))
        dens_hint = only if only in ("live", "fixture_curated", "demo_stub") else "mixed"
    else:
        dens_hint = "mixed"

    agg_raw = sum(adapter_raw_by_portal.get(pr.portal.value, 0) for pr in portal_results)
    # Prefer sum of portal diagnostics raw; fall back to merged upserts
    if agg_raw == 0:
        agg_raw = len(raw_before_merge_filter)
    agg_rooms_dropped = sum(
        (pr.diagnostics.rooms_dropped if pr.diagnostics else 0) for pr in portal_results
    )
    if agg_rooms_dropped == 0 and merge_rooms_dropped:
        agg_rooms_dropped = merge_rooms_dropped
    rooms_wipe = any(
        pr.diagnostics.rooms_filter_wiped for pr in portal_results if pr.diagnostics
    ) or (
        filters.rooms is not None
        and filters.rooms.min is not None
        and agg_raw > 0
        and len(items) == 0
        and merge_rooms_dropped == len(raw_before_merge_filter)
        and len(raw_before_merge_filter) > 0
    )

    portal_slices: list[PortalDiagnosticsSlice] = []
    for pr in portal_results:
        d = pr.diagnostics
        portal_slices.append(
            PortalDiagnosticsSlice(
                portal=pr.portal,
                raw_count=d.raw_count if d else 0,
                after_filter_count=d.after_filter_count if d else pr.count,
                rooms_dropped=d.rooms_dropped if d else 0,
                rooms_filter_wiped=d.rooms_filter_wiped if d else False,
                maturity=d.maturity if d else AdapterMaturity.live_partial,
                status=pr.status,
                error_code=pr.error.code if pr.error else None,
            )
        )

    diagnostics = SearchDiagnostics(
        raw_count=agg_raw,
        after_filter_count=len(items),
        rooms_dropped=agg_rooms_dropped,
        rooms_filter_wiped=rooms_wipe,
        portals=portal_slices,
        empty_state=_empty_state_for(
            len(items), portal_results, rooms_filter_wiped=rooms_wipe, raw_count=agg_raw
        ),
    )

    took_ms = int((time.perf_counter() - started) * 1000)
    return SearchResponse(
        search_id=search_id,
        filters=filters,
        items=items,
        portal_results=portal_results,
        diagnostics=diagnostics,
        density=SearchDensity(
            total_items=len(items),
            portals_with_multi_page=multi_page,
            mode=dens_mode,
            data_source_hint=dens_hint,
        ),
        took_ms=took_ms,
    )
