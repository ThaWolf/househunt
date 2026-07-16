"""Iter 3 report/narrative/zone tests + iter4 density override (veracity > volume)."""

from __future__ import annotations

import pytest

from app.adapters.fixtures.loader import clear_fixture_cache, load_fixture_properties
from app.adapters.types import AdapterPaginationMeta, AdapterResult, RawProperty
from app.config import get_settings
from app.schemas.common import AdapterStatus, DataSource, PortalId, PriceStance
from app.scoring.humanize import build_humanized_report
from app.scoring.narrative import build_price_narrative, is_peer
from app.zone.maps import build_map_embed
from app.zone.report import build_zone_report


@pytest.fixture(autouse=True)
def _fresh_fixtures():
    clear_fixture_cache()
    yield
    clear_fixture_cache()


def test_fixtures_purged_no_fake_density():
    """Iter4: empty fixtures OK — dense fake set purged."""
    total = sum(len(load_fixture_properties(p)) for p in PortalId)
    assert total == 0


def test_risk_safety_label_and_helptext_no_invert():
    clean = RawProperty(
        portal=PortalId.zonaprop,
        external_id="clean-1",
        source_url="https://www.zonaprop.com.ar/propiedades/clasificado/veclcain-casa-1.html",
        title="Casa luminosa",
        description="Buen estado, lista para vivir",
        rooms=3,
        bathrooms=2,
        parking=1,
        area_covered_m2=120,
        price_amount=130000,
        price_currency="USD",
        address_locality="Gonnet",
        amenities=["jardin"],
        data_source=DataSource.live,
    )
    report = build_humanized_report(clean)
    risk = next(c for c in report.components if c.id == "riskSafety")
    # iter-6: score renombrado en positivo, sin "riesgo" / "salud legal"
    assert risk.label == "Seguridad"
    assert risk.help_text
    assert "patología" not in risk.help_text.lower()
    assert risk.score >= 95  # 100 = sin alertas
    assert "Sin alertas" in (risk.summary or "")
    for c in report.components:
        assert c.help_text, f"{c.id} missing helpText"
    assert not any(c.id == "risk" for c in report.components)


def test_price_narrative_cohort():
    subject = RawProperty(
        portal=PortalId.zonaprop,
        external_id="subj",
        source_url="https://www.zonaprop.com.ar/propiedades/clasificado/s.html",
        title="Casa Gonnet",
        description="x" * 130,
        rooms=3,
        price_amount=100000,
        price_currency="USD",
        address_locality="Gonnet",
        data_source=DataSource.live,
    )
    peers = [
        RawProperty(
            portal=PortalId.argenprop,
            external_id=f"p{i}",
            source_url=f"https://www.argenprop.com/propiedad-{i}",
            title="Peer",
            rooms=3,
            price_amount=120000 + i * 1000,
            price_currency="USD",
            address_locality="Gonnet",
            data_source=DataSource.live,
        )
        for i in range(5)
    ]
    assert all(is_peer(subject, p) for p in peers)
    narrative = build_price_narrative(subject, peers)
    assert narrative.stance == PriceStance.low
    assert narrative.peers_sample_size == 5
    assert narrative.peer_median_amount is not None
    assert "por debajo" in narrative.summary.lower()


def test_zone_report_and_map_external_always():
    raw = RawProperty(
        portal=PortalId.zonaprop,
        external_id="z1",
        source_url="https://www.zonaprop.com.ar/propiedades/clasificado/z.html",
        title="Casa Gonnet",
        description="x" * 130,
        address_locality="Gonnet",
        address_raw="Gonnet, La Plata",
        geo_lat=-34.8805,
        geo_lng=-58.0178,
        rooms=3,
        price_amount=130000,
        price_currency="USD",
        data_source=DataSource.live,
    )
    zone = build_zone_report(raw)
    assert zone.provider.value == "seed"
    assert len(zone.poi) + len(zone.commerce) + len(zone.transit) >= 3
    assert zone.geo.lat is not None

    get_settings.cache_clear()
    settings = get_settings()
    settings.google_maps_api_key = "********"
    settings.feature_google_maps = True
    m = build_map_embed(raw, zone, settings=settings)
    assert m.external_url
    assert "google.com/maps" in m.external_url
    assert m.embed_url is None
    assert m.provider.value == "external_only"

    settings.google_maps_api_key = "AIzaSyTestKey1234567890"
    m2 = build_map_embed(raw, zone, settings=settings)
    assert m2.embed_url
    assert m2.provider.value == "google_embed"
    get_settings.cache_clear()


@pytest.mark.asyncio
async def test_search_with_mocked_live_density(client, monkeypatch):
    """Density targets met via mocked live items (not fake fixtures)."""
    from app.adapters import registry

    def _mk(portal: PortalId, n: int, locality: str = "Gonnet") -> list[RawProperty]:
        host = {
            PortalId.zonaprop: "https://www.zonaprop.com.ar/propiedades/clasificado/x-{i}.html",
            PortalId.mercadolibre: "https://casa.mercadolibre.com.ar/MLA-{i}-casa-_JM",
            PortalId.argenprop: "https://www.argenprop.com/propiedad-{i}",
            PortalId.remax: "https://www.remax.com.ar/listings/{i}",
            PortalId.century21: "https://century21.com.ar/propiedad/{i}",
        }[portal]
        img_host = {
            PortalId.zonaprop: "https://imgar.zonapropcdn.com/avisos/{i}.jpg",
            PortalId.mercadolibre: "https://http2.mlstatic.com/D_NQ_NP_{i}.webp",
            PortalId.argenprop: "https://www.argenprop.com/img/{i}.jpg",
            PortalId.remax: "https://www.remax.com.ar/img/{i}.jpg",
            PortalId.century21: "https://century21.com.ar/img/{i}.jpg",
        }[portal]
        out = []
        for i in range(n):
            out.append(
                RawProperty(
                    portal=portal,
                    external_id=f"{portal.value}-{i}",
                    source_url=host.format(i=1000 + i),
                    title=f"Casa {locality} {i}",
                    description="d" * 130,
                    price_amount=100000 + i * 1000,
                    price_currency="USD",
                    address_locality=locality,
                    rooms=3,
                    images=[{"url": img_host.format(i=i), "order": 0, "kind": "source"}],
                    data_source=DataSource.live,
                )
            )
        return out

    async def fake_run(portal, filters, *, settings=None):
        items = _mk(portal, 4)
        return AdapterResult(
            portal=portal,
            status=AdapterStatus.ok,
            items=items,
            pagination=AdapterPaginationMeta(
                pages_fetched=2,
                listings_raw=len(items),
                listings_after_filter=len(items),
                max_pages=3,
                page_size_hint=20,
                mode="live",
                data_source_hint="live",
            ),
        )

    monkeypatch.setattr(registry, "run_adapter", fake_run)
    import app.search.service as search_service

    monkeypatch.setattr(search_service, "run_adapter", fake_run)

    reg = await client.post(
        "/api/auth/register",
        json={"email": "dens@example.com", "password": "password123", "displayName": "D"},
    )
    assert reg.status_code == 200, reg.text
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
                "placeId": "ar-gonnet",
            },
            "price": {"max": 150000, "currency": "USD"},
        },
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["density"]["totalItems"] >= 15
    assert len(data["items"]) >= 15
    for item in data["items"]:
        assert item["dataSource"] == "live"
        assert "picsum" not in str(item.get("images"))

    prop_id = data["items"][0]["id"]
    detail = await client.get(
        f"/api/properties/{prop_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert detail.status_code == 200, detail.text
    report = detail.json()["report"]
    ids = {c["id"] for c in report["components"]}
    assert "riskSafety" in ids
    assert detail.json()["property"]["dataSource"] == "live"


@pytest.mark.asyncio
async def test_meta_google_maps_flag(client):
    reg = await client.post(
        "/api/auth/register",
        json={"email": "meta@example.com", "password": "password123"},
    )
    token = reg.json()["accessToken"]
    resp = await client.get(
        "/api/meta/adapters",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    features = resp.json()["features"]
    assert "googleMaps" in features
    assert "hybridAdapters" in features
