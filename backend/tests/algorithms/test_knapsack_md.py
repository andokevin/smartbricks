"""Tests du sac à dos multidimensionnel (n°29).

Stratégie : la force brute (2^n combinaisons, n ≤ 12) sert de référence ;
la séparation et évaluation doit trouver EXACTEMENT la même valeur optimale.
"""

import random

import pytest

from app.algorithms.knapsack_md import (
    Item,
    branch_and_bound,
    brute_force,
    explain_exclusions,
    greedy,
    greedy_with_swaps,
    verify_selection,
    what_if,
)


def random_instance(rng: random.Random) -> tuple[list[Item], int, int]:
    """Instance aléatoire à 2 dimensions, avec obligations et dépendances sans cycle.

    Une fonctionnalité j ne peut dépendre que d'une fonctionnalité i < j : pas de cycle possible.
    """
    n = rng.randint(1, 12)
    items: list[Item] = []
    for j in range(n):
        deps = tuple(i for i in range(j) if rng.random() < 0.15)
        items.append(
            Item(
                id=j,
                value=rng.randint(1, 100),
                cost=rng.randint(1, 50) * 10_000,
                hours=rng.randint(1, 40),
                mandatory=rng.random() < 0.1,
                depends_on=deps,
            )
        )
    budget = int(sum(it.cost for it in items) * rng.uniform(0.2, 0.9))
    hours = int(sum(it.hours for it in items) * rng.uniform(0.2, 0.9))
    return items, budget, hours


# --------------------------------------------------------------------------- optimalité


def test_egal_a_la_force_brute_sur_200_instances() -> None:
    rng = random.Random(2026)
    for _ in range(200):
        items, budget, hours = random_instance(rng)
        exact = branch_and_bound(items, budget, hours)
        ref = brute_force(items, budget, hours)

        assert exact.feasible == ref.feasible
        if ref.feasible:
            assert exact.total_value == ref.total_value
            assert exact.optimal
            # Jamais de dépassement, obligations et dépendances respectées.
            assert verify_selection(items, exact.selected, budget, hours) == []


def test_heuristiques_toujours_admissibles_et_jamais_meilleures() -> None:
    rng = random.Random(7)
    for _ in range(200):
        items, budget, hours = random_instance(rng)
        exact = branch_and_bound(items, budget, hours)
        if not exact.feasible:
            continue
        g = greedy(items, budget, hours)
        s = greedy_with_swaps(items, budget, hours)
        assert verify_selection(items, g.selected, budget, hours) == []
        assert verify_selection(items, s.selected, budget, hours) == []
        assert g.total_value <= s.total_value <= exact.total_value


# --------------------------------------------------------------------------- petits cas à la main


def test_exemple_a_la_main() -> None:
    """Budget 100 000 Ar, 10 h. A seul vaut 60 ; B + C valent 70 et tiennent : on prend B + C."""
    items = [
        Item(id="A", value=60, cost=100_000, hours=10),
        Item(id="B", value=40, cost=50_000, hours=5),
        Item(id="C", value=30, cost=50_000, hours=5),
    ]
    sol = branch_and_bound(items, budget=100_000, max_hours=10)
    assert sorted(sol.selected) == ["B", "C"]
    assert sol.total_value == 70


def test_les_deux_dimensions_comptent() -> None:
    """A tient dans le budget mais pas dans les heures : il est écarté."""
    items = [
        Item(id="A", value=90, cost=10_000, hours=50),
        Item(id="B", value=20, cost=10_000, hours=5),
    ]
    sol = branch_and_bound(items, budget=100_000, max_hours=10)
    assert sol.selected == ["B"]


def test_dependance_paiement_panier_catalogue() -> None:
    """Le paiement (très rentable) entraîne le panier et le catalogue avec lui."""
    items = [
        Item(id="catalogue", value=10, cost=30_000, hours=3),
        Item(id="panier", value=10, cost=30_000, hours=3, depends_on=("catalogue",)),
        Item(id="paiement", value=100, cost=30_000, hours=3, depends_on=("panier",)),
        Item(id="blog", value=50, cost=60_000, hours=6),
    ]
    sol = branch_and_bound(items, budget=90_000, max_hours=9)
    assert sorted(sol.selected) == ["catalogue", "paiement", "panier"]
    # Sans le catalogue, le paiement est impossible même s'il est rentable.
    assert verify_selection(items, ["paiement", "panier"], 90_000, 9) != []


def test_obligatoire_toujours_retenue() -> None:
    items = [
        Item(id="O", value=1, cost=80_000, hours=8, mandatory=True),
        Item(id="X", value=100, cost=90_000, hours=9),
    ]
    sol = branch_and_bound(items, budget=100_000, max_hours=10)
    assert sol.selected == ["O"]


def test_obligatoire_entraine_ses_dependances() -> None:
    items = [
        Item(id="base", value=1, cost=20_000, hours=2),
        Item(id="O", value=1, cost=20_000, hours=2, mandatory=True, depends_on=("base",)),
    ]
    sol = branch_and_bound(items, budget=100_000, max_hours=10)
    assert sorted(sol.selected) == ["O", "base"]


def test_cas_impossible_avec_montant_manquant() -> None:
    items = [
        Item(id="A", value=10, cost=400_000, hours=10, mandatory=True),
        Item(id="B", value=10, cost=300_000, hours=10, mandatory=True),
    ]
    sol = branch_and_bound(items, budget=600_000, max_hours=100)
    assert not sol.feasible
    assert sol.missing_cost == 100_000
    assert sol.missing_hours == 0
    assert "100 000 Ar" in sol.message


# --------------------------------------------------------------------------- explications


def test_raisons_d_exclusion() -> None:
    items = [
        Item(id="A", name="Catalogue", value=50, cost=50_000, hours=5),
        Item(id="B", name="Paiement", value=40, cost=60_000, hours=5, depends_on=("A",)),
        Item(id="C", name="Blog", value=5, cost=10_000, hours=1),
    ]
    sol = branch_and_bound(items, budget=60_000, max_hours=10)
    reasons = explain_exclusions(items, sol, budget=60_000, max_hours=10)
    assert set(reasons) == {"B"}  # A et C sont retenus
    assert "budget" in reasons["B"]


def test_et_si_plus_de_budget() -> None:
    items = [
        Item(id="A", name="Catalogue", value=50, cost=100_000, hours=5),
        Item(id="B", name="Paiement MVola", value=40, cost=10_000, hours=5),
    ]
    scenarios = what_if(items, budget=100_000, max_hours=100, increases=(0.10, 0.25))
    assert [s.increase for s in scenarios] == [0.10, 0.25]
    assert scenarios[0].extra_budget == 10_000
    assert scenarios[0].added == ["B"]
    assert "Paiement MVola" in scenarios[0].message


@pytest.mark.parametrize("solver", [branch_and_bound, greedy, greedy_with_swaps, brute_force])
def test_liste_vide(solver) -> None:  # type: ignore[no-untyped-def]
    sol = solver([], 100, 10)
    assert sol.feasible and sol.selected == [] and sol.total_value == 0
