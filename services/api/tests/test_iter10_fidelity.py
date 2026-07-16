"""iter-10 — price harden, rooms words, amenities parse, external enrich."""

from __future__ import annotations

from app.adapters.amenities_parse import parse_amenities
from app.adapters.external.extract import _normalize_locality, _price
from app.adapters.price_parse import parse_price
from app.adapters.rooms_parse import parse_rooms


def test_parse_price_rejects_street_height_prefers_usd():
    body = "Casa en venta. Calle 504 y 24 2800, Piso 0. Excelente. Precio US$ 128.000 negociable."
    amount, cur = parse_price(
        body,
        default_currency="USD",
        prefer_largest=True,
        reject_street_numbers=True,
    )
    assert amount == 128000.0
    assert cur == "USD"


def test_parse_price_street_alone_not_preferred_as_housing():
    # Without currency mark, 2800 after "y 24" should be rejected as street
    body = "504 y 24 2800, Piso 0 Casa en Gonnet tres dormitorios"
    amount, _ = parse_price(
        body,
        default_currency="USD",
        prefer_largest=True,
        reject_street_numbers=True,
    )
    assert amount is None or amount >= 40000


def test_external_price_helper_street_vs_usd():
    body = "504 y 24 2800, Piso 0. Venta US$ 155.000"
    amount, cur = _price({}, {}, body)
    assert amount == 155000.0
    assert cur == "USD"


def test_parse_rooms_word_numbers():
    assert parse_rooms("Casa de tres dormitorios en Gonnet") == 3
    assert parse_rooms("https://x.com/casa-4-ambientes--1") == 4
    assert parse_rooms("dos ambientes luminosos") == 2


def test_parse_amenities_aliases():
    tokens = parse_amenities("VENTA. DUPLEX 3 DORMITORIOS Y PILETA con parque y cochera")
    assert "pileta" in tokens
    assert "jardin" in tokens
    assert "cochera" in tokens


def test_parse_amenities_parrilla_quincho():
    assert "quincho" in parse_amenities("galería y parrilla al fondo")


def test_normalize_locality_partido_and_slug():
    loc, neigh, prov = _normalize_locality(
        "https://www.argenprop.com/casa-en-venta-en-manuel-b-gonnet-4-ambientes--1",
        "Casa en Venta en Manuel B Gonnet",
        "Casa en Gonnet",
        "",
        "Partido de La Plata, Argentina",
        "La Plata",
    )
    assert loc and "gonnet" in loc.lower()
    assert prov == "Buenos Aires"
