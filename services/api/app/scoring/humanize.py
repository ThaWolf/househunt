"""Build HumanizedReport from AppScore (no raw weights as primary UI)."""

from __future__ import annotations

from datetime import datetime, timezone

from app.adapters.types import RawProperty
from app.schemas.property import HumanizedReport, RiskHit, ScoreComponent
from app.scoring.appscore import ScoreResult, compute_appscore

COMPONENT_META: dict[str, tuple[str, str]] = {
    # id -> (label ES, note key)
    "attrs": ("Atributos", ""),
    "area": ("Área", ""),
    "zone": ("Zona", "Sin datos de zona — peso redistribuido"),
    "price_fit": ("Ajuste precio", ""),
    "risk": ("Riesgo", ""),
}

RISK_LABELS: dict[str, str] = {
    "refaccionar": "Riesgo de obra",
    "a refaccionar": "Riesgo de obra",
    "potencial": "Eufemismo de estado",
    "con potencial": "Eufemismo de estado",
    "reciclar": "Riesgo de obra",
    "a reciclar": "Riesgo de obra",
    "a terminar": "Obra incompleta",
    "en pozo": "En pozo",
    "requiere obra": "Obra explícita",
    "necesita obra": "Obra explícita",
    "para demoler": "Riesgo alto de demolición",
    "demolicion": "Riesgo alto de demolición",
    "invertido": "Sesgo no-vivienda",
    "inversionista": "Sesgo no-vivienda",
    "okupas": "Riesgo de ocupación",
    "usurpado": "Riesgo de ocupación",
    "embargado": "Riesgo legal",
    "remate judicial": "Riesgo legal",
    "sucesion": "Riesgo legal",
    "litigio": "Riesgo legal",
    "humedad": "Patología (humedad)",
    "filtraciones": "Patología (filtraciones)",
    "grietas": "Patología (grietas)",
    "rajaduras": "Patología (rajaduras)",
    "sin escritura": "Documentación incompleta",
    "boleto": "Documentación (boleto)",
    "terreno irregular": "Riesgo urbanístico",
    "uso no residencial": "Uso no residencial",
    "apuro": "Precio sospechoso",
    "urgente": "Precio sospechoso",
    "remate": "Precio sospechoso",
}


def _bar_pct(score: float, max_score: float = 100.0) -> float:
    if max_score <= 0:
        return 0.0
    return max(0.0, min(100.0, round(score / max_score * 100.0, 1)))


def build_humanized_report(
    raw: RawProperty,
    score: ScoreResult | None = None,
    *,
    poi_enabled: bool = False,
) -> HumanizedReport:
    score = score or compute_appscore(raw, poi_enabled=poi_enabled)
    bd = score.breakdown
    weights = bd.weights or {}
    zone_note = None
    if weights.get("zone", 0) == 0:
        zone_note = COMPONENT_META["zone"][1]

    components: list[ScoreComponent] = [
        ScoreComponent(
            id="attrs",
            label=COMPONENT_META["attrs"][0],
            score=round(bd.attrs, 1),
            max_score=100,
            bar_pct=_bar_pct(bd.attrs),
            note=None,
        ),
        ScoreComponent(
            id="area",
            label=COMPONENT_META["area"][0],
            score=round(bd.area, 1),
            max_score=100,
            bar_pct=_bar_pct(bd.area),
            note=None,
        ),
        ScoreComponent(
            id="zone",
            label=COMPONENT_META["zone"][0],
            score=round(bd.zone, 1),
            max_score=100,
            bar_pct=_bar_pct(bd.zone),
            note=zone_note,
        ),
        ScoreComponent(
            id="priceFit",
            label=COMPONENT_META["price_fit"][0],
            score=round(bd.price_fit, 1),
            max_score=100,
            bar_pct=_bar_pct(bd.price_fit),
            note=None,
        ),
        ScoreComponent(
            id="risk",
            label=COMPONENT_META["risk"][0],
            score=max(0.0, 100.0 - float(bd.risk_penalty)),
            max_score=100,
            bar_pct=_bar_pct(max(0.0, 100.0 - float(bd.risk_penalty))),
            note=f"Penalización {bd.risk_penalty:.0f} pts" if bd.risk_penalty else None,
        ),
    ]

    risk_hits: list[RiskHit] = []
    for term in bd.risk_hits:
        label = RISK_LABELS.get(term, term.replace("_", " ").capitalize())
        risk_hits.append(RiskHit(term=term, label=label))

    summary_parts = [f"AppScore {score.score}/100."]
    if risk_hits:
        summary_parts.append(
            "Señales de riesgo: " + ", ".join(h.label for h in risk_hits[:4]) + "."
        )
    else:
        summary_parts.append("Sin keywords de riesgo detectadas.")
    if zone_note:
        summary_parts.append(zone_note + ".")

    return HumanizedReport(
        summary=" ".join(summary_parts),
        app_score=score.score,
        components=components,
        risk_hits=risk_hits,
        generated_at=datetime.now(timezone.utc),
    )
