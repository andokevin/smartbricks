"""Tests du voyageur de commerce (n°30)."""

import random

import pytest

from app.algorithms.tsp import (
    brute_force,
    held_karp,
    nearest_neighbor,
    tour_length,
    two_opt,
)


def random_matrix(rng: random.Random, n: int) -> list[list[float]]:
    """Points aléatoires dans le plan : distances euclidiennes (symétriques, inégalité triangulaire)."""
    pts = [(rng.uniform(0, 500), rng.uniform(0, 500)) for _ in range(n)]
    return [[((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2) ** 0.5 for b in pts] for a in pts]


def is_valid(order: list[int], n: int) -> bool:
    return order[0] == 0 and sorted(order) == list(range(n))


# Carré 0-1-2-3 de côté 1 : la tournée optimale fait le tour (4), pas les diagonales.
SQUARE = [
    [0, 1, 2**0.5, 1],
    [1, 0, 1, 2**0.5],
    [2**0.5, 1, 0, 1],
    [1, 2**0.5, 1, 0],
]


def test_longueur() -> None:
    assert tour_length(SQUARE, [0, 1, 2, 3], closed=True) == pytest.approx(4)
    assert tour_length(SQUARE, [0, 1, 2, 3], closed=False) == pytest.approx(3)
    assert tour_length(SQUARE, [0, 2, 1, 3], closed=True) == pytest.approx(2 + 2 * 2**0.5)


def test_carre_held_karp() -> None:
    order, length = held_karp(SQUARE, closed=True)
    assert length == pytest.approx(4)
    assert is_valid(order, 4)


@pytest.mark.parametrize("closed", [True, False])
def test_held_karp_egal_force_brute(closed: bool) -> None:
    rng = random.Random(30)
    for _ in range(60):
        n = rng.randint(1, 8)
        m = random_matrix(rng, n)
        hk_order, hk_len = held_karp(m, closed=closed)
        bf_order, bf_len = brute_force(m, closed=closed)
        assert hk_len == pytest.approx(bf_len)
        assert is_valid(hk_order, n)
        assert tour_length(m, hk_order, closed) == pytest.approx(hk_len)


@pytest.mark.parametrize("closed", [True, False])
def test_two_opt_encadre(closed: bool) -> None:
    """Held-Karp ≤ 2-opt ≤ plus proche voisin, sur des instances jusqu'à 11 villes."""
    rng = random.Random(7)
    for _ in range(60):
        n = rng.randint(2, 11)
        m = random_matrix(rng, n)
        nn = nearest_neighbor(m)
        improved = two_opt(m, nn, closed=closed)
        _, opt = held_karp(m, closed=closed)
        assert is_valid(nn, n) and is_valid(improved, n)
        nn_len = tour_length(m, nn, closed)
        opt_len = tour_length(m, improved, closed)
        assert opt - 1e-9 <= opt_len <= nn_len + 1e-9


def test_two_opt_defait_un_croisement() -> None:
    """Sur le carré, la tournée 0-2-1-3 se croise ; 2-opt la décroise."""
    improved = two_opt(SQUARE, [0, 2, 1, 3], closed=True)
    assert tour_length(SQUARE, improved, True) == pytest.approx(4)


def test_grande_instance_reste_valide() -> None:
    m = random_matrix(random.Random(1), 60)
    order = two_opt(m, nearest_neighbor(m), closed=True)
    assert is_valid(order, 60)


def test_cas_degeneres() -> None:
    assert held_karp([[0]], closed=True) == ([0], 0)
    assert nearest_neighbor([[0]]) == [0]
    assert two_opt([[0]], [0], closed=True) == [0]
