"""Tests du sélecteur de méthode (hyper-heuristique, n°33)."""

import random
import time
from datetime import date, timedelta

from app.algorithms.csp_scheduler import SchedFreelancer, SchedTask
from app.algorithms.knapsack_md import Item, verify_selection
from app.algorithms.solver_selector import (
    choose_csp_method,
    choose_knapsack_method,
    choose_tsp_method,
    solve_knapsack,
    solve_schedule_auto,
    solve_tour,
)
from app.algorithms.tsp import held_karp, tour_length


def random_items(rng: random.Random, n: int) -> list[Item]:
    return [
        Item(id=i, value=rng.randint(1, 100), cost=rng.randint(1, 50) * 10_000, hours=rng.randint(1, 40),
             depends_on=tuple(j for j in range(i) if rng.random() < 0.05))
        for i in range(n)
    ]


def random_matrix(rng: random.Random, n: int) -> list[list[float]]:
    pts = [(rng.uniform(0, 500), rng.uniform(0, 500)) for _ in range(n)]
    return [[((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2) ** 0.5 for b in pts] for a in pts]


# --------------------------------------------------------------------------- règles de choix


def test_regle_sac_a_dos() -> None:
    small, big = choose_knapsack_method(40), choose_knapsack_method(41)
    assert small.exact and small.method == "Séparation et évaluation"
    assert not big.exact and big.method == "Glouton + échanges 1-1"
    assert "40" in small.reason and "41" in big.reason
    assert small.course_number == big.course_number == 29


def test_regle_voyageur_de_commerce() -> None:
    small, big = choose_tsp_method(12), choose_tsp_method(13)
    assert small.exact and small.method == "Held-Karp"
    assert not big.exact and big.method == "Plus proche voisin + 2-opt"
    assert "12" in small.reason and "13" in big.reason
    assert small.course_number == 30


def test_regle_csp() -> None:
    c = choose_csp_method(n_tasks=30, time_limit=3.0)
    assert c.method.startswith("Retour arrière") and "3 s" in c.reason and c.course_number == 3


def test_seuils_parametrables() -> None:
    assert not choose_knapsack_method(10, exact_threshold=5).exact
    assert choose_tsp_method(15, exact_threshold=15).exact


# --------------------------------------------------------------------------- exécution


def test_sac_a_dos_petit_exact_grand_approche() -> None:
    rng = random.Random(4)
    items = random_items(rng, 20)
    budget, hours = 2_000_000, 200
    sol, choice = solve_knapsack(items, budget, hours)
    assert choice.exact and sol.optimal

    big = random_items(rng, 120)
    t0 = time.perf_counter()
    sol, choice = solve_knapsack(big, 10_000_000, 1_000)
    assert time.perf_counter() - t0 < 3
    assert not choice.exact and not sol.optimal
    assert verify_selection(big, sol.selected, 10_000_000, 1_000) == []


def test_tournee_petite_exacte_grande_approchee() -> None:
    rng = random.Random(8)
    m = random_matrix(rng, 9)  # départ + 8 sites
    tour = solve_tour(m, closed=True)
    assert tour.choice.exact
    assert tour.length == held_karp(m, True)[1]

    m = random_matrix(rng, 40)
    tour = solve_tour(m, closed=False)
    assert not tour.choice.exact
    assert sorted(tour.order) == list(range(40)) and tour.order[0] == 0
    assert tour.length == tour_length(m, tour.order, closed=False)
    assert tour.length <= tour.nearest_neighbor_length  # 2-opt n'empire jamais


def test_csp_auto() -> None:
    lundi = date(2026, 11, 16)
    tasks = [SchedTask("A", "A", "React", 1, 8), SchedTask("B", "B", "React", 1, 8, ("A",))]
    team = [SchedFreelancer("Rivo", "Rivo", {"React": 3}, 8)]
    result, choice = solve_schedule_auto(tasks, team, lundi, lundi + timedelta(days=4))
    assert result.status == "OK"
    assert choice.method == result.method
    assert "optimal" in choice.reason.lower()
