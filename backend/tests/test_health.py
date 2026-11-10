"""Test de fumée de la phase 1 : l'API démarre, la base répond, /docs est servi."""

from httpx import AsyncClient


async def test_health_et_docs(client: AsyncClient) -> None:
    reponse = await client.get("/api/v1/health")
    assert reponse.status_code == 200
    assert reponse.json()["database"] == "ok"

    docs = await client.get("/docs")
    assert docs.status_code == 200
