"""Point d'entrée de l'API SmartBricks.

Lancement : `uvicorn app.main:app --reload` depuis le dossier backend/.
Documentation interactive : http://localhost:8000/docs
"""

import logging

from fastapi import APIRouter, Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db import get_session
from app.errors import AppError
from app.routers import admin, assistant, auth, benchmark, catalog, projects

# Journaux de l'application (consommation du LLM, bascule en mode mock…) visibles dans la console.
logging.basicConfig(level=logging.WARNING, format="%(asctime)s %(levelname)s [%(name)s] %(message)s")
logging.getLogger("smartbricks").setLevel(logging.INFO)

app = FastAPI(
    title="SmartBricks API",
    description=(
        "Du besoin flou du client au projet informatique réaliste : "
        "copilote IA et algorithmes d'optimisation."
    ),
    version="0.1.0",
)

# Le frontend Vite tourne sur le port 5173 ; il passe normalement par le proxy de Vite,
# mais on autorise aussi les appels directs en développement.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

api = APIRouter(prefix="/api/v1")


@api.get("/health", tags=["système"], summary="État de l'API et de la base")
async def health(session: AsyncSession = Depends(get_session)) -> dict[str, str]:
    """Vérifie que l'API répond et que PostgreSQL est joignable."""
    await session.execute(text("SELECT 1"))
    return {
        "status": "ok",
        "database": "ok",
        "llm_provider": get_settings().llm_provider,
        "environment": get_settings().environment,
    }


@app.exception_handler(AppError)
async def app_error_handler(_request: Request, exc: AppError) -> JSONResponse:
    """Les erreurs métier des services deviennent des réponses HTTP avec un message en français."""
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})


api.include_router(auth.router)
api.include_router(assistant.router)
api.include_router(projects.router)
api.include_router(catalog.router)
api.include_router(benchmark.router)
api.include_router(admin.router)

app.include_router(api)
