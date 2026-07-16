"""Iter-6 — price/currency parsing (fix ML/C21 USD shown as US$ parsed as ARS)."""

from __future__ import annotations

from app.adapters.price_parse import detect_currency, parse_price


def test_detect_currency_recognizes_usd_variants():
    assert detect_currency("US$ 150.000") == "USD"
    assert detect_currency("U$S 150.000") == "USD"
    assert detect_currency("USD 150.000") == "USD"
    assert detect_currency("Dólares 150.000") == "USD"
    # bare "$" on AR listing → ARS
    assert detect_currency("$ 90.000.000") == "ARS"
    assert detect_currency("") is None


def test_us_dollar_symbol_not_misread_as_ars():
    # Regression: "US$" contains "$" but must resolve to USD, not ARS.
    amount, currency = parse_price("US$ 149.900", default_currency="USD")
    assert currency == "USD"
    assert amount == 149900


def test_parse_price_picks_plausible_number_from_card_text():
    card = "3 Rec. 2 Baños\nCasa en Gonnet\nUS$ 130.000\n120 m² cubiertos"
    amount, currency = parse_price(card, default_currency="USD")
    assert currency == "USD"
    assert amount == 130000
