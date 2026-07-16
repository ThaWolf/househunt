"""Parse price amount + currency from portal card text (iter-6 + harden iter-10).

Fixes the ML/C21 coverage bug where USD listings shown as "US$ 150.000" were
parsed as ARS (only "U$S"/"USD" were recognized), then dropped by the USD
currency post-filter. See lanes/analysis/RCA.md.

iter-10: avoid treating street heights (e.g. "504 y 24 2800") as listing price
when scanning full page body text.
"""

from __future__ import annotations

import re

# USD markers used across AR real-estate portals (order matters: check before bare "$").
_USD_MARKERS = ("US$", "U$S", "U$D", "USD", "DÓLAR", "DOLAR", "DÓLARES", "DOLARES")
_ARS_MARKERS = ("ARS", "PESOS", "$")

# Street / address-ish context before a number (altura de calle).
_STREET_BEFORE = re.compile(
    r"(?:calle|av\.?|avenida|e/|entre|\by\b)\s*$",
    re.I,
)
_STREET_AFTER = re.compile(
    r"^\s*(?:bis|e/|entre|,?\s*piso)",
    re.I,
)


def detect_currency(*texts: str | None) -> str | None:
    blob = " ".join(t for t in texts if t).upper()
    if not blob:
        return None
    if any(m in blob for m in _USD_MARKERS):
        return "USD"
    if any(m in blob for m in _ARS_MARKERS):
        return "ARS"
    return None


def _looks_like_street_number(text: str, start: int, end: int) -> bool:
    before = text[max(0, start - 24) : start]
    after = text[end : min(len(text), end + 16)]
    if _STREET_BEFORE.search(before):
        return True
    if _STREET_AFTER.match(after):
        return True
    # "504 y 24 2800" — digit y digit then this number
    if re.search(r"\d{2,4}\s+y\s+\d{1,4}\s+$", before, re.I):
        return True
    return False


def parse_price(
    *texts: str | None,
    default_currency: str | None = None,
    prefer_largest: bool = False,
    reject_street_numbers: bool = False,
) -> tuple[float | None, str | None]:
    """Return (amount, currency).

    By default returns the first plausible price-looking number.
    When ``prefer_largest`` is True (body fallback), pick the best candidate
    preferring currency-marked spans and larger housing-band amounts.
    """
    currency = detect_currency(*texts) or default_currency
    candidates: list[tuple[float, bool]] = []  # amount, has_currency_nearby

    for text in texts:
        if not text:
            continue
        t = text.replace("\xa0", " ")
        for m in re.finditer(r"\d[\d.,]{2,}", t):
            if reject_street_numbers and _looks_like_street_number(t, m.start(), m.end()):
                continue
            digits = re.sub(r"[^\d]", "", m.group(0))
            if not digits:
                continue
            try:
                amount = float(digits)
            except ValueError:
                continue
            if not (1000 <= amount <= 100_000_000):
                continue
            window = t[max(0, m.start() - 12) : m.end() + 8].upper()
            marked = any(mk in window for mk in _USD_MARKERS) or "U$S" in window
            if not prefer_largest:
                return amount, currency
            candidates.append((amount, marked))

    if not candidates:
        return None, currency

    # Prefer currency-marked; among those (or all) prefer amount in housing band,
    # then largest.
    marked = [c for c in candidates if c[1]]
    pool = marked or candidates

    def rank(item: tuple[float, bool]) -> tuple[int, float]:
        amt = item[0]
        in_band = 1 if 40_000 <= amt <= 800_000 else 0
        return (in_band, amt)

    best = max(pool, key=rank)
    return best[0], currency
