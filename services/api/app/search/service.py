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
from app.schemas.common import AdapterStatus, PortalId
from app.schemas.property import (
    PortalSearchError,
    PortalSearchResult,
    SearchFilters,
    SearchResponse,
    SearchResultItem,
)
from app.scoring.appscore import compute_appscore
from app.search.postfilter import filter_merged


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
            from app.adapters.types import AdapterError
            from app.schemas.common import AdapterErrorCode

            return AdapterResult(
                portal=portal,
                status=AdapterStatus.error,
                items=[],
                error=AdapterError(
                    code=AdapterErrorCode.network,
                    message=f"Adapter timeout after {timeout}s",
                    retryable=True,
                ),
            )

    results = await asyncio.gather(*[_one(p) for p in portals], return_exceptions=True)

    portal_results: list[PortalSearchResult] = []
    merged_rows: list[models.Property] = []
    seen: set[tuple[str, str]] = set()

    for portal, res in zip(portals, results, strict=True):
        if isinstance(res, BaseException):
            from app.schemas.common import AdapterErrorCode

            portal_results.append(
                PortalSearchResult(
                    portal=portal,
                    status=AdapterStatus.error,
                    count=0,
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
        # When fixtures_only with items, surface as ok for FE (status already set)
        status = res.status
        if res.error and res.error.code.value == "fixtures_only" and res.items:
            status = AdapterStatus.ok
            # Keep error info for meta debugging? Contract allows error on ok partial —
            # leave error populated when fixtures_only for transparency
        portal_results.append(
            PortalSearchResult(
                portal=res.portal,
                status=status,
                count=len(res.items),
                unsupported_filters=res.unsupported_filters,
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

    # Authoritative post-filter (geo / price / rooms) — fixtures included
    filtered_rows = filter_merged(merged_rows, filters)

    # Recount portal slices after post-filter
    counts: dict[str, int] = {}
    for row in filtered_rows:
        counts[row.portal] = counts.get(row.portal, 0) + 1
    for pr in portal_results:
        pr.count = counts.get(pr.portal.value, 0)

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

    took_ms = int((time.perf_counter() - started) * 1000)
    return SearchResponse(
        search_id=search_id,
        filters=filters,
        items=items,
        portal_results=portal_results,
        took_ms=took_ms,
    )
