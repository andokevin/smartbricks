"""Module D — planification par CSP (n°3) : lien entre la base, le solveur et verify_schedule.

Le « scénario impossible » (et toute autre date limite de test) n'est PAS enregistré dans les tâches :
il sert à montrer le diagnostic sans abîmer le planning réel.
"""

from datetime import date, timedelta
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.algorithms.calendar import count_working_days
from app.algorithms.csp_scheduler import SchedFreelancer, SchedTask, verify_schedule
from app.algorithms.matching import PRESETS, evaluate, weighted_ranking
from app.algorithms.solver_selector import solve_schedule_auto
from app.errors import AppError, conflict
from app.models import Project, ProjectStatus, ScheduleRun, TaskStatus
from app.schemas import SolveIn
from app.services.matching_service import get_team
from app.services.project_data import (
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


async def solve_constraints(session: AsyncSession, project: Project, data: SolveIn) -> dict[str, Any]:
    deadline = scenario_deadline(project, data)
    if deadline <= project.start_date:
        raise AppError(422, "La date limite doit être après le début du projet.")
    tasks = await load_tasks(session, project.id, sprint_only=True)
    if not tasks:
        raise conflict("Aucune tâche retenue : lancez d'abord le cadrage (POST /projects/{id}/scope).")
    team = await get_team(session, project)
    if not team:
        raise conflict("Aucune équipe : composez-la d'abord (POST /projects/{id}/team).")

    deps = await load_task_dependencies(session, [t.id for t in tasks])
    by_task = {t.id: t for t in tasks}

    # Score de matching (préréglage Équilibré) pour départager les valeurs à fin égale.
    needs = [to_task_need(t) for t in tasks]
    cands = [to_candidate(p, project.start_date, project.target_deadline) for p in team]
    scores = {r.id: r.score for r in weighted_ranking(evaluate(cands, needs, total_working_days(project)),
                                                      PRESETS["Équilibré"])}

    sched_tasks = [
        SchedTask(id=t.id, title=f"{t.ref} {t.title}", skill=t.required_skill.name, min_level=t.min_level,
                  hours=t.estimated_hours, depends_on=tuple(deps[t.id]))
        for t in tasks
    ]
    sched_team = [
        SchedFreelancer(id=p.id, name=p.user.name, skills=skills_of(p), hours_per_day=p.hours_per_day,
                        unavailable=unavailable_dates(p), score=scores.get(p.id, 0.0))
        for p in team
    ]
    result, choice = solve_schedule_auto(sched_tasks, sched_team, project.start_date, deadline)
    report = (
        verify_schedule(sched_tasks, sched_team, project.start_date, deadline, result.assignments)
        if result.status == "OK"
        else None
    )
    if report is not None and not report["constraints_passed"]:  # garde-fou : jamais de planning faux renvoyé
        raise AppError(500, "Planning refusé par la vérification indépendante.")

    names = {p.id: p.user.name for p in team}
    assignments = [
        {
            "task_id": a.task_id,
            "ref": by_task[a.task_id].ref,  # type: ignore[index]
            "title": by_task[a.task_id].title,  # type: ignore[index]
            "skill": by_task[a.task_id].required_skill.name,  # type: ignore[index]
            "hours": by_task[a.task_id].estimated_hours,  # type: ignore[index]
            "freelancer_id": a.freelancer_id,
            "freelancer": names[a.freelancer_id],  # type: ignore[index]
            "start": a.start.isoformat(),
            "end": a.end.isoformat(),
            "days": a.days,
            "depends_on": [by_task[d].ref for d in deps[a.task_id]],  # type: ignore[index]
            "on_site_city": by_task[a.task_id].on_site_city.name if by_task[a.task_id].on_site_city else None,  # type: ignore[index, union-attr]
        }
        for a in sorted(result.assignments.values(), key=lambda a: (a.start, str(a.task_id)))
    ]
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
