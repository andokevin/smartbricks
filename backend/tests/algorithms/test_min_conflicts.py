"""Tests de la réparation de planning par Min-Conflict (n°11, niveau B).

Stratégie : on part d'un planning valide, on retarde une tâche, et l'on vérifie
1) que le planning réparé passe verify_schedule (avec la nouvelle durée),
2) qu'il change le moins de choses possible (tâches non concernées intactes, freelance conservé si possible),
3) qu'un retard impossible à absorber est signalé avec un diagnostic chiffré.
"""

import random
from datetime import date, timedelta

from app.algorithms.csp_scheduler import Assignment, SchedFreelancer, SchedTask, solve_schedule, verify_schedule
from app.algorithms.min_conflicts import lengthen, repair_schedule

LUNDI = date(2026, 11, 16)


def jour(n: int) -> date:
    """n-ième jour ouvré à partir du lundi 16 novembre (0 = lundi)."""
    semaines, reste = divmod(n, 5)
    return LUNDI + timedelta(weeks=semaines, days=reste)


def fl(id: str, skills: dict[str, int], hpd: int = 8, off: set[date] | None = None) -> SchedFreelancer:
    return SchedFreelancer(id=id, name=id, skills=skills, hours_per_day=hpd, unavailable=frozenset(off or set()))


def task(id: str, hours: int, skill: str = "React", deps: tuple[str, ...] = ()) -> SchedTask:
    return SchedTask(id=id, title=id, skill=skill, min_level=1, hours=hours, depends_on=deps)


def a(tid: str, fid: str, d0: int, d1: int) -> Assignment:
    return Assignment(tid, fid, jour(d0), jour(d1), d1 - d0 + 1)


def check_valid(tasks, team, deadline, result) -> None:  # type: ignore[no-untyped-def]
    assert result.status == "OK", result.diagnostics
    report = verify_schedule(tasks, team, LUNDI, deadline, result.assignments)
    assert report["constraints_passed"], report


# --------------------------------------------------------------------------- cas simples


def test_retard_sans_consequence() -> None:
    """A est seule : la retarder d'un jour ne déplace rien d'autre."""
    tasks = [task("A", 8), task("B", 8, skill="UI/UX")]
    team = [fl("Rivo", {"React": 3}), fl("Fara", {"UI/UX": 3})]
    current = {"A": a("A", "Rivo", 0, 0), "B": a("B", "Fara", 0, 0)}
    deadline = jour(9)
    r = repair_schedule(tasks, team, LUNDI, deadline, current, "A", 8)
    check_valid(lengthen(tasks, "A", 8), team, deadline, r)
    assert r.changed == [] and r.steps == 0
    assert r.assignments["A"].end == jour(1)  # 16 h à 8 h/j : lundi et mardi


def test_le_successeur_est_decale_d_un_jour() -> None:
    """A → B → C, un seul freelance. A prend 8 h de plus : B et C glissent d'un jour, rien d'autre."""
    tasks = [task("A", 8), task("B", 8, deps=("A",)), task("C", 8, deps=("B",))]
    team = [fl("Rivo", {"React": 3})]
    current = {"A": a("A", "Rivo", 0, 0), "B": a("B", "Rivo", 1, 1), "C": a("C", "Rivo", 2, 2)}
    deadline = jour(9)
    r = repair_schedule(tasks, team, LUNDI, deadline, current, "A", 8)
    check_valid(lengthen(tasks, "A", 8), team, deadline, r)
    assert r.assignments["B"].start == jour(2) and r.assignments["C"].start == jour(3)
    assert sorted(r.changed) == ["B", "C"]
    assert r.reassigned == []


def test_les_taches_non_concernees_ne_bougent_pas() -> None:
    tasks = [task("A", 8), task("B", 8, deps=("A",)), task("X", 16, skill="UI/UX")]
    team = [fl("Rivo", {"React": 3}), fl("Fara", {"UI/UX": 3})]
    current = {"A": a("A", "Rivo", 0, 0), "B": a("B", "Rivo", 1, 1), "X": a("X", "Fara", 3, 4)}
    deadline = jour(9)
    r = repair_schedule(tasks, team, LUNDI, deadline, current, "A", 8)
    check_valid(lengthen(tasks, "A", 8), team, deadline, r)
    assert r.assignments["X"] == current["X"]
    assert "X" not in r.changed


def test_prefere_garder_le_meme_freelance() -> None:
    """C pourrait passer chez Fara, mais il reste du temps chez Rivo : on garde Rivo."""
    tasks = [task("A", 8), task("C", 8)]
    team = [fl("Rivo", {"React": 3}), fl("Fara", {"React": 3})]
    current = {"A": a("A", "Rivo", 0, 0), "C": a("C", "Rivo", 1, 1)}
    deadline = jour(9)
    r = repair_schedule(tasks, team, LUNDI, deadline, current, "A", 8)
    check_valid(lengthen(tasks, "A", 8), team, deadline, r)
    assert r.assignments["C"].freelancer_id == "Rivo"
    assert r.reassigned == []


def test_change_de_freelance_si_la_date_limite_l_impose() -> None:
    """Date limite mardi : C ne peut plus rester chez Rivo (A l'occupe lundi et mardi) → Fara."""
    tasks = [task("A", 8), task("C", 8)]
    team = [fl("Rivo", {"React": 3}), fl("Fara", {"React": 3})]
    current = {"A": a("A", "Rivo", 0, 0), "C": a("C", "Rivo", 1, 1)}
    deadline = jour(1)
    r = repair_schedule(tasks, team, LUNDI, deadline, current, "A", 8)
    check_valid(lengthen(tasks, "A", 8), team, deadline, r)
    assert r.assignments["C"].freelancer_id == "Fara"
    assert r.reassigned == ["C"]


def test_retard_impossible_a_absorber() -> None:
    """A finit désormais après la date limite : aucune réparation ne peut l'éviter, diagnostic chiffré."""
    tasks = [task("A", 16)]
    team = [fl("Rivo", {"React": 3})]
    current = {"A": a("A", "Rivo", 0, 1)}
    deadline = jour(2)
    r = repair_schedule(tasks, team, LUNDI, deadline, current, "A", 16)
    assert r.status == "FAILED"
    msg = " ".join(r.diagnostics)
    assert "A" in msg and "1 jour ouvré" in msg


def test_successeurs_bloques_par_la_date_limite() -> None:
    """Le retard pousse B au-delà de la date limite : échec signalé, conflit restant compté."""
    tasks = [task("A", 8), task("B", 16, deps=("A",))]
    team = [fl("Rivo", {"React": 3})]
    current = {"A": a("A", "Rivo", 0, 0), "B": a("B", "Rivo", 1, 2)}
    deadline = jour(2)
    r = repair_schedule(tasks, team, LUNDI, deadline, current, "A", 8, max_steps=200)
    assert r.status == "FAILED"
    assert r.remaining_conflicts > 0 and r.diagnostics


def test_conge_respecte_pendant_la_reparation() -> None:
    """Rivo est absent le jeudi : B, décalé, saute ce jour-là."""
    tasks = [task("A", 8), task("B", 16, deps=("A",))]
    team = [fl("Rivo", {"React": 3}, off={jour(3)})]
    current = {"A": a("A", "Rivo", 0, 0), "B": a("B", "Rivo", 1, 2)}
    deadline = jour(9)
    r = repair_schedule(tasks, team, LUNDI, deadline, current, "A", 16)
    check_valid(lengthen(tasks, "A", 16), team, deadline, r)
    assert r.assignments["B"].start == jour(4) or r.assignments["B"].start == jour(2)


# --------------------------------------------------------------------------- instances aléatoires


def test_reparations_aleatoires_toujours_valides() -> None:
    """Plannings aléatoires résolus par le CSP, puis un retard aléatoire : toute réparation réussie est valide."""
    rng = random.Random(11)
    skills = ["React", "Node.js", "UI/UX"]
    repaired = 0
    for _ in range(40):
        n = rng.randint(4, 10)
        tasks = [SchedTask(id=f"T{k}", title=f"T{k}", skill=rng.choice(skills), min_level=1,
                           hours=rng.randint(4, 16), depends_on=tuple(f"T{i}" for i in range(k) if rng.random() < 0.2))
                 for k in range(n)]
        team = [fl(f"F{k}", {s: 3 for s in skills}, hpd=rng.choice([4, 6, 8])) for k in range(rng.randint(2, 3))]
        deadline = LUNDI + timedelta(days=rng.randint(20, 40))
        base = solve_schedule(tasks, team, LUNDI, deadline, optimize=False)
        if base.status != "OK":
            continue
        victim = rng.choice(tasks).id
        extra = rng.randint(4, 16)
        r = repair_schedule(tasks, team, LUNDI, deadline, base.assignments, victim, extra, seed=rng.randint(0, 99))
        if r.status == "OK":
            repaired += 1
            report = verify_schedule(lengthen(tasks, victim, extra), team, LUNDI, deadline, r.assignments)
            assert report["constraints_passed"], report
            # La tâche retardée garde son freelance et son début.
            assert r.assignments[victim].freelancer_id == base.assignments[victim].freelancer_id
            assert r.assignments[victim].start == base.assignments[victim].start
        else:
            assert r.diagnostics
    assert repaired >= 20
