"""Locality centroids + seed POI/commerce/transit for ZoneReport."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SeedPlace:
    id: str
    name: str
    category: str
    lat: float
    lng: float
    distance_m: float
    bucket: str  # poi | commerce | transit


# Centroids for main localities (approx)
LOCALITY_CENTROIDS: dict[str, tuple[float, float]] = {
    "gonnet": (-34.8805, -58.0178),
    "manuel b. gonnet": (-34.8805, -58.0178),
    "city bell": (-34.8689, -58.0456),
    "la plata": (-34.9214, -57.9544),
    "pilar": (-34.4587, -58.9142),
    "vicente lópez": (-34.5075, -58.4819),
    "vicente lopez": (-34.5075, -58.4819),
    "san isidro": (-34.4728, -58.5287),
    "tigre": (-34.4259, -58.5796),
    "belgrano": (-34.5627, -58.4565),
    "olivos": (-34.5078, -58.4876),
}


# Seed places keyed by normalized locality
ZONE_SEEDS: dict[str, tuple[SeedPlace, ...]] = {
    "gonnet": (
        SeedPlace("gonnet-plaza", "Plaza Rocha", "plaza", -34.8812, -58.0190, 450, "poi"),
        SeedPlace("gonnet-escuela", "Escuela Primaria N°18", "escuela", -34.8798, -58.0160, 620, "poi"),
        SeedPlace("gonnet-super", "Supermercado Día", "supermercado", -34.8820, -58.0210, 780, "commerce"),
        SeedPlace("gonnet-farm", "Farmacia Gonnet", "farmacia", -34.8800, -58.0155, 510, "commerce"),
        SeedPlace("gonnet-tren", "Estación Gonnet (Roca)", "estacion", -34.8835, -58.0140, 1100, "transit"),
        SeedPlace("gonnet-132", "Acceso Av. 132", "autopista", -34.8760, -58.0250, 1500, "transit"),
    ),
    "city bell": (
        SeedPlace("cb-plaza", "Plaza Belgrano", "plaza", -34.8695, -58.0460, 400, "poi"),
        SeedPlace("cb-club", "Club City Bell", "club", -34.8670, -58.0440, 900, "poi"),
        SeedPlace("cb-super", "Carrefour City Bell", "supermercado", -34.8710, -58.0480, 700, "commerce"),
        SeedPlace("cb-cafe", "Café Comercial", "gastronomia", -34.8685, -58.0450, 350, "commerce"),
        SeedPlace("cb-tren", "Estación City Bell", "estacion", -34.8725, -58.0495, 1200, "transit"),
    ),
    "la plata": (
        SeedPlace("lp-plaza", "Plaza Moreno", "plaza", -34.9210, -57.9545, 300, "poi"),
        SeedPlace("lp-hosp", "Hospital San Martín", "hospital", -34.9180, -57.9500, 900, "poi"),
        SeedPlace("lp-super", "Coto Centro", "supermercado", -34.9225, -57.9560, 450, "commerce"),
        SeedPlace("lp-term", "Terminal La Plata", "terminal", -34.9150, -57.9480, 1600, "transit"),
        SeedPlace("lp-tren", "Estación La Plata", "estacion", -34.9080, -57.9490, 1800, "transit"),
    ),
    "pilar": (
        SeedPlace("pi-plaza", "Plaza Pilar", "plaza", -34.4590, -58.9140, 350, "poi"),
        SeedPlace("pi-esc", "Escuela N°1", "escuela", -34.4575, -58.9120, 600, "poi"),
        SeedPlace("pi-mall", "Paseo Pilar", "shopping", -34.4620, -58.9200, 1100, "commerce"),
        SeedPlace("pi-super", "Jumbo Pilar", "supermercado", -34.4550, -58.9080, 950, "commerce"),
        SeedPlace("pi-pan", "Acceso Norte / Panamericana", "autopista", -34.4500, -58.9000, 2200, "transit"),
    ),
}


DEFAULT_SEED: tuple[SeedPlace, ...] = (
    SeedPlace("gen-plaza", "Plaza barrio", "plaza", -34.6, -58.4, 500, "poi"),
    SeedPlace("gen-super", "Supermercado local", "supermercado", -34.601, -58.401, 700, "commerce"),
    SeedPlace("gen-bus", "Parada transporte", "parada", -34.599, -58.399, 400, "transit"),
)


def normalize_locality(value: str | None) -> str:
    if not value:
        return ""
    return value.strip().lower().replace("á", "a").replace("é", "e").replace("í", "i").replace(
        "ó", "o"
    ).replace("ú", "u")


def centroid_for(locality: str | None) -> tuple[float, float] | None:
    key = normalize_locality(locality)
    if not key:
        return None
    if key in LOCALITY_CENTROIDS:
        return LOCALITY_CENTROIDS[key]
    # aliases
    if "gonnet" in key:
        return LOCALITY_CENTROIDS["gonnet"]
    if "city bell" in key:
        return LOCALITY_CENTROIDS["city bell"]
    # "la plata" or admin labels like "partido de la plata" (iter-11 · P0-4)
    if "la plata" in key:
        return LOCALITY_CENTROIDS["la plata"]
    return LOCALITY_CENTROIDS.get(key)


def seeds_for(locality: str | None) -> tuple[SeedPlace, ...]:
    key = normalize_locality(locality)
    if "gonnet" in key:
        return ZONE_SEEDS["gonnet"]
    if "city bell" in key:
        return ZONE_SEEDS["city bell"]
    if "la plata" in key:
        return ZONE_SEEDS["la plata"]
    if key == "pilar":
        return ZONE_SEEDS["pilar"]
    return DEFAULT_SEED
