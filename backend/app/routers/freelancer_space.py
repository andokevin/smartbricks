"""Espace freelance (niveau B) : routes réservées aux comptes FREELANCER."""

from typing import Any

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.models import Role, User
from app.schemas import TaskStatusIn, UnavailabilityIn
from app.security import require_role
from app.services import freelancer_space

router = APIRouter(prefix="/me", tags=["espace freelance"])
freelancer_only = require_role(Role.FREELANCER)


@router.get("/freelancer")
async def profile(session: AsyncSession = Depends(get_session), user: User = Depends(freelancer_only)) -> dict[str, Any]:
    """Mon profil : ville, taux, heures par jour, compétences, indisponibilités."""
    return await freelancer_space.profile_view(session, user)


@router.get("/tasks")
async def tasks(session: AsyncSession = Depends(get_session), user: User = Depends(freelancer_only)) -> list[dict[str, Any]]:
    """Mes tâches planifiées, avec leurs dépendances et les alertes d'indisponibilité."""
    return await freelancer_space.my_tasks(session, user)


@router.patch("/tasks/{task_id}")
async def task_status(task_id: int, data: TaskStatusIn, session: AsyncSession = Depends(get_session),
                      user: User = Depends(freelancer_only)) -> dict[str, Any]:
    """Faire avancer une de mes tâches : à faire, en cours, en relecture, terminée."""
    return await freelancer_space.set_status(session, user, task_id, data)


@router.post("/unavailability", status_code=status.HTTP_201_CREATED)
async def add_unavailability(data: UnavailabilityIn, session: AsyncSession = Depends(get_session),
                             user: User = Depends(freelancer_only)) -> dict[str, Any]:
    """Déclarer une indisponibilité ; renvoie les tâches déjà planifiées qu'elle touche."""
    return await freelancer_space.add_unavailability(session, user, data)


@router.delete("/unavailability/{unavailability_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_unavailability(unavailability_id: int, session: AsyncSession = Depends(get_session),
                                user: User = Depends(freelancer_only)) -> None:
    await freelancer_space.delete_unavailability(session, user, unavailability_id)
