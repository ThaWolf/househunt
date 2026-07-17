"""iter-11 backend: listing-scoped price, rooms dorm>ambientes, geo seed, backfill.

Evidence: lanes/analysis/RCA.md (outcome prod post-i10), API_CONTRACT.md E28-E32,
ARCHITECTURE.md §16-20. Witness case: Argenprop ``16928305`` — slug says
"6-ambientes" but the aviso is 3 dormitorios and its own price is ~128000 USD,
while the page body also carries unrelated "similar listings" prices
(90k/124k/130k/160k) that a naive "largest in body" scan would pick instead.
"""

from __future__ import annotations

import pytest

from app.adapters.external.extract import (
    _geo_from_ld,
    _ld_bedrooms,
    _ld_pick,
    _price,
    _resolve_geo,
    _iter_ld_nodes,
)
from app.adapters.rooms_parse import parse_rooms_for_listing
from app.zone.seed_data import centroid_for, seeds_for
from app.zone.report import build_zone_report
from app.adapters.types import RawProperty
from app.schemas.common import GeocodeSource, GeocodeStatus, PortalId


# --- P0-1: listing-scoped price (E30) -----------------------------------------

_SIMILARS_NOISE = (
    " Propiedades similares USD 124.000 USD 130.000 USD 160.000 USD 90.000"
)


def test_price_dom_listing_scoped_wins_over_body_noise():
    """DOM listing price (priority 3) must win even if body/hero also has other USD marks."""
    listing_price_text = "USD 128.000"
    hero_body_text = (
        "Casa en venta en La Plata 6 ambientes. 504 y 24 2800, Piso 0. "
        "USD 128.000 3 dormitorios 6 ambientes jardín cochera"
    )
    body_text = hero_body_text + _SIMILARS_NOISE

    amount, cur = _price(
        {},
        {},
        body_text,
        listing_price_text=listing_price_text,
        hero_body_text=hero_body_text,
    )
    assert amount is not None
    assert 121_600 <= amount <= 134_400  # 128000 ± 5%
    assert cur == "USD"


def test_price_hero_slice_fallback_without_dom_selector():
    """No DOM match (priority 4): hero slice (cut before 'similares') still finds 128k, not the neighbor prices."""
    hero_body_text = (
        "Casa en venta en La Plata 6 ambientes. 504 y 24 2800, Piso 0. "
        "USD 128.000 3 dormitorios 6 ambientes"
    )
    body_text = hero_body_text + _SIMILARS_NOISE

    amount, cur = _price({}, {}, body_text, listing_price_text=None, hero_body_text=hero_body_text)
    assert amount == 128000.0
    assert cur == "USD"


def test_price_never_prefers_largest_in_full_body():
    """Regression guard: without a hero cut, scanning the *raw* full body (as pre-i11
    code did with prefer_largest=True) would wrongly pick the 160k neighbor price.
    The new priority chain must not reproduce that by defaulting hero_body_text to a
    slice that still excludes the similares block when the caller doesn't pass one."""
    hero_body_text = "USD 128.000 3 dormitorios"
    body_text = hero_body_text + _SIMILARS_NOISE
    amount, _ = _price({}, {}, body_text, hero_body_text=hero_body_text)
    assert amount == 128000.0
    assert amount != 160000.0
    assert amount != 140000.0


def test_price_street_height_still_rejected():
    body = "504 y 24 2800, Piso 0. Precio USD 128.000"
    amount, cur = _price({}, {}, body, hero_body_text=body)
    assert amount == 128000.0
    assert cur == "USD"


# --- P0-3: rooms — dormitorios (bedrooms) win over slug ambientes (E31) ------


def test_rooms_bedrooms_win_over_slug_ambientes_16928305_like():
    url = "https://www.argenprop.com/casa-en-venta-en-la-plata-6-ambientes--16928305"
    title = "Casa en Venta en La Plata 6 Ambientes"
    description = "Hermosa casa con jardín y cochera."
    body = "3 dormitorios · 6 ambientes · jardín · cochera"

    rooms = parse_rooms_for_listing(url, title, description, body, ld_bedrooms=None)
    assert rooms == 3


def test_rooms_ld_bedrooms_takes_priority():
    url = "https://www.argenprop.com/casa-en-venta-en-la-plata-6-ambientes--16928305"
    rooms = parse_rooms_for_listing(url, "6 Ambientes", None, "", ld_bedrooms=3)
    assert rooms == 3


def test_rooms_falls_back_to_slug_when_no_bedroom_signal():
    url = "https://www.mercadolibre.com.ar/casa-4-ambientes-MLA1234567"
    rooms = parse_rooms_for_listing(url, "Casa 4 ambientes", None, "", ld_bedrooms=None)
    assert rooms == 4


def test_ld_bedrooms_helper_parses_numeric_and_string():
    assert _ld_bedrooms({"numberOfBedrooms": 3}) == 3
    assert _ld_bedrooms({"numberOfBedrooms": "3"}) == 3
    assert _ld_bedrooms({"numberOfBedrooms": "not-a-number"}) is None
    assert _ld_bedrooms({}) is None


def test_ld_pick_extracts_bedrooms_and_geo():
    nodes = _iter_ld_nodes(
        [
            '{"@type":"House","numberOfBedrooms":3,"numberOfRooms":6,'
            '"geo":{"@type":"GeoCoordinates","latitude":-34.88,"longitude":-58.02}}'
        ]
    )
    ld = _ld_pick(nodes)
    assert ld["numberOfBedrooms"] == 3
    assert ld["geo"]["latitude"] == -34.88


# --- P0-4: geo — portal coords, else locality seed centroid ------------------


def test_geo_from_ld_reads_geocoordinates():
    ld = {"geo": {"latitude": "-34.88", "longitude": "-58.02"}}
    lat, lng = _geo_from_ld(ld)
    assert lat == -34.88
    assert lng == -58.02


def test_geo_from_ld_missing_returns_none():
    assert _geo_from_ld({}) == (None, None)
    assert _geo_from_ld({"geo": {"latitude": None, "longitude": None}}) == (None, None)


def test_resolve_geo_prefers_portal_over_seed():
    ld = {"geo": {"latitude": -34.1, "longitude": -58.1}}
    lat, lng = _resolve_geo(ld, "Gonnet")
    assert (lat, lng) == (-34.1, -58.1)


def test_resolve_geo_falls_back_to_locality_seed():
    lat, lng = _resolve_geo({}, "Gonnet")
    assert (lat, lng) == centroid_for("Gonnet")


def test_resolve_geo_none_when_no_locality_match():
    assert _resolve_geo({}, "Localidad Inexistente XYZ") == (None, None)


def test_centroid_for_partido_de_la_plata_alias():
    assert centroid_for("Partido de La Plata") == centroid_for("La Plata")
    assert centroid_for("Partido de La Plata, Argentina") is not None


def test_seeds_for_partido_de_la_plata_alias():
    assert seeds_for("Partido de La Plata") == seeds_for("La Plata")


def test_zone_report_labels_seed_centroid_as_approximate_not_exact():
    """When extract persisted a seed centroid onto geo_lat/geo_lng (no real portal
    coords), the zone report must still say approximate/seed_locality — not a
    false 'exact'/'portal' just because the fields are non-null."""
    lat, lng = centroid_for("Gonnet")
    raw = RawProperty(
        portal=PortalId.argenprop,
        external_id="16928305",
        source_url="https://www.argenprop.com/casa-en-venta--16928305",
        title="Casa en Gonnet",
        address_locality="Gonnet",
        geo_lat=lat,
        geo_lng=lng,
    )
    report = build_zone_report(raw)
    assert report.geo.geocode_status == GeocodeStatus.approximate
    assert report.geo.geocode_source == GeocodeSource.seed_locality
    assert report.geo.lat == lat
    assert report.geo.lng == lng


def test_zone_report_labels_real_portal_coords_as_exact():
    raw = RawProperty(
        portal=PortalId.remax,
        external_id="rmx-1",
        source_url="https://www.remax.com.ar/listings/rmx-1",
        title="Casa con geo real",
        address_locality="Gonnet",
        geo_lat=-34.87651234,  # deliberately not the seed centroid
        geo_lng=-58.01789876,
    )
    report = build_zone_report(raw)
    assert report.geo.geocode_status == GeocodeStatus.exact
    assert report.geo.geocode_source == GeocodeSource.portal


def test_zone_report_missing_when_no_geo_and_unknown_locality():
    raw = RawProperty(
        portal=PortalId.external,
        external_id="ext-1",
        source_url="https://example.com/x",
        title="Sin localidad reconocible",
        address_locality=None,
    )
    report = build_zone_report(raw)
    assert report.geo.geocode_status == GeocodeStatus.missing


# --- P0-2: backfill script -----------------------------------------------------


def test_backfill_external_module_importable():
    from app.scripts import backfill_external

    assert hasattr(backfill_external, "run_backfill")
    assert hasattr(backfill_external, "main")
    assert callable(backfill_external.run_backfill)


def test_backfill_external_arg_defaults():
    from app.scripts.backfill_external import _parse_args

    args = _parse_args([])
    assert args.external_ids is None
    assert args.interest_list_id is None
    assert args.user_email is None
    assert args.dry_run is False
    assert args.delay_ms == 3000
    assert args.fail_fast is False


def test_backfill_external_arg_parsing_ids_and_dry_run():
    from app.scripts.backfill_external import _parse_args

    args = _parse_args(
        [
            "--external-ids",
            "16928305,19247558",
            "--dry-run",
            "--delay-ms",
            "5000",
            "--limit",
            "3",
        ]
    )
    assert args.external_ids == "16928305,19247558"
    assert args.dry_run is True
    assert args.delay_ms == 5000
    assert args.limit == 3


def test_backfill_valid_http_url_helper():
    from app.scripts.backfill_external import _valid_http_url

    assert _valid_http_url("https://www.argenprop.com/x") is True
    assert _valid_http_url("http://example.com") is True
    assert _valid_http_url(None) is False
    assert _valid_http_url("") is False
    assert _valid_http_url("not-a-url") is False


async def test_backfill_external_pipeline_end_to_end(tmp_path, monkeypatch):
    """Full pipeline against a real (sqlite) DB: select external row -> fake
    extract_listing -> compute_appscore -> apply_raw_to_row -> commit."""
    import uuid
    from datetime import datetime, timezone

    from app.config import get_settings
    from app.db.base import Base

    db_path = tmp_path / "backfill_iter11.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite+aiosqlite:///{db_path}")
    get_settings.cache_clear()

    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    from app.db import models

    settings = get_settings()
    engine = create_async_engine(settings.database_url)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)

    prop_id = uuid.uuid4()
    async with factory() as session:
        session.add(
            models.Property(
                id=prop_id,
                portal="argenprop",
                external_id="16928305",
                source_url="https://www.argenprop.com/casa-en-venta-en-la-plata-6-ambientes--16928305",
                data_source="external",
                title="Casa en Venta en La Plata 6 Ambientes",
                price_amount=2800,
                price_currency="USD",
                rooms=6,
                amenities=[],
                images=[],
                scraped_at=datetime.now(timezone.utc),
            )
        )
        await session.commit()
    await engine.dispose()

    from app.adapters.types import RawProperty
    from app.schemas.common import DataSource, PortalId

    async def fake_extract_listing(url, *, settings=None):
        return RawProperty(
            portal=PortalId.argenprop,
            external_id="16928305",
            source_url=url,
            title="Casa en Venta en La Plata 6 Ambientes",
            description="3 dormitorios, jardín, cochera",
            price_amount=128000.0,
            price_currency="USD",
            address_locality="Gonnet",
            geo_lat=-34.8805,
            geo_lng=-58.0178,
            rooms=3,
            amenities=["jardin", "cochera"],
            data_source=DataSource.external,
        )

    monkeypatch.setattr(
        "app.scripts.backfill_external.extract_listing", fake_extract_listing
    )

    from app.scripts.backfill_external import run_backfill

    exit_code = await run_backfill(["--external-ids", "16928305", "--delay-ms", "0"])
    assert exit_code == 0

    engine2 = create_async_engine(settings.database_url)
    factory2 = async_sessionmaker(engine2, expire_on_commit=False)
    async with factory2() as session:
        row = await session.get(models.Property, prop_id)
        assert row.price_amount == 128000.0
        assert row.rooms == 3
        assert sorted(row.amenities) == ["cochera", "jardin"]
        assert row.address_locality == "Gonnet"
        assert row.app_score is not None
    await engine2.dispose()
    get_settings.cache_clear()



@pytest.mark.asyncio
async def test_extract_raises_on_bot_wall_title(monkeypatch):
    from unittest.mock import AsyncMock

    from app.adapters.external.extract import ExternalExtractError, extract_listing

    class FakePage:
        async def wait_for_timeout(self, *_a, **_k):
            return None

        async def wait_for_selector(self, *_a, **_k):
            return None

        async def evaluate(self, *_a, **_k):
            return {
                "ld": [],
                "meta": {},
                "ogImages": [],
                "title": "Human Verification",
                "bodyText": "x" * 500,
                "listingPriceText": "",
                "heroBodyText": "",
            }

    class CM:
        async def __aenter__(self):
            return FakePage()

        async def __aexit__(self, *exc):
            return False

    monkeypatch.setattr("app.adapters.external.extract.browser_page", lambda **_k: CM())
    monkeypatch.setattr("app.adapters.external.extract.goto_html", AsyncMock())
    with pytest.raises(ExternalExtractError) as ei:
        await extract_listing("https://www.argenprop.com/casa--16928305")
    assert "bloqueo" in ei.value.message.lower() or "incompleta" in ei.value.message.lower()
