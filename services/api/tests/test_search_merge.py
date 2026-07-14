"""Search merge with 1 adapter failure."""

from __future__ import annotations

import pytest
from app.adapters import registry
from app.adapters.types import AdapterError, AdapterResult
from app.schemas.common import AdapterErrorCode, AdapterStatus, PortalId


@pytest.mark.asyncio
async def test_search_merge_with_one_adapter_fail(client, monkeypatch):
    original = registry.run_adapter

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
        return await original(portal, filters, settings=settings)

    monkeypatch.setattr(registry, "run_adapter", flaky_run)
    # Also patch where search.service imported it
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
    assert len(data["items"]) >= 1  # other portals returned fixtures

    by_portal = {p["portal"]: p for p in data["portalResults"]}
    assert by_portal["remax"]["status"] == "error"
    assert by_portal["remax"]["error"]["code"] == "bot_wall"
    # At least one other portal ok
    okish = [p for p in data["portalResults"] if p["portal"] != "remax" and p["status"] in ("ok", "partial")]
    assert okish
