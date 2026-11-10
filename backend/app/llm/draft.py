"""Brouillon de projet extrait par le copilote : modèles Pydantic et schéma JSON envoyé au LLM.

Deux niveaux de garantie :
1. le schéma JSON (`DRAFT_JSON_SCHEMA`) contraint la forme de la sortie du LLM
   (Claude : sorties structurées ; Gemini : response_json_schema) ;
2. les modèles Pydantic revalident tout côté serveur, y compris les bornes
   (valeur 1–100, heures > 0, niveau 1–5) que les schémas de sortie ne garantissent pas toujours.
"""

from datetime import date
from typing import Any, Literal

from pydantic import BaseModel, Field

ReqTypeLit = Literal["FUNCTIONAL", "TECHNICAL", "SECURITY", "COMPLIANCE"]


class DraftProject(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str = ""
    budget_mga: int = Field(ge=0)
    budget_hours: int | None = Field(default=None, gt=0)
    deadline: date
    base_city: str | None = None


class DraftFeature(BaseModel):
    ref: str = Field(min_length=1, max_length=20)
    title: str = Field(min_length=1, max_length=200)
    description: str = ""
    req_type: ReqTypeLit = "FUNCTIONAL"
    business_value: int = Field(ge=1, le=100)
    estimated_hours: int = Field(gt=0)
    is_mandatory: bool = False
    depends_on: list[str] = Field(default_factory=list)


class DraftTask(BaseModel):
    ref: str = Field(min_length=1, max_length=20)
    feature_ref: str
    title: str = Field(min_length=1, max_length=200)
    required_skill: str
    min_level: int = Field(default=1, ge=1, le=5)
    estimated_hours: int = Field(gt=0)
    depends_on: list[str] = Field(default_factory=list)
    on_site_city: str | None = None


class Draft(BaseModel):
    project: DraftProject
    features: list[DraftFeature] = Field(min_length=1)
    tasks: list[DraftTask] = Field(min_length=1)
    sites: list[str] = Field(default_factory=list)


def _obj(properties: dict[str, Any]) -> dict[str, Any]:
    """Objet JSON strict : toutes les propriétés obligatoires, aucune propriété en plus."""
    return {
        "type": "object",
        "properties": properties,
        "required": list(properties),
        "additionalProperties": False,
    }


_STR = {"type": "string"}
_INT = {"type": "integer"}
_STR_LIST = {"type": "array", "items": _STR}

# Écrit à la main (sans $ref) pour être accepté tel quel par Claude et par Gemini.
DRAFT_JSON_SCHEMA: dict[str, Any] = _obj(
    {
        "project": _obj(
            {
                "title": _STR,
                "description": _STR,
                "budget_mga": _INT,
                "budget_hours": {"type": ["integer", "null"]},
                "deadline": {"type": "string", "description": "Date AAAA-MM-JJ"},
                "base_city": {"type": ["string", "null"]},
            }
        ),
        "features": {
            "type": "array",
            "items": _obj(
                {
                    "ref": _STR,
                    "title": _STR,
                    "description": _STR,
                    "req_type": {"type": "string", "enum": ["FUNCTIONAL", "TECHNICAL", "SECURITY", "COMPLIANCE"]},
                    "business_value": _INT,
                    "estimated_hours": _INT,
                    "is_mandatory": {"type": "boolean"},
                    "depends_on": _STR_LIST,
                }
            ),
        },
        "tasks": {
            "type": "array",
            "items": _obj(
                {
                    "ref": _STR,
                    "feature_ref": _STR,
                    "title": _STR,
                    "required_skill": _STR,
                    "min_level": _INT,
                    "estimated_hours": _INT,
                    "depends_on": _STR_LIST,
                    "on_site_city": {"type": ["string", "null"]},
                }
            ),
        },
        "sites": _STR_LIST,
    }
)
