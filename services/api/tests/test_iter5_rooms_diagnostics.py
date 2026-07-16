"""Iter 5 — rooms parse (E22) + diagnostics roomsFilterWiped (E23)."""

from __future__ import annotations

import pytest

from app.adapters.common import live_ok_result
from app.adapters.mercadolibre.live import build_search_url as ml_url
from app.adapters.rooms_parse import parse_rooms
from app.adapters.types import RawProperty
from app.adapters.veracity import image_host_ok_for_portal
from app.adapters.zonaprop.live import build_search_url as zp_url
from app.config import get_settings
from app.schemas.common import AdapterErrorCode, AdapterStatus, DataSource, PortalId
from app.schemas.property import Location, MinIntFilter, SearchFilters


@pytest.fixture(autouse=True)
def _settings():
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def test_parse_rooms_from_card_and_slug():
    assert parse_rooms("Casa 4 ambientes en Gonnet") == 4
    assert parse_rooms("https://www.argenprop.com/casa-en-venta-5-ambientes--123") == 5
    assert parse_rooms(".../3-ambientes/bsas-gba-sur/...") == 3
    assert parse_rooms("3 Rec. 2 Baños") == 3
    assert parse_rooms("sin datos de ambientes") is None


def test_ml_and_zp_search_url_include_rooms():
    filters = SearchFilters(
        location=Location(
            query="Gonnet",
            locality="Gonnet",
            district="La Plata",
            province="Buenos Aires",
            country="AR",
        ),
        rooms=MinIntFilter(min=3),
    )
    assert "3-ambientes" in ml_url(filters)
    assert "mas-de-3-ambientes" in zp_url(filters)


def test_live_ok_result_wipes_only_when_all_rooms_known_below_min():
    """iter-6: wipe legítimo solo si TODOS los rooms son conocidos y < min."""
    settings = get_settings()
    filters = SearchFilters(rooms=MinIntFilter(min=3))
    raw = [
        RawProperty(
            portal=PortalId.zonaprop,
            external_id="1",
            source_url="https://www.zonaprop.com.ar/propiedades/clasificado/casa-1.html",
            title="Casa 1 amb",
            rooms=1,
            price_amount=100000,
            price_currency="USD",
            data_source=DataSource.live,
            images=[{"url": "/placeholder-listing.svg", "order": 0, "kind": "placeholder"}],
        ),
        RawProperty(
            portal=PortalId.zonaprop,
            external_id="2",
            source_url="https://www.zonaprop.com.ar/propiedades/clasificado/casa-2.html",
            title="Casa 2 amb",
            rooms=2,
            price_amount=110000,
            price_currency="USD",
            data_source=DataSource.live,
            images=[{"url": "/placeholder-listing.svg", "order": 0, "kind": "placeholder"}],
        ),
    ]
    result = live_ok_result(PortalId.zonaprop, filters, raw, settings=settings)
    assert result.status == AdapterStatus.partial
    assert result.items == []
    assert result.raw_count == 2
    assert result.rooms_dropped == 2
    assert result.rooms_filter_wiped is True
    assert result.error is not None
    assert result.error.code == AdapterErrorCode.filtered_rooms_null


def test_live_ok_result_keeps_unknown_rooms():
    """iter-6: rooms=None NO se descarta con rooms.min (coverage ML/C21)."""
    settings = get_settings()
    filters = SearchFilters(rooms=MinIntFilter(min=3))
    raw = [
        RawProperty(
            portal=PortalId.century21,
            external_id="309776",
            source_url="https://century21.com.ar/propiedad/309776",
            title="Casa en venta Gonnet",
            rooms=None,
            price_amount=None,
            address_locality="Gonnet",
            data_source=DataSource.live,
            images=[{"url": "/placeholder-listing.svg", "order": 0, "kind": "placeholder"}],
        )
    ]
    result = live_ok_result(PortalId.century21, filters, raw, settings=settings)
    assert result.status == AdapterStatus.ok
    assert len(result.items) == 1
    assert result.rooms_filter_wiped is False
    assert result.rooms_dropped == 0


def test_live_ok_result_keeps_items_when_rooms_parsed():
    settings = get_settings()
    filters = SearchFilters(rooms=MinIntFilter(min=3))
    raw = [
        RawProperty(
            portal=PortalId.mercadolibre,
            external_id="99",
            source_url="https://casa.mercadolibre.com.ar/MLA-99-_JM",
            title="Casa 4 ambientes Gonnet",
            rooms=4,
            price_amount=150000,
            price_currency="USD",
            address_locality="Gonnet",
            data_source=DataSource.live,
            images=[{"url": "https://http2.mlstatic.com/D_NQ_1.webp", "order": 0, "kind": "source"}],
        )
    ]
    result = live_ok_result(PortalId.mercadolibre, filters, raw, settings=settings)
    assert result.status == AdapterStatus.ok
    assert len(result.items) == 1
    assert result.rooms_filter_wiped is False


def test_remax_cloudfront_allowlisted():
    url = (
        "https://d1acdg20u0pmxj.cloudfront.net/listings/"
        "ffff55ec-4749-444b-b695-3af4d0ad9f55/1080xAUTO/x.jpg"
    )
    assert image_host_ok_for_portal(PortalId.remax, url)
    assert image_host_ok_for_portal(PortalId.century21, "https://cdn.21online.lat/argentina/x.jpg")


@pytest.mark.asyncio
async def test_search_response_includes_diagnostics(client, monkeypatch):
    from app.adapters import registry
    import app.search.service as search_service

    async def fake_run(portal, filters, *, settings=None):
        rooms = None if portal == PortalId.remax else 4
        item = RawProperty(
            portal=portal,
            external_id=f"{portal.value}-diag",
            source_url=f"https://www.zonaprop.com.ar/propiedades/clasificado/{portal.value}.html"
            if portal == PortalId.zonaprop
            else f"https://casa.mercadolibre.com.ar/MLA-{portal.value}-_JM"
            if portal == PortalId.mercadolibre
            else f"https://www.argenprop.com/casa-en-venta--{portal.value}"
            if portal == PortalId.argenprop
            else f"https://www.remax.com.ar/listings/{portal.value}"
            if portal == PortalId.remax
            else f"https://century21.com.ar/propiedad/{portal.value}",
            title=f"Casa {portal.value}",
            rooms=rooms,
            price_amount=120000,
            price_currency="USD",
            address_locality="Gonnet",
            data_source=DataSource.live,
            images=[{"url": "/placeholder-listing.svg", "order": 0, "kind": "placeholder"}],
        )
        return live_ok_result(portal, filters, [item], settings=get_settings())

    monkeypatch.setattr(registry, "run_adapter", fake_run)
    monkeypatch.setattr(search_service, "run_adapter", fake_run)

    reg = await client.post(
        "/api/auth/register",
        json={"email": "diag@example.com", "password": "password123", "displayName": "D"},
    )
    token = reg.json()["accessToken"]
    resp = await client.post(
        "/api/search",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "operation": "buy",
            "propertyType": "house",
            "location": {
                "query": "Gonnet",
                "locality": "Gonnet",
                "district": "La Plata",
                "province": "Buenos Aires",
                "country": "AR",
            },
            "rooms": {"min": 3},
        },
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert "diagnostics" in data
    assert "rawCount" in data["diagnostics"]
    assert "roomsFilterWiped" in data["diagnostics"]
    by = {p["portal"]: p for p in data["portalResults"]}
    # iter-6: remax con rooms=None ya NO se wipea (coverage) → aparece
    assert by["remax"]["diagnostics"]["roomsFilterWiped"] is False
    assert by["remax"]["count"] >= 1
    assert data["diagnostics"]["emptyState"] is None
    # 4 portales rooms=4 + remax rooms=None (kept) = 5 items
    assert len(data["items"]) >= 5
