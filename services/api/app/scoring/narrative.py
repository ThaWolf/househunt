"""PriceNarrative vs cohort: same locality, rooms ±1 (DOMAIN §15)."""

from __future__ import annotations

from statistics import median
from typing import Sequence

from app.adapters.types import RawProperty
from app.schemas.common import Currency, PriceStance
from app.schemas.property import PriceNarrative


def _norm_locality(value: str | None) -> str:
    if not value:
        return ""
    return value.strip().lower()


def is_peer(subject: RawProperty, candidate: RawProperty) -> bool:
    if candidate.external_id == subject.external_id and candidate.portal == subject.portal:
        return False
    if subject.price_amount is None or candidate.price_amount is None:
        return False
    subj_cur = (subject.price_currency or "USD").upper()
    cand_cur = (candidate.price_currency or "USD").upper()
    if subj_cur != cand_cur:
        return False
    if _norm_locality(subject.address_locality) != _norm_locality(candidate.address_locality):
        return False
    if subject.rooms is not None and candidate.rooms is not None:
        if abs(candidate.rooms - subject.rooms) > 1:
            return False
    elif subject.rooms is None:
        return False  # unknown rooms → stance unknown path
    return True


def stance_from_ratio(ratio: float) -> PriceStance:
    if ratio <= 0.90:
        return PriceStance.low
    if ratio >= 1.10:
        return PriceStance.high
    return PriceStance.fair


def price_fit_from_stance(stance: PriceStance) -> float:
    """Buyer-facing fit: low price → high fit."""
    return {
        PriceStance.low: 88.0,
        PriceStance.fair: 65.0,
        PriceStance.high: 35.0,
        PriceStance.unknown: 50.0,
    }[stance]


def build_price_narrative(
    subject: RawProperty,
    peers: Sequence[RawProperty],
) -> PriceNarrative:
    currency = None
    if subject.price_currency:
        try:
            currency = Currency(subject.price_currency.upper())
        except ValueError:
            currency = Currency.USD

    if subject.price_amount is None or subject.rooms is None:
        return PriceNarrative(
            summary=(
                "No hay suficientes casas similares en esta búsqueda para comparar el precio."
            ),
            stance=PriceStance.unknown,
            peers_sample_size=0,
            peer_median_amount=None,
            currency=currency,
        )

    peer_prices = [float(p.price_amount) for p in peers if p.price_amount is not None]
    n = len(peer_prices)
    if n < 3:
        return PriceNarrative(
            summary=(
                "No hay suficientes casas similares en esta búsqueda para comparar el precio."
            ),
            stance=PriceStance.unknown,
            peers_sample_size=n,
            peer_median_amount=None,
            currency=currency,
        )

    med = float(median(peer_prices))
    ratio = float(subject.price_amount) / med if med else 1.0
    stance = stance_from_ratio(ratio)
    locality = subject.address_locality or "la zona"
    lo = max(1, subject.rooms - 1)
    hi = subject.rooms + 1

    if stance == PriceStance.low:
        posture = "por debajo del típico"
    elif stance == PriceStance.high:
        posture = "por encima del típico"
    else:
        posture = "en línea con el típico"

    summary = (
        f"El precio está {posture} de casas similares en {locality} "
        f"(según {n} avisos con {lo}–{hi} ambientes). "
        "Puede ser oportunidad o reflejar estado/ubicación; revisá el aviso original."
    )
    return PriceNarrative(
        summary=summary,
        stance=stance,
        peers_sample_size=n,
        peer_median_amount=round(med, 2),
        currency=currency,
    )
