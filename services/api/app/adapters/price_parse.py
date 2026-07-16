"""Parse price amount + currency from portal card text (iter-6).

Fixes the ML/C21 coverage bug where USD listings shown as "US$ 150.000" were
parsed as ARS (only "U$S"/"USD" were recognized), then dropped by the USD
currency post-filter. See lanes/analysis/RCA.md.
"""

from __future__ import annotations

import re

# USD markers used across AR real-estate portals (order matters: check before bare "$").
_USD_MARKERS = ("US$", "U$S", "U$D", "USD", "DÓLAR", "DOLAR", "DÓLARES", "DOLARES")
_ARS_MARKERS = ("ARS", "PESOS", "$")


def detect_currency(*texts: str | None) -> str | None:
    blob = " ".join(t for t in texts if t).upper()
    if not blob:
        return None
    if any(m in blob for m in _USD_MARKERS):
        return "USD"
    if any(m in blob for m in _ARS_MARKERS):
        return "ARS"
    return None


def parse_price(*texts: str | None, default_currency: str | None = None) -> tuple[float | None, str | None]:
    """Return (amount, currency). Amount is the first plausible price-looking number."""
    currency = detect_currency(*texts) or default_currency
    for text in texts:
        if not text:
            continue
        t = text.replace("\xa0", " ")
        # Number groups with '.'/',' thousands separators (no whitespace → no cross-line concat).
        for m in re.finditer(r"\d[\d.,]{2,}", t):
            digits = re.sub(r"[^\d]", "", m.group(0))
            if not digits:
                continue
            try:
                amount = float(digits)
            except ValueError:
                continue
            # Ignore obviously non-price small/huge tokens
            if 1000 <= amount <= 100_000_000:
                return amount, currency
    return None, currency
