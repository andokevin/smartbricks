"""Tests de la détection et de la suppression des cycles de dépendances (tri topologique de Kahn)."""

import random

from app.algorithms.dependencies import break_cycles, find_cycle, topological_order


def test_ordre_topologique_sans_cycle() -> None:
    deps = {"T1": [], "T2": ["T1"], "T3": ["T1", "T2"]}
    order, remaining = topological_order(["T1", "T2", "T3"], deps)
    assert order == ["T1", "T2", "T3"] and remaining == []


def test_cycle_detecte() -> None:
    deps = {"A": ["C"], "B": ["A"], "C": ["B"], "D": []}
    order, remaining = topological_order(["A", "B", "C", "D"], deps)
    assert order == ["D"] and sorted(remaining) == ["A", "B", "C"]
    cycle = find_cycle(["A", "B", "C", "D"], deps)
    assert cycle is not None and sorted(cycle) == ["A", "B", "C"]


def test_arete_la_moins_justifiee_retiree() -> None:
    """T2 dépend de T1 (normal), mais T1 dépend de T3, déclarée APRÈS : c'est elle qu'on retire."""
    refs = ["T1", "T2", "T3"]
    deps = {"T1": ["T3"], "T2": ["T1"], "T3": ["T2"]}
    clean, removed = break_cycles(refs, deps)
    assert removed == [("T1", "T3")]
    assert clean == {"T1": [], "T2": ["T1"], "T3": ["T2"]}
    assert topological_order(refs, clean)[1] == []


def test_auto_dependance_retiree() -> None:
    clean, removed = break_cycles(["A"], {"A": ["A"]})
    assert removed == [("A", "A")] and clean == {"A": []}


def test_graphes_aleatoires_toujours_acycliques_apres_reparation() -> None:
    rng = random.Random(11)
    for _ in range(200):
        n = rng.randint(1, 15)
        refs = [f"N{i}" for i in range(n)]
        deps = {r: [s for s in refs if rng.random() < 0.15] for r in refs}
        clean, removed = break_cycles(refs, deps)
        assert topological_order(refs, clean)[1] == []  # plus aucun cycle
        # On n'a retiré que des arêtes existantes, et seulement des arêtes « vers l'arrière ».
        for u, v in removed:
            assert v in deps[u] and refs.index(v) >= refs.index(u)
        # Sans cycle au départ, rien n'est retiré.
        if topological_order(refs, deps)[1] == []:
            assert removed == []
