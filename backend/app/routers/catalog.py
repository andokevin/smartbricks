"""Référentiels publics : freelances, villes, compétences."""

from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.models import City, Skill
from app.services.project_data import load_freelancers, skills_of

router = APIRouter(tags=["référentiels"])


@router.get("/freelancers")
async def freelancers(skill: str | None = None, city: str | None = None,
                      session: AsyncSession = Depends(get_session)) -> list[dict[str, Any]]:
    """Freelances, filtrables par compétence et par ville (sans tenir compte des majuscules)."""
    out = []
    for p in await load_freelancers(session):
        skills = skills_of(p)
        if skill and skill.lower() not in {s.lower() for s in skills}:
            continue
        if city and city.lower() != p.city.name.lower():
            continue
        out.append({
            "id": p.id, "name": p.user.name, "city": p.city.name, "hourly_rate_mga": p.hourly_rate_mga,
            "rating": p.rating, "on_time_rate": p.on_time_rate, "completed_projects": p.completed_projects,
            "hours_per_day": p.hours_per_day, "skills": skills, "bio": p.bio,
            "unavailability": [{"start": u.start_date.isoformat(), "end": u.end_date.isoformat(), "reason": u.reason}
                               for u in p.unavailability],
        })
    return out


@router.get("/cities")
async def cities(session: AsyncSession = Depends(get_session)) -> list[dict[str, Any]]:
    rows = (await session.scalars(select(City).order_by(City.id))).all()
    return [{"id": c.id, "name": c.name, "latitude": c.latitude, "longitude": c.longitude} for c in rows]


@router.get("/skills")
async def skills(session: AsyncSession = Depends(get_session)) -> list[dict[str, Any]]:
    return [{"id": s.id, "name": s.name} for s in (await session.scalars(select(Skill).order_by(Skill.id))).all()]
