"""Estimation du coût des fonctionnalités (en Ariary).

Règle de la spécification : coût = heures × taux horaire moyen des freelances qui ont la compétence.
Une fonctionnalité regroupe des tâches de compétences différentes : son coût est donc la somme,
sur ses tâches, de `heures de la tâche × taux moyen de la compétence de la tâche`.

Avant le choix de l'équipe : moyenne sur TOUS les freelances qui ont la compétence.
Après le choix (POST /team) : moyenne sur les membres de l'équipe qui ont la compétence ;
si aucun membre ne l'a, on garde la moyenne générale de cette compétence.
"""

from collections.abc import Collection

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Feature, FreelancerProfile, FreelancerSkill, ProjectTeam, Task


async def average_rate_by_skill(
    session: AsyncSession, freelancer_ids: Collection[int] | None = None
) -> dict[int, float]:
    """Taux horaire moyen (Ar) par compétence : {skill_id: taux}, éventuellement limité à une équipe."""
    query = (
        select(FreelancerSkill.skill_id, func.avg(FreelancerProfile.hourly_rate_mga))
        .join(FreelancerProfile, FreelancerProfile.id == FreelancerSkill.freelancer_id)
        .group_by(FreelancerSkill.skill_id)
    )
    if freelancer_ids is not None:
        query = query.where(FreelancerProfile.id.in_(list(freelancer_ids)))
    rows = await session.execute(query)
    return {skill_id: float(avg) for skill_id, avg in rows.all()}


async def global_average_rate(session: AsyncSession) -> float:
    """Taux moyen de tous les freelances : repli si une compétence n'a aucun freelance."""
    value = await session.scalar(select(func.avg(FreelancerProfile.hourly_rate_mga)))
    return float(value) if value is not None else 30_000.0


def feature_cost(feature: Feature, tasks: list[Task], rates: dict[int, float], fallback: float) -> int:
    """Coût estimé d'une fonctionnalité, arrondi au millier d'Ariary."""
    if tasks:
        cost = sum(t.estimated_hours * rates.get(t.required_skill_id, fallback) for t in tasks)
    else:
        cost = feature.estimated_hours * fallback
    return int(round(cost / 1000.0)) * 1000


async def recompute_feature_costs(session: AsyncSession, project_id: int) -> None:
    """Recalcule `estimated_cost_mga` de toutes les fonctionnalités d'un projet
    (avec les taux de l'équipe si elle est déjà choisie)."""
    rates = await average_rate_by_skill(session)
    team = (await session.scalars(select(ProjectTeam.freelancer_id).where(ProjectTeam.project_id == project_id))).all()
    if team:
        rates.update(await average_rate_by_skill(session, team))  # les taux de l'équipe priment
    fallback = await global_average_rate(session)
    features = (await session.scalars(select(Feature).where(Feature.project_id == project_id))).all()
    tasks = (await session.scalars(select(Task).where(Task.project_id == project_id))).all()
    for feature in features:
        own_tasks = [t for t in tasks if t.feature_id == feature.id]
        feature.estimated_cost_mga = feature_cost(feature, own_tasks, rates, fallback)
