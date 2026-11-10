"""Fournisseur LLM simulé : réponses DÉTERMINISTES, sans clé d'API ni réseau.

Il suit exactement le même protocole qu'un vrai LLM (questions une par une, marqueur
[BROUILLON_PRET], JSON conforme au schéma, explication à partir des seules données),
ce qui permet de tester toute la chaîne et de faire la démonstration hors ligne.

Il ne « comprend » qu'un projet : Boutique Soa (voir demo_data.py). Il lit quand même dans
la conversation le budget, le délai et la réponse sur la livraison à domicile, pour que la
démonstration réagisse à ce que tape le client.
"""

from __future__ import annotations

import json
import re
import unicodedata
from datetime import date, timedelta
from typing import Any

from app import demo_data
from app.algorithms.formatting import format_ar, format_date_fr
from app.llm.base import LLMProvider, Message, Purpose
from app.llm.prompts import READY_MARKER

DELIVERY_QUESTION = (
    "Merci, c'est très clair ! Une question avant de préparer votre projet : "
    "faut-il prévoir la livraison à domicile pour vos clients (choix de la livraison et suivi du livreur) ?"
)
_CITY_WORDS = ["tana", "antananarivo", "toamasina", "tamatave", "antsirabe", "fianarantsoa", "fianar",
               "mahajanga", "majunga", "toliara", "antsiranana", "diego", "morondava", "manakara",
               "ambositra", "ambatondrazaka", "nosy be"]


def _plain(text: str) -> str:
    """Minuscules sans accents, pour des recherches de mots-clés simples."""
    return unicodedata.normalize("NFKD", text.lower()).encode("ascii", "ignore").decode()


def _parse_budget(text: str) -> int | None:
    """« 6 millions d'ariary », « 6 000 000 Ar », « 6M Ar » → 6000000."""
    t = _plain(text)
    m = re.search(r"(\d+(?:[.,]\d+)?)\s*(?:millions?|m)\b", t)
    if m:
        return int(float(m.group(1).replace(",", ".")) * 1_000_000)
    m = re.search(r"(\d[\d\s.]{3,})\s*(?:ar\b|ariary)", t)
    if m:
        return int(re.sub(r"[^\d]", "", m.group(1)))
    return None


def _parse_weeks(text: str) -> int | None:
    t = _plain(text)
    if m := re.search(r"(\d+)\s*semaines?", t):
        return int(m.group(1))
    if m := re.search(r"(\d+)\s*mois", t):
        return int(m.group(1)) * 4
    return None


def _user_text(messages: list[Message]) -> str:
    return " ".join(m["content"] for m in messages if m["role"] == "user")


class MockProvider(LLMProvider):
    name = "mock"
    model = "mock-boutique-soa"

    def __init__(self, fallback_reason: str | None = None, today: date | None = None) -> None:
        self.fallback_reason = fallback_reason
        self.today = today

    # ------------------------------------------------------------------ dialogue
    async def chat(self, messages: list[Message], system: str, purpose: Purpose = "chat") -> str:
        if purpose == "explain":
            facts = _facts_from_messages(messages)
            return template_explanation(facts)

        text = _plain(_user_text(messages))
        asked = " ".join(m["content"] for m in messages if m["role"] == "assistant")
        if len(text) < 30:
            return "Bonjour ! Décrivez-moi votre projet : que voulez-vous que votre site ou votre application fasse ?"
        if _parse_budget(text) is None:
            return "Quel budget avez-vous prévu pour ce projet, en Ariary ?"
        if _parse_weeks(text) is None and not re.search(r"\d{4}-\d{2}-\d{2}", text):
            return "Pour quand le projet doit-il être prêt (par exemple « dans 8 semaines ») ?"
        if not any(c in text for c in _CITY_WORDS):
            return "Dans quelle ville se trouve votre entreprise ?"
        if "livraison a domicile" not in _plain(asked):
            return DELIVERY_QUESTION
        return (
            f"{READY_MARKER} Parfait. Je résume : une boutique en ligne avec paiement MVola, une application "
            "mobile de suivi des commandes, et le réseau de vos agences. Je prépare le brouillon : vous "
            "pourrez corriger chaque estimation avant de lancer les calculs."
        )

    # ------------------------------------------------------------------ extraction
    async def extract(self, messages: list[Message], json_schema: dict[str, Any], system: str) -> dict[str, Any]:
        text = _user_text(messages)
        start = demo_data.next_monday(self.today or date.today())
        draft = demo_data.demo_draft(start)

        if (budget := _parse_budget(text)) is not None:
            draft["project"]["budget_mga"] = budget
        if (weeks := _parse_weeks(text)) is not None:
            draft["project"]["deadline"] = (start + timedelta(weeks=weeks) - timedelta(days=3)).isoformat()

        # Réponse à la question sur la livraison : « non » → on retire la fonctionnalité F9.
        answer = _answer_after(messages, "livraison a domicile")
        if answer is not None and re.match(r"\s*(non|pas)\b", _plain(answer)):
            draft["features"] = [f for f in draft["features"] if f["ref"] != "F9"]
            draft["tasks"] = [t for t in draft["tasks"] if t["feature_ref"] != "F9"]
        return draft


def _answer_after(messages: list[Message], question_words: str) -> str | None:
    """Réponse du client au message du copilote contenant `question_words`.

    Fonctionne aussi quand la conversation est transmise en un seul bloc <conversation>.
    """
    for k, m in enumerate(messages):
        if m["role"] == "assistant" and question_words in _plain(m["content"]) and k + 1 < len(messages):
            return messages[k + 1]["content"]
    blob = _plain("\n".join(m["content"] for m in messages))  # tout en minuscules sans accents
    idx = blob.find(question_words)
    if idx >= 0:
        rest = blob[idx:]
        if (pos := rest.find("client :")) >= 0:
            return rest[pos + len("client :") :].split("\n")[0]
    return None


def _facts_from_messages(messages: list[Message]) -> dict[str, Any]:
    blob = messages[-1]["content"] if messages else ""
    m = re.search(r"<donnees>(.*)</donnees>", blob, re.S)
    try:
        return json.loads(m.group(1)) if m else {}
    except json.JSONDecodeError:
        return {}


def template_explanation(facts: dict[str, Any]) -> str:
    """Explication construite UNIQUEMENT avec les valeurs présentes dans `facts`.

    Sert de réponse au fournisseur simulé, et de repli quand un vrai LLM cite un chiffre inventé.
    """
    parts: list[str] = []
    p = facts.get("projet", {})
    if p:
        parts.append(
            f"Votre projet « {p.get('titre', 'sans titre')} » dispose d'un budget de "
            f"{format_ar(p.get('budget_mga', 0))} et doit être prêt pour le {format_date_fr(p.get('date_limite'))}."
        )
    s = facts.get("sprint", {})
    if s:
        kept = ", ".join(s.get("retenues", [])) or "aucune fonctionnalité"
        txt = (
            f"Pour le premier sprint, nous avons retenu : {kept}. Cette combinaison coûte "
            f"{format_ar(s.get('cout_mga', 0))} pour {s.get('heures', 0)} heures de travail : c'est celle qui "
            "apporte le plus de valeur sans dépasser votre budget ni vos heures."
        )
        if s.get("et_si"):
            txt += " " + s["et_si"][0]
        parts.append(txt)
    team = facts.get("equipe", [])
    if team:
        people = ", ".join(f"{m['nom']} ({', '.join(m.get('competences', []))})" for m in team)
        parts.append(f"L'équipe proposée : {people}.")
    pl = facts.get("planning", {})
    if pl:
        if pl.get("statut") == "OK":
            parts.append(
                f"Le planning tient toutes les contraintes (dépendances, compétences, congés, date limite) : "
                f"le travail se termine le {format_date_fr(pl.get('date_fin'))}, en {pl.get('duree_jours')} jours ouvrés."
            )
        else:
            parts.append("Le planning n'est pas réalisable en l'état : " + " ".join(pl.get("diagnostics", [])))
    t = facts.get("tournee", {})
    if t:
        parts.append(
            f"Pour les interventions sur place, l'ordre conseillé est : {' → '.join(t.get('ordre', []))}, "
            f"soit {t.get('distance_km')} km de route et {format_ar(t.get('cout_mga', 0))} de frais de trajet."
        )
    if not parts:
        return "Aucun résultat n'a encore été calculé pour ce projet."
    return "\n\n".join(parts)
