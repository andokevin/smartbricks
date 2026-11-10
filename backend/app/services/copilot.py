"""Copilote (module A, n°33) : dialogue, extraction contrôlée et explication vérifiée.

Ce service ne dépend pas de la base : il reçoit un fournisseur LLM et les listes de compétences
et de villes connues. Les routes (phase 5) se chargent de lire et d'écrire en base.

LES CONTRÔLES SANS LLM APRÈS L'EXTRACTION
    1. validation du schéma par Pydantic (types, bornes, champs obligatoires) ;
    2. références cohérentes (pas de doublon, chaque tâche appartient à une fonctionnalité existante) ;
    3. compétences et villes reconnues par CORRESPONDANCE APPROCHÉE avec la base
       (« react.js » → React, « Tamatave » → Toamasina) ;
    4. dépendances inconnues retirées ; CYCLES détectés par le tri topologique de Kahn
       et cassés en retirant l'arête la moins justifiée (algorithms/dependencies.py) ;
    5. si le JSON est invalide : UNE seule nouvelle tentative, avec le message d'erreur.

L'EXPLICATION VÉRIFIÉE
    Le LLM ne reçoit que les résultats calculés. On vérifie ensuite que chaque nombre de son texte
    figure dans ces données ; sinon le texte est remplacé par une explication construite
    automatiquement à partir des données (aucun chiffre inventé ne peut atteindre le client).
"""

from __future__ import annotations

import difflib
import json
import re
import unicodedata
from dataclasses import dataclass, field
from datetime import date
from typing import Any

from pydantic import ValidationError

from app.algorithms.dependencies import break_cycles
from app.llm.base import LLMError, LLMProvider, Message
from app.llm.draft import DRAFT_JSON_SCHEMA, Draft
from app.llm.mock import template_explanation
from app.llm.prompts import CHAT_SYSTEM, EXPLAIN_SYSTEM, READY_MARKER, extract_system

# =========================================================================== correspondance approchée

SKILL_ALIASES = {
    "react": "React", "reactjs": "React", "nextjs": "React",
    "node": "Node.js", "nodejs": "Node.js", "express": "Node.js", "backend": "Node.js",
    "python": "FastAPI", "api": "Node.js",
    "postgres": "PostgreSQL", "postgresql": "PostgreSQL", "sql": "PostgreSQL", "basededonnees": "PostgreSQL",
    "mobile": "Flutter", "android": "Flutter",
    "design": "UI/UX", "ux": "UI/UX", "ui": "UI/UX", "maquettes": "UI/UX", "designer": "UI/UX",
    "devops": "DevOps", "deploiement": "DevOps", "hebergement": "DevOps",
    "qa": "Tests/QA", "tests": "Tests/QA", "test": "Tests/QA",
    "reseau": "Réseau", "network": "Réseau", "reseaux": "Réseau",
    "maintenance": "Maintenance matériel", "materiel": "Maintenance matériel",
    "securite": "Sécurité", "security": "Sécurité", "cybersecurite": "Sécurité",
}
CITY_ALIASES = {
    "tana": "Antananarivo", "tananarive": "Antananarivo",
    "tamatave": "Toamasina", "majunga": "Mahajanga", "tulear": "Toliara",
    "diego": "Antsiranana", "diegosuarez": "Antsiranana", "fianar": "Fianarantsoa",
    "hellville": "Nosy Be",
}


def normalize_name(text: str) -> str:
    """« Node.js » → « nodejs », « Réseau » → « reseau » : minuscules, sans accents ni ponctuation."""
    plain = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]", "", plain)


def match_name(raw: str | None, known: list[str], aliases: dict[str, str], cutoff: float = 0.75) -> str | None:
    """Nom officiel le plus proche de `raw`, ou None.

    Ordre : égalité exacte (après normalisation) → alias → similarité de chaînes (difflib,
    ratio ≥ cutoff, fondé sur la plus longue sous-séquence commune).
    """
    if not raw:
        return None
    key = normalize_name(raw)
    by_key = {normalize_name(k): k for k in known}
    if key in by_key:
        return by_key[key]
    if key in aliases and aliases[key] in known:
        return aliases[key]
    close = difflib.get_close_matches(key, list(by_key), n=1, cutoff=cutoff)
    return by_key[close[0]] if close else None


# =========================================================================== dialogue


@dataclass
class CopilotTurn:
    reply: str
    ready: bool  # True quand le copilote estime avoir assez d'informations pour le brouillon
    provider: str


async def converse(provider: LLMProvider, history: list[Message]) -> CopilotTurn:
    """Une réponse du copilote. `history` alterne client / copilote et se termine par le client."""
    text = (await provider.chat(history, CHAT_SYSTEM)).strip()
    ready = text.startswith(READY_MARKER)
    return CopilotTurn(reply=text.removeprefix(READY_MARKER).strip(), ready=ready, provider=provider.name)


# =========================================================================== extraction


class DraftError(Exception):
    """Brouillon inexploitable (message lisible, renvoyé au LLM lors de la nouvelle tentative)."""


@dataclass
class DraftResult:
    draft: Draft
    warnings: list[str] = field(default_factory=list)
    attempts: int = 1
    provider: str = ""


def transcript(history: list[Message]) -> str:
    lines = [f"{'Client' if m['role'] == 'user' else 'Copilote'} : {m['content']}" for m in history]
    return "<conversation>\n" + "\n".join(lines) + "\n</conversation>"


def _readable(e: ValidationError) -> str:
    return "; ".join(f"{'.'.join(str(p) for p in err['loc'])} : {err['msg']}" for err in e.errors()[:10])


def validate_draft(raw: dict[str, Any], skills: list[str], cities: list[str]) -> tuple[Draft, list[str]]:
    """Contrôles sans LLM. Lève DraftError si le brouillon est inexploitable ; sinon le renvoie
    normalisé, avec la liste des corrections faites automatiquement."""
    try:
        draft = Draft.model_validate(raw)
    except ValidationError as e:
        raise DraftError(f"Schéma non respecté : {_readable(e)}") from e
    warnings: list[str] = []

    # --- références
    f_refs = [f.ref for f in draft.features]
    t_refs = [t.ref for t in draft.tasks]
    for refs, kind in ((f_refs, "fonctionnalité"), (t_refs, "tâche")):
        dup = sorted({r for r in refs if refs.count(r) > 1})
        if dup:
            raise DraftError(f"Références de {kind} en double : {', '.join(dup)}.")
    orphans = [t.ref for t in draft.tasks if t.feature_ref not in f_refs]
    if orphans:
        raise DraftError(f"Tâches rattachées à une fonctionnalité inexistante : {', '.join(orphans)}.")

    # --- compétences (obligatoires : une compétence inconnue rend la tâche inplanifiable)
    unknown_skills = []
    for t in draft.tasks:
        found = match_name(t.required_skill, skills, SKILL_ALIASES)
        if found is None:
            unknown_skills.append(f"{t.ref} ({t.required_skill})")
        elif found != t.required_skill:
            warnings.append(f"Compétence « {t.required_skill} » de {t.ref} reconnue comme « {found} ».")
            t.required_skill = found
    if unknown_skills:
        raise DraftError(
            f"Compétences inconnues : {', '.join(unknown_skills)}. Compétences possibles : {', '.join(skills)}."
        )

    # --- villes (facultatives : une ville inconnue est retirée avec un avertissement)
    def city(raw_name: str | None, where: str) -> str | None:
        if raw_name is None:
            return None
        found = match_name(raw_name, cities, CITY_ALIASES)
        if found is None:
            warnings.append(f"Ville « {raw_name} » ({where}) inconnue : ignorée.")
        elif found != raw_name:
            warnings.append(f"Ville « {raw_name} » ({where}) reconnue comme « {found} ».")
        return found

    draft.project.base_city = city(draft.project.base_city, "ville de base")
    for t in draft.tasks:
        t.on_site_city = city(t.on_site_city, f"tâche {t.ref}")
    sites = [c for c in (city(s, "sites") for s in draft.sites) if c]
    sites += [t.on_site_city for t in draft.tasks if t.on_site_city]
    draft.sites = list(dict.fromkeys(sites))  # sans doublon, ordre conservé

    # --- dépendances : inconnues retirées, puis cycles cassés
    for items, refs, kind in ((draft.features, f_refs, "fonctionnalité"), (draft.tasks, t_refs, "tâche")):
        for it in items:
            bad = [d for d in it.depends_on if d not in refs]
            if bad:
                warnings.append(f"Dépendances inconnues de la {kind} {it.ref} retirées : {', '.join(bad)}.")
                it.depends_on = [d for d in it.depends_on if d in refs]
        clean, removed = break_cycles(refs, {it.ref: it.depends_on for it in items})
        for u, v in removed:
            warnings.append(
                f"Dépendance circulaire détectée : la dépendance « {u} dépend de {v} » a été retirée "
                f"({v} est déclarée après {u})."
            )
        for it in items:
            it.depends_on = clean[it.ref]
    return draft, warnings


async def extract_draft(
    provider: LLMProvider, history: list[Message], skills: list[str], cities: list[str], today: date
) -> DraftResult:
    """Extraction du brouillon, contrôlée ; une seule nouvelle tentative si elle échoue."""
    system = extract_system(today.isoformat(), skills, cities)
    messages: list[Message] = [{"role": "user", "content": transcript(history)}]
    raw: dict[str, Any] | None = None
    error = ""
    for attempt in (1, 2):
        try:
            raw = await provider.extract(messages, DRAFT_JSON_SCHEMA, system)
            draft, warnings = validate_draft(raw, skills, cities)
            return DraftResult(draft, warnings, attempts=attempt, provider=provider.name)
        except (DraftError, LLMError) as e:
            error = str(e)
            # Nouvelle tentative : on montre au LLM sa réponse et l'erreur précise.
            messages = [
                messages[0],
                {"role": "assistant", "content": json.dumps(raw, ensure_ascii=False) if raw else "(réponse invalide)"},
                {"role": "user", "content": f"Ce JSON est invalide : {error} Corrige-le et renvoie le JSON complet."},
            ]
    raise DraftError(f"Brouillon invalide après deux tentatives : {error}")


# =========================================================================== explication


@dataclass
class Explanation:
    text: str
    provider: str
    verified: bool  # True si tous les nombres du texte figurent dans les données
    replaced: bool  # True si le texte du LLM a été remplacé par l'explication automatique
    unknown_numbers: list[str] = field(default_factory=list)


_NUMBER = re.compile(r"\d+(?:[\s  ]\d{3})*(?:[.,]\d+)?")


def _canonical(token: str) -> str:
    """« 6 000 000 » → « 6000000 », « 3,50 » → « 3.5 », « 08 » → « 8 »."""
    s = re.sub(r"[\s  ]", "", token).replace(",", ".")
    try:
        x = float(s)
    except ValueError:
        return s
    return str(int(x)) if x == int(x) else f"{x:g}"


def allowed_numbers(data: Any) -> set[str]:
    """Tous les nombres présents dans les données, sous leurs écritures acceptables."""
    found: set[str] = {"1"}  # « 1 » sert à tout (« sprint 1 », « une tâche »)

    def add_value(x: float) -> None:
        for r in (0, 1, 2):
            found.add(_canonical(str(round(x, r))))
        if 0 < x <= 1:  # taux exprimé en pourcentage
            found.add(_canonical(str(round(x * 100))))

    def walk(v: Any) -> None:
        if isinstance(v, bool):
            return
        if isinstance(v, (int, float)):
            add_value(float(v))
        elif isinstance(v, str):
            for tok in _NUMBER.findall(v):
                found.add(_canonical(tok))
            for tok in re.findall(r"\d+", v):  # parties de dates « 2027-01-08 »
                found.add(_canonical(tok))
        elif isinstance(v, dict):
            for item in v.values():
                walk(item)
        elif isinstance(v, (list, tuple)):
            for item in v:
                walk(item)

    walk(data)
    return found


def unknown_numbers(text: str, data: Any) -> list[str]:
    allowed = allowed_numbers(data)
    return [tok.strip() for tok in _NUMBER.findall(text) if _canonical(tok) not in allowed]


async def explain(provider: LLMProvider, facts: dict[str, Any], question: str | None = None) -> Explanation:
    payload = f"<donnees>{json.dumps(facts, ensure_ascii=False)}</donnees>"
    if question:
        payload += f"\n<question_client>{question}</question_client>"
    text = (await provider.chat([{"role": "user", "content": payload}], EXPLAIN_SYSTEM, purpose="explain")).strip()
    invented = unknown_numbers(text, facts)
    if invented:
        return Explanation(template_explanation(facts), provider.name, verified=True, replaced=True,
                           unknown_numbers=invented)
    return Explanation(text, provider.name, verified=True, replaced=False)
