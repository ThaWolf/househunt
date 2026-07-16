"""Tests for shared interest lists (membership, invite, addedBy, visits)."""

from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient

from app.db import models


async def _register(client: AsyncClient, email: str, password: str = "secret123") -> dict:
    res = await client.post(
        "/api/auth/register",
        json={"email": email, "password": password, "displayName": email.split("@")[0]},
    )
    assert res.status_code == 200, res.text
    return res.json()


def _auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def _default_list_id(client: AsyncClient, token: str) -> str:
    res = await client.get("/api/interest/lists", headers=_auth_headers(token))
    assert res.status_code == 200
    items = res.json()["items"]
    assert items
    return items[0]["id"]


async def _seed_property(db_session) -> uuid.UUID:
    prop = models.Property(
        portal="zonaprop",
        external_id=f"test-{uuid.uuid4().hex[:8]}",
        source_url="https://example.com/listing",
        title="Casa test",
        operation="buy",
        property_type="house",
        scraped_at=__import__("datetime").datetime.now(__import__("datetime").timezone.utc),
    )
    db_session.add(prop)
    await db_session.flush()
    await db_session.commit()
    return prop.id


@pytest.mark.asyncio
async def test_default_list_created_on_lists_get(client):
    owner = await _register(client, "owner@example.com")
    res = await client.get("/api/interest/lists", headers=_auth_headers(owner["accessToken"]))
    assert res.status_code == 200
    data = res.json()
    assert len(data["items"]) == 1
    assert data["items"][0]["role"] == "owner"
    assert data["items"][0]["memberCount"] == 1


@pytest.mark.asyncio
async def test_invite_existing_user(client):
    owner = await _register(client, "owner2@example.com")
    collab = await _register(client, "collab@example.com")
    list_id = await _default_list_id(client, owner["accessToken"])

    res = await client.post(
        f"/api/interest/lists/{list_id}/members",
        headers=_auth_headers(owner["accessToken"]),
        json={"email": "collab@example.com"},
    )
    assert res.status_code == 201
    assert res.json()["role"] == "collaborator"

    collab_lists = await client.get(
        "/api/interest/lists", headers=_auth_headers(collab["accessToken"])
    )
    assert collab_lists.status_code == 200
    assert any(i["id"] == list_id for i in collab_lists.json()["items"])


@pytest.mark.asyncio
async def test_invite_unknown_user_422(client):
    owner = await _register(client, "owner3@example.com")
    list_id = await _default_list_id(client, owner["accessToken"])
    res = await client.post(
        f"/api/interest/lists/{list_id}/members",
        headers=_auth_headers(owner["accessToken"]),
        json={"email": "ghost@example.com"},
    )
    assert res.status_code == 422
    assert res.json()["code"] == "user_not_found"


@pytest.mark.asyncio
async def test_non_member_forbidden(client, db_session):
    owner = await _register(client, "owner4@example.com")
    outsider = await _register(client, "outsider@example.com")
    list_id = await _default_list_id(client, owner["accessToken"])

    res = await client.get(
        f"/api/interest?listId={list_id}",
        headers=_auth_headers(outsider["accessToken"]),
    )
    assert res.status_code == 403


@pytest.mark.asyncio
async def test_added_by_on_create(client, db_session):
    owner = await _register(client, "owner5@example.com")
    list_id = await _default_list_id(client, owner["accessToken"])
    prop_id = await _seed_property(db_session)

    res = await client.post(
        "/api/interest",
        headers=_auth_headers(owner["accessToken"]),
        json={"propertyId": str(prop_id), "listId": list_id},
    )
    assert res.status_code == 201
    body = res.json()
    assert body["addedBy"]["email"] == "owner5@example.com"


@pytest.mark.asyncio
async def test_collaborator_item_visible_to_owner(client, db_session):
    owner = await _register(client, "owner6@example.com")
    collab = await _register(client, "collab6@example.com")
    list_id = await _default_list_id(client, owner["accessToken"])
    await client.post(
        f"/api/interest/lists/{list_id}/members",
        headers=_auth_headers(owner["accessToken"]),
        json={"email": "collab6@example.com"},
    )
    prop_id = await _seed_property(db_session)

    created = await client.post(
        "/api/interest",
        headers=_auth_headers(collab["accessToken"]),
        json={"propertyId": str(prop_id), "listId": list_id},
    )
    assert created.status_code == 201
    assert created.json()["addedBy"]["email"] == "collab6@example.com"

    listed = await client.get(
        f"/api/interest?listId={list_id}",
        headers=_auth_headers(owner["accessToken"]),
    )
    assert listed.status_code == 200
    assert len(listed.json()["items"]) == 1


@pytest.mark.asyncio
async def test_shared_visit(client, db_session):
    owner = await _register(client, "owner7@example.com")
    collab = await _register(client, "collab7@example.com")
    list_id = await _default_list_id(client, owner["accessToken"])
    await client.post(
        f"/api/interest/lists/{list_id}/members",
        headers=_auth_headers(owner["accessToken"]),
        json={"email": "collab7@example.com"},
    )
    prop_id = await _seed_property(db_session)
    await client.post(
        "/api/interest",
        headers=_auth_headers(owner["accessToken"]),
        json={"propertyId": str(prop_id), "listId": list_id},
    )

    at = "2026-07-20T15:30:00+00:00"
    put = await client.put(
        f"/api/properties/{prop_id}/visit",
        headers=_auth_headers(collab["accessToken"]),
        json={"status": "scheduled", "at": at, "listId": list_id},
    )
    assert put.status_code == 200

    owner_list = await client.get(
        f"/api/interest?listId={list_id}",
        headers=_auth_headers(owner["accessToken"]),
    )
    assert owner_list.json()["items"][0]["visit"]["status"] == "scheduled"


@pytest.mark.asyncio
async def test_archive_shared(client, db_session):
    owner = await _register(client, "owner8@example.com")
    collab = await _register(client, "collab8@example.com")
    list_id = await _default_list_id(client, owner["accessToken"])
    await client.post(
        f"/api/interest/lists/{list_id}/members",
        headers=_auth_headers(owner["accessToken"]),
        json={"email": "collab8@example.com"},
    )
    prop_id = await _seed_property(db_session)
    created = await client.post(
        "/api/interest",
        headers=_auth_headers(owner["accessToken"]),
        json={"propertyId": str(prop_id), "listId": list_id},
    )
    interest_id = created.json()["id"]

    archived = await client.post(
        f"/api/interest/{interest_id}/archive",
        headers=_auth_headers(collab["accessToken"]),
    )
    assert archived.status_code == 200

    archived_list = await client.get(
        f"/api/interest?listId={list_id}&state=archived",
        headers=_auth_headers(owner["accessToken"]),
    )
    assert len(archived_list.json()["items"]) == 1


@pytest.mark.asyncio
async def test_calendar_list_scoped(client, db_session):
    owner = await _register(client, "owner9@example.com")
    list_id = await _default_list_id(client, owner["accessToken"])
    prop_id = await _seed_property(db_session)
    await client.post(
        "/api/interest",
        headers=_auth_headers(owner["accessToken"]),
        json={"propertyId": str(prop_id), "listId": list_id},
    )
    at = "2026-07-21T10:00:00+00:00"
    await client.put(
        f"/api/properties/{prop_id}/visit",
        headers=_auth_headers(owner["accessToken"]),
        json={"status": "scheduled", "at": at, "listId": list_id},
    )

    cal = await client.get(
        f"/api/calendar?listId={list_id}&from=2026-07-01T00:00:00Z&to=2026-07-31T23:59:59Z",
        headers=_auth_headers(owner["accessToken"]),
    )
    assert cal.status_code == 200
    assert len(cal.json()["events"]) == 1
