"""Iter 3: dense fixtures, riskSafety, narrative, zone/map, http images."""

from __future__ import annotations

import pytest

from app.adapters.fixtures.loader import clear_fixture_cache, load_fixture_properties
from app.adapters.types import RawProperty
from app.config import get_settings
from app.schemas.common import PortalId, PriceStance
from app.scoring.humanize import build_humanized_report
from app.scoring.narrative import build_price_narrative, is_peer
from app.zone.maps import build_map_embed
from app.zone.report import build_zone_report


@pytest.fixture(autouse=True)
def _fresh_fixtures():
    clear_fixture_cache()
    yield
    clear_fixture_cache()


def test_fixture_density_per_portal():
    for portal in PortalId:
        items = load_fixture_properties(portal)
        assert len(items) >= 8, f"{portal} has {len(items)} fixtures"
        assert len(items) >= 10


def test_gonnet_band_total_ge_15():
    total = 0
    for portal in PortalId:
        for item in load_fixture_properties(portal):
            if (item.address_locality or "").lower() == "gonnet" and (
                item.price_amount is not None and item.price_amount <= 150_000
            ):
                total += 1
    assert total >= 15


def test_solo_max_price_band_ge_15():
    total = 0
    for portal in PortalId:
        for item in load_fixture_properties(portal):
            if item.price_amount is not None and item.price_amount <= 150_000:
                total += 1
    assert total >= 15


def test_images_are_http_source():
    for portal in PortalId:
        for item in load_fixture_properties(portal):
            assert item.images, f"{portal}/{item.external_id} missing images"
            for img in item.images:
                url = img["url"]
                assert url.startswith("http://") or url.startswith("https://")
                assert "placehold.co" not in url
                assert img.get("kind", "source") == "source"


def test_descriptions_are_long():
    for portal in PortalId:
        for item in load_fixture_properties(portal):
            assert item.description and len(item.description) >= 120


def test_risk_safety_label_and_helptext_no_invert():
    clean = RawProperty(
        portal=PortalId.zonaprop,
        external_id="clean-1",
        source_url="https://example.com/c",
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
    )
    report = build_humanized_report(clean)
    risk = next(c for c in report.components if c.id == "riskSafety")
    assert risk.label == "Salud legal / riesgo"
    assert risk.help_text
    assert risk.score >= 95  # 100 = sin señales
    assert "Sin señales" in (risk.summary or "")
    for c in report.components:
        assert c.help_text, f"{c.id} missing helpText"
    assert not any(c.id == "risk" for c in report.components)


def test_price_narrative_cohort():
    subject = RawProperty(
        portal=PortalId.zonaprop,
        external_id="subj",
        source_url="https://example.com/s",
        title="Casa Gonnet",
        description="x" * 130,
        rooms=3,
        price_amount=100000,
        price_currency="USD",
        address_locality="Gonnet",
    )
    peers = [
        RawProperty(
            portal=PortalId.argenprop,
            external_id=f"p{i}",
            source_url=f"https://example.com/{i}",
            title="Peer",
            rooms=3,
            price_amount=120000 + i * 1000,
            price_currency="USD",
            address_locality="Gonnet",
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
        source_url="https://example.com/z",
        title="Casa Gonnet",
        description="x" * 130,
        address_locality="Gonnet",
        address_raw="Gonnet, La Plata",
        geo_lat=-34.8805,
        geo_lng=-58.0178,
        rooms=3,
        price_amount=130000,
        price_currency="USD",
    )
    zone = build_zone_report(raw)
    assert zone.provider.value == "seed"
    assert len(zone.poi) + len(zone.commerce) + len(zone.transit) >= 3
    assert zone.geo.lat is not None

    get_settings.cache_clear()
    settings = get_settings()
    # No valid maps key in tests → external_only, embedUrl null
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
async def test_search_gonnet_density_and_pagination(client):
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

    # pagination meta present
    for pr in data["portalResults"]:
        assert pr.get("pagination") is not None
        assert pr["pagination"]["listingsRaw"] >= 8

    # http images
    with_http = 0
    for item in data["items"]:
        imgs = item.get("images") or []
        if imgs and str(imgs[0]["url"]).startswith("http"):
            with_http += 1
    assert with_http / max(len(data["items"]), 1) >= 0.8

    # detail: riskSafety + zone + map
    prop_id = data["items"][0]["id"]
    detail = await client.get(
        f"/api/properties/{prop_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert detail.status_code == 200, detail.text
    report = detail.json()["report"]
    ids = {c["id"] for c in report["components"]}
    assert "riskSafety" in ids
    risk = next(c for c in report["components"] if c["id"] == "riskSafety")
    assert risk["label"] == "Salud legal / riesgo"
    assert risk.get("helpText")
    assert report.get("priceNarrative") is not None
    assert report.get("zoneReport") is not None
    assert report["map"]["externalUrl"]
    assert detail.json()["property"].get("description")
    assert len(detail.json()["property"]["description"]) >= 120


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
