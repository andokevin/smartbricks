"""Tests des distances entre villes."""

import pytest

from app.algorithms.geo import (
    ROAD_FACTOR,
    distance_matrix,
    haversine_km,
    road_distance_km,
    travel_cost_mga,
    travel_hours,
)

TANA = (-18.8792, 47.5079)
ANTSIRABE = (-19.8659, 47.0333)


def test_un_degre_de_latitude_vaut_111_km() -> None:
    assert haversine_km((0.0, 0.0), (1.0, 0.0)) == pytest.approx(111.19, abs=0.05)


def test_distance_nulle_et_symetrique() -> None:
    assert haversine_km(TANA, TANA) == 0
    assert haversine_km(TANA, ANTSIRABE) == pytest.approx(haversine_km(ANTSIRABE, TANA))


def test_tana_antsirabe_ordre_de_grandeur() -> None:
    """Environ 120 km à vol d'oiseau ; la route réelle fait environ 170 km."""
    vol = haversine_km(TANA, ANTSIRABE)
    assert 115 < vol < 125
    assert road_distance_km(TANA, ANTSIRABE) == pytest.approx(vol * ROAD_FACTOR)


def test_matrice() -> None:
    m = distance_matrix([TANA, ANTSIRABE, TANA])
    assert m[0][0] == 0 and m[0][2] == 0
    assert m[0][1] == m[1][0] > 0


def test_cout_et_duree() -> None:
    assert travel_cost_mga(100) == 120_000  # 1 200 Ar/km par défaut
    assert travel_cost_mga(100, cost_per_km=1_000) == 100_000
    assert travel_hours(80) == pytest.approx(2.0)  # 40 km/h de moyenne
