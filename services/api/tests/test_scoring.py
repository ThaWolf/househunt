"""Keyword scoring tests."""

from app.adapters.types import RawProperty
from app.schemas.common import PortalId
from app.scoring.appscore import compute_appscore
from app.scoring.lexicon import find_risk_hits, risk_penalty


def test_risk_keywords_detect_obra_and_humedad():
    hits = find_risk_hits(
        "Casa a refaccionar",
        "Requiere obra y hay humedad en muros",
    )
    labels = {h for h, _ in hits}
    assert "refaccionar" in labels
    assert "requiere obra" in labels
    assert "humedad" in labels
    assert risk_penalty(hits) >= 8 + 10 + 6


def test_a_estrenar_not_penalized():
    hits = find_risk_hits("Casa a estrenar", "Lista para vivir a estrenar")
    assert hits == []


def test_appscore_lowers_with_risk():
    clean = RawProperty(
        portal=PortalId.argenprop,
        external_id="a1",
        source_url="https://example.com/1",
        title="Casa luminosa",
        description="Buen estado",
        rooms=4,
        bathrooms=2,
        parking=1,
        area_covered_m2=180,
        price_amount=300000,
        price_currency="USD",
        amenities=["jardin", "pileta"],
    )
    risky = RawProperty(
        portal=PortalId.argenprop,
        external_id="a2",
        source_url="https://example.com/2",
        title="Casa para demoler",
        description="Okupas. Embargado. Remate judicial.",
        rooms=4,
        bathrooms=2,
        parking=1,
        area_covered_m2=180,
        price_amount=300000,
        price_currency="USD",
        amenities=["jardin", "pileta"],
    )
    s_clean = compute_appscore(clean)
    s_risky = compute_appscore(risky)
    assert 0 <= s_clean.score <= 100
    assert 0 <= s_risky.score <= 100
    assert s_risky.score < s_clean.score
    assert s_risky.breakdown.risk_penalty > 0
    assert "demolicion" in s_risky.breakdown.risk_hits or "okupas" in s_risky.breakdown.risk_hits
