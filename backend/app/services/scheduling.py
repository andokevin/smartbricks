"""Module D — planification par CSP (n°3) : lien entre la base, le solveur et verify_schedule.

Le « scénario impossible » (et toute autre date limite de test) n'est PAS enregistré dans les tâches :
il sert à montrer le diagnostic sans abîmer le planning réel.
"""

from datetime import date, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.algorithms.calendar import count_working_days
from app.algorithms.csp_scheduler import Assignment, SchedFreelancer, SchedTask, solve_schedule, verify_schedule
from app.algorithms.matching import PRESETS, evaluate, weighted_ranking
from app.algorithms.min_conflicts import lengthen, repair_schedule
from app.algorithms.solver_selector import solve_schedule_auto
from app.errors import AppError, conflict, not_found
from sqlalchemy.orm import selectinload

from app.models import FreelancerProfile, Project, ProjectStatus, Role, ScheduleRun, Task, TaskStatus, TourRun, User
from app.schemas import DelayIn, SolveIn, TourIn
from app.services.freelancer_space import schedule_alerts
from app.services.matching_service import get_team
from app.services.touring import compute_tour
from app.services.project_data import (
    get_project,
    load_task_dependencies,
    load_tasks,
    skills_of,
    to_candidate,
    to_task_need,
    total_working_days,
    unavailable_dates,
)

IMPOSSIBLE_WEEKS = 3


def scenario_deadline(project: Project, data: SolveIn) -> date:
    if data.deadline is not None:
        return data.deadline
    if data.scenario == "impossible":
        # Vendredi de la 3e semaine : 15 jours ouvrés si le projet commence un lundi.
        return project.start_date + timedelta(weeks=IMPOSSIBLE_WEEKS) - timedelta(days=3)
    return project.target_deadline


async def latest_schedule(session: AsyncSession, project: Project) -> dict[str, Any]:
    """Dernier planning réel calculé (les scénarios de test ne sont pas renvoyés), sans recalcul."""
    run = await session.scalar(
        select(ScheduleRun)
        .where(ScheduleRun.project_id == project.id, ScheduleRun.report["scenario"].astext == "normal")
        .order_by(ScheduleRun.id.desc())
        .limit(1)
    )
    if run is None:
        raise AppError(404, "Aucun planning calculé pour ce projet : lancez-le (POST /projects/{id}/solve-constraints).")
    # Indisponibilités déclarées APRÈS le calcul (espace freelance) : recalculées à chaque lecture.
    alerts = await schedule_alerts(session, run.report.get("assignments", []))
    return {**run.report, "run_id": run.id, "alerts": alerts}


class _Inputs:
    """Entrées communes au CSP et à la réparation : tâches retenues, équipe, et leur traduction pour les algorithmes."""

    def __init__(self, tasks: list[Task], team: list[Any], deps: dict[int, list[int]],
                 sched_tasks: list[SchedTask], sched_team: list[SchedFreelancer]) -> None:
        self.tasks, self.team, self.deps = tasks, team, deps
        self.sched_tasks, self.sched_team = sched_tasks, sched_team
        self.by_task = {t.id: t for t in tasks}
        self.names = {p.id: p.user.name for p in team}


async def _load_inputs(session: AsyncSession, project: Project) -> _Inputs:
    tasks = await load_tasks(session, project.id, sprint_only=True)
    if not tasks:
        raise conflict("Aucune tâche retenue : lancez d'abord le cadrage (POST /projects/{id}/scope).")
    team = await get_team(session, project)
    if not team:
        raise conflict("Aucune équipe : composez-la d'abord (POST /projects/{id}/team).")
    deps = await load_task_dependencies(session, [t.id for t in tasks])
    # Score de matching (préréglage Équilibré) pour départager les valeurs à fin égale.
    needs = [to_task_need(t) for t in tasks]
    cands = [to_candidate(p, project.start_date, project.target_deadline) for p in team]
    scores = {r.id: r.score for r in weighted_ranking(evaluate(cands, needs, total_working_days(project)),
                                                      PRESETS["Équilibré"])}
    sched_tasks = [
        SchedTask(id=t.id, title=f"{t.ref} {t.title}", skill=t.required_skill.name, min_level=t.min_level,
                  hours=t.estimated_hours, depends_on=tuple(deps[t.id]),
                  site=t.on_site_city.name if t.on_site_city else None)
        for t in tasks
    ]
    sched_team = [
        SchedFreelancer(id=p.id, name=p.user.name, skills=skills_of(p), hours_per_day=p.hours_per_day,
                        unavailable=unavailable_dates(p), score=scores.get(p.id, 0.0))
        for p in team
    ]
    return _Inputs(tasks, team, deps, sched_tasks, sched_team)


TRAVEL_DAYS = 1  # jour ouvré de trajet entre deux villes différentes (contrainte 6)


async def _site_order(session: AsyncSession, project: Project, inp: _Inputs) -> dict[str, Any] | None:
    """Ordre de visite des villes imposé aux tâches sur site (contrainte 6, niveau B).

    1. la dernière tournée VALIDÉE (POST /tour) fait foi ;
    2. sinon, tournée optimale (Held-Karp, module E) au départ de la ville du technicien probable :
       le membre de l'équipe qui sait faire le plus de tâches sur site (puis le meilleur score) —
       c'est aussi le technicien que l'écran Tournée propose par défaut une fois le planning fait.
    """
    on_site = [s for s in inp.sched_tasks if s.site is not None]
    if not on_site:
        return None
    run = await session.scalar(
        select(TourRun).where(TourRun.project_id == project.id).order_by(TourRun.id.desc()).limit(1)
    )
    if run is not None:
        return {"cities": list(run.order), "source": "tournée validée", "travel_days": TRAVEL_DAYS}
    able = [(sum(1 for t in on_site if f.can_do(t)), f.score, f) for f in inp.sched_team]
    count, _, tech = max(able, key=lambda x: (x[0], x[1]))
    if count == 0:
        return None  # personne ne peut aller sur site : le CSP le diagnostiquera (compétence absente)
    tour = await compute_tour(session, project, TourIn(freelancer_id=tech.id, closed=True), persist=False)
    return {
        "cities": [stop["name"] for stop in tour["order"]],
        "source": f"tournée optimale au départ de {tour['start']['name']} (ville de {tech.name})",
        "travel_days": TRAVEL_DAYS,
    }


def _rows(inp: _Inputs, assignments: dict[Any, Assignment], hours: dict[int, int] | None = None) -> list[dict[str, Any]]:
    """Lignes du planning pour l'API (triées par début)."""
    rows = []
    for a in sorted(assignments.values(), key=lambda a: (a.start, str(a.task_id))):
        t = inp.by_task[a.task_id]  # type: ignore[index]
        rows.append({
            "task_id": a.task_id,
            "ref": t.ref,
            "title": t.title,
            "skill": t.required_skill.name,
            "hours": (hours or {}).get(t.id, t.estimated_hours),
            "freelancer_id": a.freelancer_id,
            "freelancer": inp.names[a.freelancer_id],  # type: ignore[index]
            "start": a.start.isoformat(),
            "end": a.end.isoformat(),
            "days": a.days,
            "depends_on": [inp.by_task[d].ref for d in inp.deps[t.id]],
            "on_site_city": t.on_site_city.name if t.on_site_city else None,
        })
    return rows


async def propagate_delay(session: AsyncSession, user: User, task_id: int, data: DelayIn) -> dict[str, Any]:
    """Module D, niveau B : une tâche prend `delay_hours` de plus ; on RÉPARE le planning par Min-Conflict (n°11).

    En cas de succès, le planning réparé devient le planning réel (tâches mises à jour, nouvelle exécution
    enregistrée). En cas d'échec, rien n'est modifié et le diagnostic est renvoyé.
    """
    task = await session.get(Task, task_id)
    if task is None:
        raise not_found("Tâche")
    if user.role == Role.FREELANCER:
        # Espace freelance : le freelance peut signaler un retard sur une tâche qui LUI est confiée.
        profile = await session.scalar(select(FreelancerProfile).where(FreelancerProfile.user_id == user.id))
        if profile is None or task.assigned_freelancer_id != profile.id:
            raise AppError(403, "Cette tâche ne vous est pas confiée.")
        project = await session.scalar(
            select(Project).where(Project.id == task.project_id).options(selectinload(Project.base_city))
        )
        assert project is not None
    else:
        project = await get_project(session, task.project_id, user)
    previous = await latest_schedule(session, project)  # 404 s'il n'y a pas encore de planning
    inp = await _load_inputs(session, project)
    if task_id not in inp.by_task:
        raise conflict("Cette tâche ne fait pas partie du sprint planifié.")
    current: dict[Any, Assignment] = {}
    for t in inp.tasks:
        if t.assigned_freelancer_id is None or t.start_date is None or t.end_date is None:
            raise conflict("Le planning enregistré est incomplet : recalculez-le avant de signaler un retard.")
        f = next(p for p in inp.sched_team if p.id == t.assigned_freelancer_id)
        sched = next(s for s in inp.sched_tasks if s.id == t.id)
        current[t.id] = Assignment(t.id, f.id, t.start_date, t.end_date, f.duration(sched))

    deadline = project.target_deadline
    # Même ordre de tournée que le planning qu'on répare (cohérence de la contrainte 6).
    sites = previous.get("site_order")
    order = sites["cities"] if sites else []
    result = repair_schedule(inp.sched_tasks, inp.sched_team, project.start_date, deadline, current,
                             task_id, data.delay_hours, site_order=order, travel_days=TRAVEL_DAYS)
    longer = lengthen(inp.sched_tasks, task_id, data.delay_hours)
    delayed = inp.by_task[task_id]
    # Point de comparaison : une replanification COMPLÈTE par le CSP (n°3), limitée à 1 s. Elle donne souvent
    # un planning plus court, mais déplace plus de tâches : le client choisit en connaissance de cause.
    full = solve_schedule(longer, inp.sched_team, project.start_date, deadline, time_limit=1.0,
                          site_order=order, travel_days=TRAVEL_DAYS)
    full_replan = {
        "status": full.status,
        "makespan_days": full.makespan_days,
        "end_date": full.end_date.isoformat() if full.end_date else None,
        "changed_count": sum(
            1 for tid, a in full.assignments.items()
            if tid != task_id and (a.freelancer_id, a.start) != (current[tid].freelancer_id, current[tid].start)
        ) if full.status == "OK" else None,
    }
    repair = {
        "task_ref": delayed.ref,
        "task_title": delayed.title,
        "delay_hours": data.delay_hours,
        "status": result.status,
        "changed": [inp.by_task[t].ref for t in result.changed],  # type: ignore[index]
        "reassigned": [inp.by_task[t].ref for t in result.reassigned],  # type: ignore[index]
        "steps": result.steps,
        "elapsed_ms": round(result.elapsed_ms, 1),
        "previous_makespan_days": previous.get("makespan_days"),
        "previous_end_date": previous.get("end_date"),
        "new_makespan_days": result.makespan_days if result.status == "OK" else None,
        "delayed_end": result.delayed_end.isoformat() if result.delayed_end else None,
        "diagnostics": result.diagnostics,
        "full_replan": full_replan,
        "method": {"problem": "Réparation du planning", "method": "Min-Conflict", "exact": False,
                   "reason": "Recherche locale : on ne déplace que les tâches en conflit, en gardant si possible "
                             "le même freelance, au plus près des dates prévues.", "course_number": 11},
    }
    if result.status != "OK":
        return {"repair": repair, "schedule": None}

    report = verify_schedule(longer, inp.sched_team, project.start_date, deadline, result.assignments,
                             site_order=order, travel_days=TRAVEL_DAYS)
    if not report["constraints_passed"]:  # garde-fou : jamais de planning faux enregistré
        raise AppError(500, "Planning réparé refusé par la vérification indépendante.")
    bound = full  # borne et chemin critique recalculés avec la nouvelle durée (propagation du CSP)
    new_hours = {task_id: delayed.estimated_hours + data.delay_hours}
    payload: dict[str, Any] = {
        "scenario": "normal",
        "status": "OK",
        "start_date": project.start_date.isoformat(),
        "deadline": deadline.isoformat(),
        "working_days_available": count_working_days(project.start_date, deadline),
        "makespan_days": result.makespan_days,
        "end_date": result.end_date.isoformat() if result.end_date else None,
        "lower_bound_days": bound.lower_bound_days,
        "critical_path": [inp.by_task[i].ref for i in bound.critical_path],  # type: ignore[index]
        "optimal": False,
        "nodes": result.steps,
        "elapsed_ms": round(result.elapsed_ms, 1),
        "method": repair["method"],
        "diagnostics": [],
        "verification": report,
        "assignments": _rows(inp, result.assignments, new_hours),
        "team": [{"id": p.id, "name": p.user.name, "hours_per_day": p.hours_per_day} for p in inp.team],
        "site_order": sites,
        "repair": repair,
    }
    run = ScheduleRun(project_id=project.id, method=result.method, status="OK",
                      makespan_days=result.makespan_days, report=payload)
    session.add(run)
    delayed.estimated_hours += data.delay_hours  # l'effort réel de la tâche a augmenté
    for a in result.assignments.values():
        t = inp.by_task[a.task_id]  # type: ignore[index]
        t.assigned_freelancer_id, t.start_date, t.end_date = a.freelancer_id, a.start, a.end  # type: ignore[assignment]
    await session.commit()
    payload["run_id"] = run.id
    return {"repair": repair, "schedule": payload}


async def solve_constraints(session: AsyncSession, project: Project, data: SolveIn) -> dict[str, Any]:
    deadline = scenario_deadline(project, data)
    if deadline <= project.start_date:
        raise AppError(422, "La date limite doit être après le début du projet.")
    inp = await _load_inputs(session, project)
    team, by_task, sched_tasks, sched_team = inp.team, inp.by_task, inp.sched_tasks, inp.sched_team
    sites = await _site_order(session, project, inp)
    order = sites["cities"] if sites else []
    result, choice = solve_schedule_auto(sched_tasks, sched_team, project.start_date, deadline,
                                         site_order=order, travel_days=TRAVEL_DAYS)
    report = (
        verify_schedule(sched_tasks, sched_team, project.start_date, deadline, result.assignments,
                        site_order=order, travel_days=TRAVEL_DAYS)
        if result.status == "OK"
        else None
    )
    if report is not None and not report["constraints_passed"]:  # garde-fou : jamais de planning faux renvoyé
        raise AppError(500, "Planning refusé par la vérification indépendante.")

    assignments = _rows(inp, result.assignments)
    payload: dict[str, Any] = {
        "scenario": "impossible" if data.scenario == "impossible" and data.deadline is None else
                    ("date de test" if data.deadline else "normal"),
        "status": result.status,
        "start_date": project.start_date.isoformat(),
        "deadline": deadline.isoformat(),
        "working_days_available": count_working_days(project.start_date, deadline),
        "makespan_days": result.makespan_days,
        "end_date": result.end_date.isoformat() if result.end_date else None,
        "lower_bound_days": result.lower_bound_days,
        "critical_path": [by_task[i].ref for i in result.critical_path],  # type: ignore[index]
        "optimal": result.optimal,
        "nodes": result.nodes,
        "elapsed_ms": round(result.elapsed_ms, 1),
        "method": choice.__dict__,
        "diagnostics": result.diagnostics,
        "verification": report,
        "assignments": assignments,
        "team": [{"id": p.id, "name": p.user.name, "hours_per_day": p.hours_per_day} for p in team],
        "site_order": sites,
    }

    run = ScheduleRun(project_id=project.id, method=result.method, status=result.status,
                      makespan_days=result.makespan_days, report=payload)
    session.add(run)
    if result.status == "OK" and payload["scenario"] == "normal":
        for a in result.assignments.values():
            t = by_task[a.task_id]  # type: ignore[index]
            t.assigned_freelancer_id, t.start_date, t.end_date = a.freelancer_id, a.start, a.end  # type: ignore[assignment]
            t.status = TaskStatus.TODO
        project.status = ProjectStatus.PLANNED
    await session.commit()
    payload["run_id"] = run.id
    return payload
