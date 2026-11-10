"""Remplissage de la base avec les données de démonstration (reproductibles : random.seed(42)).

Utilisation :
- par l'API : POST /api/v1/admin/reset-demo (développement uniquement) ;
- en ligne de commande, depuis backend/ : `python -m app.seed`.

Ce qui est créé :
- 12 villes de Madagascar, 11 compétences ;
- 25 freelances (compte utilisateur + profil + compétences + quelques indisponibilités) ;
- un compte client (client@smartbricks.mg / demo1234) et un compte administrateur ;
- le projet de démonstration « Boutique Soa » (statut DRAFT), pour pouvoir tester
  les modules B à E sans passer par le copilote.
"""

import asyncio
import random
import unicodedata
from datetime import date, timedelta

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app import demo_data
from app.db import Base, SessionLocal
from app.models import (
    City,
    FreelancerProfile,
    FreelancerSkill,
    FreelancerUnavailability,
    Role,
    Skill,
    User,
)
from app.schemas import ResetDemoOut
from app.security import hash_password
from app.services.project_builder import create_project_from_draft

SEED = 42


def _slug(name: str) -> str:
    """« Hery » → « hery » (sans accents), pour fabriquer les emails."""
    ascii_name = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode()
    return ascii_name.lower().replace(" ", "")


def _hourly_rate(rng: random.Random, best_level: int) -> int:
    """Taux horaire en Ar, lié au meilleur niveau du freelance, entre 15 000 et 60 000 Ar."""
    rate = 10_000 * best_level - 3_000 + rng.randint(-2_000, 8_000)
    rate = max(15_000, min(60_000, rate))
    return int(round(rate / 500)) * 500


async def _truncate_all(session: AsyncSession) -> None:
    """Vide toutes les tables et remet les compteurs d'identifiants à 1."""
    tables = ", ".join(f'"{t.name}"' for t in Base.metadata.sorted_tables)
    await session.execute(text(f"TRUNCATE {tables} RESTART IDENTITY CASCADE"))


async def reset_demo(session: AsyncSession, today: date | None = None) -> ResetDemoOut:
    rng = random.Random(SEED)
    start = demo_data.next_monday(today or date.today())

    await _truncate_all(session)

    # Référentiels.
    cities = {name: City(name=name, latitude=lat, longitude=lon) for name, lat, lon in demo_data.CITIES}
    skills = {name: Skill(name=name) for name in demo_data.SKILLS}
    session.add_all([*cities.values(), *skills.values()])

    # Comptes client et administrateur.
    client = User(
        name=demo_data.CLIENT_ACCOUNT["name"],
        email=demo_data.CLIENT_ACCOUNT["email"],
        password_hash=hash_password(demo_data.CLIENT_ACCOUNT["password"]),
        role=Role.CLIENT,
        organization_name=demo_data.CLIENT_ACCOUNT["organization_name"],
    )
    admin = User(
        name=demo_data.ADMIN_ACCOUNT["name"],
        email=demo_data.ADMIN_ACCOUNT["email"],
        password_hash=hash_password(demo_data.ADMIN_ACCOUNT["password"]),
        role=Role.ADMIN,
        organization_name="SmartBricks",
    )
    session.add_all([client, admin])

    # Freelances. Le mot de passe est haché une seule fois (argon2 est volontairement lent) :
    # acceptable pour des comptes de démonstration.
    freelancer_hash = hash_password(demo_data.DEMO_PASSWORD)
    profiles: dict[str, FreelancerProfile] = {}
    for first, last, city, skill_levels in demo_data.FREELANCERS:
        user = User(
            name=f"{first} {last}",
            email=f"{_slug(first)}@freelance.mg",
            password_hash=freelancer_hash,
            role=Role.FREELANCER,
        )
        best = max(skill_levels.values())
        profile = FreelancerProfile(
            user=user,
            city=cities[city],
            hourly_rate_mga=_hourly_rate(rng, best),
            rating=round(rng.uniform(3.2, 5.0), 1),
            completed_projects=rng.randint(2, 40),
            on_time_rate=round(rng.uniform(0.60, 0.98), 2),
            hours_per_day=rng.choice([4, 5, 6, 7, 8]),
            bio=f"{', '.join(skill_levels)} — basé(e) à {city}.",
            skills=[FreelancerSkill(skill=skills[s], level=lvl) for s, lvl in skill_levels.items()],
        )
        session.add(profile)
        profiles[first] = profile

    # Indisponibilités : Rivo est en congé la 3e semaine (cas visible dans le planning),
    # puis 8 autres freelances tirés au hasard ont un bloc de 2 à 5 jours dans les 8 semaines.
    profiles["Rivo"].unavailability.append(
        FreelancerUnavailability(
            start_date=start + timedelta(weeks=2),
            end_date=start + timedelta(weeks=2, days=4),
            reason="Congé",
        )
    )
    others = [name for name in profiles if name != "Rivo"]
    for name in rng.sample(others, 8):
        offset = rng.randint(0, 7 * demo_data.DEMO_WEEKS - 7)
        length = rng.randint(2, 5)
        profiles[name].unavailability.append(
            FreelancerUnavailability(
                start_date=start + timedelta(days=offset),
                end_date=start + timedelta(days=offset + length - 1),
                reason=rng.choice(["Autre mission", "Formation", "Raison familiale", "Congé"]),
            )
        )

    await session.flush()

    # Projet de démonstration.
    draft = demo_data.demo_draft(start)
    project = await create_project_from_draft(session, client.id, draft, start)
    await session.commit()

    return ResetDemoOut(
        cities=len(cities),
        skills=len(skills),
        freelancers=len(profiles),
        users=len(profiles) + 2,
        demo_project_id=project.id,
        features=len(draft["features"]),
        tasks=len(draft["tasks"]),
        accounts={
            "client": f"{demo_data.CLIENT_ACCOUNT['email']} / {demo_data.CLIENT_ACCOUNT['password']}",
            "admin": f"{demo_data.ADMIN_ACCOUNT['email']} / {demo_data.ADMIN_ACCOUNT['password']}",
            "freelances": f"<prénom>@freelance.mg / {demo_data.DEMO_PASSWORD} (ex. rivo@freelance.mg)",
        },
    )


async def _main() -> None:
    async with SessionLocal() as session:
        result = await reset_demo(session)
    print(result.model_dump_json(indent=2))


if __name__ == "__main__":
    asyncio.run(_main())
