"""Module C — matching (n°22 agrégation pondérée, n°21 Pareto) et composition de l'équipe."""

import math
from collections.abc import Mapping, Sequence
from typing import Any

from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.algorithms.matching import (
    CRITERIA,
    LABELS,
    PRESETS,
    Candidate,
    Ranked,
    TaskNeed,
    best_compromise,
    evaluate,
    non_dominated_sort,
    normalize_weights,
    suggest_team,
    weighted_ranking,
)
from app.errors import AppError, conflict
from app.models import FreelancerProfile, Project, ProjectStatus, ProjectTeam
from app.schemas import TeamIn, TeamMemberOut, TeamOut
from app.services.costing import recompute_feature_costs
from app.services.project_data import (
    load_freelancers,
    load_tasks,
    load_team_ids,
    skills_of,
    to_candidate,
    to_task_need,
    total_working_days,
)


def resolve_weights(preset: str | None, weights: Mapping[str, float | None]) -> tuple[dict[str, float], str]:
    """Poids des curseurs s'ils sont donnés, sinon ceux du préréglage (Équilibré par défaut)."""
    given = {k: v for k, v in weights.items() if v is not None}
    if given:
        return normalize_weights(given), "Personnalisé"
    name = preset or "Équilibré"
    if name not in PRESETS:
        raise AppError(422, f"Préréglage inconnu : {name}. Choix : {', '.join(PRESETS)}.")
    return dict(PRESETS[name]), name


async def _inputs(session: AsyncSession, project: Project) -> tuple[list[Candidate], list[TaskNeed], list[FreelancerProfile]]:
    tasks = await load_tasks(session, project.id, sprint_only=True)
    if not tasks:
        raise conflict("Aucune tâche retenue : lancez d'abord le cadrage du sprint (POST /projects/{id}/scope).")
    profiles = await load_freelancers(session)
    candidates = [to_candidate(p, project.start_date, project.target_deadline) for p in profiles]
    return candidates, [to_task_need(t) for t in tasks], profiles


def _finite(x: float) -> float | None:
    return round(x, 3) if math.isfinite(x) else None


async def compute_matching(
    session: AsyncSession, project: Project, weights: dict[str, float], preset_name: str, pareto_keys: Sequence[str]
) -> dict[str, Any]:
    keys = [k for k in pareto_keys if k in CRITERIA]
    if len(keys) < 2:
        raise AppError(422, f"Choisissez au moins deux critères de Pareto parmi : {', '.join(CRITERIA)}.")
    candidates, needs, profiles = await _inputs(session, project)
    by_id = {p.id: p for p in profiles}
    crit = evaluate(candidates, needs, total_working_days(project))
    ranking = weighted_ranking(crit, weights)
    fronts = non_dominated_sort(crit, keys)
    front_of = {i: k + 1 for k, front in enumerate(fronts) for i in front}
    best = best_compromise(crit, fronts[0], keys) if fronts else None
    team = suggest_team(candidates, needs, ranking)

    def row(rank: int, r: Ranked) -> dict[str, Any]:
        p, c = by_id[r.id], crit[r.id]  # type: ignore[index]
        return {
            "rank": rank,
            "id": p.id,
            "name": p.user.name,
            "city": p.city.name,
            "hourly_rate_mga": p.hourly_rate_mga,
            "hours_per_day": p.hours_per_day,
            "skills": skills_of(p),
            "criteria": {
                "cost": int(c.cost), "speed": _finite(c.speed), "quality": round(c.quality, 3),
                "availability": int(c.availability), "coverage": round(c.coverage, 3),
            },
            "normalized": {k: round(v, 3) for k, v in r.normalized.items()},
            "contributions": {k: round(v, 4) for k, v in r.contributions.items()},
            "score": round(r.score, 4),
            "front": front_of[r.id],
            "best_compromise": r.id == best,
        }

    return {
        "algorithms": [
            {"number": 22, "name": "Agrégation pondérée", "role": "classement selon les poids"},
            {"number": 21, "name": "Optimisation de Pareto", "role": "fronts non dominés et meilleur compromis"},
        ],
        "preset": preset_name,
        "weights": {k: round(v, 4) for k, v in weights.items()},
        "criteria_labels": LABELS,
        "pareto_criteria": keys,
        "tasks_considered": len(needs),
        "total_hours": sum(n.hours for n in needs),
        "working_days": total_working_days(project),
        "ranking": [row(k + 1, r) for k, r in enumerate(ranking)],
        "fronts": [[int(i) for i in f] for f in fronts],  # type: ignore[call-overload]
        "best_compromise": best,
        "suggested_team": {"members": team.members, "absorbable": team.absorbable, "warnings": team.warnings},
    }


async def set_team(session: AsyncSession, project: Project, data: TeamIn) -> TeamOut:
    candidates, needs, profiles = await _inputs(session, project)
    by_id = {p.id: p for p in profiles}
    warnings: list[str] = []
    if data.suggested:
        weights, _ = resolve_weights(data.preset, {})
        crit = evaluate(candidates, needs, total_working_days(project))
        suggestion = suggest_team(candidates, needs, weighted_ranking(crit, weights))
        ids = [int(i) for i in suggestion.members]  # type: ignore[call-overload]
        warnings += suggestion.warnings
        absorbable = suggestion.absorbable
    else:
        if not data.freelancer_ids:
            raise AppError(422, "Donnez une liste de freelances (freelancer_ids) ou demandez l'équipe suggérée.")
        unknown = [i for i in data.freelancer_ids if i not in by_id]
        if unknown:
            raise AppError(422, f"Freelances inconnus : {unknown}.")
        ids = list(dict.fromkeys(data.freelancer_ids))
        chosen = [c for c in candidates if c.id in ids]
        for n in needs:
            if not any(c.can_do(n) for c in chosen):
                warnings.append(f"Personne dans l'équipe n'a {n.skill} au niveau {n.min_level} (tâche n°{n.id}).")
        absorbable = not warnings

    await session.execute(delete(ProjectTeam).where(ProjectTeam.project_id == project.id))
    session.add_all([ProjectTeam(project_id=project.id, freelancer_id=i) for i in ids])
    project.status = ProjectStatus.TEAM_SELECTED
    await session.flush()
    await recompute_feature_costs(session, project.id)  # coûts recalculés avec les taux de l'équipe
    await session.commit()
    return TeamOut(project_id=project.id, members=[member_out(by_id[i]) for i in ids], warnings=warnings,
                   absorbable=absorbable)


def member_out(p: FreelancerProfile) -> TeamMemberOut:
    return TeamMemberOut(id=p.id, name=p.user.name, city=p.city.name, hourly_rate_mga=p.hourly_rate_mga,
                         hours_per_day=p.hours_per_day, skills=skills_of(p))


async def get_team(session: AsyncSession, project: Project) -> list[FreelancerProfile]:
    ids = await load_team_ids(session, project.id)
    return await load_freelancers(session, ids) if ids else []
