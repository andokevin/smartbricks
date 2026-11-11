"""Benchmark exact contre approché (modules B, D, E) — réservé à l'administrateur."""

from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.models import Role, User
from app.security import require_role
from app.services.benchmark import run_benchmark
from app.services.project_data import get_project

router = APIRouter(tags=["benchmark"])


@router.get("/benchmark")
async def benchmark(
    project_id: int | None = None,
    session: AsyncSession = Depends(get_session),
    admin: User = Depends(require_role(Role.ADMIN)),
) -> dict[str, Any]:
    """Mesure valeur, écart et temps des méthodes exactes et approchées : sur le projet choisi
    (s'il est donné) et sur des instances aléatoires reproductibles. Quelques secondes de calcul."""
    project = await get_project(session, project_id, admin) if project_id is not None else None
    return await run_benchmark(session, project)
