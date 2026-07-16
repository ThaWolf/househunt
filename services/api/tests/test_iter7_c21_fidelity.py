"""iter-7: fidelidad C21 — parse tipo/localidad reales + enforce tipo=casa."""

from __future__ import annotations

from app.adapters.listing_meta import detect_locality, detect_property_type
from app.db import models
from app.schemas.common import PropertyType
from app.schemas.property import Location, PriceFilters, SearchFilters
from app.search.postfilter import passes_post_filters, passes_type

C21 = "https://century21.com.ar/propiedad/{id}_{slug}"


def _href(slug: str, id_: str = "309776") -> str:
    return C21.format(id=id_, slug=slug)


# --- detect_property_type -------------------------------------------------

def test_casa_with_cochera_amenity_is_house_not_other():
    # Regresión 309776: el slug termina en "-verde-cochera" pero es una CASA.
    href = _href("casa-en-venta-en-la-plata-ideal-fines-comerciales-gonnet-verde-cochera")
    assert detect_property_type(href, "Casa en venta en La Plata") is PropertyType.house


def test_departamento_is_apartment():
    assert (
        detect_property_type(_href("departamento-en-venta-en-la-plata-centro", "111"))
        is PropertyType.apartment
    )


def test_ph_is_apartment():
    assert detect_property_type(_href("ph-en-venta-en-tolosa", "112")) is PropertyType.apartment


def test_oficina_local_cochera_are_other():
    assert detect_property_type(_href("oficina-en-venta-en-la-plata", "1")) is PropertyType.other
    assert detect_property_type(_href("local-comercial-en-venta-la-plata", "2")) is PropertyType.other
    assert detect_property_type(_href("cochera-en-venta-en-la-plata", "3")) is PropertyType.other


def test_terreno_is_land():
    assert detect_property_type(_href("terreno-en-venta-en-gorina", "4")) is PropertyType.land


def test_unknown_slug_defaults_other_not_house():
    # Nunca "house" por defecto: evita re-colar no-casas.
    assert detect_property_type(_href("xyz-en-venta", "5")) is PropertyType.other


# --- detect_locality ------------------------------------------------------

def test_locality_gonnet_from_slug():
    loc, neigh = detect_locality(
        _href("casa-en-venta-en-la-plata-ideal-fines-comerciales-gonnet-verde-cochera")
    )
    assert loc == "Gonnet"
    assert neigh == "Gonnet"


def test_locality_tolosa_not_gonnet():
    loc, neigh = detect_locality(_href("casa-en-venta-en-tolosa-la-plata", "222"))
    assert loc == "Tolosa"


def test_locality_plain_la_plata_has_no_neighborhood():
    loc, neigh = detect_locality(_href("casa-en-venta-en-la-plata-centro", "333"))
    assert loc == "La Plata"
    assert neigh is None


# --- enforce tipo=casa (central) -----------------------------------------

def _row(**kw) -> models.Property:
    defaults = dict(
        portal="century21",
        external_id="x",
        source_url="https://century21.com.ar/propiedad/1_casa",
        title="Casa en venta Gonnet",
        operation="buy",
        property_type="house",
        address_locality="Gonnet",
        address_province="Buenos Aires",
        price_amount=140000.0,
        price_currency="USD",
        rooms=3,
    )
    defaults.update(kw)
    return models.Property(**defaults)


def _filters() -> SearchFilters:
    return SearchFilters(
        property_type=PropertyType.house,
        location=Location(query="Gonnet", locality="Gonnet", district="La Plata", province="Buenos Aires"),
        price=PriceFilters(max=150000, currency="USD"),
    )


def test_passes_type_drops_apartment():
    assert passes_type(_row(property_type="apartment"), _filters()) is False
    assert passes_type(_row(property_type="other"), _filters()) is False
    assert passes_type(_row(property_type="house"), _filters()) is True


def test_post_filters_drops_non_casa_and_wrong_locality():
    f = _filters()
    # depto en Gonnet → fuera (tipo)
    assert passes_post_filters(_row(property_type="apartment"), f) is False
    # casa en Tolosa → fuera (ubicación)
    tolosa = _row(address_locality="Tolosa", title="Casa en venta Tolosa")
    assert passes_post_filters(tolosa, f) is False
    # casa en Gonnet ≤150k → pasa
    assert passes_post_filters(_row(), f) is True
