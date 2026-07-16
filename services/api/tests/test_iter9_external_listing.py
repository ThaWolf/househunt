"""iter-9: extractor de publicación externa + endpoint POST /api/interest/external."""

from __future__ import annotations

import pytest

from app.adapters.external.extract import (
    _collect_images,
    _detect_portal,
    _external_id,
    _iter_ld_nodes,
    _ld_pick,
    _price,
)
from app.adapters.types import RawProperty
from app.schemas.common import DataSource, PortalId


# --- extractor: pure helpers ---------------------------------------------------

def test_detect_portal_known_and_unknown():
    assert _detect_portal("century21.com.ar") is PortalId.century21
    assert _detect_portal("www.zonaprop.com.ar") is PortalId.zonaprop
    assert _detect_portal("casa.mercadolibre.com.ar") is PortalId.mercadolibre
    assert _detect_portal("example.com") is None


def test_external_id_known_portal_from_url():
    c21 = "https://century21.com.ar/propiedad/309776_casa-en-venta-gonnet"
    assert _external_id(c21, PortalId.century21) == "309776"
    ml = "https://casa.mercadolibre.com.ar/MLA-1234567-casa-_JM"
    assert _external_id(ml, PortalId.mercadolibre) == "1234567"


def test_external_id_unknown_is_stable_hash():
    url = "https://example.com/propiedad/casa-linda?utm=1"
    a = _external_id(url, None)
    b = _external_id(url + "#frag", None)  # querystring/fragment stripped by _clean_url
    assert a.startswith("ext-")
    assert a == b  # estable → dedupe


def test_iter_ld_nodes_flattens_graph_and_lists():
    blocks = [
        '{"@graph":[{"@type":"Product","name":"Casa"},{"@type":"Offer","price":"140000"}]}',
        '[{"@type":"Residence","description":"linda"}]',
        "not json {",
    ]
    nodes = _iter_ld_nodes(blocks)
    names = [n.get("name") for n in nodes if n.get("name")]
    assert "Casa" in names


def test_ld_pick_and_price():
    nodes = _iter_ld_nodes(
        [
            '{"@type":"Product","name":"Casa Gonnet","description":"hermosa",'
            '"image":["https://cdn.21online.lat/a.jpg"],'
            '"offers":{"price":"140000","priceCurrency":"USD"}}'
        ]
    )
    ld = _ld_pick(nodes)
    assert ld["name"] == "Casa Gonnet"
    amount, currency = _price(ld, {}, "")
    assert amount == 140000
    assert currency == "USD"


def test_collect_images_filters_banned_and_dedupes():
    ld = {"image": ["https://cdn.21online.lat/a.jpg", "https://picsum.photos/x.jpg"]}
    og = ["https://cdn.21online.lat/a.jpg", "https://cdn.example.com/b.jpg"]
    imgs = _collect_images(ld, og, None)
    urls = [i["url"] for i in imgs]
    assert "https://cdn.21online.lat/a.jpg" in urls
    assert "https://cdn.example.com/b.jpg" in urls
    assert "https://picsum.photos/x.jpg" not in urls  # banned
    assert len(urls) == len(set(urls))  # dedupe
    assert all(i["kind"] == "source" for i in imgs)


# --- endpoint: POST /api/interest/external ------------------------------------

def _fake_raw() -> RawProperty:
    return RawProperty(
        portal=PortalId.external,
        external_id="ext-abc123def456",
        source_url="https://example.com/casa-linda",
        title="Casa linda en Gonnet",
        description="d" * 140,
        price_amount=150000,
        price_currency="USD",
        address_locality="Gonnet",
        address_province="Buenos Aires",
        rooms=3,
        images=[{"url": "https://cdn.example.com/1.jpg", "order": 0, "kind": "source"}],
        data_source=DataSource.external,
    )


async def _token(client) -> str:
    reg = await client.post(
        "/api/auth/register",
        json={"email": "ext@example.com", "password": "password123", "displayName": "E"},
    )
    assert reg.status_code == 200, reg.text
    return reg.json()["accessToken"]


@pytest.mark.asyncio
async def test_external_interest_happy_path(client, monkeypatch):
    async def fake_extract(url, *, settings=None):
        return _fake_raw()

    monkeypatch.setattr("app.interest.router.extract_listing", fake_extract)
    token = await _token(client)
    headers = {"Authorization": f"Bearer {token}"}

    resp = await client.post(
        "/api/interest/external",
        headers=headers,
        json={"url": "https://example.com/casa-linda"},
    )
    assert resp.status_code == 201, resp.text
    item = resp.json()
    assert item["property"]["dataSource"] == "external"
    assert item["property"]["sourceUrl"] == "https://example.com/casa-linda"
    assert item["property"]["images"][0]["url"] == "https://cdn.example.com/1.jpg"
    assert item["state"] == "active"

    # aparece en la lista de intereses
    lst = await client.get("/api/interest", headers=headers)
    assert lst.status_code == 200
    ext_urls = [it["property"]["sourceUrl"] for it in lst.json()["items"]]
    assert "https://example.com/casa-linda" in ext_urls


@pytest.mark.asyncio
async def test_external_interest_dedupe_conflict(client, monkeypatch):
    async def fake_extract(url, *, settings=None):
        return _fake_raw()

    monkeypatch.setattr("app.interest.router.extract_listing", fake_extract)
    token = await _token(client)
    headers = {"Authorization": f"Bearer {token}"}
    body = {"url": "https://example.com/casa-linda"}

    first = await client.post("/api/interest/external", headers=headers, json=body)
    assert first.status_code == 201
    second = await client.post("/api/interest/external", headers=headers, json=body)
    # iter-10: refresh existing interest (200) instead of 409 stale
    assert second.status_code == 200
    assert second.json()["id"] == first.json()["id"]
    assert second.json()["property"]["id"] == first.json()["property"]["id"]


@pytest.mark.asyncio
async def test_external_interest_unsupported_url(client, monkeypatch):
    from app.adapters.external import ExternalExtractError

    async def fail_extract(url, *, settings=None):
        raise ExternalExtractError("unsupported_url", "URL inválida")

    monkeypatch.setattr("app.interest.router.extract_listing", fail_extract)
    token = await _token(client)
    headers = {"Authorization": f"Bearer {token}"}

    resp = await client.post(
        "/api/interest/external",
        headers=headers,
        json={"url": "notaurl"},
    )
    assert resp.status_code == 422, resp.text
