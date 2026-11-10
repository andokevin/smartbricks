"""Routes d'administration de la démo."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db import get_session
from app.schemas import ResetDemoOut
from app.seed import reset_demo

router = APIRouter(prefix="/admin", tags=["administration"])


@router.post("/reset-demo", response_model=ResetDemoOut)
async def reset_demo_route(session: AsyncSession = Depends(get_session)) -> ResetDemoOut:
    """Vide la base et la remplit avec les données de démonstration.

    Disponible uniquement en développement (ENVIRONMENT=development ou test).
    Sans authentification : après le reset, les anciens jetons ne correspondent plus à rien.
    """
    if get_settings().environment == "production":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Réinitialisation interdite en production.")
    return await reset_demo(session)
