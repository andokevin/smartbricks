"""Suivi des coûts, budget et fournisseurs payants — SANS appel réseau (clients simulés)."""

import logging
from types import SimpleNamespace
from typing import Any

import pytest
from httpx import AsyncClient
from sqlalchemy import delete

from app.config import Settings
from app.db import SessionLocal
from app.llm.base import TokenUsage
from app.llm.claude import ClaudeProvider
from app.llm.draft import DRAFT_JSON_SCHEMA
from app.llm.mock import MockProvider
from app.models import LlmUsage
from app.services import llm_usage
from app.services.llm_usage import Prices, compute_cost_usd, get_provider

TEST_MODEL = "test-model-pytest"


def settings(**overrides: Any) -> Settings:
    base: dict[str, Any] = {
        "llm_provider": "claude",
        "anthropic_api_key": "sk-ant-test",
        "claude_price_input_per_mtok": 1.0,
        "claude_price_output_per_mtok": 5.0,
        "llm_budget_usd": 4.0,
    }
    return Settings(**{**base, **overrides})


@pytest.fixture
async def clean_usage() -> Any:
    yield
    async with SessionLocal() as s:
        await s.execute(delete(LlmUsage).where(LlmUsage.model == TEST_MODEL))
        await s.commit()


# --------------------------------------------------------------------------- coût


def test_calcul_du_cout() -> None:
    u = TokenUsage("claude", "m", "chat", input_tokens=1_000_000, output_tokens=200_000)
    assert compute_cost_usd(u, Prices(1.0, 5.0)) == pytest.approx(1.0 + 1.0)
    cached = TokenUsage("claude", "m", "chat", 0, 0, cache_creation_input_tokens=1_000_000,
                        cache_read_input_tokens=1_000_000)
    assert compute_cost_usd(cached, Prices(1.0, 5.0)) == pytest.approx(1.25 + 0.1)


# --------------------------------------------------------------------------- choix du fournisseur


async def test_mode_mock_par_defaut() -> None:
    async with SessionLocal() as s:
        p = await get_provider(s, settings(llm_provider="mock"))
    assert isinstance(p, MockProvider) and p.fallback_reason is None


async def test_claude_sans_prix_reste_en_mock(caplog: pytest.LogCaptureFixture) -> None:
    llm_usage._last_fallback_reason = None
    with caplog.at_level(logging.WARNING, logger="smartbricks.llm"):
        async with SessionLocal() as s:
            p = await get_provider(s, settings(claude_price_input_per_mtok=None))
    assert isinstance(p, MockProvider) and "prix" in (p.fallback_reason or "")
    assert "passage automatique en mode mock" in caplog.text


async def test_claude_sans_cle_reste_en_mock() -> None:
    async with SessionLocal() as s:
        p = await get_provider(s, settings(anthropic_api_key=""))
    assert isinstance(p, MockProvider)


async def test_claude_actif_sous_le_budget(clean_usage: None) -> None:
    async with SessionLocal() as s:
        p = await get_provider(s, settings(llm_budget_usd=1_000_000))
    assert isinstance(p, ClaudeProvider) and p.model == "claude-haiku-5-5"


async def test_budget_depasse_bascule_en_mock(clean_usage: None, caplog: pytest.LogCaptureFixture) -> None:
    llm_usage._last_fallback_reason = None
    async with SessionLocal() as s:
        s.add(LlmUsage(provider="claude", model=TEST_MODEL, purpose="chat", input_tokens=1, output_tokens=1,
                       cost_usd=4.5))
        await s.commit()
    with caplog.at_level(logging.WARNING, logger="smartbricks.llm"):
        async with SessionLocal() as s:
            p = await get_provider(s, settings())
    assert isinstance(p, MockProvider)
    assert "budget LLM atteint" in (p.fallback_reason or "")
    assert "budget LLM atteint" in caplog.text


# --------------------------------------------------------------------------- fournisseur Claude (client simulé)


class FakeMessages:
    def __init__(self, text: str, stop_reason: str = "end_turn") -> None:
        self.text, self.stop_reason = text, stop_reason
        self.kwargs: dict[str, Any] = {}

    async def create(self, **kwargs: Any) -> Any:
        self.kwargs = kwargs
        return SimpleNamespace(
            content=[SimpleNamespace(type="text", text=self.text)],
            stop_reason=self.stop_reason,
            usage=SimpleNamespace(input_tokens=1200, output_tokens=300,
                                  cache_creation_input_tokens=None, cache_read_input_tokens=0),
        )


async def test_claude_extraction_et_suivi_des_tokens() -> None:
    seen: list[TokenUsage] = []

    async def on_usage(u: TokenUsage) -> None:
        seen.append(u)

    fake = FakeMessages('{"ok": true}')
    p = ClaudeProvider(settings(claude_max_tokens=3000), on_usage=on_usage, client=SimpleNamespace(messages=fake))
    data = await p.extract([{"role": "user", "content": "bonjour"}], DRAFT_JSON_SCHEMA, "système")

    assert data == {"ok": True}
    assert fake.kwargs["model"] == "claude-haiku-5-5"
    assert fake.kwargs["max_tokens"] == 3000
    assert fake.kwargs["output_config"]["format"] == {"type": "json_schema", "schema": DRAFT_JSON_SCHEMA}
    assert fake.kwargs["system"] == "système"  # consigne séparée des données du client
    assert seen == [TokenUsage("claude", "claude-haiku-5-5", "extract", 1200, 300, 0, 0)]


async def test_claude_reponse_tronquee_mais_comptee() -> None:
    from app.llm.base import LLMError

    seen: list[TokenUsage] = []

    async def on_usage(u: TokenUsage) -> None:
        seen.append(u)

    p = ClaudeProvider(settings(), on_usage=on_usage,
                       client=SimpleNamespace(messages=FakeMessages("{", stop_reason="max_tokens")))
    with pytest.raises(LLMError, match="tronquée"):
        await p.chat([{"role": "user", "content": "x"}], "s")
    assert len(seen) == 1  # facturée, donc comptée


async def test_claude_refus_signale() -> None:
    from app.llm.base import LLMError

    p = ClaudeProvider(settings(), client=SimpleNamespace(messages=FakeMessages("", stop_reason="refusal")))
    with pytest.raises(LLMError, match="refusé"):
        await p.chat([{"role": "user", "content": "x"}], "s")


class SequenceMessages:
    """Client simulé qui renvoie successivement plusieurs textes (un par appel)."""

    def __init__(self, texts: list[str]) -> None:
        self.texts = texts
        self.calls: list[dict[str, Any]] = []

    async def create(self, **kwargs: Any) -> Any:
        self.calls.append(kwargs)
        text = self.texts[min(len(self.calls), len(self.texts)) - 1]
        return SimpleNamespace(content=[SimpleNamespace(type="text", text=text)], stop_reason="end_turn",
                               usage=SimpleNamespace(input_tokens=10, output_tokens=5,
                                                     cache_creation_input_tokens=0, cache_read_input_tokens=0))


async def test_claude_json_invalide_puis_nouvelle_tentative() -> None:
    """Premier JSON illisible → une seule nouvelle tentative, avec l'erreur renvoyée au modèle."""
    import json
    from datetime import date

    from app import demo_data
    from app.services.copilot import extract_draft

    good = json.dumps(demo_data.demo_draft(date(2026, 11, 16)))
    fake = SequenceMessages(["{ceci n'est pas du JSON", good])
    p = ClaudeProvider(settings(), client=SimpleNamespace(messages=fake))
    history = [{"role": "user", "content": demo_data.DEMO_DESCRIPTION}]
    result = await extract_draft(p, history, list(demo_data.SKILLS), [c[0] for c in demo_data.CITIES],  # type: ignore[arg-type]
                                 date(2026, 11, 11))
    assert result.attempts == 2 and len(result.draft.features) == 14
    assert len(fake.calls) == 2
    assert "JSON invalide" in fake.calls[1]["messages"][-1]["content"]


async def test_enregistrement_de_la_consommation(clean_usage: None, monkeypatch: pytest.MonkeyPatch) -> None:
    """record_usage écrit une ligne dans llm_usage avec le coût calculé à partir des prix de .env."""
    from sqlalchemy import select

    monkeypatch.setattr(llm_usage, "get_settings", lambda: settings(claude_price_input_per_mtok=1.0,
                                                                    claude_price_output_per_mtok=5.0))
    await llm_usage.record_usage(TokenUsage("claude", TEST_MODEL, "extract", 1_000_000, 100_000))
    async with SessionLocal() as s:
        row = await s.scalar(select(LlmUsage).where(LlmUsage.model == TEST_MODEL))
    assert row is not None and row.purpose == "extract"
    assert row.cost_usd == pytest.approx(1.0 + 0.5)


# --------------------------------------------------------------------------- route d'administration


async def test_route_llm_usage(client: AsyncClient, demo: dict[str, object]) -> None:
    async def token(email: str, pwd: str) -> str:
        r = await client.post("/api/v1/auth/login", json={"email": email, "password": pwd})
        return str(r.json()["access_token"])

    admin = await token("admin@smartbricks.mg", "admin1234")
    r = await client.get("/api/v1/admin/llm-usage", headers={"Authorization": f"Bearer {admin}"})
    assert r.status_code == 200
    body = r.json()
    assert body["effective_provider"] == "mock"
    assert body["budget_usd"] == 4.0
    assert {"spent_usd", "remaining_usd", "input_tokens", "output_tokens", "recent_calls"} <= body.keys()

    soa = await token("client@smartbricks.mg", "demo1234")
    r = await client.get("/api/v1/admin/llm-usage", headers={"Authorization": f"Bearer {soa}"})
    assert r.status_code == 403
