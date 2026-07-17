"""Backfill external Properties — re-extract + rescore (iter-11 · E28-E29).

Existing rows with ``data_source=external`` are populated once when a user
pastes a URL (``POST /interest/external``) but never re-extracted afterwards.
This CLI replays the same pipeline (``extract_listing`` -> ``compute_appscore``
-> ``apply_raw_to_row``) against already-stored Properties so price/rooms/
amenities/geo/app_score reflect the current extractor without the user having
to re-paste every URL.

Contract: ``projects/househunt/factory/lanes/design/API_CONTRACT.md`` §12,
``ARCHITECTURE.md`` §17.

Usage (from ``services/api``, with the venv activated and ``DATABASE_URL`` set):

    python -m app.scripts.backfill_external
    python -m app.scripts.backfill_external --external-ids 16928305,19247558
    python -m app.scripts.backfill_external --user-email augusto.woelfert@gmail.com
    python -m app.scripts.backfill_external --dry-run --limit 5

Exit code is 1 when at least one row failed with a Critical error (extract
failure), so CI/devops can gate on it; 0 otherwise (rows with no eligible
scope, or only skips, still exit 0).
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys
from dataclasses import asdict, dataclass
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.adapters.external import ExternalExtractError, extract_listing
from app.config import get_settings
from app.db import models
from app.mappers import apply_raw_to_row
from app.scoring.appscore import compute_appscore

logger = logging.getLogger("backfill_external")


@dataclass
class RowOutcome:
    portal: str
    external_id: str
    ok: bool
    price: float | None = None
    rooms: int | None = None
    amenities_count: int = 0
    locality: str | None = None
    geo_set: bool = False
    error: str | None = None
    critical: bool = False


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="python -m app.scripts.backfill_external",
        description=(
            "Re-extract + rescore Properties with data_source=external "
            "(iter-11 P0-2 backfill)."
        ),
    )
    parser.add_argument(
        "--external-ids", default=None, help="CSV of external_id to limit scope"
    )
    parser.add_argument(
        "--interest-list-id",
        default=None,
        help="UUID: only Properties currently in this interest list",
    )
    parser.add_argument(
        "--user-email",
        default=None,
        help="Resolve the owned interest list of this user (smoke Augusto)",
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Log planned changes, do not commit"
    )
    parser.add_argument("--limit", type=int, default=None, help="Cap on rows processed")
    parser.add_argument(
        "--delay-ms",
        type=int,
        default=3000,
        help="Pause between extractions in ms (default 3000; Playwright/Railway rate-limit)",
    )
    parser.add_argument(
        "--timeout-seconds",
        type=float,
        default=None,
        help="Per-page Playwright timeout override (floor 20s)",
    )
    parser.add_argument(
        "--fail-fast",
        action="store_true",
        help="Stop at the first Critical failure instead of continuing",
    )
    return parser.parse_args(argv)


def _valid_http_url(url: str | None) -> bool:
    return bool(url) and (url.startswith("http://") or url.startswith("https://"))


async def _resolve_list_property_ids(db: AsyncSession, list_id: UUID) -> set[UUID]:
    rows = (
        await db.execute(
            select(models.InterestItem.property_id).where(models.InterestItem.list_id == list_id)
        )
    ).scalars().all()
    return set(rows)


async def _resolve_id_filter(
    db: AsyncSession,
    *,
    external_ids: list[str] | None,
    interest_list_id: UUID | None,
    user_email: str | None,
) -> set[UUID] | None:
    """Intersect optional scoping filters. ``None`` means "no id restriction"."""
    ids: set[UUID] | None = None

    if interest_list_id is not None or user_email is not None:
        list_id = interest_list_id
        if list_id is None:
            user = (
                await db.execute(select(models.User).where(models.User.email == user_email))
            ).scalar_one_or_none()
            if user is None:
                raise SystemExit(f"--user-email not found: {user_email}")
            owned = (
                await db.execute(
                    select(models.InterestList).where(
                        models.InterestList.owner_user_id == user.id
                    )
                )
            ).scalar_one_or_none()
            if owned is None:
                raise SystemExit(f"user has no owned interest list: {user_email}")
            list_id = owned.id
        ids = await _resolve_list_property_ids(db, list_id)

    if external_ids:
        rows = (
            await db.execute(
                select(models.Property.id).where(
                    models.Property.external_id.in_(external_ids)
                )
            )
        ).scalars().all()
        by_ext = set(rows)
        ids = by_ext if ids is None else (ids & by_ext)

    return ids


async def _select_rows(
    db: AsyncSession, *, id_filter: set[UUID] | None, limit: int | None
) -> list[models.Property]:
    stmt = select(models.Property).where(models.Property.data_source == "external")
    if id_filter is not None:
        if not id_filter:
            return []
        stmt = stmt.where(models.Property.id.in_(id_filter))
    stmt = stmt.order_by(models.Property.updated_at.asc())
    if limit:
        stmt = stmt.limit(limit)
    return list((await db.execute(stmt)).scalars().all())


async def run_backfill(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    args = _parse_args(argv)

    settings = get_settings()
    if args.timeout_seconds:
        settings.adapter_timeout_seconds = max(args.timeout_seconds, 20.0)

    external_ids = (
        [x.strip() for x in args.external_ids.split(",") if x.strip()]
        if args.external_ids
        else None
    )
    interest_list_id = UUID(args.interest_list_id) if args.interest_list_id else None

    engine = create_async_engine(settings.database_url, pool_pre_ping=True)
    factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

    outcomes: list[RowOutcome] = []
    skipped = 0

    async with factory() as db:
        id_filter = await _resolve_id_filter(
            db,
            external_ids=external_ids,
            interest_list_id=interest_list_id,
            user_email=args.user_email,
        )
        rows = await _select_rows(db, id_filter=id_filter, limit=args.limit)
        logger.info("backfill_external: %d row(s) selected (dry_run=%s)", len(rows), args.dry_run)

        for idx, row in enumerate(rows):
            if not _valid_http_url(row.source_url):
                skipped += 1
                logger.warning("skip %s/%s: invalid source_url", row.portal, row.external_id)
                continue

            if idx > 0 and args.delay_ms > 0:
                await asyncio.sleep(args.delay_ms / 1000.0)

            try:
                raw = await extract_listing(row.source_url, settings=settings)
            except ExternalExtractError as exc:
                outcomes.append(
                    RowOutcome(
                        portal=row.portal,
                        external_id=row.external_id,
                        ok=False,
                        error=f"{exc.code}: {exc.message}",
                        critical=True,
                    )
                )
                logger.error("FAILED %s/%s: %s", row.portal, row.external_id, exc.message)
                if args.fail_fast:
                    break
                continue
            except Exception as exc:  # noqa: BLE001 — keep batch alive on unexpected errors
                outcomes.append(
                    RowOutcome(
                        portal=row.portal,
                        external_id=row.external_id,
                        ok=False,
                        error=f"unexpected {type(exc).__name__}: {exc}",
                        critical=True,
                    )
                )
                logger.error("FAILED %s/%s: %s", row.portal, row.external_id, exc)
                if args.fail_fast:
                    break
                continue

            # Thin extract = bot wall / partial HTML. Never overwrite a richer DB row.
            img_count = len(raw.images or [])
            thin = (
                raw.price_amount is None
                and img_count == 0
                and not (raw.address_locality or "").strip()
            )
            if thin:
                outcomes.append(
                    RowOutcome(
                        portal=row.portal,
                        external_id=row.external_id,
                        ok=False,
                        price=None,
                        rooms=raw.rooms,
                        amenities_count=len(raw.amenities or []),
                        locality=raw.address_locality,
                        geo_set=False,
                        error="thin_extract: price=null imgs=0 locality=null (skipped apply)",
                        critical=True,
                    )
                )
                logger.error(
                    "FAILED %s/%s: thin extract — refuse to overwrite existing row",
                    row.portal,
                    row.external_id,
                )
                if args.fail_fast:
                    break
                continue

            score = compute_appscore(raw, poi_enabled=settings.feature_poi)
            breakdown = score.breakdown.model_dump(by_alias=False)

            outcomes.append(
                RowOutcome(
                    portal=row.portal,
                    external_id=row.external_id,
                    ok=True,
                    price=raw.price_amount,
                    rooms=raw.rooms,
                    amenities_count=len(raw.amenities or []),
                    locality=raw.address_locality,
                    geo_set=raw.geo_lat is not None and raw.geo_lng is not None,
                )
            )
            logger.info(
                "OK %s/%s price=%s rooms=%s amenities=%s locality=%s geo_set=%s score=%s",
                row.portal,
                row.external_id,
                raw.price_amount,
                raw.rooms,
                len(raw.amenities or []),
                raw.address_locality,
                raw.geo_lat is not None and raw.geo_lng is not None,
                score.score,
            )

            if args.dry_run:
                continue

            apply_raw_to_row(row, raw, app_score=score.score, score_breakdown=breakdown)
            await db.flush()

        if args.dry_run:
            await db.rollback()
        else:
            await db.commit()

    await engine.dispose()

    ok_count = sum(1 for o in outcomes if o.ok)
    failed = [o for o in outcomes if not o.ok]
    summary = {
        "processed": len(outcomes),
        "ok": ok_count,
        "failed": len(failed),
        "skipped": skipped,
        "dry_run": args.dry_run,
        "rows": [asdict(o) for o in outcomes],
    }
    print(json.dumps(summary, indent=2, ensure_ascii=False, default=str))

    critical_failures = sum(1 for o in failed if o.critical)
    if critical_failures > 0:
        logger.error("backfill_external: %d Critical failure(s)", critical_failures)
        return 1
    return 0


def main() -> None:
    sys.exit(asyncio.run(run_backfill()))


if __name__ == "__main__":
    main()
