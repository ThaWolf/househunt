"""iter-8: C21 build_search_url arma la URL de resultados filtrada server-side."""

from __future__ import annotations

from app.adapters.century21.live import (
    C21_GBA_SUR,
    C21_SEARCH_UI,
    build_search_url,
)
from app.schemas.common import Currency, PropertyType
from app.schemas.property import Location, MinIntFilter, PriceFilters, SearchFilters


def _filters(
    *,
    locality: str = "Gonnet",
    rooms_min: int | None = None,
    price_max: float | None = None,
    price_min: float | None = None,
    currency: Currency = Currency.USD,
) -> SearchFilters:
    price = None
    if price_max is not None or price_min is not None:
        price = PriceFilters(min=price_min, max=price_max, currency=currency)
    return SearchFilters(
        property_type=PropertyType.house,
        location=Location(
            query=locality, locality=locality, district="La Plata", province="Buenos Aires"
        ),
        price=price,
        rooms=MinIntFilter(min=rooms_min) if rooms_min is not None else None,
    )


def test_gonnet_3dorm_150k_matches_reference_url():
    url = build_search_url(_filters(locality="Gonnet", rooms_min=3, price_max=150000))
    assert url == (
        "https://century21.com.ar/v/resultados/"
        "tipo_casa-o-casa-duplex-o-cabana-o-casa-nautica/operacion_venta/uso_habitacional/"
        "en-pais_argentina/en-estado_gba-sur/en-municipio_gba-sur-la-plata/"
        "en-colonia_la-plata-manuel-b-gonnet/dormitorios_3/moneda_usd/precio-hasta_150000"
    )


def test_gonnet_no_rooms_omits_dormitorios():
    url = build_search_url(_filters(locality="Gonnet", price_max=150000))
    assert "en-colonia_la-plata-manuel-b-gonnet" in url
    assert "dormitorios_" not in url
    assert url.endswith("moneda_usd/precio-hasta_150000")


def test_gonnet_no_price_omits_moneda_and_precio():
    url = build_search_url(_filters(locality="Gonnet"))
    assert "moneda_" not in url
    assert "precio-" not in url
    assert url.endswith("en-colonia_la-plata-manuel-b-gonnet")


def test_price_min_and_max_emit_desde_and_hasta():
    url = build_search_url(_filters(locality="Gonnet", price_min=80000, price_max=150000))
    assert "precio-desde_80000" in url
    assert "precio-hasta_150000" in url


def test_city_bell_uses_municipio_level_no_colonia():
    url = build_search_url(_filters(locality="City Bell", price_max=150000))
    assert "en-municipio_gba-sur-la-plata" in url
    assert "en-colonia_" not in url  # sin colonia confirmada → geo-cleanup afina


def test_plain_la_plata_municipio_level():
    url = build_search_url(_filters(locality="La Plata", rooms_min=2))
    assert "en-municipio_gba-sur-la-plata" in url
    assert "en-colonia_" not in url
    assert "dormitorios_2" in url


def test_unmapped_locality_falls_back_to_search_ui():
    # Localidad fuera del scope La Plata / GBA Sur conocido → fallback iter-7.
    url = build_search_url(_filters(locality="Cordoba Capital", price_max=150000))
    assert url in (C21_SEARCH_UI, C21_GBA_SUR)


def test_ars_currency_segment():
    url = build_search_url(
        _filters(locality="Gonnet", price_max=50000000, currency=Currency.ARS)
    )
    assert "moneda_ars" in url
