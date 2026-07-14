"""Iter-2 post-filter acceptance: Gonnet≠Pilar, solo max price ≥8, rooms.min."""

from __future__ import annotations

import pytest

from app.adapters.fixtures.loader import clear_fixture_cache, load_fixture_properties
from app.geo.match import location_matches_listing
from app.geo.suggest import suggest_places
from app.schemas.common import PortalId
from app.schemas.property import Location


GONNET_LOCATION = {
    "query": "Manuel B. Gonnet, La Plata, Buenos Aires",
    "locality": "Gonnet",
    "district": "La Plata",
    "province": "Buenos Aires",
    "country": "AR",
    "placeId": "ar-gonnet",
}


@pytest.fixture(autouse=True)
def _reload_fixtures():
    clear_fixture_cache()
    yield
    clear_fixture_cache()


def test_gonnet_hard_excludes_pilar_unit():
    loc = Location.model_validate(GONNET_LOCATION)
    assert location_matches_listing(
        loc,
        address_locality="Gonnet",
        address_raw="Manuel B. Gonnet, La Plata",
        title="Casa en Gonnet",
    )
    assert not location_matches_listing(
        loc,
        address_locality="Pilar",
        address_raw="Pilar, Buenos Aires",
        title="Casa en Pilar GBA Norte",
    )
    assert not location_matches_listing(
        loc,
        address_locality="City Bell",
        address_raw="City Bell, La Plata",
        title="Casa City Bell",
    )


def test_la_plata_parent_expands_children():
    loc = Location(
        query="La Plata, Buenos Aires",
        locality="La Plata",
        district="La Plata",
        province="Buenos Aires",
        country="AR",
        place_id="ar-la-plata",
    )
    assert location_matches_listing(loc, address_locality="Gonnet", address_raw="Gonnet")
    assert location_matches_listing(loc, address_locality="City Bell", address_raw="City Bell")
    assert location_matches_listing(loc, address_locality="La Plata", address_raw="La Plata centro")
    assert not location_matches_listing(loc, address_locality="Pilar", address_raw="Pilar")


def test_geo_suggest_gonnet():
    items = suggest_places("gonnet")
    assert items
    assert any(i.place_id == "ar-gonnet" for i in items)
    assert items[0].locality == "Gonnet"


def test_fixture_inventory_under_150k_at_least_8():
    total = 0
    for portal in PortalId:
        for raw in load_fixture_properties(portal):
            if (
                raw.price_amount is not None
                and (raw.price_currency or "USD").upper() == "USD"
                and raw.price_amount <= 150000
            ):
                total += 1
    assert total >= 8, f"expected ≥8 fixtures ≤150k USD, got {total}"


@pytest.mark.asyncio
async def test_search_gonnet_excludes_pilar(client):
    reg = await client.post(
        "/api/auth/register",
        json={"email": "gonnet@example.com", "password": "password123", "displayName": "G"},
    )
    assert reg.status_code == 200, reg.text
    token = reg.json()["accessToken"]

    resp = await client.post(
        "/api/search",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "operation": "buy",
            "propertyType": "house",
            "location": GONNET_LOCATION,
            "price": {"max": 150000, "currency": "USD"},
        },
    )
    assert resp.status_code == 200, resp.text
    items = resp.json()["items"]
    assert items, "expected at least one Gonnet fixture ≤150k"
    for item in items:
        locality = (item.get("address") or {}).get("locality") or ""
        assert "pilar" not in locality.lower()
        assert "pilar" not in (item.get("title") or "").lower() or "gonnet" in locality.lower()
        # locality must be Gonnet (strict)
        assert locality.lower() == "gonnet"


@pytest.mark.asyncio
async def test_search_solo_max_price_at_least_8(client):
    reg = await client.post(
        "/api/auth/register",
        json={"email": "maxprice@example.com", "password": "password123", "displayName": "M"},
    )
    assert reg.status_code == 200, reg.text
    token = reg.json()["accessToken"]

    resp = await client.post(
        "/api/search",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "operation": "buy",
            "propertyType": "house",
            "price": {"max": 150000, "currency": "USD"},
        },
    )
    assert resp.status_code == 200, resp.text
    items = resp.json()["items"]
    assert len(items) >= 8, f"N=8 required, got {len(items)}"
    for item in items:
        amount = (item.get("price") or {}).get("amount")
        assert amount is not None and amount <= 150000


@pytest.mark.asyncio
async def test_search_rooms_min_excludes_null_and_low(client):
    reg = await client.post(
        "/api/auth/register",
        json={"email": "rooms@example.com", "password": "password123", "displayName": "R"},
    )
    assert reg.status_code == 200, reg.text
    token = reg.json()["accessToken"]

    resp = await client.post(
        "/api/search",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "operation": "buy",
            "propertyType": "house",
            "location": GONNET_LOCATION,
            "rooms": {"min": 3},
            "price": {"max": 150000, "currency": "USD"},
        },
    )
    assert resp.status_code == 200, resp.text
    items = resp.json()["items"]
    assert items
    for item in items:
        assert item.get("rooms") is not None
        assert item["rooms"] >= 3
    # null-rooms fixture rx-4102 must be excluded
    ext_ids = {i["externalId"] for i in items}
    assert "rx-4102" not in ext_ids


@pytest.mark.asyncio
async def test_geo_suggest_endpoint(client):
    reg = await client.post(
        "/api/auth/register",
        json={"email": "geo@example.com", "password": "password123", "displayName": "Geo"},
    )
    token = reg.json()["accessToken"]
    resp = await client.get(
        "/api/geo/suggest",
        params={"q": "manuel b gonnet"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200, resp.text
    items = resp.json()["items"]
    assert items
    assert items[0]["placeId"] == "ar-gonnet"
    assert items[0]["label"]


@pytest.mark.asyncio
async def test_detail_humanized_report_and_images(client):
    reg = await client.post(
        "/api/auth/register",
        json={"email": "detail@example.com", "password": "password123", "displayName": "D"},
    )
    token = reg.json()["accessToken"]
    search = await client.post(
        "/api/search",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "operation": "buy",
            "propertyType": "house",
            "location": GONNET_LOCATION,
            "price": {"max": 150000, "currency": "USD"},
        },
    )
    prop_id = search.json()["items"][0]["id"]
    detail = await client.get(
        f"/api/properties/{prop_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert detail.status_code == 200, detail.text
    data = detail.json()
    report = data["report"]
    assert "appScore" in report
    assert "components" in report and len(report["components"]) >= 4
    assert all("barPct" in c and "label" in c for c in report["components"])
    assert "weights" not in report
    images = data["property"]["images"]
    assert isinstance(images, list) and len(images) >= 1


@pytest.mark.asyncio
async def test_interest_rooms_and_amenities_highlight(client):
    reg = await client.post(
        "/api/auth/register",
        json={"email": "interest@example.com", "password": "password123", "displayName": "I"},
    )
    token = reg.json()["accessToken"]
    search = await client.post(
        "/api/search",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "operation": "buy",
            "propertyType": "house",
            "location": GONNET_LOCATION,
            "price": {"max": 150000, "currency": "USD"},
        },
    )
    prop = next(i for i in search.json()["items"] if i.get("rooms"))
    created = await client.post(
        "/api/interest",
        headers={"Authorization": f"Bearer {token}"},
        json={"propertyId": prop["id"]},
    )
    assert created.status_code == 201, created.text
    body = created.json()
    assert "rooms" in body
    assert body["rooms"] == prop["rooms"]
    hl = body["amenitiesHighlight"]
    assert len(hl) >= 2
    tokens = {h["token"]: h for h in hl}
    assert "pileta" in tokens and "jardin" in tokens
    assert "present" in tokens["pileta"]
