"""Lecture des données d'un projet, avec contrôle d'accès, et conversion vers les entrées des algorithmes.

Toutes les relations utiles sont chargées d'avance (selectinload) : en SQLAlchemy asynchrone,
un accès paresseux à une relation non chargée est une erreur.
"""

from collections.abc import Collection
from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.algorithms.calendar import available_days, count_working_days
from app.algorithms.matching import Candidate, TaskNeed
from app.errors import AppError, not_found
from app.models import (
    Feature,
    FreelancerProfile,
    FreelancerSkill,
    Project,
    ProjectSite,
    ProjectTeam,
    Role,
    Task,
    TaskDependency,
    User,
)


async def get_project(session: AsyncSession, project_id: int, user: User) -> Project:
    """Projet du client connecté (l'administrateur voit tout)."""
    project = await session.scalar(
        select(Project).where(Project.id == project_id).options(selectinload(Project.base_city))
    )
    if project is None:
        raise not_found("Projet")
    if user.role != Role.ADMIN and project.client_id != user.id:
        raise AppError(403, "Ce projet appartient à un autre client.")
    return project


async def load_features(session: AsyncSession, project_id: int) -> list[Feature]:
    return list((await session.scalars(select(Feature).where(Feature.project_id == project_id).order_by(Feature.id))).all())


async def load_tasks(session: AsyncSession, project_id: int, sprint_only: bool = False) -> list[Task]:
    query = (
        select(Task)
        .where(Task.project_id == project_id)
        .options(selectinload(Task.required_skill), selectinload(Task.on_site_city))
        .order_by(Task.id)
    )
    if sprint_only:
        query = query.join(Feature, Feature.id == Task.feature_id).where(Feature.selected_for_sprint.is_(True))
    return list((await session.scalars(query)).all())


async def load_task_dependencies(session: AsyncSession, task_ids: Collection[int]) -> dict[int, list[int]]:
    """{tâche: [tâches dont elle dépend]}, limité aux tâches données."""
    ids = set(task_ids)
    rows = (await session.execute(select(TaskDependency).where(TaskDependency.task_id.in_(ids)))).scalars().all()
    deps: dict[int, list[int]] = {i: [] for i in ids}
    for d in rows:
        if d.depends_on_task_id in ids:
            deps[d.task_id].append(d.depends_on_task_id)
    return deps


async def load_freelancers(session: AsyncSession, ids: Collection[int] | None = None) -> list[FreelancerProfile]:
    query = (
        select(FreelancerProfile)
        .options(
            selectinload(FreelancerProfile.user),
            selectinload(FreelancerProfile.city),
            selectinload(FreelancerProfile.skills).selectinload(FreelancerSkill.skill),
            selectinload(FreelancerProfile.unavailability),
        )
        .order_by(FreelancerProfile.id)
    )
    if ids is not None:
        query = query.where(FreelancerProfile.id.in_(list(ids)))
    return list((await session.scalars(query)).all())


async def load_team_ids(session: AsyncSession, project_id: int) -> list[int]:
    rows = await session.scalars(
        select(ProjectTeam.freelancer_id).where(ProjectTeam.project_id == project_id).order_by(ProjectTeam.freelancer_id)
    )
    return list(rows.all())


async def load_sites(session: AsyncSession, project_id: int) -> list[ProjectSite]:
    rows = await session.scalars(
        select(ProjectSite)
        .where(ProjectSite.project_id == project_id)
        .options(selectinload(ProjectSite.city))
        .order_by(ProjectSite.position)
    )
    return list(rows.all())


# --------------------------------------------------------------------------- conversions


def unavailable_dates(profile: FreelancerProfile) -> frozenset[date]:
    days: set[date] = set()
    for period in profile.unavailability:
        d = period.start_date
        while d <= period.end_date:
            days.add(d)
            d = date.fromordinal(d.toordinal() + 1)
    return frozenset(days)


def skills_of(profile: FreelancerProfile) -> dict[str, int]:
    return {fs.skill.name: fs.level for fs in profile.skills}


def to_candidate(profile: FreelancerProfile, start: date, deadline: date) -> Candidate:
    return Candidate(
        id=profile.id,
        name=profile.user.name,
        hourly_rate=profile.hourly_rate_mga,
        rating=profile.rating,
        on_time_rate=profile.on_time_rate,
        hours_per_day=profile.hours_per_day,
        skills=skills_of(profile),
        available_days=len(available_days(start, deadline, unavailable_dates(profile))),
    )


def to_task_need(task: Task) -> TaskNeed:
    return TaskNeed(id=task.id, skill=task.required_skill.name, min_level=task.min_level, hours=task.estimated_hours)


def total_working_days(project: Project) -> int:
    return count_working_days(project.start_date, project.target_deadline)
