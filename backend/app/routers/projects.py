"""Projets et modules B à E, plus l'explication (module A)."""

from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.models import User
from app.schemas import (
    ExplainIn,
    ExplainOut,
    FeatureOut,
    FeaturePatch,
    ProjectOut,
    ProjectSummary,
    ScopeOut,
    SolveIn,
    TeamIn,
    TeamOut,
    TourIn,
)
from app.security import get_current_user
from app.services import explaining, matching_service, projects_view, scheduling, scoping, touring
from app.services.project_data import get_project

router = APIRouter(tags=["projets"])


@router.get("/projects", response_model=list[ProjectSummary])
async def projects(session: AsyncSession = Depends(get_session),
                   user: User = Depends(get_current_user)) -> list[ProjectSummary]:
    return await projects_view.list_projects(session, user)


@router.get("/projects/{project_id}", response_model=ProjectOut)
async def project(project_id: int, session: AsyncSession = Depends(get_session),
                  user: User = Depends(get_current_user)) -> ProjectOut:
    return await projects_view.project_detail(session, await get_project(session, project_id, user))


@router.patch("/features/{feature_id}", response_model=FeatureOut, tags=["projets"])
async def patch_feature(feature_id: int, data: FeaturePatch, session: AsyncSession = Depends(get_session),
                        user: User = Depends(get_current_user)) -> FeatureOut:
    """Corrige la valeur métier, les heures ou le caractère obligatoire. Le cadrage est à relancer."""
    return await projects_view.patch_feature(session, user, feature_id, data)


@router.get("/projects/{project_id}/scope", response_model=ScopeOut, tags=["B · sac à dos (n°29)"])
async def get_scope(project_id: int, session: AsyncSession = Depends(get_session),
                    user: User = Depends(get_current_user)) -> ScopeOut:
    """Dernier cadrage calculé (sans recalcul) ; 404 s'il n'a jamais été lancé."""
    return scoping.stored_scope(await get_project(session, project_id, user))


@router.post("/projects/{project_id}/scope", response_model=ScopeOut, tags=["B · sac à dos (n°29)"])
async def scope(project_id: int, session: AsyncSession = Depends(get_session),
                user: User = Depends(get_current_user)) -> ScopeOut:
    """Sprint 1 optimal sous le budget en Ar ET les heures, avec raisons et scénarios « et si ? »."""
    return await scoping.run_scope(session, await get_project(session, project_id, user))


@router.get("/projects/{project_id}/matching", tags=["C · matching (n°22 et n°21)"])
async def matching(
    project_id: int,
    preset: str | None = Query(default=None, description="Économique, Rapide, Qualité ou Équilibré"),
    w_cost: float | None = None,
    w_speed: float | None = None,
    w_quality: float | None = None,
    w_availability: float | None = None,
    w_coverage: float | None = None,
    pareto: str = Query(default="cost,speed,quality", description="Critères du front de Pareto"),
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Classement pondéré (curseurs ou préréglage), fronts de Pareto, meilleur compromis, équipe suggérée."""
    p = await get_project(session, project_id, user)
    weights, name = matching_service.resolve_weights(preset, {
        "cost": w_cost, "speed": w_speed, "quality": w_quality,
        "availability": w_availability, "coverage": w_coverage,
    })
    keys = [k.strip() for k in pareto.split(",") if k.strip()]
    return await matching_service.compute_matching(session, p, weights, name, keys)


@router.post("/projects/{project_id}/team", response_model=TeamOut, tags=["C · matching (n°22 et n°21)"])
async def team(project_id: int, data: TeamIn, session: AsyncSession = Depends(get_session),
               user: User = Depends(get_current_user)) -> TeamOut:
    """`{"suggested": true}` pour l'équipe suggérée, ou `{"freelancer_ids": [...]}`."""
    return await matching_service.set_team(session, await get_project(session, project_id, user), data)


@router.post("/projects/{project_id}/solve-constraints", tags=["D · planning CSP (n°3)"])
async def solve(project_id: int, data: SolveIn, session: AsyncSession = Depends(get_session),
                user: User = Depends(get_current_user)) -> dict[str, Any]:
    """Planning des tâches retenues + rapport de vérification, ou diagnostic chiffré.

    `{"scenario": "impossible"}` : date limite ramenée à 3 semaines, sans rien enregistrer.
    """
    return await scheduling.solve_constraints(session, await get_project(session, project_id, user), data)


@router.post("/projects/{project_id}/tour", tags=["E · tournée (n°30)"])
async def tour(project_id: int, data: TourIn, session: AsyncSession = Depends(get_session),
               user: User = Depends(get_current_user)) -> dict[str, Any]:
    """Ordre optimal des visites sur site, distance, coût, durée, gain par rapport à l'ordre saisi."""
    return await touring.compute_tour(session, await get_project(session, project_id, user), data)


@router.post("/projects/{project_id}/explain", response_model=ExplainOut, tags=["A · copilote (n°33)"])
async def explain(project_id: int, data: ExplainIn, session: AsyncSession = Depends(get_session),
                  user: User = Depends(get_current_user)) -> ExplainOut:
    """Explication en français simple, à partir des seuls résultats calculés."""
    return await explaining.explain_project(session, await get_project(session, project_id, user), data)
