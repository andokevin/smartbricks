"""Création d'un projet complet (fonctionnalités, tâches, dépendances, sites) à partir d'un brouillon.

Le brouillon a le format JSON produit par le copilote (voir CLAUDE.md, module A).
Utilisé par le seed (projet de démonstration) et, en phase 5, par POST /assistant/confirm.

Ici, le brouillon est supposé DÉJÀ VALIDÉ (compétences et villes reconnues, pas de cycle) :
la validation approchée et la détection de cycles arrivent avec le copilote (phase 4).
"""

from datetime import date
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.algorithms.calendar import count_working_days

from app.models import City, Feature, Project, ProjectSite, ProjectStatus, ReqType, Skill, Task, TaskDependency
from app.services.costing import recompute_feature_costs

# Valeur par défaut de budget_hours quand le client ne l'a pas donné :
# une petite équipe de 2 personnes à 6 h par jour ouvré jusqu'à la date limite.
DEFAULT_TEAM_SIZE = 2
DEFAULT_HOURS_PER_DAY = 6


def default_budget_hours(start: date, deadline: date) -> int:
    return count_working_days(start, deadline) * DEFAULT_HOURS_PER_DAY * DEFAULT_TEAM_SIZE


async def create_project_from_draft(
    session: AsyncSession, client_id: int, draft: dict[str, Any], start_date: date
) -> Project:
    """Insère le projet et tout son contenu ; renvoie le projet (non commité)."""
    skills = {s.name.lower(): s.id for s in (await session.scalars(select(Skill))).all()}
    cities = {c.name.lower(): c.id for c in (await session.scalars(select(City))).all()}

    def city_id(name: str | None) -> int | None:
        return cities.get(name.lower()) if name else None

    p = draft["project"]
    deadline = date.fromisoformat(p["deadline"])
    project = Project(
        client_id=client_id,
        title=p["title"],
        description=p.get("description"),
        budget_mga=int(p["budget_mga"]),
        budget_hours=int(p.get("budget_hours") or default_budget_hours(start_date, deadline)),
        start_date=start_date,
        target_deadline=deadline,
        base_city_id=city_id(p.get("base_city")),
        status=ProjectStatus.DRAFT,
    )
    session.add(project)
    await session.flush()  # pour obtenir project.id

    # 1) Fonctionnalités, puis leurs dépendances (les identifiants n'existent qu'après flush).
    features: dict[str, Feature] = {}
    for f in draft["features"]:
        feature = Feature(
            project_id=project.id,
            ref=f["ref"],
            title=f["title"],
            description=f.get("description"),
            req_type=ReqType(f["req_type"]),
            business_value=int(f["business_value"]),
            estimated_hours=int(f["estimated_hours"]),
            is_mandatory=bool(f.get("is_mandatory", False)),
            depends_on_feature_ids=[],
        )
        session.add(feature)
        features[f["ref"]] = feature
    await session.flush()
    for f in draft["features"]:
        features[f["ref"]].depends_on_feature_ids = [features[d].id for d in f.get("depends_on", [])]

    # 2) Tâches, puis dépendances entre tâches.
    tasks: dict[str, Task] = {}
    for t in draft["tasks"]:
        task = Task(
            project_id=project.id,
            feature_id=features[t["feature_ref"]].id,
            ref=t["ref"],
            title=t["title"],
            description=t.get("description"),
            required_skill_id=skills[t["required_skill"].lower()],
            min_level=int(t.get("min_level", 1)),
            estimated_hours=int(t["estimated_hours"]),
            on_site_city_id=city_id(t.get("on_site_city")),
        )
        session.add(task)
        tasks[t["ref"]] = task
    await session.flush()
    for t in draft["tasks"]:
        for dep in t.get("depends_on", []):
            session.add(TaskDependency(task_id=tasks[t["ref"]].id, depends_on_task_id=tasks[dep].id))

    # 3) Sites à visiter, dans l'ordre saisi.
    for position, name in enumerate(draft.get("sites", [])):
        cid = city_id(name)
        if cid is not None:
            session.add(ProjectSite(project_id=project.id, city_id=cid, position=position))

    await session.flush()
    await recompute_feature_costs(session, project.id)
    return project
