"""Export PDF du cahier des charges (niveau B)."""

import re
from typing import Any

from httpx import AsyncClient

from tests.test_api_flow import API, login
from tests.test_propagate_delay import planned_project


async def test_pdf_avant_tout_calcul(client: AsyncClient, demo: dict[str, Any]) -> None:
    """Projet juste créé : le PDF existe, les sections non calculées sont signalées."""
    h = await login(client)
    r = await client.get(f"{API}/projects/{demo['demo_project_id']}/cahier-des-charges.pdf", headers=h)
    assert r.status_code == 200 and r.headers["content-type"] == "application/pdf"
    assert r.content.startswith(b"%PDF") and len(r.content) > 5_000
    assert "attachment" in r.headers["content-disposition"]


async def test_pdf_projet_complet(client: AsyncClient, demo: dict[str, Any]) -> None:
    h, pid, _ = await planned_project(client, demo)
    await client.post(f"{API}/projects/{pid}/tour", headers=h, json={"closed": True})
    r = await client.get(f"{API}/projects/{pid}/cahier-des-charges.pdf", headers=h)
    assert r.status_code == 200 and r.content.startswith(b"%PDF")
    pages = re.search(rb"/Count (\d+)", r.content)
    assert pages and int(pages.group(1)) >= 3  # projet, exigences, tâches, équipe, planning, tournée


async def test_pdf_reserve_au_client_du_projet(client: AsyncClient, demo: dict[str, Any]) -> None:
    other = await client.post(f"{API}/auth/register", json={
        "name": "Autre client", "email": "autre-pdf@exemple.mg", "password": "motdepasse1"})
    h = {"Authorization": f"Bearer {other.json()['access_token']}"}
    r = await client.get(f"{API}/projects/{demo['demo_project_id']}/cahier-des-charges.pdf", headers=h)
    assert r.status_code == 403
