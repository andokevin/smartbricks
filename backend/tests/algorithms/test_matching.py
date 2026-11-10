"""Tests du matching : agrégation pondérée (n°22) et optimisation de Pareto (n°21)."""

import math
import random

import pytest

from app.algorithms.matching import (
    CRITERIA,
    PRESETS,
    Candidate,
    Criteria,
    TaskNeed,
    best_compromise,
    compute_criteria,
    dominates,
    evaluate,
    non_dominated_sort,
    normalize,
    normalize_weights,
    suggest_team,
    weighted_ranking,
)

TASKS = [
    TaskNeed(id="T1", skill="React", min_level=3, hours=40),
    TaskNeed(id="T2", skill="Node.js", min_level=3, hours=40),
    TaskNeed(id="T3", skill="React", min_level=5, hours=20),
]


def cand(id: str, rate: int, skills: dict[str, int], rating: float = 4.0, on_time: float = 0.8,
         hpd: int = 8, days: int = 20) -> Candidate:
    return Candidate(id=id, name=id, hourly_rate=rate, rating=rating, on_time_rate=on_time,
                     hours_per_day=hpd, skills=skills, available_days=days)


# --------------------------------------------------------------------------- critères


def test_calcul_des_criteres_a_la_main() -> None:
    """Rivo : React 4 et Node.js 3 → peut faire T1 et T2 (80 h), pas T3 (niveau 5)."""
    rivo = cand("Rivo", 30_000, {"React": 4, "Node.js": 3}, rating=4.0, on_time=0.9, hpd=8, days=15)
    c = compute_criteria(rivo, TASKS, total_days=20)
    assert c.cost == 30_000 * 80
    # 80 h / (8 h/j × 15/20 des jours disponibles) = 80 / 6 = 13,33 jours
    assert c.speed == pytest.approx(80 / (8 * 15 / 20))
    assert c.quality == pytest.approx(4.0 * (0.5 + 0.5 * 0.9))
    assert c.availability == 15
    assert c.coverage == pytest.approx(80 / 100)


def test_candidat_sans_tache_faisable_exclu() -> None:
    debutant = cand("Débutant", 10_000, {"React": 1})
    assert evaluate([debutant], TASKS, total_days=20) == {}


def test_aucune_disponibilite_vitesse_infinie() -> None:
    absent = cand("Absent", 20_000, {"React": 3}, days=0)
    assert math.isinf(compute_criteria(absent, TASKS, total_days=20).speed)


# --------------------------------------------------------------------------- normalisation et poids


def test_normalisation_min_max_et_inversion() -> None:
    crit = {
        "A": Criteria(cost=100, speed=10, quality=2, availability=5, coverage=0.2),
        "B": Criteria(cost=300, speed=30, quality=4, availability=15, coverage=0.6),
        "C": Criteria(cost=200, speed=20, quality=3, availability=10, coverage=0.4),
    }
    n = normalize(crit)
    assert n["A"]["cost"] == 1.0 and n["B"]["cost"] == 0.0  # moins cher = meilleur
    assert n["C"]["cost"] == pytest.approx(0.5)
    assert n["B"]["quality"] == 1.0 and n["A"]["quality"] == 0.0  # à maximiser
    for scores in n.values():
        assert all(0.0 <= v <= 1.0 for v in scores.values())


def test_critere_constant_vaut_1() -> None:
    crit = {k: Criteria(cost=100, speed=1, quality=3, availability=10, coverage=0.5) for k in "AB"}
    assert all(v == 1.0 for scores in normalize(crit).values() for v in scores.values())


def test_poids_normalises() -> None:
    w = normalize_weights({"cost": 2, "speed": 2, "quality": 0, "availability": 0, "coverage": 0})
    assert w["cost"] == 0.5 and w["speed"] == 0.5 and sum(w.values()) == pytest.approx(1)
    assert normalize_weights({}) == {k: 0.2 for k in CRITERIA}  # tout à zéro → équilibré
    for preset in PRESETS.values():
        assert sum(preset.values()) == pytest.approx(1)


def test_poids_100_pourcent_cout_classe_par_cout_croissant() -> None:
    rng = random.Random(1)
    crit = {f"F{i}": _random_criteria(rng) for i in range(30)}
    ranking = weighted_ranking(crit, {"cost": 1})
    costs = [crit[r.id].cost for r in ranking]
    assert costs == sorted(costs)


def test_contributions_somment_au_score() -> None:
    rng = random.Random(3)
    crit = {f"F{i}": _random_criteria(rng) for i in range(10)}
    for r in weighted_ranking(crit, PRESETS["Équilibré"]):
        assert sum(r.contributions.values()) == pytest.approx(r.score)


# --------------------------------------------------------------------------- Pareto


def _random_criteria(rng: random.Random) -> Criteria:
    return Criteria(
        cost=rng.randint(1, 50) * 10_000,
        speed=rng.uniform(1, 30),
        quality=rng.uniform(1, 5),
        availability=rng.randint(0, 40),
        coverage=rng.uniform(0, 1),
    )


def test_dominance() -> None:
    a = Criteria(cost=100, speed=5, quality=4, availability=10, coverage=0.5)
    b = Criteria(cost=200, speed=5, quality=4, availability=10, coverage=0.5)
    assert dominates(a, b, ("cost", "speed", "quality"))
    assert not dominates(b, a, ("cost", "speed", "quality"))
    assert not dominates(a, a, ("cost", "speed", "quality"))  # strictement meilleur sur au moins un


@pytest.mark.parametrize("keys", [("cost", "speed", "quality"), ("cost", "coverage"), CRITERIA])
def test_proprietes_des_fronts(keys: tuple[str, ...]) -> None:
    rng = random.Random(42)
    for _ in range(50):
        crit = {f"F{i}": _random_criteria(rng) for i in range(rng.randint(1, 25))}
        fronts = non_dominated_sort(crit, keys)

        # Les fronts forment une partition des candidats.
        flat = [i for f in fronts for i in f]
        assert sorted(flat) == sorted(crit)

        # Aucun point du premier front n'est dominé, par personne.
        for i in fronts[0]:
            assert not any(dominates(crit[j], crit[i], keys) for j in crit)

        # Chaque point du front k est dominé par au moins un point du front k−1.
        for k in range(1, len(fronts)):
            for i in fronts[k]:
                assert any(dominates(crit[j], crit[i], keys) for j in fronts[k - 1])


def test_meilleur_compromis_exemple() -> None:
    """A très bon marché mais lent, B très rapide mais cher, C bon partout : C est le compromis."""
    crit = {
        "A": Criteria(cost=100, speed=30, quality=3, availability=10, coverage=0.5),
        "B": Criteria(cost=500, speed=5, quality=3, availability=10, coverage=0.5),
        "C": Criteria(cost=200, speed=10, quality=3, availability=10, coverage=0.5),
    }
    keys = ("cost", "speed")
    fronts = non_dominated_sort(crit, keys)
    assert sorted(fronts[0]) == ["A", "B", "C"]
    assert best_compromise(crit, fronts[0], keys) == "C"


# --------------------------------------------------------------------------- équipe suggérée


def test_equipe_suggeree_couvre_les_competences() -> None:
    candidates = [
        cand("ReactExpert", 50_000, {"React": 5}),
        cand("NodeDev", 30_000, {"Node.js": 4}),
        cand("ReactMoyen", 20_000, {"React": 3}),
    ]
    crit = evaluate(candidates, TASKS, total_days=20)
    ranking = weighted_ranking(crit, PRESETS["Équilibré"])
    team = suggest_team(candidates, TASKS, ranking)
    assert "ReactExpert" in team.members and "NodeDev" in team.members  # T3 exige React 5
    assert team.uncovered_tasks == []
    assert team.absorbable


def test_equipe_signale_competence_introuvable() -> None:
    candidates = [cand("NodeDev", 30_000, {"Node.js": 4})]
    team = suggest_team(candidates, TASKS, weighted_ranking(evaluate(candidates, TASKS, 20), {}))
    assert set(team.uncovered_tasks) == {"T1", "T3"}
    assert any("React" in w for w in team.warnings)


def test_equipe_ajoute_un_renfort_si_charge_trop_forte() -> None:
    """120 h de React à faire, chaque développeur n'a que 10 j × 8 h = 80 h : il en faut deux."""
    tasks = [TaskNeed(id=f"R{i}", skill="React", min_level=2, hours=40) for i in range(3)]
    candidates = [cand("R1", 20_000, {"React": 3}, days=10), cand("R2", 25_000, {"React": 3}, days=10)]
    ranking = weighted_ranking(evaluate(candidates, tasks, total_days=10), {"cost": 1})
    team = suggest_team(candidates, tasks, ranking)
    assert team.members == ["R1", "R2"]
    assert team.absorbable
