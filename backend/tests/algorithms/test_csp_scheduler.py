"""Tests de la planification par satisfaction de contraintes (n°3) et de verify_schedule."""

import random
from datetime import date, timedelta

from app.algorithms.calendar import is_working_day
from app.algorithms.csp_scheduler import (
    Assignment,
    SchedFreelancer,
    SchedTask,
    solve_schedule,
    verify_schedule,
)

LUNDI = date(2026, 11, 16)


def fl(id: str, skills: dict[str, int], hpd: int = 8, off: set[date] | None = None, score: float = 0.5) -> SchedFreelancer:
    return SchedFreelancer(id=id, name=id, skills=skills, hours_per_day=hpd,
                           unavailable=frozenset(off or set()), score=score)


def task(id: str, hours: int, skill: str = "React", deps: tuple[str, ...] = (), level: int = 1) -> SchedTask:
    return SchedTask(id=id, title=id, skill=skill, min_level=level, hours=hours, depends_on=deps)


def check_ok(tasks, team, start, deadline, result) -> None:  # type: ignore[no-untyped-def]
    assert result.status == "OK", result.diagnostics
    report = verify_schedule(tasks, team, start, deadline, result.assignments)
    assert report["constraints_passed"], report


# --------------------------------------------------------------------------- cas simples


def test_chaine_sequentielle() -> None:
    """A → B → C, 8 h chacune, un freelance à 8 h/j : lundi, mardi, mercredi."""
    tasks = [task("A", 8), task("B", 8, deps=("A",)), task("C", 8, deps=("B",))]
    team = [fl("Rivo", {"React": 3})]
    r = solve_schedule(tasks, team, LUNDI, LUNDI + timedelta(days=11))
    check_ok(tasks, team, LUNDI, LUNDI + timedelta(days=11), r)
    assert [r.assignments[t].start for t in "ABC"] == [LUNDI + timedelta(days=i) for i in range(3)]
    assert r.makespan_days == 3
    assert r.optimal  # égal à la borne du chemin critique


def test_taches_paralleles_reparties() -> None:
    """Deux tâches indépendantes de 16 h, deux freelances : 2 jours au lieu de 4."""
    tasks = [task("A", 16), task("B", 16)]
    team = [fl("Rivo", {"React": 3}), fl("Fara", {"React": 3})]
    r = solve_schedule(tasks, team, LUNDI, LUNDI + timedelta(days=11))
    check_ok(tasks, team, LUNDI, LUNDI + timedelta(days=11), r)
    assert r.makespan_days == 2
    assert r.assignments["A"].freelancer_id != r.assignments["B"].freelancer_id


def test_duree_depend_des_heures_par_jour() -> None:
    """10 h à 4 h/j = ceil(2,5) = 3 jours."""
    tasks = [task("A", 10)]
    team = [fl("Mi-temps", {"React": 3}, hpd=4)]
    r = solve_schedule(tasks, team, LUNDI, LUNDI + timedelta(days=11))
    assert r.assignments["A"].days == 3
    assert r.assignments["A"].end == LUNDI + timedelta(days=2)


def test_indisponibilites_respectees() -> None:
    """Rivo est absent lundi et mardi : sa tâche de 2 jours va de mercredi à jeudi."""
    off = {LUNDI, LUNDI + timedelta(days=1)}
    tasks = [task("A", 16)]
    team = [fl("Rivo", {"React": 3}, off=off)]
    r = solve_schedule(tasks, team, LUNDI, LUNDI + timedelta(days=11))
    check_ok(tasks, team, LUNDI, LUNDI + timedelta(days=11), r)
    assert r.assignments["A"].start == LUNDI + timedelta(days=2)


def test_competence_et_niveau() -> None:
    tasks = [task("A", 8, skill="Flutter", level=3)]
    team = [fl("Junior", {"Flutter": 2}), fl("Senior", {"Flutter": 4})]
    r = solve_schedule(tasks, team, LUNDI, LUNDI + timedelta(days=4))
    assert r.assignments["A"].freelancer_id == "Senior"


# --------------------------------------------------------------------------- diagnostics


def test_chemin_critique_trop_long() -> None:
    """API → Tests → Déploiement = 3 jours ; la date limite n'en laisse que 2."""
    tasks = [task("API", 8), task("Tests", 8, deps=("API",)), task("Déploiement", 8, deps=("Tests",))]
    team = [fl("Rivo", {"React": 3})]
    r = solve_schedule(tasks, team, LUNDI, LUNDI + timedelta(days=1))
    assert r.status == "INFEASIBLE"
    msg = " ".join(r.diagnostics)
    assert "chemin critique (API → Tests → Déploiement)" in msg
    assert "3 jours ouvrés" in msg and "en laisse 2" in msg and "1 jour ouvré" in msg
    assert r.critical_path == ["API", "Tests", "Déploiement"]


def test_competence_absente() -> None:
    tasks = [task("App", 8, skill="Flutter", level=3)]
    team = [fl("Rivo", {"React": 5})]
    r = solve_schedule(tasks, team, LUNDI, LUNDI + timedelta(days=11))
    assert r.status == "INFEASIBLE"
    assert "Aucun freelance de l'équipe n'a la compétence Flutter au niveau 3" in " ".join(r.diagnostics)


def test_surcharge_d_un_freelance() -> None:
    """140 h pour Rivo seul, 12 jours ouvrés × 8 h = 96 h disponibles."""
    tasks = [task(f"T{i}", 20) for i in range(7)]
    team = [fl("Rivo", {"React": 3})]
    deadline = LUNDI + timedelta(days=15)  # 12 jours ouvrés
    r = solve_schedule(tasks, team, LUNDI, deadline)
    assert r.status == "INFEASIBLE"
    assert "Charge de Rivo : 140 h pour 96 h disponibles" in " ".join(r.diagnostics)


def test_surcharge_en_jours_malgre_des_heures_suffisantes() -> None:
    """6 tâches de 13 h à 6 h/j : 78 h ≤ 90 h disponibles, MAIS ceil(13/6) = 3 jours chacune,
    soit 18 jours pour 15 disponibles : impossible, et le diagnostic doit le dire en jours."""
    tasks = [task(f"T{i}", 13) for i in range(6)]
    team = [fl("Hasina", {"React": 4}, hpd=6), fl("Fara", {"UI/UX": 5})]
    deadline = LUNDI + timedelta(days=18)  # vendredi de la 3e semaine : 15 jours ouvrés
    r = solve_schedule(tasks, team, LUNDI, deadline)
    assert r.status == "INFEASIBLE" and r.nodes == 0  # détecté avant toute recherche
    msg = " ".join(r.diagnostics)
    assert "Charge de Hasina" in msg and "18 jours ouvrés" in msg and "15 jours ouvrés" in msg
    assert "78 h" in msg


# --------------------------------------------------------------------------- vérification indépendante


def test_verify_schedule_detecte_les_violations() -> None:
    tasks = [task("A", 16), task("B", 8, deps=("A",)), task("C", 8, skill="Flutter", level=3)]
    team = [fl("Rivo", {"React": 3}, off={LUNDI + timedelta(days=4)})]
    deadline = LUNDI + timedelta(days=3)
    mauvais = {
        "A": Assignment("A", "Rivo", LUNDI, LUNDI + timedelta(days=1), 2),
        # B commence avant la fin de A et chevauche A
        "B": Assignment("B", "Rivo", LUNDI + timedelta(days=1), LUNDI + timedelta(days=1), 1),
        # C : Rivo n'a pas Flutter, tombe sur son congé (vendredi) et dépasse la date limite
        "C": Assignment("C", "Rivo", LUNDI + timedelta(days=4), LUNDI + timedelta(days=4), 1),
    }
    report = verify_schedule(tasks, team, LUNDI, deadline, mauvais)
    assert not report["constraints_passed"]
    failed = {c["name"] for c in report["checks"] if not c["passed"]}
    assert failed == {"Dépendances", "Compétences", "Disponibilité", "Pas de chevauchement", "Date limite"}


def test_verify_schedule_tache_manquante() -> None:
    tasks = [task("A", 8)]
    team = [fl("Rivo", {"React": 3})]
    report = verify_schedule(tasks, team, LUNDI, LUNDI + timedelta(days=4), {})
    assert not report["constraints_passed"]


# --------------------------------------------------------------------------- instances aléatoires


def random_instance(rng: random.Random) -> tuple[list[SchedTask], list[SchedFreelancer], date]:
    skills = ["React", "Node.js", "UI/UX"]
    n = rng.randint(3, 12)
    tasks = []
    for k in range(n):
        deps = tuple(f"T{i}" for i in range(k) if rng.random() < 0.2)
        tasks.append(task(f"T{k}", rng.randint(2, 24), skill=rng.choice(skills), deps=deps,
                          level=rng.randint(1, 3)))
    team = []
    for k in range(rng.randint(2, 4)):
        off_start = LUNDI + timedelta(days=rng.randint(0, 20))
        off = {off_start + timedelta(days=i) for i in range(rng.randint(0, 3))}
        team.append(fl(f"F{k}", {s: rng.randint(2, 5) for s in skills}, hpd=rng.choice([4, 6, 8]), off=off,
                       score=rng.random()))
    return tasks, team, LUNDI + timedelta(days=rng.randint(10, 40))


def test_verify_valide_toutes_les_solutions_aleatoires() -> None:
    rng = random.Random(42)
    solved = 0
    for _ in range(60):
        tasks, team, deadline = random_instance(rng)
        r = solve_schedule(tasks, team, LUNDI, deadline, time_limit=0.3)
        if r.status == "OK":
            solved += 1
            report = verify_schedule(tasks, team, LUNDI, deadline, r.assignments)
            assert report["constraints_passed"], report
            assert all(is_working_day(a.start) and is_working_day(a.end) for a in r.assignments.values())
            assert r.makespan_days >= r.lower_bound_days
        else:
            assert r.diagnostics  # toute impossibilité est expliquée
    assert solved >= 30  # la plupart des instances ont une solution


def test_optimisation_ne_degrade_jamais() -> None:
    """La recherche de meilleure durée ne fait jamais pire que la première solution."""
    rng = random.Random(5)
    for _ in range(20):
        tasks, team, deadline = random_instance(rng)
        first = solve_schedule(tasks, team, LUNDI, deadline, optimize=False)
        best = solve_schedule(tasks, team, LUNDI, deadline, time_limit=0.3)
        if first.status == "OK":
            assert best.status == "OK"
            assert best.makespan_days <= first.makespan_days
