"""Configuration de l'application, lue depuis les variables d'environnement ou le fichier .env.

Le fichier .env est cherché dans backend/ puis à la racine du projet,
pour que l'on puisse lancer uvicorn ou pytest depuis backend/.
Une variable présente mais vide (« CLAUDE_PRICE_INPUT_PER_MTOK= ») est ignorée :
c'est la valeur par défaut ci-dessous qui s'applique.
"""

from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
        env_ignore_empty=True,
    )

    database_url: str = "postgresql+asyncpg://smartbricks:smartbricks@localhost:5435/smartbricks"
    # Au moins 32 octets pour HS256 (RFC 7518) ; à remplacer en production.
    jwt_secret: str = "dev-secret-smartbricks-a-changer-en-production"
    jwt_expire_minutes: int = 60 * 24

    # ------------------------------------------------------------------ copilote LLM
    # « mock » par défaut, pour que la démo marche sans clé ni réseau.
    llm_provider: Literal["mock", "gemini", "claude"] = "mock"
    # Budget total en dollars pour les fournisseurs payants ; au-delà, retour automatique au mock.
    llm_budget_usd: float = 4.0

    anthropic_api_key: str = ""
    claude_model: str = "claude-haiku-5-5"  # le Haiku le plus récent
    claude_max_tokens: int = 8000  # plafond de tokens générés par appel
    claude_effort: Literal["low", "medium", "high"] = "low"  # profondeur de réflexion (coût)
    # Prix en dollars par million de tokens, à renseigner dans .env (sinon Claude reste désactivé).
    claude_price_input_per_mtok: float | None = None
    claude_price_output_per_mtok: float | None = None

    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.5-flash"
    gemini_max_tokens: int = 8000
    gemini_price_input_per_mtok: float | None = None
    gemini_price_output_per_mtok: float | None = None

    environment: Literal["development", "production", "test"] = "development"


@lru_cache
def get_settings() -> Settings:
    """Renvoie la configuration (mise en cache : lue une seule fois)."""
    return Settings()
