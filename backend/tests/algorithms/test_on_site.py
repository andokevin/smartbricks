"""Contrainte 6 (niveau B) : tâches sur site d'un même freelance dans l'ordre de la tournée,
avec un jour de trajet entre deux villes différentes. Vérifiée par le CSP, Min-Conflict et verify_schedule."""

from datetime import date, timedelta

from app.algorithms.csp_scheduler import Assignment, SchedFreelancer, SchedTask, sites_compatible, solve_schedule, verify_schedule
from app.algorithms.min_conflicts import lengthen, repair_schedule

LUNDI = date(2026, 11, 16)
ORDRE = ["Fianarantsoa", "Toamasina", "Antananarivo", "Antsirabe"]  # ordre de la tournée
RANK = {c: k for k, c in enumerate(ORDRE)}


def jour(n: int) -> date:
    semaines, reste = divmod(n, 5)
    return LUNDI + timedelta(weeks=semaines, days=reste)


def site(id: str, city: str, hours: int = 8) -> SchedTask:
    return SchedTask(id=id, title=id, skill="Réseau", min_level=1, hours=hours, site=city)


TECH = [SchedFreelancer(id="Solo", name="Solo", skills={"Réseau": 4}, hours_per_day=8)]


def check(tasks, team, deadline, assignments) -> dict:  # type: ignore[no-untyped-def]
    return verify_schedule(tasks, team, LUNDI, deadline, assignments, site_order=ORDRE)


# --------------------------------------------------------------------------- la règle elle-même


def test_regle_ordre_et_trajet() -> None:
    # Fianarantsoa (rang 0) jours 0-0, puis Toamasina (rang 1) : il faut un jour de trajet → début ≥ 2.
    assert sites_compatible("Fianarantsoa", 0, 0, "Toamasina", 2, 2, RANK)
    assert not sites_compatible("Fianarantsoa", 0, 0, "Toamasina", 1, 1, RANK)  # pas de jour de trajet
    assert not sites_compatible("Toamasina", 0, 0, "Fianarantsoa", 2, 2, RANK)  # ordre inversé
    assert sites_compatible("Antsirabe", 0, 0, "Antsirabe", 1, 1, RANK)  # même ville : pas de trajet
    assert not sites_compatible("Antsirabe", 0, 1, "Antsirabe", 1, 1, RANK)  # mais pas de chevauchement


# --------------------------------------------------------------------------- CSP


def test_csp_suit_l_ordre_de_la_tournee() -> None:
    """Déclarées dans le désordre, les 4 agences sont visitées dans l'ordre de la tournée, un jour de trajet entre chaque."""
    tasks = [site("Tana", "Antananarivo"), site("Antsirabe", "Antsirabe"), site("Toamasina", "Toamasina"),
             site("Fianar", "Fianarantsoa")]
    deadline = jour(19)
    r = solve_schedule(tasks, TECH, LUNDI, deadline, site_order=ORDRE)
    assert r.status == "OK", r.diagnostics
    starts = {t: r.assignments[t].start for t in ("Fianar", "Toamasina", "Tana", "Antsirabe")}
    assert list(starts.values()) == [jour(0), jour(2), jour(4), jour(6)]
    report = check(tasks, TECH, deadline, r.assignments)
    assert report["constraints_passed"] and len(report["checks"]) == 8


def test_meme_ville_sans_jour_de_trajet() -> None:
    tasks = [site("A1", "Antsirabe"), site("A2", "Antsirabe")]
    r = solve_schedule(tasks, TECH, LUNDI, jour(9), site_order=ORDRE)
    assert r.makespan_days == 2


def test_freelances_differents_independants() -> None:
    team = TECH + [SchedFreelancer(id="Rado", name="Rado", skills={"Réseau": 4}, hours_per_day=8)]
    tasks = [site("Toamasina", "Toamasina"), site("Fianar", "Fianarantsoa")]
    r = solve_schedule(tasks, team, LUNDI, jour(9), site_order=ORDRE)
    assert r.makespan_days == 1  # deux techniciens en parallèle : aucune contrainte entre eux


def test_trajet_peut_rendre_impossible() -> None:
    """3 villes en 4 jours : 3 jours de travail + 2 jours de trajet = 5 > 4."""
    tasks = [site("F", "Fianarantsoa"), site("T", "Toamasina"), site("A", "Antananarivo")]
    r = solve_schedule(tasks, TECH, LUNDI, jour(3), site_order=ORDRE)
    assert r.status == "INFEASIBLE" and r.diagnostics


# --------------------------------------------------------------------------- vérification indépendante


def test_verify_detecte_ordre_et_trajet() -> None:
    tasks = [site("F", "Fianarantsoa"), site("T", "Toamasina")]
    deadline = jour(9)
    sans_trajet = {"F": Assignment("F", "Solo", jour(0), jour(0), 1), "T": Assignment("T", "Solo", jour(1), jour(1), 1)}
    inverse = {"F": Assignment("F", "Solo", jour(2), jour(2), 1), "T": Assignment("T", "Solo", jour(0), jour(0), 1)}
    for bad in (sans_trajet, inverse):
        report = check(tasks, TECH, deadline, bad)
        failed = {c["name"] for c in report["checks"] if not c["passed"]}
        assert failed == {"Sur site (ordre de la tournée)"}


def test_sans_tache_sur_site_le_controle_passe() -> None:
    tasks = [SchedTask(id="X", title="X", skill="Réseau", min_level=1, hours=8)]
    r = solve_schedule(tasks, TECH, LUNDI, jour(4))
    report = verify_schedule(tasks, TECH, LUNDI, jour(4), r.assignments)
    assert report["constraints_passed"] and any(c["name"].startswith("Sur site") for c in report["checks"])


# --------------------------------------------------------------------------- Min-Conflict


def test_min_conflict_garde_le_jour_de_trajet() -> None:
    """Fianarantsoa prend un jour de plus : Toamasina glisse en gardant son jour de trajet."""
    tasks = [site("F", "Fianarantsoa"), site("T", "Toamasina")]
    current = {"F": Assignment("F", "Solo", jour(0), jour(0), 1), "T": Assignment("T", "Solo", jour(2), jour(2), 1)}
    deadline = jour(9)
    r = repair_schedule(tasks, TECH, LUNDI, deadline, current, "F", 8, site_order=ORDRE)
    assert r.status == "OK"
    assert r.assignments["T"].start == jour(3)
    assert check(lengthen(tasks, "F", 8), TECH, deadline, r.assignments)["constraints_passed"]
