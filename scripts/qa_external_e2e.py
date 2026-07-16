#!/usr/bin/env python3
"""QA e2e (iter-9): agregar publicación externa por URL → aparece en Intereses.

register → POST /api/interest/external {url} → GET /api/interest → asserts.

Exit codes:
  0 — OK (interés creado con título + source_url real + imagen)
  1 — Critical failure
  2 — API unreachable / config

Env:
  HOUSEHUNT_API_BASE   default http://127.0.0.1:8000
  QA_EXTERNAL_URL      default C21 309776 (known real listing)
"""

from __future__ import annotations

import json
import os
import sys
import uuid
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

BASE = os.environ.get("HOUSEHUNT_API_BASE", "http://127.0.0.1:8000").rstrip("/")
URL = os.environ.get(
    "QA_EXTERNAL_URL",
    "https://century21.com.ar/propiedad/309776_casa-en-venta-en-la-plata-ideal-fines-comerciales-gonnet-verde-cochera",
)
BANNED = ("picsum.photos", "placeholder.com", "loremflickr.com", "placehold.co", "dummyimage.com")


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
    email = f"qa-ext-{uuid.uuid4().hex[:10]}@example.com"

    try:
        status, reg = _req(
            "POST",
            "/api/auth/register",
            {"email": email, "password": "qa-ext-pass-123", "displayName": "QA Ext"},
        )
    except URLError as exc:
        print(f"CRITICAL: API unreachable at {BASE}: {exc}", file=sys.stderr)
        return 2
    token = reg.get("accessToken")
    if not token:
        print(f"CRITICAL: no token ({status}) {reg}", file=sys.stderr)
        return 1

    status, item = _req("POST", "/api/interest/external", {"url": URL}, token=token)
    if status != 201:
        print(f"CRITICAL: external POST HTTP {status}: {item}", file=sys.stderr)
        return 1

    prop = item.get("property") or {}
    title = prop.get("title") or ""
    source_url = prop.get("sourceUrl") or ""
    data_source = prop.get("dataSource")
    images = prop.get("images") or []
    first_img = (images[0] if images else {}).get("url", "")

    print(
        json.dumps(
            {
                "interestId": item.get("id"),
                "title": title[:80],
                "dataSource": data_source,
                "sourceUrl": source_url,
                "price": prop.get("price"),
                "portal": prop.get("portal"),
                "imageCount": len(images),
                "firstImage": first_img[:80],
            },
            indent=2,
        )
    )

    if not title:
        critical.append("external listing has no title")
    # 'external' para listings nuevos; 'live'/'fixture_curated' si dedup reusa uno ya conocido
    if data_source not in ("external", "live", "fixture_curated"):
        critical.append(f"unexpected dataSource ({data_source})")
    if not source_url.startswith("http"):
        critical.append(f"sourceUrl not real: {source_url}")
    if not images:
        critical.append("external listing has no image")
    if any(b in first_img.lower() for b in BANNED):
        critical.append(f"banned image host: {first_img}")

    # aparece en la lista de intereses
    status, lst = _req("GET", "/api/interest?state=active", token=token)
    ids = {it.get("id") for it in (lst.get("items") or [])}
    if item.get("id") not in ids:
        critical.append("external interest not present in /api/interest list")

    # error path: URL inválida → 4xx claro
    status_bad, _ = _req("POST", "/api/interest/external", {"url": "notaurl"}, token=token)
    if status_bad < 400 or status_bad >= 500:
        critical.append(f"invalid URL should be 4xx, got {status_bad}")

    print(json.dumps({"critical": critical}, indent=2), file=sys.stderr)
    return 1 if critical else 0


if __name__ == "__main__":
    raise SystemExit(main())
