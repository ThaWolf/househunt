"""AppScore 0–100 per DOMAIN §3.3."""

from __future__ import annotations

from dataclasses import dataclass

from app.adapters.types import RawProperty
from app.schemas.common import ScoreBreakdown
from app.scoring.lexicon import find_risk_hits, risk_penalty


@dataclass
class ScoreResult:
    score: int
    breakdown: ScoreBreakdown


def _clamp(value: float, lo: float = 0.0, hi: float = 100.0) -> float:
    return max(lo, min(hi, value))


def attrs_score(raw: RawProperty) -> float:
    points = 40.0
    if raw.rooms is not None:
        points += min(20.0, raw.rooms * 4)
    if raw.bathrooms is not None:
        points += min(15.0, raw.bathrooms * 5)
    if raw.parking is not None and raw.parking > 0:
        points += 10.0
    amenity_bonus = min(15.0, len(raw.amenities or []) * 3)
    points += amenity_bonus
    return _clamp(points)


def area_score(raw: RawProperty) -> float:
    covered = raw.area_covered_m2
    total = raw.area_total_m2
    if covered is None and total is None:
        return 50.0  # neutral when missing — will redistribute
    base = 30.0
    if covered is not None:
        base += min(40.0, covered / 3.0)
    if total is not None:
        base += min(30.0, total / 10.0)
    return _clamp(base)


def price_fit_score(raw: RawProperty) -> float:
    """MVP stub: midscore if priced; lower if suspiciously low without details."""
    if raw.price_amount is None:
        return 50.0
    amount = float(raw.price_amount)
    if amount <= 0:
        return 40.0
    # Heuristic bands for GBA houses (USD-ish)
    if 80000 <= amount <= 450000:
        return 75.0
    if amount < 40000:
        return 35.0
    if amount > 800000:
        return 55.0
    return 60.0


def compute_appscore(raw: RawProperty, *, poi_enabled: bool = False) -> ScoreResult:
    hits = find_risk_hits(raw.title, raw.description)
    penalty = risk_penalty(hits)

    components: dict[str, float] = {
        "attrs": attrs_score(raw),
        "area": area_score(raw),
        "price_fit": price_fit_score(raw),
    }
    # Zone: stub 50 when POI off — redistribuir if we treat zone as unavailable
    base_weights = {
        "attrs": 0.25,
        "area": 0.20,
        "zone": 0.20,
        "price_fit": 0.20,
    }
    if poi_enabled:
        components["zone"] = 50.0
        weights = dict(base_weights)
    else:
        # Redistribute zone weight over available components
        weights = {"attrs": 0.30, "area": 0.25, "price_fit": 0.25, "zone": 0.0}
        components["zone"] = 50.0  # recorded for transparency; weight 0

    weighted = sum(weights[k] * components[k] for k in ("attrs", "area", "price_fit", "zone"))
    # Normalize weight sum (price+attrs+area = 0.80 when zone 0)
    wsum = sum(weights.values()) or 1.0
    normalized = weighted / wsum * (0.85)  # leave headroom for risk
    # Simpler DOMAIN formula: sum(W_i * score_i) - penalty, clamp
    raw_score = (
        weights["attrs"] * components["attrs"]
        + weights["area"] * components["area"]
        + weights["zone"] * components["zone"]
        + weights["price_fit"] * components["price_fit"]
        - penalty
    )
    # When zone weight redistributed, scale to keep ~0-100 range
    if weights["zone"] == 0:
        scale = 1.0 / 0.80
        raw_score = (
            (weights["attrs"] * components["attrs"]
             + weights["area"] * components["area"]
             + weights["price_fit"] * components["price_fit"])
            * scale
            - penalty
        )

    score = int(round(_clamp(raw_score)))
    breakdown = ScoreBreakdown(
        attrs=round(components["attrs"], 2),
        area=round(components["area"], 2),
        zone=round(components["zone"], 2),
        price_fit=round(components["price_fit"], 2),
        risk_penalty=penalty,
        weights=weights,
        risk_hits=[h for h, _ in hits],
    )
    return ScoreResult(score=score, breakdown=breakdown)


def report_stub(raw: RawProperty, score: ScoreResult) -> dict:
    hits = score.breakdown.risk_hits
    summary = "Reporte básico MVP: atributos + keywords de riesgo."
    if hits:
        summary += f" Señales de riesgo: {', '.join(hits)}."
    else:
        summary += " Sin keywords de riesgo detectadas."
    if not poi_enabled_note():
        summary += " ZoneScore stub (POI deshabilitado)."
    return {
        "summary": summary,
        "risk_hits": hits,
    }


def poi_enabled_note() -> bool:
    from app.config import get_settings

    return get_settings().feature_poi
