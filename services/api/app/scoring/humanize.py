"""Build HumanizedReport from AppScore (no raw weights as primary UI)."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Sequence

from app.adapters.types import RawProperty
from app.schemas.property import (
    HumanizedReport,
    MapEmbed,
    PriceNarrative,
    RiskHit,
    ScoreComponent,
    ZoneReport,
)
from app.scoring.appscore import ScoreResult, compute_appscore
from app.scoring.lexicon import find_risk_hits
from app.scoring.narrative import build_price_narrative, is_peer, price_fit_from_stance

# id -> (label, helpText)
COMPONENT_META: dict[str, tuple[str, str]] = {
    "attrs": (
        "Atributos",
        "Habitaciones, baños, cochera y amenities vs lo esperado para una casa.",
    ),
    "area": (
        "Superficie",
        "Metros cubiertos y terreno frente a un rango típico del cohort local.",
    ),
    "zone": (
        "Zona",
        "Actividad del entorno (POI, comercios, transporte) cerca del inmueble.",
    ),
    "priceFit": (
        "Ajuste de precio",
        "Qué tan alineado está el precio vs casas similares (mismo band de zona).",
    ),
    "riskSafety": (
        "Salud legal / riesgo",
        "Señales en el texto del aviso (obra, legal, patología). 100 = sin señales; 0 = muchas.",
    ),
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

_WEIGHT_BY_TERM: dict[str, float] = {
    "para demoler": 25,
    "demolicion": 25,
    "okupas": 20,
    "usurpado": 20,
    "embargado": 18,
    "remate judicial": 18,
    "refaccionar": 8,
    "a refaccionar": 8,
    "requiere obra": 10,
    "necesita obra": 10,
    "humedad": 6,
}


def _bar_pct(score: float, max_score: float = 100.0) -> float:
    if max_score <= 0:
        return 0.0
    return max(0.0, min(100.0, round(score / max_score * 100.0, 1)))


def _component(
    cid: str,
    score: float,
    *,
    summary: str | None = None,
) -> ScoreComponent:
    label, help_text = COMPONENT_META[cid]
    return ScoreComponent(
        id=cid,  # type: ignore[arg-type]
        label=label,
        help_text=help_text,
        score=round(score, 1),
        max_score=100,
        bar_pct=_bar_pct(score),
        summary=summary,
        note=summary,
    )


def build_humanized_report(
    raw: RawProperty,
    score: ScoreResult | None = None,
    *,
    poi_enabled: bool = False,
    peers: Sequence[RawProperty] | None = None,
    price_narrative: PriceNarrative | None = None,
    zone_report: ZoneReport | None = None,
    map_embed: MapEmbed | None = None,
) -> HumanizedReport:
    score = score or compute_appscore(raw, poi_enabled=poi_enabled)
    bd = score.breakdown
    weights = bd.weights or {}

    zone_summary = None
    if weights.get("zone", 0) == 0:
        zone_summary = "Sin datos de zona — peso redistribuido"
    elif zone_report and zone_report.summary:
        zone_summary = zone_report.summary

    # Price narrative + consistent priceFit
    if price_narrative is None and peers is not None:
        peer_list = [p for p in peers if is_peer(raw, p)]
        price_narrative = build_price_narrative(raw, peer_list)
    elif price_narrative is None:
        price_narrative = build_price_narrative(raw, [])

    price_fit_score = price_fit_from_stance(price_narrative.stance)
    price_summary = price_narrative.summary

    # riskSafety: 100 = sin señales (NO invert polarity to "100 = malo")
    risk_safety = max(0.0, 100.0 - float(bd.risk_penalty))
    hits_raw = find_risk_hits(raw.title, raw.description)
    risk_hits: list[RiskHit] = []
    for term, weight in hits_raw:
        label = RISK_LABELS.get(term, term.replace("_", " ").capitalize())
        risk_hits.append(
            RiskHit(
                keyword=term,
                term=term,
                weight=float(weight or _WEIGHT_BY_TERM.get(term, 1.0)),
                label=label,
            )
        )

    if risk_hits:
        risk_summary = "Señales: " + ", ".join(
            (h.label or h.keyword or "") for h in risk_hits[:4]
        )
    else:
        risk_summary = "Sin señales de riesgo en el aviso"

    components: list[ScoreComponent] = [
        _component("attrs", bd.attrs),
        _component("area", bd.area),
        _component("zone", bd.zone, summary=zone_summary),
        _component("priceFit", price_fit_score, summary=price_summary),
        _component("riskSafety", risk_safety, summary=risk_summary),
    ]

    summary_parts = [f"AppScore {score.score}/100."]
    if risk_hits:
        summary_parts.append(
            "Señales de riesgo: " + ", ".join(h.label or "" for h in risk_hits[:4]) + "."
        )
    else:
        summary_parts.append("Sin señales de riesgo en el aviso.")
    if zone_summary and weights.get("zone", 0) == 0:
        summary_parts.append(zone_summary + ".")

    return HumanizedReport(
        summary=" ".join(summary_parts),
        app_score=score.score,
        components=components,
        risk_hits=risk_hits,
        price_narrative=price_narrative,
        zone_report=zone_report,
        map=map_embed,
        generated_at=datetime.now(timezone.utc),
    )
