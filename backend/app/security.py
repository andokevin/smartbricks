"""Sécurité : hachage des mots de passe (argon2) et jetons d'accès (JWT).

- argon2 est l'algorithme recommandé pour hacher les mots de passe : lent et gourmand
  en mémoire exprès, avec un sel aléatoire, ce qui rend les attaques par force brute coûteuses.
- Le JWT contient l'identifiant de l'utilisateur (`sub`) et son rôle, signé avec JWT_SECRET
  (HS256) et limité dans le temps (`exp`).
"""

from collections.abc import Awaitable, Callable
from datetime import UTC, datetime, timedelta

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerificationError
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db import get_session
from app.models import Role, User

_hasher = PasswordHasher()
_bearer = HTTPBearer(auto_error=False)
ALGORITHM = "HS256"


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return _hasher.verify(password_hash, password)
    except VerificationError:
        return False


def create_access_token(user: User) -> str:
    settings = get_settings()
    now = datetime.now(UTC)
    payload = {
        "sub": str(user.id),
        "role": user.role.value,
        "iat": now,
        "exp": now + timedelta(minutes=settings.jwt_expire_minutes),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=ALGORITHM)


_NON_AUTHENTIFIE = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Authentification requise ou jeton invalide.",
    headers={"WWW-Authenticate": "Bearer"},
)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    session: AsyncSession = Depends(get_session),
) -> User:
    """Dépendance FastAPI : renvoie l'utilisateur du jeton « Authorization: Bearer … »."""
    if credentials is None:
        raise _NON_AUTHENTIFIE
    try:
        payload = jwt.decode(credentials.credentials, get_settings().jwt_secret, algorithms=[ALGORITHM])
        user_id = int(payload["sub"])
    except (jwt.PyJWTError, KeyError, ValueError):
        raise _NON_AUTHENTIFIE from None
    user = await session.get(User, user_id)
    if user is None:
        raise _NON_AUTHENTIFIE
    return user


def require_role(*roles: Role) -> Callable[..., Awaitable[User]]:
    """Dépendance qui n'autorise que certains rôles, par exemple `require_role(Role.ADMIN)`."""

    async def checker(user: User = Depends(get_current_user)) -> User:
        if user.role not in roles:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Accès réservé : rôle insuffisant.")
        return user

    return checker
