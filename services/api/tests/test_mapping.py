"""Property mapping tests."""

from datetime import datetime, timezone
from uuid import uuid4

from app.adapters.types import RawProperty
from app.db.models import Property
from app.mappers import property_to_dto, raw_property_to_model
from app.schemas.common import Operation, PortalId, PropertyType


def test_raw_property_to_model_and_dto():
    raw = RawProperty(
        portal=PortalId.zonaprop,
        external_id="zp-map-1",
        source_url="https://www.zonaprop.com.ar/propiedades/x.html",
        title="Casa mapping",
        description="desc",
        operation=Operation.buy,
        property_type=PropertyType.house,
        price_amount=200000,
        price_currency="USD",
        address_raw="Vicente López",
        address_province="Buenos Aires",
        address_locality="Vicente López",
        rooms=4,
        bathrooms=2,
        parking=1,
        area_covered_m2=150,
        area_total_m2=300,
        amenities=["jardin"],
        images=[{"url": "https://placehold.co/1.png", "order": 0}],
        scraped_at=datetime.now(timezone.utc),
    )
    row = raw_property_to_model(raw, property_id=uuid4(), app_score=72, score_breakdown={"attrs": 80})
    assert isinstance(row, Property)
    assert row.portal == "zonaprop"
    assert row.external_id == "zp-map-1"
    assert row.price_amount == 200000
    assert row.amenities == ["jardin"]

    dto = property_to_dto(row)
    dumped = dto.model_dump(by_alias=True)
    assert dumped["externalId"] == "zp-map-1"
    assert dumped["sourceUrl"].startswith("https://")
    assert dumped["area"]["coveredM2"] == 150
    assert dumped["appScore"] == 72
