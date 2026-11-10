"""Modèles SQLAlchemy (tables de la base).

Phase 1 : fichier vide, importé par Alembic.
Les tables (users, skills, projects, features, tasks…) arrivent en phase 2.
"""

from app.db import Base

__all__ = ["Base"]
