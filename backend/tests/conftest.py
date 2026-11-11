"""Fixtures communes.

Attention : les tests d'API utilisent la base de développement et appellent reset-demo,
qui la vide puis la remplit à nouveau (données reproductibles, donc sans perte réelle).
"""

import os
from collections.abc import AsyncIterator

# Les tests tournent TOUJOURS avec le copilote simulé, même si .env active Claude ou Gemini :
# résultats reproductibles, aucun appel payant. Une variable d'environnement l'emporte sur .env,
# et elle doit être posée avant le premier chargement de la configuration (import de app.main).
os.environ["LLM_PROVIDER"] = "mock"

import pytest  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402

from app.main import app  # noqa: E402


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
