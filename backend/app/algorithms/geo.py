"""Distances, coûts et durées de trajet entre villes de Madagascar.

DISTANCE ROUTIÈRE (APPROXIMATION ASSUMÉE)
    On ne dispose pas d'une matrice des distances routières réelles. On calcule la distance
    « à vol d'oiseau » sur la sphère terrestre (formule de haversine), puis on la multiplie par
    un FACTEUR ROUTIER de 1,35 : les routes ne sont pas droites (relief des Hautes Terres, RN7,
    RN2…). Tana → Antsirabe : ≈ 120 km à vol d'oiseau × 1,35 ≈ 162 km, pour ≈ 170 km réels.
    C'est une approximation documentée ; une vraie matrice routière est une perspective.

FORMULE DE HAVERSINE
    a = sin²(Δφ/2) + cos φ1 · cos φ2 · sin²(Δλ/2)
    d = 2 R · atan2(√a, √(1 − a))         R = 6 371 km (rayon moyen de la Terre)
    φ = latitude, λ = longitude, en radians.
"""

import math
from collections.abc import Sequence

EARTH_RADIUS_KM = 6371.0
ROAD_FACTOR = 1.35  # facteur routier approximatif (voir ci-dessus)
DEFAULT_COST_PER_KM = 1_200  # Ar par km (carburant, véhicule, chauffeur…)
AVERAGE_SPEED_KMH = 40.0  # vitesse moyenne réaliste sur les routes nationales

Coord = tuple[float, float]  # (latitude, longitude) en degrés


def haversine_km(a: Coord, b: Coord) -> float:
    """Distance à vol d'oiseau en km entre deux points (latitude, longitude)."""
    lat1, lon1 = map(math.radians, a)
    lat2, lon2 = map(math.radians, b)
    dlat, dlon = lat2 - lat1, lon2 - lon1
    h = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return 2 * EARTH_RADIUS_KM * math.atan2(math.sqrt(h), math.sqrt(1 - h))


def road_distance_km(a: Coord, b: Coord) -> float:
    """Distance routière estimée = haversine × facteur routier."""
    return haversine_km(a, b) * ROAD_FACTOR


def distance_matrix(coords: Sequence[Coord]) -> list[list[float]]:
    """Matrice symétrique des distances routières estimées. O(n²)."""
    n = len(coords)
    m = [[0.0] * n for _ in range(n)]
    for i in range(n):
        for j in range(i + 1, n):
            m[i][j] = m[j][i] = road_distance_km(coords[i], coords[j])
    return m


def travel_cost_mga(km: float, cost_per_km: int = DEFAULT_COST_PER_KM) -> int:
    """Coût du trajet en Ariary (entier)."""
    return int(round(km * cost_per_km))


def travel_hours(km: float, speed_kmh: float = AVERAGE_SPEED_KMH) -> float:
    """Durée de trajet estimée en heures."""
    return km / speed_kmh
