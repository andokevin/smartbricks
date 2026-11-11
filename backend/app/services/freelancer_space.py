"""Espace freelance (niveau B) : le freelance voit ses tâches, déclare ses indisponibilités, fait avancer ses tâches.

Les indisponibilités déclarées ici sont celles que le matching (n°22/21) et le CSP (n°3) utilisent.
Si une nouvelle indisponibilité tombe sur une tâche déjà planifiée, le planning n'est PAS modifié en
silence : le freelance est averti, et l'écran Planning du client affiche une alerte (voir `schedule_alerts`).
"""

from datetime import date, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.algorithms.calendar import working_days
from app.algorithms.formatting import format_date_fr
from app.errors import AppError, not_found
from app.models import (
    FreelancerProfile,
    FreelancerSkill,
    FreelancerUnavailability,
    Project,
    Task,
    TaskDependency,
    TaskStatus,
    User,
)
from app.schemas import TaskStatusIn, UnavailabilityIn

ALLOWED_STATUSES = {TaskStatus.TODO, TaskStatus.IN_PROGRESS, TaskStatus.REVIEW, TaskStatus.DONE}


async def my_profile(session: AsyncSession, user: User) -> FreelancerProfile:
    profile = await session.scalar(
        select(FreelancerProfile)
        .where(FreelancerProfile.user_id == user.id)
        .options(
            selectinload(FreelancerProfile.city),
            selectinload(FreelancerProfile.skills).selectinload(FreelancerSkill.skill),
            selectinload(FreelancerProfile.unavailability),
        )
    )
    if profile is None:
        raise AppError(404, "Aucun profil freelance pour ce compte.")
    return profile


def overlap_days(start: date, end: date, periods: list[FreelancerUnavailability]) -> list[tuple[FreelancerUnavailability, list[date]]]:
    """Jours ouvrés de [start, end] qui tombent dans une indisponibilité (par période)."""
    out = []
    for u in periods:
        days = [d for d in working_days(max(start, u.start_date), min(end, u.end_date))]
        if days:
            out.append((u, days))
    return out


def period_text(u: FreelancerUnavailability) -> str:
    """« le 18 novembre 2026 » ou « du 18 au 20 novembre 2026 »."""
    if u.start_date == u.end_date:
        return f"le {format_date_fr(u.start_date)}"
    return f"du {format_date_fr(u.start_date)} au {format_date_fr(u.end_date)}"


def days_text(n: int) -> str:
    return "1 jour ouvré" if n == 1 else f"{n} jours ouvrés"


def _period(u: FreelancerUnavailability) -> dict[str, Any]:
    return {"id": u.id, "start": u.start_date.isoformat(), "end": u.end_date.isoformat(), "reason": u.reason}


async def profile_view(session: AsyncSession, user: User) -> dict[str, Any]:
    p = await my_profile(session, user)
    return {
        "id": p.id,
        "name": user.name,
        "email": user.email,
        "city": p.city.name,
        "hourly_rate_mga": p.hourly_rate_mga,
        "hours_per_day": p.hours_per_day,
        "rating": p.rating,
        "on_time_rate": p.on_time_rate,
        "skills": {s.skill.name: s.level for s in sorted(p.skills, key=lambda s: -s.level)},
        "unavailability": [_period(u) for u in sorted(p.unavailability, key=lambda u: u.start_date)],
    }


async def my_tasks(session: AsyncSession, user: User) -> list[dict[str, Any]]:
    """Tâches planifiées confiées au freelance, triées par date de début, avec leurs dépendances et alertes."""
    p = await my_profile(session, user)
    tasks = list((await session.scalars(
        select(Task)
        .where(Task.assigned_freelancer_id == p.id)
        .options(selectinload(Task.required_skill), selectinload(Task.on_site_city),
                 selectinload(Task.project).selectinload(Project.client))
        .order_by(Task.start_date, Task.id)
    )).all())
    ids = [t.id for t in tasks]
    deps = (await session.execute(select(TaskDependency).where(TaskDependency.task_id.in_(ids)))).scalars().all()
    pred_ids = {d.depends_on_task_id for d in deps}
    preds = {t.id: t for t in (await session.scalars(
        select(Task).where(Task.id.in_(pred_ids)).options(selectinload(Task.assigned_freelancer).selectinload(FreelancerProfile.user))
    )).all()} if pred_ids else {}
    by_task: dict[int, list[Task]] = {}
    for d in deps:
        if d.depends_on_task_id in preds:
            by_task.setdefault(d.task_id, []).append(preds[d.depends_on_task_id])

    out = []
    for t in tasks:
        alerts = []
        if t.start_date and t.end_date:
            for u, days in overlap_days(t.start_date, t.end_date, list(p.unavailability)):
                alerts.append(
                    f"Votre indisponibilité ({period_text(u)}) tombe pendant cette tâche ({days_text(len(days))}) : "
                    "le client est prévenu et doit recalculer le planning."
                )
        before = by_task.get(t.id, [])
        out.append({
            "id": t.id,
            "ref": t.ref,
            "title": t.title,
            "description": t.description,
            "project": {"id": t.project.id, "title": t.project.title,
                        "client": t.project.client.organization_name or t.project.client.name},
            "skill": t.required_skill.name,
            "min_level": t.min_level,
            "hours": t.estimated_hours,
            "start": t.start_date.isoformat() if t.start_date else None,
            "end": t.end_date.isoformat() if t.end_date else None,
            "status": t.status.value,
            "on_site_city": t.on_site_city.name if t.on_site_city else None,
            "depends_on": [
                {"ref": d.ref, "title": d.title, "status": d.status.value,
                 "freelancer": d.assigned_freelancer.user.name if d.assigned_freelancer else None,
                 "end": d.end_date.isoformat() if d.end_date else None}
                for d in before
            ],
            "ready": all(d.status == TaskStatus.DONE for d in before),
            "alerts": alerts,
        })
    return out


async def set_status(session: AsyncSession, user: User, task_id: int, data: TaskStatusIn) -> dict[str, Any]:
    p = await my_profile(session, user)
    task = await session.get(Task, task_id)
    if task is None:
        raise not_found("Tâche")
    if task.assigned_freelancer_id != p.id:
        raise AppError(403, "Cette tâche ne vous est pas confiée.")
    status = TaskStatus(data.status)
    if status not in ALLOWED_STATUSES:
        raise AppError(422, "Statut non modifiable depuis l'espace freelance.")
    task.status = status
    await session.commit()
    return {"id": task.id, "status": task.status.value}


async def add_unavailability(session: AsyncSession, user: User, data: UnavailabilityIn) -> dict[str, Any]:
    if data.end < data.start:
        raise AppError(422, "La fin de l'indisponibilité doit être après son début.")
    if (data.end - data.start) > timedelta(days=366):
        raise AppError(422, "Une indisponibilité ne peut pas dépasser un an.")
    p = await my_profile(session, user)
    u = FreelancerUnavailability(freelancer_id=p.id, start_date=data.start, end_date=data.end, reason=data.reason)
    session.add(u)
    await session.commit()
    await session.refresh(u)
    # Tâches déjà planifiées touchées par cette nouvelle indisponibilité.
    tasks = (await session.scalars(
        select(Task).where(Task.assigned_freelancer_id == p.id, Task.start_date.is_not(None))
    )).all()
    affected = [t.ref + " " + t.title for t in tasks
                if t.start_date and t.end_date and overlap_days(t.start_date, t.end_date, [u])]
    return {"unavailability": _period(u), "affected_tasks": affected}


async def delete_unavailability(session: AsyncSession, user: User, unavailability_id: int) -> None:
    p = await my_profile(session, user)
    u = await session.get(FreelancerUnavailability, unavailability_id)
    if u is None or u.freelancer_id != p.id:
        raise not_found("Indisponibilité")
    await session.delete(u)
    await session.commit()


async def schedule_alerts(session: AsyncSession, assignments: list[dict[str, Any]]) -> list[str]:
    """Pour l'écran Planning du client : tâches du planning enregistré qui tombent désormais sur une
    indisponibilité déclarée APRÈS le calcul. Le planning n'est jamais modifié en silence."""
    ids = {a["freelancer_id"] for a in assignments}
    if not ids:
        return []
    profiles = {p.id: p for p in (await session.scalars(
        select(FreelancerProfile).where(FreelancerProfile.id.in_(ids))
        .options(selectinload(FreelancerProfile.unavailability), selectinload(FreelancerProfile.user))
    )).all()}
    alerts = []
    for a in assignments:
        p = profiles.get(a["freelancer_id"])
        if p is None:
            continue
        for u, days in overlap_days(date.fromisoformat(a["start"]), date.fromisoformat(a["end"]), list(p.unavailability)):
            alerts.append(
                f"{p.user.name} a déclaré une indisponibilité ({period_text(u)}) qui tombe pendant {a['ref']} "
                f"« {a['title']} » ({days_text(len(days))}) : recalculez le planning."
            )
    return alerts
