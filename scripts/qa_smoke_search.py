#!/usr/bin/env python3
"""QA smoke: register → login → search Gonnet rooms≥2|3 → Critical if totalItems==0.

Exit codes:
  0 — Critical asserts passed (totalItems ≥ MIN)
  1 — Critical failure (0 items, auth/search HTTP fail, demo_stub in live, ban images)
  2 — config / unreachable API

Env:
  HOUSEHUNT_API_BASE  default http://127.0.0.1:8000
  QA_SMOKE_ROOMS_MIN  default 2 (set 3 for rooms-parse check)
  QA_SMOKE_MIN_ITEMS  default 3 (alt MIN with ≥2 portals; ITERATION prefers 10)
"""

from __future__ import annotations

import json
import os
import sys
import time
import uuid
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

BASE = os.environ.get("HOUSEHUNT_API_BASE", "http://127.0.0.1:8000").rstrip("/")
ROOMS_MIN = int(os.environ.get("QA_SMOKE_ROOMS_MIN", "2"))
MIN_ITEMS = int(os.environ.get("QA_SMOKE_MIN_ITEMS", "3"))
BANNED = (
    "picsum.photos",
    "placeholder.com",
    "loremflickr.com",
    "placekitten.com",
    "placehold.co",
    "dummyimage.com",
)


def _req(method: str, path: str, body: dict | None = None, token: str | None = None) -> tuple[int, Any]:
    data = None if body is None else json.dumps(body).encode("utf-8")
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = Request(f"{BASE}{path}", data=data, headers=headers, method=method)
    try:
        with urlopen(req, timeout=180) as resp:
            raw = resp.read().decode("utf-8")
            return resp.status, json.loads(raw) if raw else {}
    except HTTPError as exc:
        raw = exc.read().decode("utf-8") if exc.fp else ""
        try:
            parsed = json.loads(raw) if raw else {}
        except json.JSONDecodeError:
            parsed = {"raw": raw}
        return exc.code, parsed


def main() -> int:
    critical: list[str] = []
    major: list[str] = []

    email = f"qa-smoke-{uuid.uuid4().hex[:10]}@example.com"
    password = "qa-smoke-pass-123"

    try:
        status, reg = _req(
            "POST",
            "/api/auth/register",
            {"email": email, "password": password, "displayName": "QA Smoke"},
        )
    except URLError as exc:
        print(f"CRITICAL: API unreachable at {BASE}: {exc}", file=sys.stderr)
        return 2

    if status >= 400:
        status, login = _req("POST", "/api/auth/login", {"email": email, "password": password})
        if status >= 400:
            critical.append(f"auth failed register={status} login={status}")
            print(json.dumps({"critical": critical}, indent=2))
            return 1
        token = login.get("accessToken")
    else:
        token = reg.get("accessToken")

    if not token:
        critical.append("missing accessToken")
        print(json.dumps({"critical": critical}, indent=2))
        return 1

    body = {
        "operation": "buy",
        "propertyType": "house",
        "location": {
            "query": "Gonnet",
            "locality": "Gonnet",
            "district": "La Plata",
            "province": "Buenos Aires",
            "country": "AR",
        },
        "price": {"max": 200000, "currency": "USD"},
        "rooms": {"min": ROOMS_MIN},
        "maxPages": 2,
        "pageSizeHint": 20,
    }

    t0 = time.time()
    status, data = _req("POST", "/api/search", body, token=token)
    took = int((time.time() - t0) * 1000)

    if status != 200:
        critical.append(f"search HTTP {status}: {data}")
        print(json.dumps({"critical": critical}, indent=2))
        return 1

    items = data.get("items") or []
    density = data.get("density") or {}
    total = density.get("totalItems", len(items))
    diagnostics = data.get("diagnostics") or {}
    portal_results = data.get("portalResults") or []

    print(
        json.dumps(
            {
                "tookMs": data.get("tookMs", took),
                "totalItems": total,
                "roomsMin": ROOMS_MIN,
                "minRequired": MIN_ITEMS,
                "roomsFilterWiped": diagnostics.get("roomsFilterWiped"),
                "rawCount": diagnostics.get("rawCount"),
                "emptyState": diagnostics.get("emptyState"),
                "portals": [
                    {
                        "portal": p.get("portal"),
                        "status": p.get("status"),
                        "count": p.get("count"),
                        "diagnostics": p.get("diagnostics"),
                        "error": p.get("error"),
                    }
                    for p in portal_results
                ],
            },
            indent=2,
        )
    )

    # A1/A2 — Critical if 0
    if total == 0 or len(items) == 0:
        critical.append("totalItems==0 (E27 Critical)")

    # A3 — MIN items
    portals_live = sum(
        1
        for p in portal_results
        if (p.get("count") or 0) >= 1
        or ((p.get("diagnostics") or {}).get("afterFilterCount") or 0) >= 1
    )
    if total < MIN_ITEMS:
        # alt gate: ≥3 with ≥2 portals OK; else mark critical when below
        if not (total >= 3 and portals_live >= 2):
            critical.append(
                f"totalItems={total} < MIN={MIN_ITEMS} and portals_with_items={portals_live}<2"
            )

    # A9 — no demo_stub in live smoke
    for it in items:
        if it.get("dataSource") == "demo_stub":
            critical.append(f"demo_stub item {it.get('id')}")

    # A7 — ban-list images
    for it in items[:15]:
        for img in it.get("images") or []:
            url = (img.get("url") or "").lower()
            if img.get("kind") == "source" and any(b in url for b in BANNED):
                critical.append(f"banned image host: {url}")

    # A10 iter-7 — fidelidad: solo casas + solo la localidad pedida (Gonnet)
    def _norm(s: str | None) -> str:
        return (s or "").strip().lower()

    allowed_loc = {"gonnet", "manuel b gonnet", "manuel b. gonnet", "la plata", ""}
    non_casa = [it.get("id") for it in items if it.get("propertyType") != "house"]
    if non_casa:
        critical.append(
            f"non-casa items in results ({len(non_casa)}): {non_casa[:5]} (iter-7 fidelity)"
        )
    wrong_loc = []
    for it in items:
        addr = it.get("address") or {}
        loc = _norm(addr.get("locality"))
        neigh = _norm(addr.get("neighborhood"))
        title = _norm(it.get("title"))
        if not loc and not neigh and "gonnet" not in title:
            continue  # sin dato de localidad → lo decide el geo-match, no lo penalizamos acá
        ok = (
            "gonnet" in loc
            or "gonnet" in neigh
            or "gonnet" in title
            or loc in allowed_loc
        )
        if not ok:
            wrong_loc.append({"id": it.get("id"), "locality": addr.get("locality")})
    if wrong_loc:
        critical.append(
            f"wrong-locality items ({len(wrong_loc)}): {wrong_loc[:5]} (iter-7 fidelity)"
        )

    # A11 iter-8 — el aviso testigo C21 debe aparecer (ahora alcanzable server-side)
    expect_id = os.environ.get("QA_SMOKE_EXPECT_ID", "309776").strip()
    if expect_id:
        ext_ids = {str(it.get("externalId") or "") for it in items}
        if expect_id not in ext_ids:
            critical.append(
                f"expected C21 listing {expect_id} not present (iter-8 coverage)"
            )
        c21 = next(
            (p for p in portal_results if p.get("portal") == "century21"),
            None,
        )
        if c21 and (c21.get("count") or 0) == 0:
            critical.append("century21 count==0 (iter-8 coverage)")

    # A12 iter-9 — imágenes C21 reales (no placeholders); host 21online.lat
    c21_items = [it for it in items if (it.get("portal") == "century21")]
    if c21_items:
        c21_source = 0
        c21_placeholder = 0
        for it in c21_items:
            imgs = it.get("images") or []
            first = imgs[0] if imgs else {}
            kind = first.get("kind")
            host = (first.get("url") or "").lower()
            if kind == "source" and "21online.lat" in host:
                c21_source += 1
            elif kind == "placeholder" or not imgs:
                c21_placeholder += 1
        if c21_source == 0:
            critical.append(
                "no C21 item has a real source image (cdn.21online.lat) — iter-9 P0-1"
            )
        if c21_placeholder:
            major.append(f"C21 items still on placeholder: {c21_placeholder}")

    # A4 major — diagnostics present
    if not diagnostics:
        major.append("missing diagnostics")
    for p in portal_results:
        d = p.get("diagnostics")
        if not d or "rawCount" not in d:
            major.append(f"portal {p.get('portal')} missing diagnostics")

    print(json.dumps({"critical": critical, "major": major}, indent=2), file=sys.stderr)
    return 1 if critical else 0


if __name__ == "__main__":
    raise SystemExit(main())
