"""Fournisseur Claude (API Anthropic, SDK officiel `anthropic`).

- Modèle configurable (CLAUDE_MODEL, par défaut le Haiku le plus récent : claude-haiku-5-5).
- `max_tokens` plafonné (CLAUDE_MAX_TOKENS) et réflexion au niveau « low » (CLAUDE_EFFORT)
  pour limiter les coûts : la réflexion du modèle est facturée comme des tokens de sortie.
- Extraction : SORTIES STRUCTURÉES (`output_config.format` = schéma JSON). Le JSON renvoyé est
  garanti conforme au schéma. On n'utilise pas un outil forcé (`tool_choice`), refusé (erreur 400)
  par plusieurs modèles Claude récents.
- Chaque réponse rapporte ses tokens (`response.usage`) au callback de suivi des coûts,
  y compris quand la réponse est ensuite rejetée (refus, troncature) : elle est facturée.
"""

from __future__ import annotations

import json
from typing import Any

from app.config import Settings
from app.llm.base import LLMError, LLMProvider, LLMUnavailable, Message, Purpose, TokenUsage, UsageCallback


class ClaudeProvider(LLMProvider):
    name = "claude"

    def __init__(self, settings: Settings, on_usage: UsageCallback | None = None, client: Any = None) -> None:
        self.model = settings.claude_model
        self.max_tokens = settings.claude_max_tokens
        self.effort = settings.claude_effort
        self.on_usage = on_usage
        if client is None:
            from anthropic import AsyncAnthropic  # import tardif : inutile en mode mock

            client = AsyncAnthropic(api_key=settings.anthropic_api_key or None, timeout=60.0, max_retries=2)
        self.client = client

    async def _create(
        self, purpose: Purpose, system: str, messages: list[Message], output_format: dict[str, Any] | None = None
    ) -> str:
        import anthropic

        output_config: dict[str, Any] = {"effort": self.effort}
        if output_format is not None:
            output_config["format"] = output_format
        try:
            response = await self.client.messages.create(
                model=self.model,
                max_tokens=self.max_tokens,
                system=system,
                messages=[{"role": m["role"], "content": m["content"]} for m in messages],
                output_config=output_config,
            )
        except anthropic.RateLimitError as e:
            raise LLMUnavailable("Claude : trop de requêtes, réessayez dans un instant.") from e
        except anthropic.AuthenticationError as e:
            raise LLMUnavailable("Claude : clé d'API invalide.") from e
        except anthropic.APIStatusError as e:
            raise LLMUnavailable(f"Claude : erreur {e.status_code}.") from e
        except anthropic.APIConnectionError as e:
            raise LLMUnavailable("Claude : service injoignable (réseau).") from e

        await self._report(purpose, response.usage)

        if response.stop_reason == "refusal":
            raise LLMError("Claude a refusé de répondre à cette demande.")
        if response.stop_reason == "max_tokens":
            raise LLMError(f"Réponse tronquée (plafond de {self.max_tokens} tokens atteint).")
        return "".join(block.text for block in response.content if block.type == "text")

    async def _report(self, purpose: Purpose, usage: Any) -> None:
        if self.on_usage is None or usage is None:
            return
        await self.on_usage(
            TokenUsage(
                provider=self.name,
                model=self.model,
                purpose=purpose,
                input_tokens=usage.input_tokens or 0,
                output_tokens=usage.output_tokens or 0,
                cache_creation_input_tokens=usage.cache_creation_input_tokens or 0,
                cache_read_input_tokens=usage.cache_read_input_tokens or 0,
            )
        )

    async def chat(self, messages: list[Message], system: str, purpose: Purpose = "chat") -> str:
        return await self._create(purpose, system, messages)

    async def extract(self, messages: list[Message], json_schema: dict[str, Any], system: str) -> dict[str, Any]:
        text = await self._create("extract", system, messages, {"type": "json_schema", "schema": json_schema})
        try:
            data = json.loads(text)
        except json.JSONDecodeError as e:
            raise LLMError(f"JSON invalide : {e}") from e
        if not isinstance(data, dict):
            raise LLMError("Le JSON renvoyé n'est pas un objet.")
        return data
