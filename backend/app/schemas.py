"""Schémas Pydantic v2 : formats d'entrée et de sortie de l'API."""

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models import Role


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
