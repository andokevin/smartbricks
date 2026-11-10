"""Tests du copilote avec le fournisseur simulé (aucune clé, aucun réseau)."""

import copy
from datetime import date
from typing import Any

import pytest

from app import demo_data
from app.llm.base import LLMError, Message, Purpose
from app.llm.draft import Draft
from app.llm.mock import MockProvider, template_explanation
from app.services.copilot import (
    DraftError,
    converse,
    explain,
    extract_draft,
    match_name,
    unknown_numbers,
    validate_draft,
)

TODAY = date(2026, 11, 11)
SKILLS = list(demo_data.SKILLS)
CITIES = [c[0] for c in demo_data.CITIES]


def msg(role: str, content: str) -> Message:
    return {"role": role, "content": content}  # type: ignore[typeddict-item]


# --------------------------------------------------------------------------- dialogue simulé


async def test_dialogue_une_question_puis_brouillon() -> None:
    mock = MockProvider(today=TODAY)
    history = [msg("user", demo_data.DEMO_DESCRIPTION)]
    first = await converse(mock, history)
    assert not first.ready and "livraison à domicile" in first.reply  # une question de précision

    history += [msg("assistant", first.reply), msg("user", "Oui, la livraison à domicile est importante.")]
    second = await converse(mock, history)
    assert second.ready and "[BROUILLON" not in second.reply  # marqueur retiré du texte affiché


async def test_dialogue_demande_ce_qui_manque() -> None:
    mock = MockProvider(today=TODAY)
    turn = await converse(mock, [msg("user", "Je veux un site pour vendre mes vêtements en ligne avec MVola.")])
    assert "budget" in turn.reply.lower()


# --------------------------------------------------------------------------- extraction


async def demo_history(answer: str = "Oui") -> list[Message]:
    mock = MockProvider(today=TODAY)
    history = [msg("user", demo_data.DEMO_DESCRIPTION)]
    history.append(msg("assistant", (await converse(mock, history)).reply))
    history.append(msg("user", answer))
    return history


async def test_extraction_simulee_produit_un_json_valide() -> None:
    result = await extract_draft(MockProvider(today=TODAY), await demo_history(), SKILLS, CITIES, TODAY)
    d = result.draft
    assert isinstance(d, Draft) and result.attempts == 1
    assert len(d.features) == 14 and len(d.tasks) == 30
    assert sum(f.is_mandatory for f in d.features) == 3
    assert d.project.budget_mga == 6_000_000
    assert d.project.deadline == date(2027, 1, 8)  # lundi 16/11/2026 + 8 semaines − 3 jours
    assert d.sites == ["Antananarivo", "Antsirabe", "Toamasina", "Fianarantsoa"]
    assert all(t.required_skill in SKILLS for t in d.tasks)


async def test_reponse_non_retire_la_livraison() -> None:
    result = await extract_draft(MockProvider(today=TODAY), await demo_history("Non, pas besoin."), SKILLS, CITIES, TODAY)
    assert "F9" not in {f.ref for f in result.draft.features}
    assert len(result.draft.tasks) == 28


def _demo_raw() -> dict[str, Any]:
    return copy.deepcopy(demo_data.demo_draft(date(2026, 11, 16)))


def test_dependance_cyclique_detectee_et_retiree() -> None:
    raw = _demo_raw()
    task = {t["ref"]: t for t in raw["tasks"]}
    task["T3"]["depends_on"] = ["T5"]  # T5 → T2 → T3 → T5 : cycle
    draft, warnings = validate_draft(raw, SKILLS, CITIES)
    assert any("circulaire" in w and "T3 dépend de T5" in w for w in warnings)
    t3 = next(t for t in draft.tasks if t.ref == "T3")
    assert t3.depends_on == []
    # Fonctionnalités aussi : F1 dépend de F3, alors que F3 → F2 → F1.
    raw = _demo_raw()
    raw["features"][0]["depends_on"] = ["F3"]
    _, warnings = validate_draft(raw, SKILLS, CITIES)
    assert any("F1 dépend de F3" in w for w in warnings)


def test_correspondance_approchee() -> None:
    assert match_name("react.js", SKILLS, {"reactjs": "React"}) == "React"
    assert match_name("NodeJS", SKILLS, {}) == "Node.js"
    assert match_name("Postgre SQL", SKILLS, {}) == "PostgreSQL"
    assert match_name("Tamatave", CITIES, {"tamatave": "Toamasina"}) == "Toamasina"
    assert match_name("Fianarantsoaa", CITIES, {}) == "Fianarantsoa"
    assert match_name("Paris", CITIES, {}) is None


def test_competences_et_villes_normalisees() -> None:
    raw = _demo_raw()
    raw["tasks"][0]["required_skill"] = "design"
    raw["tasks"][21]["on_site_city"] = "Tana"
    raw["project"]["base_city"] = "Atlantis"
    draft, warnings = validate_draft(raw, SKILLS, CITIES)
    assert draft.tasks[0].required_skill == "UI/UX"
    assert draft.tasks[21].on_site_city == "Antananarivo"
    assert draft.project.base_city is None
    assert any("Atlantis" in w for w in warnings)


def test_competence_inconnue_refusee() -> None:
    raw = _demo_raw()
    raw["tasks"][0]["required_skill"] = "Cobol"
    with pytest.raises(DraftError, match="Cobol"):
        validate_draft(raw, SKILLS, CITIES)


def test_heures_strictement_positives() -> None:
    raw = _demo_raw()
    raw["tasks"][0]["estimated_hours"] = 0
    with pytest.raises(DraftError, match="estimated_hours"):
        validate_draft(raw, SKILLS, CITIES)


class FlakyProvider(MockProvider):
    """Renvoie d'abord un JSON invalide, puis (ou non) un JSON correct."""

    def __init__(self, recover: bool) -> None:
        super().__init__(today=TODAY)
        self.recover = recover
        self.calls: list[list[Message]] = []

    async def extract(self, messages: list[Message], json_schema: dict[str, Any], system: str) -> dict[str, Any]:
        self.calls.append(messages)
        if len(self.calls) == 1 or not self.recover:
            bad = _demo_raw()
            del bad["project"]["budget_mga"]
            return bad
        return _demo_raw()


async def test_une_seule_nouvelle_tentative_avec_l_erreur() -> None:
    ok = FlakyProvider(recover=True)
    result = await extract_draft(ok, await demo_history(), SKILLS, CITIES, TODAY)
    assert result.attempts == 2
    assert "budget_mga" in ok.calls[1][-1]["content"]  # l'erreur est renvoyée au LLM

    ko = FlakyProvider(recover=False)
    with pytest.raises(DraftError, match="deux tentatives"):
        await extract_draft(ko, await demo_history(), SKILLS, CITIES, TODAY)
    assert len(ko.calls) == 2  # pas de troisième essai


# --------------------------------------------------------------------------- explication

FACTS = {
    "projet": {"titre": "Boutique Soa", "budget_mga": 6_000_000, "date_limite": "2027-01-08"},
    "sprint": {"retenues": ["Catalogue", "Panier"], "cout_mga": 5_541_000, "heures": 136,
               "et_si": ["Avec 600 000 Ar de plus (+10 %), vous ajoutez : Paiement MVola."]},
    "planning": {"statut": "OK", "date_fin": "2026-12-01", "duree_jours": 12},
    "tournee": {"ordre": ["Antananarivo", "Toamasina"], "distance_km": 1286, "cout_mga": 1_542_777},
}


async def test_explication_simulee_sans_chiffre_invente() -> None:
    e = await explain(MockProvider(), FACTS)
    assert not e.replaced and unknown_numbers(e.text, FACTS) == []
    assert "5 541 000 Ar" in e.text and "1286 km" in e.text


class LiarProvider(MockProvider):
    async def chat(self, messages: list[Message], system: str, purpose: Purpose = "chat") -> str:
        return "Votre projet coûtera 7 200 000 Ar et sera prêt en 9 jours."


async def test_chiffre_invente_remplace() -> None:
    e = await explain(LiarProvider(), FACTS)
    assert e.replaced and "7 200 000" in e.unknown_numbers
    assert e.text == template_explanation(FACTS)


def test_nombres_reconnus() -> None:
    assert unknown_numbers("Budget de 6 000 000 Ar, fin le 8 janvier 2027, 136 h.", FACTS) == []
    assert unknown_numbers("Il reste 459 000 Ar.", FACTS) == ["459 000"]


async def test_erreur_llm_propagee() -> None:
    class Broken(MockProvider):
        async def chat(self, messages: list[Message], system: str, purpose: Purpose = "chat") -> str:
            raise LLMError("refus")

    with pytest.raises(LLMError):
        await explain(Broken(), FACTS)
