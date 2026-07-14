"""Iter 4 veracity guardrails — no picsum / fake portal paths / host mismatch."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.adapters.fixtures.loader import FIXTURES_PATH, clear_fixture_cache, load_fixture_properties
from app.adapters.types import AdapterResult, RawProperty
from app.adapters.veracity import (
    BANNED_IMAGE_HOST_PATTERNS,
    is_banned_image_host,
    is_fake_source_url,
    source_url_matches_portal,
)
from app.config import get_settings
from app.schemas.common import AdapterStatus, DataSource, PortalId
from app.schemas.property import SearchFilters


@pytest.fixture(autouse=True)
def _fresh():
    clear_fixture_cache()
    get_settings.cache_clear()
    yield
    clear_fixture_cache()
    get_settings.cache_clear()


def test_fixtures_file_has_no_picsum_or_fake_paths():
    raw = json.loads(FIXTURES_PATH.read_text(encoding="utf-8"))
    for portal, rows in raw.items():
        for row in rows:
            assert not is_fake_source_url(row.get("sourceUrl", "")), row
            for img in row.get("images") or []:
                url = img.get("url") or ""
                kind = img.get("kind") or "source"
                if kind == "source":
                    assert not is_banned_image_host(url), (portal, url)
                    for banned in BANNED_IMAGE_HOST_PATTERNS:
                        assert banned not in url.lower()


def test_loaded_fixtures_empty_or_curated():
    """Empty fixture set is valid (veracity > density)."""
    total = 0
    for portal in PortalId:
        items = load_fixture_properties(portal)
        total += len(items)
        for item in items:
            assert item.data_source in (
                DataSource.fixture_curated,
                DataSource.demo_stub,
            )
            assert not is_fake_source_url(item.source_url)
            assert not any(
                is_banned_image_host(img.get("url", ""))
                for img in item.images
                if img.get("kind") == "source"
            )
    # Prefer empty over lies in iter 4
    assert total == 0 or all(
        source_url_matches_portal(item.portal, item.source_url)
        for portal in PortalId
        for item in load_fixture_properties(portal)
        if item.data_source == DataSource.fixture_curated
    )


def test_banned_host_helpers():
    assert is_banned_image_host("https://picsum.photos/seed/x/800/500")
    assert is_banned_image_host("https://via.placeholder.com/150")
    assert not is_banned_image_host("https://imgar.zonapropcdn.com/avisos/1.jpg")
    assert is_fake_source_url("https://www.zonaprop.com.ar/propiedades/zp-2000.html")
    assert not is_fake_source_url(
        "https://www.zonaprop.com.ar/propiedades/clasificado/veclcain-casa-58805371.html"
    )


def test_live_looking_fixture_host_must_match_portal():
    """When mocking live-style fixtures, sourceUrl host must match portal."""
    good = RawProperty(
        portal=PortalId.zonaprop,
        external_id="58805371",
        source_url="https://www.zonaprop.com.ar/propiedades/clasificado/veclcain-casa-58805371.html",
        title="Casa Gonnet",
        images=[
            {
                "url": "https://imgar.zonapropcdn.com/avisos/1/00/58/80/53/71/720x532/x.jpg",
                "order": 0,
                "kind": "source",
            }
        ],
        data_source=DataSource.live,
    )
    assert source_url_matches_portal(good.portal, good.source_url)
    for img in good.images:
        assert img["kind"] != "source" or not is_banned_image_host(img["url"])

    bad = RawProperty(
        portal=PortalId.zonaprop,
        external_id="x",
        source_url="https://www.mercadolibre.com.ar/MLA-1",
        title="wrong host",
        data_source=DataSource.live,
    )
    assert not source_url_matches_portal(bad.portal, bad.source_url)


@pytest.mark.asyncio
async def test_bot_wall_returns_empty_not_invented(monkeypatch):
    from app.adapters import zonaprop
    from app.adapters.browser import BrowserFetchError
    from app.adapters.zonaprop.adapter import ZonaPropAdapter

    monkeypatch.setenv("ADAPTER_USE_FIXTURES", "false")
    get_settings.cache_clear()

    async def boom(*_a, **_k):
        raise BrowserFetchError("bot_wall", "CF challenge")

    monkeypatch.setattr(
        "app.adapters.zonaprop.adapter.fetch_zonaprop_live",
        boom,
    )
    result = await ZonaPropAdapter().fetch(SearchFilters())
    assert result.items == []
    assert result.error is not None
    assert result.error.code.value == "bot_wall"
    assert result.status == AdapterStatus.partial


@pytest.mark.asyncio
async def test_search_mocked_live_has_data_source_and_hosts(client, monkeypatch):
    from app.adapters import registry
    from app.adapters.types import AdapterPaginationMeta

    live_items = [
        RawProperty(
            portal=PortalId.zonaprop,
            external_id="58805371",
            source_url="https://www.zonaprop.com.ar/propiedades/clasificado/veclcain-casa-gonnet-58805371.html",
            title="Casa en venta Gonnet",
            description="x" * 130,
            price_amount=140000,
            price_currency="USD",
            address_locality="Gonnet",
            address_raw="Manuel B Gonnet, La Plata",
            rooms=3,
            images=[
                {
                    "url": "https://imgar.zonapropcdn.com/avisos/1/00/58/80/53/71/720x532/2044885303.jpg",
                    "order": 0,
                    "kind": "source",
                }
            ],
            data_source=DataSource.live,
        ),
        RawProperty(
            portal=PortalId.mercadolibre,
            external_id="3359609358",
            source_url="https://casa.mercadolibre.com.ar/MLA-3359609358-casa-en-venta-en-la-plata-_JM",
            title="Casa En Venta En La Plata",
            description="y" * 130,
            price_amount=120000,
            price_currency="USD",
            address_locality="La Plata",
            rooms=3,
            images=[
                {
                    "url": "https://http2.mlstatic.com/D_NQ_NP_2X_933317-MLA111076545704_052026-E.webp",
                    "order": 0,
                    "kind": "source",
                }
            ],
            data_source=DataSource.live,
        ),
    ]

    async def fake_run(portal, filters, *, settings=None):
        items = [i for i in live_items if i.portal == portal]
        return AdapterResult(
            portal=portal,
            status=AdapterStatus.ok if items else AdapterStatus.skipped,
            items=items,
            pagination=AdapterPaginationMeta(
                pages_fetched=1 if items else 0,
                listings_raw=len(items),
                listings_after_filter=len(items),
                max_pages=3,
                page_size_hint=20,
                mode="live",
                data_source_hint="live" if items else None,
            ),
        )

    monkeypatch.setattr(registry, "run_adapter", fake_run)
    import app.search.service as search_service

    monkeypatch.setattr(search_service, "run_adapter", fake_run)

    reg = await client.post(
        "/api/auth/register",
        json={"email": "verity@example.com", "password": "password123"},
    )
    token = reg.json()["accessToken"]
    resp = await client.post(
        "/api/search",
        headers={"Authorization": f"Bearer {token}"},
        json={"operation": "buy", "propertyType": "house", "geo": {"mode": "gba"}},
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert len(data["items"]) >= 2
    for item in data["items"]:
        assert item["dataSource"] == "live"
        assert item["images"]
        for img in item["images"]:
            assert "kind" in img
            if img["kind"] == "source":
                assert not is_banned_image_host(img["url"])
                assert "picsum" not in img["url"]
        portal = PortalId(item["portal"])
        assert source_url_matches_portal(portal, item["sourceUrl"])
