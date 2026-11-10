"""Le seed remplit la base avec une démonstration cohérente et reproductible."""

from httpx import AsyncClient
from sqlalchemy import func, select

from app.db import SessionLocal
from app.models import Feature, FreelancerProfile, FreelancerUnavailability, Project, Task, TaskDependency


async def test_reset_demo_remplit_la_base(demo: dict[str, object]) -> None:
    assert demo["cities"] == 12
    assert demo["freelancers"] == 25
    assert demo["features"] == 14
    assert demo["tasks"] == 30


async def test_projet_demo_force_de_vrais_choix(demo: dict[str, object]) -> None:
    """La somme des fonctionnalités dépasse le budget, mais les obligatoires y tiennent."""
    async with SessionLocal() as s:
        project = await s.get(Project, demo["demo_project_id"])
        assert project is not None
        features = (await s.scalars(select(Feature).where(Feature.project_id == project.id))).all()

        total = sum(f.estimated_cost_mga for f in features)
        mandatory = [f for f in features if f.is_mandatory]
        assert len(mandatory) == 3
        assert total > project.budget_mga
        assert sum(f.estimated_cost_mga for f in mandatory) <= project.budget_mga
        assert sum(f.estimated_hours for f in mandatory) <= project.budget_hours

        # Chaîne de dépendances : paiement MVola → panier → catalogue.
        by_ref = {f.ref: f for f in features}
        assert by_ref["F3"].depends_on_feature_ids == [by_ref["F2"].id]
        assert by_ref["F2"].depends_on_feature_ids == [by_ref["F1"].id]


async def test_taches_sur_site_et_dependances(demo: dict[str, object]) -> None:
    async with SessionLocal() as s:
        on_site = await s.scalar(select(func.count()).select_from(Task).where(Task.on_site_city_id.is_not(None)))
        assert on_site == 4
        deps = await s.scalar(select(func.count()).select_from(TaskDependency))
        assert deps and deps > 20


async def test_freelances_realistes(demo: dict[str, object]) -> None:
    async with SessionLocal() as s:
        rates = (await s.scalars(select(FreelancerProfile.hourly_rate_mga))).all()
        assert all(15_000 <= r <= 60_000 for r in rates)
        assert await s.scalar(select(func.count()).select_from(FreelancerUnavailability)) == 9


async def test_seed_reproductible(client: AsyncClient, demo: dict[str, object]) -> None:
    """Deux resets donnent exactement les mêmes taux horaires (graine 42)."""
    async with SessionLocal() as s:
        first = (await s.scalars(select(FreelancerProfile.hourly_rate_mga).order_by(FreelancerProfile.id))).all()
    await client.post("/api/v1/admin/reset-demo")
    async with SessionLocal() as s:
        second = (await s.scalars(select(FreelancerProfile.hourly_rate_mga).order_by(FreelancerProfile.id))).all()
    assert first == second
