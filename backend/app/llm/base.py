"""Interface commune des fournisseurs LLM.

Chaque fournisseur sait faire deux choses :
- `chat(messages, system)`            → une réponse en texte libre ;
- `extract(messages, json_schema, system)` → un dictionnaire conforme au schéma JSON.

Les fournisseurs payants signalent leur consommation (tokens) au `UsageCallback` reçu
à la construction ; le calcul du coût et le contrôle du budget sont faits ailleurs
(services/llm_usage.py), pour que les fournisseurs restent simples.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any, Literal, TypedDict


class Message(TypedDict):
    role: Literal["user", "assistant"]
    content: str


Purpose = Literal["chat", "extract", "explain"]


@dataclass(frozen=True)
class TokenUsage:
    provider: str
    model: str
    purpose: Purpose
    input_tokens: int
    output_tokens: int
    cache_creation_input_tokens: int = 0
    cache_read_input_tokens: int = 0


UsageCallback = Callable[[TokenUsage], Awaitable[None]]


class LLMError(Exception):
    """Réponse inexploitable (refus, réponse tronquée, JSON invalide…)."""


class LLMUnavailable(LLMError):
    """Le service est injoignable (réseau, quota, clé invalide…)."""


class LLMProvider(ABC):
    name: str = "base"
    model: str = ""
    # Si le fournisseur effectif n'est pas celui demandé (budget atteint…), la raison est ici.
    fallback_reason: str | None = None

    @abstractmethod
    async def chat(self, messages: list[Message], system: str, purpose: Purpose = "chat") -> str: ...

    @abstractmethod
    async def extract(self, messages: list[Message], json_schema: dict[str, Any], system: str) -> dict[str, Any]: ...
