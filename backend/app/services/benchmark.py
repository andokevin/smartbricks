"""Benchmark : méthodes exactes contre méthodes approchées, mesurées (valeur, écart, temps).

Deux sources d'instances :
1. le projet choisi (fonctionnalités, tâches + équipe, villes à visiter) ;
2. des instances ALÉATOIRES reproductibles (graine fixe), de tailles croissantes,
   pour justifier les seuils du sélecteur de méthode (n°33).

Écart (« gap ») d'une méthode approchée :
    sac à dos (maximisation)  : (optimum − valeur) / optimum
    tournée / planning (minimisation) : (valeur − optimum) / optimum
"""

from __future__ import annotations

import random
import statistics
import time
from datetime import date, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.algorithms import knapsack_md, tsp
from app.algorithms.csp_scheduler import SchedFreelancer, SchedTask, solve_schedule
from app.algorithms.geo import distance_matrix
from app.algorithms.solver_selector import CSP_TIME_LIMIT_S, KNAPSACK_EXACT_MAX, TSP_EXACT_MAX_SITES
from app.models import City, Project
from app.services.project_data import (
    load_features,
    load_freelancers,
    load_sites,
    load_task_dependencies,
    load_tasks,
    load_team_ids,
    skills_of,
    unavailable_dates,
)
from app.services.scoping import to_items

SEED = 2026


def _ms(t0: float) -> float:
    return round((time.perf_counter() - t0) * 1000, 3)


def _pct(x: float) -> float:
    return round(100 * x, 2)


# =========================================================================== sac à dos (n°29)


def _knapsack_run(items: list[knapsack_md.Item], budget: int, hours: int) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, solver in (
        ("exact", knapsack_md.branch_and_bound),
        ("greedy", knapsack_md.greedy),
        ("swaps", knapsack_md.greedy_with_swaps),
    ):
        t0 = time.perf_counter()
        s = solver(items, budget, hours)
        out[key] = {
            "method": s.method, "feasible": s.feasible, "value": s.total_value, "cost_mga": s.total_cost,
            "hours": s.total_hours, "time_ms": _ms(t0), "nodes": s.nodes, "optimal": s.optimal,
            "selected": len(s.selected),
        }
    best = out["exact"]["value"]
    for key in ("greedy", "swaps"):
        out[key]["gap_pct"] = _pct((best - out[key]["value"]) / best) if best else 0.0
    return out


def _random_items(rng: random.Random, n: int) -> tuple[list[knapsack_md.Item], int, int]:
    items = [
        knapsack_md.Item(
            id=i, value=rng.randint(1, 100), cost=rng.randint(1, 50) * 10_000, hours=rng.randint(1, 40),
            mandatory=rng.random() < 0.05, depends_on=tuple(j for j in range(i) if rng.random() < 0.05),
        )
        for i in range(n)
    ]
    return items, int(sum(i.cost for i in items) * 0.4), int(sum(i.hours for i in items) * 0.4)


def knapsack_benchmark(project_items: list[knapsack_md.Item] | None, budget: int, hours: int) -> dict[str, Any]:
    rng = random.Random(SEED)
    series = []
    for n in (10, 20, 30, 40):
        runs = []
        for _ in range(10):
            items, b, h = _random_items(rng, n)
            r = _knapsack_run(items, b, h)
            if r["exact"]["feasible"]:
                runs.append(r)
        series.append({
            "n": n,
            "instances": len(runs),
            "exact_ms_avg": round(statistics.mean(r["exact"]["time_ms"] for r in runs), 3),
            "exact_ms_max": max(r["exact"]["time_ms"] for r in runs),
            "nodes_max": max(r["exact"]["nodes"] for r in runs),
            "greedy_ms_avg": round(statistics.mean(r["greedy"]["time_ms"] for r in runs), 3),
            "swaps_ms_avg": round(statistics.mean(r["swaps"]["time_ms"] for r in runs), 3),
            "greedy_gap_avg_pct": round(statistics.mean(r["greedy"]["gap_pct"] for r in runs), 2),
            "greedy_gap_max_pct": max(r["greedy"]["gap_pct"] for r in runs),
            "swaps_gap_avg_pct": round(statistics.mean(r["swaps"]["gap_pct"] for r in runs), 2),
            "swaps_gap_max_pct": max(r["swaps"]["gap_pct"] for r in runs),
            "greedy_optimal_count": sum(1 for r in runs if r["greedy"]["gap_pct"] == 0),
        })
    return {
        "course_number": 29,
        "exact_method": "Séparation et évaluation",
        "approx_methods": ["Glouton par densité", "Glouton + échanges 1-1"],
        "threshold": f"exact jusqu'à {KNAPSACK_EXACT_MAX} fonctionnalités",
        "project": _knapsack_run(project_items, budget, hours) if project_items else None,
        "random": series,
    }


# =========================================================================== planning CSP (n°3)

_LUNDI = date(2026, 11, 16)


def _random_csp(rng: random.Random, n: int) -> tuple[list[SchedTask], list[SchedFreelancer], date]:
    skills = ["React", "Node.js", "UI/UX"]
    tasks = [
        SchedTask(id=f"T{k}", title=f"T{k}", skill=rng.choice(skills), min_level=rng.randint(1, 3),
                  hours=rng.randint(4, 24), depends_on=tuple(f"T{i}" for i in range(k) if rng.random() < 0.15))
        for k in range(n)
    ]
    team = [
        SchedFreelancer(id=f"F{k}", name=f"F{k}", skills={s: rng.randint(2, 5) for s in skills},
                        hours_per_day=rng.choice([4, 6, 8]), score=rng.random())
        for k in range(rng.randint(3, 4))
    ]
    return tasks, team, _LUNDI + timedelta(weeks=8)


def _csp_pair(tasks: list[SchedTask], team: list[SchedFreelancer], start: date, deadline: date,
              limit: float) -> dict[str, Any] | None:
    first = solve_schedule(tasks, team, start, deadline, optimize=False)
    best = solve_schedule(tasks, team, start, deadline, time_limit=limit)
    if first.status != "OK" or best.status != "OK":
        return None
    return {
        "lower_bound_days": best.lower_bound_days,
        "first": {"makespan_days": first.makespan_days, "time_ms": round(first.elapsed_ms, 3), "nodes": first.nodes},
        "optimized": {"makespan_days": best.makespan_days, "time_ms": round(best.elapsed_ms, 3), "nodes": best.nodes,
                      "optimal": best.optimal},
        "gap_pct": _pct((first.makespan_days - best.makespan_days) / best.makespan_days),  # type: ignore[operator]
    }


async def csp_benchmark(session: AsyncSession, project: Project | None) -> dict[str, Any]:
    instance = None
    note = None
    if project is not None:
        tasks = await load_tasks(session, project.id, sprint_only=True)
        team_ids = await load_team_ids(session, project.id)
        if tasks and team_ids:
            deps = await load_task_dependencies(session, [t.id for t in tasks])
            team = await load_freelancers(session, team_ids)
            st = [SchedTask(id=t.id, title=t.ref, skill=t.required_skill.name, min_level=t.min_level,
                            hours=t.estimated_hours, depends_on=tuple(deps[t.id])) for t in tasks]
            sf = [SchedFreelancer(id=p.id, name=p.user.name, skills=skills_of(p), hours_per_day=p.hours_per_day,
                                  unavailable=unavailable_dates(p)) for p in team]
            instance = _csp_pair(st, sf, project.start_date, project.target_deadline, CSP_TIME_LIMIT_S)
            if instance:
                instance.update({"tasks": len(st), "team": len(sf)})
        else:
            note = "Le projet n'a pas encore de périmètre et d'équipe : seules les instances aléatoires sont mesurées."
    rng = random.Random(SEED)
    series = []
    for n in (8, 12, 16):
        runs: list[dict[str, Any]] = []
        for _ in range(5):
            tasks, team, deadline = _random_csp(rng, n)
            r = _csp_pair(tasks, team, _LUNDI, deadline, 0.5)
            if r:
                runs.append(r)
        if runs:
            series.append({
                "n": n,
                "instances": len(runs),
                "first_ms_avg": round(statistics.mean(r["first"]["time_ms"] for r in runs), 3),
                "optimized_ms_avg": round(statistics.mean(r["optimized"]["time_ms"] for r in runs), 3),
                "gap_avg_pct": round(statistics.mean(r["gap_pct"] for r in runs), 2),
                "gap_max_pct": max(r["gap_pct"] for r in runs),
                "optimal_count": sum(1 for r in runs if r["optimized"]["optimal"]),
            })
    return {
        "course_number": 3,
        "exact_method": f"Retour arrière + propagation, optimisation de la durée ({CSP_TIME_LIMIT_S:g} s max)",
        "approx_methods": ["Première solution trouvée (MRV, fin la plus tôt)"],
        "threshold": f"limite de {CSP_TIME_LIMIT_S:g} s ; aléatoires limitées à 0,5 s",
        "project": instance,
        "note": note,
        "random": series,
    }


# =========================================================================== tournée (n°30)


def _tsp_run(matrix: list[list[float]], closed: bool = True) -> dict[str, Any]:
    t0 = time.perf_counter()
    order, exact = tsp.held_karp(matrix, closed)
    hk_ms = _ms(t0)
    t0 = time.perf_counter()
    nn = tsp.nearest_neighbor(matrix)
    nn_ms = _ms(t0)
    nn_len = tsp.tour_length(matrix, nn, closed)
    t0 = time.perf_counter()
    opt = tsp.two_opt(matrix, nn, closed)
    two_ms = _ms(t0) + nn_ms
    two_len = tsp.tour_length(matrix, opt, closed)
    return {
        "held_karp": {"km": round(exact, 1), "time_ms": hk_ms, "order": order},
        "nearest_neighbor": {"km": round(nn_len, 1), "time_ms": nn_ms, "gap_pct": _pct((nn_len - exact) / exact) if exact else 0.0},
        "two_opt": {"km": round(two_len, 1), "time_ms": round(two_ms, 3), "gap_pct": _pct((two_len - exact) / exact) if exact else 0.0},
    }


def _random_matrix(rng: random.Random, n: int) -> list[list[float]]:
    pts = [(rng.uniform(-25, -12), rng.uniform(43.5, 50.5)) for _ in range(n)]
    return distance_matrix(pts)


async def tsp_benchmark(session: AsyncSession, project: Project | None) -> dict[str, Any]:
    cities = (await session.scalars(select(City).order_by(City.id))).all()
    all_matrix = distance_matrix([(c.latitude, c.longitude) for c in cities])
    national = _tsp_run(all_matrix)
    national["cities"] = [cities[i].name for i in national["held_karp"]["order"]]  # type: ignore[index]

    project_run = None
    if project is not None:
        sites = [s.city for s in await load_sites(session, project.id)]
        if len(sites) >= 3:
            run = _tsp_run(distance_matrix([(c.latitude, c.longitude) for c in sites]))
            run["cities"] = [sites[i].name for i in run["held_karp"]["order"]]  # type: ignore[index]
            project_run = run

    rng = random.Random(SEED)
    series = []
    for n in (6, 8, 10, 12, 13):
        runs = [_tsp_run(_random_matrix(rng, n + 1)) for _ in range(5 if n < 13 else 2)]  # n sites + départ
        series.append({
            "sites": n,
            "instances": len(runs),
            "held_karp_ms_avg": round(statistics.mean(r["held_karp"]["time_ms"] for r in runs), 3),
            "two_opt_ms_avg": round(statistics.mean(r["two_opt"]["time_ms"] for r in runs), 3),
            "nn_gap_avg_pct": round(statistics.mean(r["nearest_neighbor"]["gap_pct"] for r in runs), 2),
            "two_opt_gap_avg_pct": round(statistics.mean(r["two_opt"]["gap_pct"] for r in runs), 2),
            "two_opt_gap_max_pct": max(r["two_opt"]["gap_pct"] for r in runs),
        })
    for r in (national, project_run):
        if r:
            r["held_karp"].pop("order", None)
    return {
        "course_number": 30,
        "exact_method": "Held-Karp",
        "approx_methods": ["Plus proche voisin", "Plus proche voisin + 2-opt"],
        "threshold": f"exact jusqu'à {TSP_EXACT_MAX_SITES} sites",
        "project": project_run,
        "national": national,
        "random": series,
    }


# =========================================================================== ensemble


async def run_benchmark(session: AsyncSession, project: Project | None) -> dict[str, Any]:
    t0 = time.perf_counter()
    items = None
    budget = hours = 0
    if project is not None:
        features = await load_features(session, project.id)
        if features:
            items, budget, hours = to_items(features), project.budget_mga, project.budget_hours
    knap = knapsack_benchmark(items, budget, hours)
    csp = await csp_benchmark(session, project)
    tour = await tsp_benchmark(session, project)
    return {
        "seed": SEED,
        "project": {"id": project.id, "title": project.title} if project else None,
        "knapsack": knap,
        "csp": csp,
        "tsp": tour,
        "selector": {
            "course_number": 33,
            "rules": [
                {"problem": "Sac à dos", "exact": "Séparation et évaluation", "approx": "Glouton + échanges 1-1",
                 "threshold": f"≤ {KNAPSACK_EXACT_MAX} fonctionnalités"},
                {"problem": "Planning (CSP)", "exact": "Retour arrière + propagation",
                 "approx": "Meilleure solution trouvée ; Min-Conflict n°11 après un retard",
                 "threshold": f"limite de {CSP_TIME_LIMIT_S:g} s"},
                {"problem": "Tournée", "exact": "Held-Karp", "approx": "Plus proche voisin + 2-opt",
                 "threshold": f"≤ {TSP_EXACT_MAX_SITES} sites"},
            ],
        },
        "total_ms": _ms(t0),
    }
