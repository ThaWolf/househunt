"""Search merge with 1 adapter failure — honest empty OK."""

from __future__ import annotations

import pytest

from app.adapters import registry
from app.adapters.types import AdapterError, AdapterPaginationMeta, AdapterResult, RawProperty
from app.schemas.common import AdapterErrorCode, AdapterStatus, DataSource, PortalId


@pytest.mark.asyncio
async def test_search_merge_with_one_adapter_fail(client, monkeypatch):
    async def flaky_run(portal, filters, *, settings=None):
        if portal == PortalId.remax:
            return AdapterResult(
                portal=portal,
                status=AdapterStatus.error,
                items=[],
                error=AdapterError(
                    code=AdapterErrorCode.bot_wall,
                    message="Remax bot wall",
                    retryable=True,
                ),
            )
        # Honest partial live slice for other portals
        item = RawProperty(
            portal=portal,
            external_id=f"{portal.value}-1",
            source_url={
                PortalId.zonaprop: "https://www.zonaprop.com.ar/propiedades/clasificado/casa-1.html",
                PortalId.argenprop: "https://www.argenprop.com/propiedad-1",
                PortalId.mercadolibre: "https://casa.mercadolibre.com.ar/MLA-1-_JM",
                PortalId.century21: "https://century21.com.ar/propiedad/1",
            }.get(portal, f"https://example.com/{portal.value}"),
            title=f"Casa {portal.value}",
            description="d" * 130,
            price_amount=120000,
            price_currency="USD",
            address_locality="Gonnet",
            rooms=3,
            images=[
                {
                    "url": "https://imgar.zonapropcdn.com/avisos/1.jpg"
                    if portal == PortalId.zonaprop
                    else "https://http2.mlstatic.com/D_NQ_1.webp"
                    if portal == PortalId.mercadolibre
                    else f"https://www.{portal.value}.com/img/1.jpg"
                    if portal != PortalId.century21
                    else "https://century21.com.ar/img/1.jpg",
                    "order": 0,
                    "kind": "source",
                }
            ],
            data_source=DataSource.live,
        )
        return AdapterResult(
            portal=portal,
            status=AdapterStatus.ok,
            items=[item],
            pagination=AdapterPaginationMeta(
                pages_fetched=1,
                listings_raw=1,
                listings_after_filter=1,
                max_pages=3,
                page_size_hint=20,
                mode="live",
                data_source_hint="live",
            ),
        )

    monkeypatch.setattr(registry, "run_adapter", flaky_run)
    import app.search.service as search_service

    monkeypatch.setattr(search_service, "run_adapter", flaky_run)

    reg = await client.post(
        "/api/auth/register",
        json={"email": "search@example.com", "password": "password123", "displayName": "S"},
    )
    assert reg.status_code == 200, reg.text
    token = reg.json()["accessToken"]

    resp = await client.post(
        "/api/search",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "operation": "buy",
            "propertyType": "house",
            "geo": {"mode": "gba"},
        },
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert "items" in data
    assert "portalResults" in data
    assert len(data["items"]) >= 1

    by_portal = {p["portal"]: p for p in data["portalResults"]}
    assert by_portal["remax"]["status"] == "error"
    assert by_portal["remax"]["error"]["code"] == "bot_wall"
    okish = [
        p for p in data["portalResults"] if p["portal"] != "remax" and p["status"] in ("ok", "partial")
    ]
    assert okish
