"""Modèles SQLAlchemy : les tables de la base SmartBricks.

Choix de conception :
- Les énumérations (rôle, statut…) sont stockées en VARCHAR avec une contrainte CHECK
  (`native_enum=False`) : plus simple à faire évoluer avec Alembic qu'un type ENUM PostgreSQL.
- Les montants sont des entiers en Ariary (Ar).
- Les dates de planning sont des `date` (jours ouvrés), pas des horodatages.
- `project_sites` est une extension de la spécification : la liste des villes à visiter
  pour le projet (sortie « sites » du copilote), utilisée par la tournée (module E).
"""

from __future__ import annotations

import enum
from datetime import date, datetime
from typing import Any

from sqlalchemy import (
    ARRAY,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


def _enum(cls: type[enum.Enum], name: str) -> Enum:
    """Énumération stockée en texte, avec contrainte CHECK nommée."""
    return Enum(
        cls,
        name=name,
        native_enum=False,
        create_constraint=True,
        length=20,
        values_callable=lambda e: [m.value for m in e],
    )


# --------------------------------------------------------------------------- énumérations


class Role(str, enum.Enum):
    CLIENT = "CLIENT"
    FREELANCER = "FREELANCER"
    ADMIN = "ADMIN"


class ProjectStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    SCOPED = "SCOPED"
    TEAM_SELECTED = "TEAM_SELECTED"
    PLANNED = "PLANNED"


class ReqType(str, enum.Enum):
    FUNCTIONAL = "FUNCTIONAL"
    TECHNICAL = "TECHNICAL"
    SECURITY = "SECURITY"
    COMPLIANCE = "COMPLIANCE"


class TaskStatus(str, enum.Enum):
    BACKLOG = "BACKLOG"
    TODO = "TODO"
    IN_PROGRESS = "IN_PROGRESS"
    REVIEW = "REVIEW"
    DONE = "DONE"
    OVERDUE = "OVERDUE"


# --------------------------------------------------------------------------- référentiels


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[Role] = mapped_column(_enum(Role, "user_role"))
    organization_name: Mapped[str | None] = mapped_column(String(200))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    freelancer_profile: Mapped[FreelancerProfile | None] = relationship(back_populates="user")


class Skill(Base):
    __tablename__ = "skills"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(80), unique=True)


class City(Base):
    __tablename__ = "cities"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(80), unique=True)
    latitude: Mapped[float] = mapped_column(Float)
    longitude: Mapped[float] = mapped_column(Float)


# --------------------------------------------------------------------------- freelances


class FreelancerProfile(Base):
    __tablename__ = "freelancer_profiles"
    __table_args__ = (
        CheckConstraint("rating BETWEEN 0 AND 5", name="ck_rating"),
        CheckConstraint("on_time_rate BETWEEN 0 AND 1", name="ck_on_time_rate"),
        CheckConstraint("hours_per_day > 0 AND hours_per_day <= 12", name="ck_hours_per_day"),
        CheckConstraint("hourly_rate_mga > 0", name="ck_hourly_rate"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True)
    city_id: Mapped[int] = mapped_column(ForeignKey("cities.id"))
    hourly_rate_mga: Mapped[int] = mapped_column(Integer)
    rating: Mapped[float] = mapped_column(Float)
    completed_projects: Mapped[int] = mapped_column(Integer, default=0)
    on_time_rate: Mapped[float] = mapped_column(Float)
    hours_per_day: Mapped[int] = mapped_column(Integer)
    bio: Mapped[str | None] = mapped_column(Text)

    user: Mapped[User] = relationship(back_populates="freelancer_profile")
    city: Mapped[City] = relationship()
    skills: Mapped[list[FreelancerSkill]] = relationship(cascade="all, delete-orphan")
    unavailability: Mapped[list[FreelancerUnavailability]] = relationship(cascade="all, delete-orphan")


class FreelancerSkill(Base):
    __tablename__ = "freelancer_skills"
    __table_args__ = (CheckConstraint("level BETWEEN 1 AND 5", name="ck_level"),)

    freelancer_id: Mapped[int] = mapped_column(
        ForeignKey("freelancer_profiles.id", ondelete="CASCADE"), primary_key=True
    )
    skill_id: Mapped[int] = mapped_column(ForeignKey("skills.id"), primary_key=True)
    level: Mapped[int] = mapped_column(Integer)

    skill: Mapped[Skill] = relationship()


class FreelancerUnavailability(Base):
    __tablename__ = "freelancer_unavailability"
    __table_args__ = (CheckConstraint("end_date >= start_date", name="ck_unavailability_dates"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    freelancer_id: Mapped[int] = mapped_column(ForeignKey("freelancer_profiles.id", ondelete="CASCADE"))
    start_date: Mapped[date] = mapped_column(Date)
    end_date: Mapped[date] = mapped_column(Date)
    reason: Mapped[str | None] = mapped_column(String(200))


# --------------------------------------------------------------------------- projets


class Project(Base):
    __tablename__ = "projects"
    __table_args__ = (
        CheckConstraint("budget_mga >= 0", name="ck_budget_mga"),
        CheckConstraint("budget_hours >= 0", name="ck_budget_hours"),
        CheckConstraint("target_deadline > start_date", name="ck_project_dates"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    client_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str | None] = mapped_column(Text)
    budget_mga: Mapped[int] = mapped_column(Integer)
    budget_hours: Mapped[int] = mapped_column(Integer)
    start_date: Mapped[date] = mapped_column(Date)
    target_deadline: Mapped[date] = mapped_column(Date)
    base_city_id: Mapped[int | None] = mapped_column(ForeignKey("cities.id"))
    status: Mapped[ProjectStatus] = mapped_column(
        _enum(ProjectStatus, "project_status"), default=ProjectStatus.DRAFT
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    base_city: Mapped[City | None] = relationship()
    features: Mapped[list[Feature]] = relationship(
        back_populates="project", cascade="all, delete-orphan", order_by="Feature.id"
    )
    tasks: Mapped[list[Task]] = relationship(
        back_populates="project", cascade="all, delete-orphan", order_by="Task.id"
    )


class ProjectSite(Base):
    """Ville où le projet demande une intervention physique (extension de la spécification)."""

    __tablename__ = "project_sites"

    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), primary_key=True)
    city_id: Mapped[int] = mapped_column(ForeignKey("cities.id"), primary_key=True)
    position: Mapped[int] = mapped_column(Integer, default=0)  # ordre saisi par le client

    city: Mapped[City] = relationship()


class Feature(Base):
    """Fonctionnalité (exigence du cahier des charges) : un objet du sac à dos."""

    __tablename__ = "features"
    __table_args__ = (
        CheckConstraint("business_value BETWEEN 1 AND 100", name="ck_business_value"),
        CheckConstraint("estimated_hours > 0", name="ck_feature_hours"),
        CheckConstraint("estimated_cost_mga >= 0", name="ck_feature_cost"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    ref: Mapped[str] = mapped_column(String(20))  # « F1 », « F2 »… (référence du brouillon)
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str | None] = mapped_column(Text)
    req_type: Mapped[ReqType] = mapped_column(_enum(ReqType, "req_type"))
    business_value: Mapped[int] = mapped_column(Integer)
    estimated_hours: Mapped[int] = mapped_column(Integer)
    estimated_cost_mga: Mapped[int] = mapped_column(Integer, default=0)
    is_mandatory: Mapped[bool] = mapped_column(Boolean, default=False)
    depends_on_feature_ids: Mapped[list[int]] = mapped_column(ARRAY(Integer), default=list)
    selected_for_sprint: Mapped[bool] = mapped_column(Boolean, default=False)

    project: Mapped[Project] = relationship(back_populates="features")


class Task(Base):
    __tablename__ = "tasks"
    __table_args__ = (
        CheckConstraint("estimated_hours > 0", name="ck_task_hours"),
        CheckConstraint("min_level BETWEEN 1 AND 5", name="ck_task_min_level"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    feature_id: Mapped[int] = mapped_column(ForeignKey("features.id", ondelete="CASCADE"))
    ref: Mapped[str] = mapped_column(String(20))  # « T1 », « T2 »…
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str | None] = mapped_column(Text)
    required_skill_id: Mapped[int] = mapped_column(ForeignKey("skills.id"))
    min_level: Mapped[int] = mapped_column(Integer, default=1)
    estimated_hours: Mapped[int] = mapped_column(Integer)
    on_site_city_id: Mapped[int | None] = mapped_column(ForeignKey("cities.id"))
    status: Mapped[TaskStatus] = mapped_column(_enum(TaskStatus, "task_status"), default=TaskStatus.BACKLOG)
    priority: Mapped[int] = mapped_column(Integer, default=0)
    assigned_freelancer_id: Mapped[int | None] = mapped_column(
        ForeignKey("freelancer_profiles.id", ondelete="SET NULL")
    )
    start_date: Mapped[date | None] = mapped_column(Date)
    end_date: Mapped[date | None] = mapped_column(Date)
    deadline: Mapped[date | None] = mapped_column(Date)

    project: Mapped[Project] = relationship(back_populates="tasks")
    feature: Mapped[Feature] = relationship()
    required_skill: Mapped[Skill] = relationship()
    on_site_city: Mapped[City | None] = relationship()


class TaskDependency(Base):
    """B dépend de A : la tâche `task_id` ne peut commencer qu'après la fin de `depends_on_task_id`."""

    __tablename__ = "task_dependencies"
    __table_args__ = (CheckConstraint("task_id <> depends_on_task_id", name="ck_no_self_dependency"),)

    task_id: Mapped[int] = mapped_column(ForeignKey("tasks.id", ondelete="CASCADE"), primary_key=True)
    depends_on_task_id: Mapped[int] = mapped_column(ForeignKey("tasks.id", ondelete="CASCADE"), primary_key=True)


class ProjectTeam(Base):
    __tablename__ = "project_team"

    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), primary_key=True)
    freelancer_id: Mapped[int] = mapped_column(
        ForeignKey("freelancer_profiles.id", ondelete="CASCADE"), primary_key=True
    )


# --------------------------------------------------------------------------- historiques de calcul


class ScheduleRun(Base):
    __tablename__ = "schedule_runs"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    method: Mapped[str] = mapped_column(String(80))
    status: Mapped[str] = mapped_column(String(30))
    makespan_days: Mapped[int | None] = mapped_column(Integer)
    report: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class TourRun(Base):
    __tablename__ = "tour_runs"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    freelancer_id: Mapped[int | None] = mapped_column(ForeignKey("freelancer_profiles.id", ondelete="SET NULL"))
    method: Mapped[str] = mapped_column(String(80))
    order: Mapped[list[Any]] = mapped_column(JSONB, default=list)
    distance_km: Mapped[float] = mapped_column(Float)
    cost_mga: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


# --------------------------------------------------------------------------- copilote


class AssistantConversation(Base):
    __tablename__ = "assistant_conversations"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    project_id: Mapped[int | None] = mapped_column(ForeignKey("projects.id", ondelete="SET NULL"))
    draft: Mapped[dict[str, Any] | None] = mapped_column(JSONB)  # brouillon extrait, quand il est prêt
    status: Mapped[str] = mapped_column(String(20), default="OPEN")  # OPEN | DRAFT_READY | CONFIRMED
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    messages: Mapped[list[AssistantMessage]] = relationship(
        cascade="all, delete-orphan", order_by="AssistantMessage.id"
    )


class LlmUsage(Base):
    """Un appel à un fournisseur LLM payant : tokens consommés et coût calculé.

    Cette table n'est PAS vidée par reset-demo : le budget doit survivre aux réinitialisations.
    """

    __tablename__ = "llm_usage"

    id: Mapped[int] = mapped_column(primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
    provider: Mapped[str] = mapped_column(String(20))
    model: Mapped[str] = mapped_column(String(80))
    purpose: Mapped[str] = mapped_column(String(20))  # chat | extract | explain
    input_tokens: Mapped[int] = mapped_column(Integer, default=0)
    output_tokens: Mapped[int] = mapped_column(Integer, default=0)
    cache_creation_input_tokens: Mapped[int] = mapped_column(Integer, default=0)
    cache_read_input_tokens: Mapped[int] = mapped_column(Integer, default=0)
    cost_usd: Mapped[float] = mapped_column(Float, default=0.0)


class AssistantMessage(Base):
    __tablename__ = "assistant_messages"

    id: Mapped[int] = mapped_column(primary_key=True)
    conversation_id: Mapped[int] = mapped_column(
        ForeignKey("assistant_conversations.id", ondelete="CASCADE"), index=True
    )
    role: Mapped[str] = mapped_column(String(20))  # « user » ou « assistant »
    content: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
