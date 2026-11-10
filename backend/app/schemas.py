"""Schémas Pydantic v2 : formats d'entrée et de sortie de l'API (visibles dans /docs)."""

from datetime import date
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.llm.draft import Draft
from app.models import ProjectStatus, Role

# =========================================================================== authentification


class RegisterIn(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    # On ne peut pas s'inscrire soi-même comme administrateur.
    role: Role = Role.CLIENT
    organization_name: str | None = Field(default=None, max_length=200)


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    email: str
    role: Role
    organization_name: str | None


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


class ResetDemoOut(BaseModel):
    """Résumé de ce que le seed a créé."""

    cities: int
    skills: int
    freelancers: int
    users: int
    demo_project_id: int
    features: int
    tasks: int
    accounts: dict[str, str]


# =========================================================================== module A — copilote


class ChatIn(BaseModel):
    conversation_id: int | None = Field(default=None, description="Vide pour commencer une nouvelle conversation.")
    message: str = Field(min_length=1, max_length=4000)


class ChatOut(BaseModel):
    conversation_id: int
    reply: str
    ready: bool = Field(description="True quand le brouillon a été extrait.")
    draft: Draft | None = None
    warnings: list[str] = []
    provider: str
    fallback_reason: str | None = None


class ConfirmIn(BaseModel):
    conversation_id: int
    draft: Draft | None = Field(default=None, description="Brouillon corrigé par le client (sinon celui extrait).")


class ConfirmOut(BaseModel):
    project_id: int
    title: str
    features: int
    tasks: int
    sites: list[str]
    warnings: list[str] = []


class MessageOut(BaseModel):
    role: str
    content: str


class ConversationOut(BaseModel):
    id: int
    status: str
    project_id: int | None
    messages: list[MessageOut]
    draft: Draft | None = None
    warnings: list[str] = []


class ExplainIn(BaseModel):
    question: str | None = Field(default=None, max_length=1000)


class ExplainOut(BaseModel):
    text: str
    provider: str
    replaced: bool = Field(description="True si le texte du LLM citait un chiffre absent des données.")
    unknown_numbers: list[str] = []
    fallback_reason: str | None = None


# =========================================================================== projets


class FeatureOut(BaseModel):
    id: int
    ref: str
    title: str
    description: str | None
    req_type: str
    business_value: int
    estimated_hours: int
    estimated_cost_mga: int
    is_mandatory: bool
    depends_on: list[str]
    selected_for_sprint: bool


class TaskOut(BaseModel):
    id: int
    ref: str
    feature_ref: str
    title: str
    required_skill: str
    min_level: int
    estimated_hours: int
    depends_on: list[str]
    on_site_city: str | None
    status: str
    assigned_freelancer_id: int | None
    start_date: date | None
    end_date: date | None


class ProjectSummary(BaseModel):
    id: int
    title: str
    status: ProjectStatus
    budget_mga: int
    budget_hours: int
    start_date: date
    target_deadline: date
    base_city: str | None


class ProjectOut(ProjectSummary):
    description: str | None
    features: list[FeatureOut]
    tasks: list[TaskOut]
    sites: list[str]
    team: list[int]


class FeaturePatch(BaseModel):
    business_value: int | None = Field(default=None, ge=1, le=100)
    estimated_hours: int | None = Field(default=None, gt=0)
    is_mandatory: bool | None = None


# =========================================================================== module B — cadrage


class MethodOut(BaseModel):
    problem: str
    method: str
    exact: bool
    reason: str
    course_number: int


class ScopeFeature(BaseModel):
    id: int
    ref: str
    title: str
    business_value: int
    estimated_hours: int
    estimated_cost_mga: int
    is_mandatory: bool
    depends_on: list[str]
    selected: bool
    reason: str | None


class WhatIfOut(BaseModel):
    increase_pct: int
    extra_budget_mga: int
    new_budget_mga: int
    added: list[str]
    removed: list[str]
    value_gain: int
    message: str


class ScopeOut(BaseModel):
    feasible: bool
    message: str
    method: MethodOut
    optimal: bool
    nodes: int
    elapsed_ms: float
    total_value: int
    total_cost_mga: int
    total_hours: int
    budget_mga: int
    budget_hours: int
    budget_usage: float = Field(description="Part du budget utilisée (0 à 1).")
    hours_usage: float
    missing_cost_mga: int = 0
    missing_hours: int = 0
    features: list[ScopeFeature]
    what_if: list[WhatIfOut]
    verification: list[str] = Field(description="Violations détectées par la vérification indépendante (vide = OK).")


# =========================================================================== module C — matching


class TeamIn(BaseModel):
    freelancer_ids: list[int] | None = None
    suggested: bool = False
    preset: str = Field(default="Équilibré", description="Préréglage utilisé pour l'équipe suggérée.")


class TeamMemberOut(BaseModel):
    id: int
    name: str
    city: str
    hourly_rate_mga: int
    hours_per_day: int
    skills: dict[str, int]


class TeamOut(BaseModel):
    project_id: int
    members: list[TeamMemberOut]
    warnings: list[str]
    absorbable: bool


# =========================================================================== module D — planning


class SolveIn(BaseModel):
    scenario: Literal["normal", "impossible"] = Field(
        default="normal", description="« impossible » : date limite ramenée à 3 semaines (non enregistrée)."
    )
    deadline: date | None = Field(default=None, description="Autre date limite à tester (non enregistrée).")


# =========================================================================== module E — tournée


class TourIn(BaseModel):
    freelancer_id: int | None = Field(default=None, description="Technicien qui part de sa ville (sinon déduit).")
    closed: bool = True
    cost_per_km: int = Field(default=1_200, gt=0)


AnyDict = dict[str, Any]
