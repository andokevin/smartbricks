"""Configuration de l'application, lue depuis les variables d'environnement ou le fichier .env.

Le fichier .env est cherché dans backend/ puis à la racine du projet,
pour que l'on puisse lancer uvicorn ou pytest depuis backend/.
"""

from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: str = "postgresql+asyncpg://smartbricks:smartbricks@localhost:5435/smartbricks"
    # Au moins 32 octets pour HS256 (RFC 7518) ; à remplacer en production.
    jwt_secret: str = "dev-secret-smartbricks-a-changer-en-production"
    jwt_expire_minutes: int = 60 * 24

    # Fournisseur LLM : « mock » par défaut, pour que la démo marche sans clé ni réseau.
    llm_provider: Literal["mock", "gemini", "claude"] = "mock"
    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.5-flash"
    anthropic_api_key: str = ""
    claude_model: str = "claude-haiku-5-5"

    environment: Literal["development", "production", "test"] = "development"


@lru_cache
def get_settings() -> Settings:
    """Renvoie la configuration (mise en cache : lue une seule fois)."""
    return Settings()
