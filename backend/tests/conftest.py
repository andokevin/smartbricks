"""Fixtures communes.

Attention : les tests d'API utilisent la base de développement et appellent reset-demo,
qui la vide puis la remplit à nouveau (données reproductibles, donc sans perte réelle).
"""

from collections.abc import AsyncIterator

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.fixture
async def client() -> AsyncIterator[AsyncClient]:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


@pytest.fixture
async def demo(client: AsyncClient) -> dict[str, object]:
    """Base remise à l'état de démonstration ; renvoie le résumé du seed."""
    reponse = await client.post("/api/v1/admin/reset-demo")
    assert reponse.status_code == 200, reponse.text
    return reponse.json()
