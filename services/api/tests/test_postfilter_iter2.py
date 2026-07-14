"""Iter-2 post-filter acceptance (mocked honest live inventory; fixtures purged in i4)."""

from __future__ import annotations

import pytest

from app.adapters import registry
from app.adapters.types import AdapterPaginationMeta, AdapterResult, RawProperty
from app.geo.match import location_matches_listing
from app.geo.suggest import suggest_places
from app.schemas.common import AdapterStatus, DataSource, PortalId
from app.schemas.property import Location


GONNET_LOCATION = {
    "query": "Manuel B. Gonnet, La Plata, Buenos Aires",
    "locality": "Gonnet",
    "district": "La Plata",
    "province": "Buenos Aires",
    "country": "AR",
    "placeId": "ar-gonnet",
}


def _inventory() -> list[RawProperty]:
    """Honest-looking live URLs for post-filter tests (not loaded as product fixtures)."""
    rows: list[RawProperty] = []
    # Gonnet band
    for i in range(10):
        rows.append(
            RawProperty(
                portal=PortalId.zonaprop,
                external_id=f"zp-g-{i}",
                source_url=f"https://www.zonaprop.com.ar/propiedades/clasificado/casa-gonnet-{50000 + i}.html",
                title=f"Casa Gonnet {i}",
                description="d" * 130,
                price_amount=90000 + i * 5000,
                price_currency="USD",
                address_locality="Gonnet",
                address_raw="Manuel B. Gonnet, La Plata",
                rooms=3 if i > 0 else None,  # one null rooms for rooms.min exclude
                amenities=["jardin", "pileta"] if i % 2 == 0 else ["jardin"],
                images=[
                    {
                        "url": f"https://imgar.zonapropcdn.com/avisos/{i}.jpg",
                        "order": 0,
                        "kind": "source",
                    }
                ],
                data_source=DataSource.live,
            )
        )
    # Pilar distractors (must be excluded on Gonnet search)
    for i in range(3):
        rows.append(
            RawProperty(
                portal=PortalId.remax,
                external_id=f"rx-p-{i}",
                source_url=f"https://www.remax.com.ar/listings/{7000 + i}",
                title=f"Casa en Pilar GBA Norte {i}",
                description="d" * 130,
                price_amount=110000,
                price_currency="USD",
                address_locality="Pilar",
                address_raw="Pilar, Buenos Aires",
                rooms=3,
                images=[
                    {
                        "url": f"https://www.remax.com.ar/img/{i}.jpg",
                        "order": 0,
                        "kind": "source",
                    }
                ],
                data_source=DataSource.live,
            )
        )
    # Extra portals for solo max-price N≥8
    for i in range(4):
        rows.append(
            RawProperty(
                portal=PortalId.mercadolibre,
                external_id=f"ml-{i}",
                source_url=f"https://casa.mercadolibre.com.ar/MLA-{2000 + i}-casa-_JM",
                title=f"Casa La Plata {i}",
                description="d" * 130,
                price_amount=100000 + i * 1000,
                price_currency="USD",
                address_locality="La Plata",
                rooms=4,
                images=[
                    {
                        "url": f"https://http2.mlstatic.com/D_NQ_{i}.webp",
                        "order": 0,
                        "kind": "source",
                    }
                ],
                data_source=DataSource.live,
            )
        )
    return rows


@pytest.fixture
def mock_live_adapters(monkeypatch):
    inv = _inventory()

    async def fake_run(portal, filters, *, settings=None):
        items = [x for x in inv if x.portal == portal]
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
    return inv


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


def test_live_inventory_under_150k_at_least_8():
    total = sum(
        1
        for raw in _inventory()
        if raw.price_amount is not None
        and (raw.price_currency or "USD").upper() == "USD"
        and raw.price_amount <= 150000
    )
    assert total >= 8


@pytest.mark.asyncio
async def test_search_gonnet_excludes_pilar(client, mock_live_adapters):
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
    assert items, "expected at least one Gonnet listing ≤150k"
    for item in items:
        locality = (item.get("address") or {}).get("locality") or ""
        assert "pilar" not in locality.lower()
        assert locality.lower() == "gonnet"
        assert item["dataSource"] == "live"


@pytest.mark.asyncio
async def test_search_solo_max_price_at_least_8(client, mock_live_adapters):
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
async def test_search_rooms_min_excludes_null_and_low(client, mock_live_adapters):
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
    ext_ids = {i["externalId"] for i in items}
    assert "zp-g-0" not in ext_ids  # null rooms


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
async def test_detail_humanized_report_and_images(client, mock_live_adapters):
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
    assert data["property"]["dataSource"] == "live"


@pytest.mark.asyncio
async def test_interest_rooms_and_amenities_highlight(client, mock_live_adapters):
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
    prop = next(i for i in search.json()["items"] if i.get("rooms") and i.get("amenities"))
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
