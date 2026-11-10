"""Test de fumée de la phase 1 : l'API démarre, la base répond, /docs est servi."""

from httpx import ASGITransport, AsyncClient

from app.main import app


async def test_health_et_docs() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        reponse = await client.get("/api/v1/health")
        assert reponse.status_code == 200
        assert reponse.json()["database"] == "ok"

        docs = await client.get("/docs")
        assert docs.status_code == 200
