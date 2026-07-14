"""Load fixture listings for adapters."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from app.adapters.types import RawProperty
from app.schemas.common import Operation, PortalId, PropertyType


FIXTURES_PATH = Path(__file__).with_name("sample_listings.json")


@lru_cache
def _raw_data() -> dict:
    with FIXTURES_PATH.open(encoding="utf-8") as f:
        return json.load(f)


def load_fixture_properties(portal: PortalId) -> list[RawProperty]:
    rows = _raw_data().get(portal.value, [])
    out: list[RawProperty] = []
    for row in rows:
        out.append(
            RawProperty(
                portal=portal,
                external_id=row["externalId"],
                source_url=row["sourceUrl"],
                title=row["title"],
                description=row.get("description"),
                operation=Operation.buy,
                property_type=PropertyType.house,
                price_amount=row.get("priceAmount"),
                price_currency=row.get("priceCurrency", "USD"),
                address_raw=row.get("addressRaw"),
                address_province=row.get("addressProvince"),
                address_locality=row.get("addressLocality"),
                address_neighborhood=row.get("addressNeighborhood"),
                rooms=row.get("rooms"),
                bathrooms=row.get("bathrooms"),
                parking=row.get("parking"),
                area_covered_m2=row.get("areaCoveredM2"),
                area_total_m2=row.get("areaTotalM2"),
                amenities=row.get("amenities") or [],
                images=row.get("images") or [],
                agent_name=row.get("agentName"),
                agent_phone=row.get("agentPhone"),
                raw_hints={"source": "fixture"},
            )
        )
    return out
