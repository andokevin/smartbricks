"""Suivi des coûts LLM, contrôle du budget et choix du fournisseur effectif.

RÈGLES
- Chaque appel payant est enregistré dans la table `llm_usage` (tokens d'entrée et de sortie,
  coût en dollars calculé avec les prix par million de tokens lus dans .env).
- Avant chaque utilisation, on additionne les coûts déjà enregistrés. Si le total atteint
  LLM_BUDGET_USD, on bascule AUTOMATIQUEMENT sur le fournisseur simulé et on l'écrit dans les logs.
- Claude n'est jamais activé sans prix renseignés : sans prix, le budget serait incontrôlable.

COÛT D'UN APPEL (en dollars)
    entrée × prix_entrée + écriture cache × 1,25 × prix_entrée + lecture cache × 0,1 × prix_entrée
    + sortie × prix_sortie            (tous les prix sont par million de tokens)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.db import SessionLocal
from app.llm.base import LLMProvider, TokenUsage
from app.llm.mock import MockProvider
from app.models import LlmUsage

logger = logging.getLogger("smartbricks.llm")
_last_fallback_reason: str | None = None


@dataclass(frozen=True)
class Prices:
    input_per_mtok: float
    output_per_mtok: float


def prices_for(provider: str, settings: Settings) -> Prices | None:
    """Prix configurés pour un fournisseur, ou None s'ils ne sont pas renseignés."""
    if provider == "claude":
        pin, pout = settings.claude_price_input_per_mtok, settings.claude_price_output_per_mtok
    elif provider == "gemini":
        pin, pout = settings.gemini_price_input_per_mtok, settings.gemini_price_output_per_mtok
    else:
        return Prices(0.0, 0.0)
    if pin is None or pout is None:
        return None
    return Prices(pin, pout)


def compute_cost_usd(usage: TokenUsage, prices: Prices) -> float:
    per_in = prices.input_per_mtok / 1_000_000
    per_out = prices.output_per_mtok / 1_000_000
    return (
        usage.input_tokens * per_in
        + usage.cache_creation_input_tokens * per_in * 1.25
        + usage.cache_read_input_tokens * per_in * 0.1
        + usage.output_tokens * per_out
    )


async def record_usage(usage: TokenUsage) -> None:
    """Callback donné aux fournisseurs : enregistre l'appel dans sa PROPRE session,
    pour que la consommation soit conservée même si la requête en cours échoue ensuite."""
    settings = get_settings()
    prices = prices_for(usage.provider, settings) or Prices(0.0, 0.0)
    cost = compute_cost_usd(usage, prices)
    async with SessionLocal() as session:
        session.add(
            LlmUsage(
                provider=usage.provider,
                model=usage.model,
                purpose=usage.purpose,
                input_tokens=usage.input_tokens,
                output_tokens=usage.output_tokens,
                cache_creation_input_tokens=usage.cache_creation_input_tokens,
                cache_read_input_tokens=usage.cache_read_input_tokens,
                cost_usd=cost,
            )
        )
        await session.commit()
    logger.info(
        "Appel %s (%s, %s) : %d tokens en entrée, %d en sortie, %.6f $",
        usage.provider, usage.model, usage.purpose, usage.input_tokens, usage.output_tokens, cost,
    )


async def total_spent_usd(session: AsyncSession) -> float:
    return float(await session.scalar(select(func.coalesce(func.sum(LlmUsage.cost_usd), 0.0))) or 0.0)


async def get_provider(session: AsyncSession, settings: Settings | None = None) -> LLMProvider:
    """Fournisseur à utiliser maintenant, en appliquant les garde-fous de configuration et de budget."""
    settings = settings or get_settings()
    wanted = settings.llm_provider
    if wanted == "mock":
        return MockProvider()

    def fallback(reason: str) -> LLMProvider:
        global _last_fallback_reason
        if reason != _last_fallback_reason:  # un seul message par changement de situation
            logger.warning("Copilote : passage automatique en mode mock — %s", reason)
            _last_fallback_reason = reason
        return MockProvider(fallback_reason=reason)

    key = settings.anthropic_api_key if wanted == "claude" else settings.gemini_api_key
    if not key:
        return fallback(f"aucune clé d'API {wanted} dans .env.")
    if wanted == "claude" and prices_for("claude", settings) is None:
        return fallback(
            "prix de Claude non renseignés (CLAUDE_PRICE_INPUT_PER_MTOK, CLAUDE_PRICE_OUTPUT_PER_MTOK) : "
            "le budget ne pourrait pas être contrôlé."
        )
    spent = await total_spent_usd(session)
    if spent >= settings.llm_budget_usd:
        return fallback(f"budget LLM atteint ({spent:.4f} $ dépensés pour {settings.llm_budget_usd:.2f} $ autorisés).")

    if wanted == "claude":
        from app.llm.claude import ClaudeProvider

        return ClaudeProvider(settings, on_usage=record_usage)
    from app.llm.gemini import GeminiProvider

    return GeminiProvider(settings, on_usage=record_usage)


async def usage_summary(session: AsyncSession, settings: Settings | None = None, last: int = 20) -> dict[str, Any]:
    """Résumé de la consommation pour GET /admin/llm-usage."""
    settings = settings or get_settings()
    provider = await get_provider(session, settings)
    spent = await total_spent_usd(session)
    totals = (
        await session.execute(
            select(
                func.count(LlmUsage.id),
                func.coalesce(func.sum(LlmUsage.input_tokens), 0),
                func.coalesce(func.sum(LlmUsage.output_tokens), 0),
            )
        )
    ).one()
    by_model = (
        await session.execute(
            select(
                LlmUsage.provider,
                LlmUsage.model,
                func.count(LlmUsage.id),
                func.sum(LlmUsage.input_tokens),
                func.sum(LlmUsage.output_tokens),
                func.sum(LlmUsage.cost_usd),
            ).group_by(LlmUsage.provider, LlmUsage.model)
        )
    ).all()
    recent = (await session.scalars(select(LlmUsage).order_by(LlmUsage.id.desc()).limit(last))).all()
    claude_prices = prices_for("claude", settings)
    return {
        "configured_provider": settings.llm_provider,
        "effective_provider": provider.name,
        "fallback_reason": provider.fallback_reason,
        "budget_usd": settings.llm_budget_usd,
        "spent_usd": round(spent, 6),
        "remaining_usd": round(max(0.0, settings.llm_budget_usd - spent), 6),
        "calls": totals[0],
        "input_tokens": int(totals[1]),
        "output_tokens": int(totals[2]),
        "claude": {
            "model": settings.claude_model,
            "max_tokens": settings.claude_max_tokens,
            "effort": settings.claude_effort,
            "price_input_per_mtok": claude_prices.input_per_mtok if claude_prices else None,
            "price_output_per_mtok": claude_prices.output_per_mtok if claude_prices else None,
        },
        "by_model": [
            {
                "provider": p, "model": m, "calls": n, "input_tokens": int(i or 0),
                "output_tokens": int(o or 0), "cost_usd": round(float(c or 0), 6),
            }
            for p, m, n, i, o, c in by_model
        ],
        "recent_calls": [
            {
                "at": u.created_at.isoformat(), "provider": u.provider, "model": u.model, "purpose": u.purpose,
                "input_tokens": u.input_tokens, "output_tokens": u.output_tokens, "cost_usd": round(u.cost_usd, 6),
            }
            for u in recent
        ],
    }
