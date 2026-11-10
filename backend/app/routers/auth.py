"""Inscription, connexion et profil courant."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.models import Role, User
from app.schemas import LoginIn, RegisterIn, TokenOut, UserOut
from app.security import create_access_token, get_current_user, hash_password, verify_password

router = APIRouter(prefix="/auth", tags=["authentification"])


@router.post("/register", response_model=TokenOut, status_code=status.HTTP_201_CREATED)
async def register(data: RegisterIn, session: AsyncSession = Depends(get_session)) -> TokenOut:
    """Crée un compte client ou freelance et renvoie directement un jeton."""
    if data.role == Role.ADMIN:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Impossible de créer un compte administrateur.")
    email = data.email.lower()
    existing = await session.scalar(select(User).where(func.lower(User.email) == email))
    if existing is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "Un compte existe déjà avec cet email.")

    user = User(
        name=data.name,
        email=email,
        password_hash=hash_password(data.password),
        role=data.role,
        organization_name=data.organization_name,
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return TokenOut(access_token=create_access_token(user), user=UserOut.model_validate(user))


@router.post("/login", response_model=TokenOut)
async def login(data: LoginIn, session: AsyncSession = Depends(get_session)) -> TokenOut:
    """Vérifie l'email et le mot de passe, puis renvoie un jeton JWT."""
    user = await session.scalar(select(User).where(func.lower(User.email) == data.email.lower()))
    # Même message dans les deux cas : on ne révèle pas si l'email existe.
    if user is None or not verify_password(data.password, user.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Email ou mot de passe incorrect.")
    return TokenOut(access_token=create_access_token(user), user=UserOut.model_validate(user))


@router.get("/me", response_model=UserOut)
async def me(user: User = Depends(get_current_user)) -> UserOut:
    """Renvoie l'utilisateur connecté (utile pour tester le jeton depuis /docs)."""
    return UserOut.model_validate(user)
