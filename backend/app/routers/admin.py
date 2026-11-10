"""Routes d'administration : réinitialisation de la démo et consommation du LLM."""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db import get_session
from app.models import Role, User
from app.schemas import ResetDemoOut
from app.security import require_role
from app.seed import reset_demo
from app.services.llm_usage import usage_summary

router = APIRouter(prefix="/admin", tags=["administration"])


@router.post("/reset-demo", response_model=ResetDemoOut)
async def reset_demo_route(session: AsyncSession = Depends(get_session)) -> ResetDemoOut:
    """Vide la base et la remplit avec les données de démonstration.

    Disponible uniquement en développement (ENVIRONMENT=development ou test).
    Sans authentification : après le reset, les anciens jetons ne correspondent plus à rien.
    La consommation du LLM (table llm_usage) est conservée.
    """
    if get_settings().environment == "production":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Réinitialisation interdite en production.")
    return await reset_demo(session)


@router.get("/llm-usage")
async def llm_usage(
    session: AsyncSession = Depends(get_session),
    _admin: User = Depends(require_role(Role.ADMIN)),
) -> dict[str, Any]:
    """Consommation du LLM : fournisseur effectif, budget, dépense, tokens, derniers appels.

    Réservé à l'administrateur (admin@smartbricks.mg / admin1234 dans la démo).
    """
    return await usage_summary(session)
