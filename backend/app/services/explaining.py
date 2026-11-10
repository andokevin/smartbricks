"""Module A — rassemble les résultats DÉJÀ CALCULÉS d'un projet pour l'explication du copilote.

Le LLM ne reçoit que ces données : il ne voit ni la base, ni les algorithmes.
"""

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Project, ScheduleRun, TourRun
from app.schemas import ExplainIn, ExplainOut
from app.services.copilot import explain
from app.services.llm_usage import get_provider
from app.services.matching_service import get_team
from app.services.project_data import load_features, skills_of
from app.services.scoping import sprint_summary


async def build_facts(session: AsyncSession, project: Project) -> dict[str, Any]:
    facts: dict[str, Any] = {
        "projet": {
            "titre": project.title,
            "budget_mga": project.budget_mga,
            "budget_heures": project.budget_hours,
            "date_limite": project.target_deadline.isoformat(),
        }
    }
    features = await load_features(session, project.id)
    if any(f.selected_for_sprint for f in features):
        sprint = sprint_summary(features)
        report = project.scope_report or {}
        # « Et si ? » tels que présentés au client lors du cadrage (le premier qui ajoute quelque chose).
        sprint["et_si"] = [w["message"] for w in report.get("what_if", []) if w.get("added")][:1]
        sprint["methode"] = (report.get("method") or {}).get("method")
        facts["sprint"] = sprint

    team = await get_team(session, project)
    if team:
        facts["equipe"] = [
            {"nom": p.user.name, "competences": list(skills_of(p)), "taux_horaire_mga": p.hourly_rate_mga}
            for p in team
        ]

    # Dernier planning RÉEL (les scénarios de test comme « impossible » ne sont pas expliqués).
    run = await session.scalar(
        select(ScheduleRun)
        .where(ScheduleRun.project_id == project.id, ScheduleRun.report["scenario"].astext == "normal")
        .order_by(ScheduleRun.id.desc())
        .limit(1)
    )
    if run is not None:
        r = run.report
        facts["planning"] = {
            "statut": r.get("status"),
            "scenario": r.get("scenario"),
            "date_fin": r.get("end_date"),
            "duree_jours": r.get("makespan_days"),
            "diagnostics": r.get("diagnostics", []),
        }

    tour = await session.scalar(
        select(TourRun).where(TourRun.project_id == project.id).order_by(TourRun.id.desc()).limit(1)
    )
    if tour is not None:
        facts["tournee"] = {
            "ordre": list(tour.order),
            "distance_km": round(tour.distance_km),
            "cout_mga": tour.cost_mga,
            "methode": tour.method,
        }
    return facts


async def explain_project(session: AsyncSession, project: Project, data: ExplainIn) -> ExplainOut:
    facts = await build_facts(session, project)
    provider = await get_provider(session)
    e = await explain(provider, facts, data.question)
    return ExplainOut(text=e.text, provider=e.provider, replaced=e.replaced, unknown_numbers=e.unknown_numbers,
                      fallback_reason=provider.fallback_reason)
