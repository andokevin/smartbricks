"""Connexion asynchrone à PostgreSQL avec SQLAlchemy 2.

- `engine` : le moteur de connexion (pool de connexions asyncpg).
- `SessionLocal` : fabrique de sessions.
- `get_session` : dépendance FastAPI qui ouvre une session par requête et la ferme ensuite.
"""

from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.config import get_settings

engine = create_async_engine(get_settings().database_url, pool_pre_ping=True)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False)


class Base(DeclarativeBase):
    """Classe mère de tous les modèles (tables) SQLAlchemy."""


async def get_session() -> AsyncIterator[AsyncSession]:
    async with SessionLocal() as session:
        yield session
