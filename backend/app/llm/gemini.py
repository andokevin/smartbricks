"""Fournisseur Gemini (SDK officiel `google-genai`).

- Extraction : `response_mime_type="application/json"` et `response_json_schema` = schéma attendu.
- Les tokens (`usage_metadata`) sont rapportés au suivi des coûts ; les tokens de réflexion
  (`thoughts_token_count`) sont facturés comme des tokens de sortie, on les ajoute donc à la sortie.
- Le rôle « assistant » s'appelle « model » chez Gemini.
"""

from __future__ import annotations

import json
from typing import Any

from app.config import Settings
from app.llm.base import LLMError, LLMProvider, LLMUnavailable, Message, Purpose, TokenUsage, UsageCallback


class GeminiProvider(LLMProvider):
    name = "gemini"

    def __init__(self, settings: Settings, on_usage: UsageCallback | None = None, client: Any = None) -> None:
        self.model = settings.gemini_model
        self.max_tokens = settings.gemini_max_tokens
        self.on_usage = on_usage
        if client is None:
            from google import genai  # import tardif : inutile en mode mock

            client = genai.Client(api_key=settings.gemini_api_key or None)
        self.client = client

    async def _generate(
        self, purpose: Purpose, system: str, messages: list[Message], json_schema: dict[str, Any] | None = None
    ) -> str:
        from google.genai import errors, types

        config: dict[str, Any] = {"system_instruction": system, "max_output_tokens": self.max_tokens}
        if json_schema is not None:
            config["response_mime_type"] = "application/json"
            config["response_json_schema"] = json_schema
        contents = [
            types.Content(role="model" if m["role"] == "assistant" else "user", parts=[types.Part(text=m["content"])])
            for m in messages
        ]
        try:
            response = await self.client.aio.models.generate_content(
                model=self.model, contents=contents, config=types.GenerateContentConfig(**config)
            )
        except errors.APIError as e:
            raise LLMUnavailable(f"Gemini : erreur {getattr(e, 'code', '?')}.") from e

        meta = response.usage_metadata
        if self.on_usage is not None and meta is not None:
            await self.on_usage(
                TokenUsage(
                    provider=self.name,
                    model=self.model,
                    purpose=purpose,
                    # Comme chez Claude, input_tokens = tokens d'entrée NON servis par le cache.
                    input_tokens=(meta.prompt_token_count or 0) - (meta.cached_content_token_count or 0),
                    output_tokens=(meta.candidates_token_count or 0) + (meta.thoughts_token_count or 0),
                    cache_read_input_tokens=meta.cached_content_token_count or 0,
                )
            )
        if not response.text:
            raise LLMError("Gemini n'a renvoyé aucun texte (réponse bloquée ou tronquée).")
        return response.text

    async def chat(self, messages: list[Message], system: str, purpose: Purpose = "chat") -> str:
        return await self._generate(purpose, system, messages)

    async def extract(self, messages: list[Message], json_schema: dict[str, Any], system: str) -> dict[str, Any]:
        text = await self._generate("extract", system, messages, json_schema)
        try:
            data = json.loads(text)
        except json.JSONDecodeError as e:
            raise LLMError(f"JSON invalide : {e}") from e
        if not isinstance(data, dict):
            raise LLMError("Le JSON renvoyé n'est pas un objet.")
        return data
