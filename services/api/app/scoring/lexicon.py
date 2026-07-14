"""Risk keyword lexicon v0 (DOMAIN §4)."""

from __future__ import annotations

import re

# (pattern, weight, label) — case-insensitive match on title+description
# "a estrenar" weight 0 — do not penalize
RISK_KEYWORDS: list[tuple[str, int, str]] = [
    (r"\brefaccionar\b|\ba\s+refaccionar\b", 8, "refaccionar"),
    (r"\bpotencial\b|\bcon\s+potencial\b", 6, "potencial"),
    (r"\breciclar\b|\ba\s+reciclar\b", 8, "reciclar"),
    (r"\ba\s+terminar\b", 5, "a terminar"),
    (r"\ben\s+pozo\b", 4, "en pozo"),
    (r"\brequiere\s+obra\b|\bnecesita\s+obra\b", 10, "requiere obra"),
    (r"\bpara\s+demoler\b|\bdemolici[oó]n\b", 12, "demolicion"),
    (r"\binvertido\b|\binversionista\b", 4, "inversor"),
    (r"\bokupas?\b|\busurpado\b", 15, "okupas"),
    (r"\bembargado\b|\bremate\s+judicial\b", 12, "embargo"),
    (r"\bsucesi[oó]n\b|\blitigio\b", 8, "sucesion"),
    (r"\bhumedad\b|\bfiltraciones\b", 6, "humedad"),
    (r"\bgrietas\b|\brajaduras\b", 5, "grietas"),
    (r"\bsin\s+escritura\b|\bboleto\b", 7, "sin escritura"),
    (r"\bterreno\s+irregular\b|\buso\s+no\s+residencial\b", 6, "uso irregular"),
    (r"\bapuro\b|\burgente\b|\bremate\b", 5, "apuro"),
]

MAX_RISK_PENALTY = 40


def find_risk_hits(title: str | None, description: str | None) -> list[tuple[str, int]]:
    text = f"{title or ''} {description or ''}".lower()
    hits: list[tuple[str, int]] = []
    seen: set[str] = set()
    for pattern, weight, label in RISK_KEYWORDS:
        if weight <= 0:
            continue
        if re.search(pattern, text, flags=re.IGNORECASE):
            if label not in seen:
                seen.add(label)
                hits.append((label, weight))
    return hits


def risk_penalty(hits: list[tuple[str, int]]) -> float:
    return float(min(MAX_RISK_PENALTY, sum(w for _, w in hits)))
