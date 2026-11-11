"""Espace freelance (niveau B) : tâches, statut, indisponibilités, retard signalé par le freelance."""

from typing import Any

from httpx import AsyncClient

from tests.test_api_flow import API, login
from tests.test_propagate_delay import planned_project

HASINA = ("hasina@freelance.mg", "demo1234")


async def test_mes_taches_et_statut(client: AsyncClient, demo: dict[str, Any]) -> None:
    _, pid, plan = await planned_project(client, demo)
    h = await login(client, *HASINA)
    me = (await client.get(f"{API}/me/freelancer", headers=h)).json()
    assert me["name"].startswith("Hasina") and "React" in me["skills"]

    tasks = (await client.get(f"{API}/me/tasks", headers=h)).json()
    expected = sorted(a["ref"] for a in plan["assignments"] if a["freelancer"].startswith("Hasina"))
    assert sorted(t["ref"] for t in tasks) == expected and tasks
    assert all(t["project"]["client"] == "Boutique Soa" for t in tasks)
    t2 = next(t for t in tasks if t["ref"] == "T2")
    assert t2["depends_on"][0]["ref"] == "T3" and t2["ready"] is False  # T3 (Fanja) n'est pas terminée

    r = await client.patch(f"{API}/me/tasks/{t2['id']}", headers=h, json={"status": "IN_PROGRESS"})
    assert r.status_code == 200 and r.json()["status"] == "IN_PROGRESS"
    # Une tâche d'un autre freelance : refus.
    t3 = next(a for a in plan["assignments"] if a["ref"] == "T3")
    assert (await client.patch(f"{API}/me/tasks/{t3['task_id']}", headers=h, json={"status": "DONE"})).status_code == 403


async def test_indisponibilite_alerte_le_freelance_et_le_client(client: AsyncClient, demo: dict[str, Any]) -> None:
    hc, pid, plan = await planned_project(client, demo)
    h = await login(client, *HASINA)
    t2 = next(a for a in plan["assignments"] if a["ref"] == "T2")
    r = await client.post(f"{API}/me/unavailability", headers=h,
                          json={"start": t2["start"], "end": t2["start"], "reason": "Rendez-vous médical"})
    assert r.status_code == 201
    created = r.json()
    assert any(a.startswith("T2") for a in created["affected_tasks"])

    mine = (await client.get(f"{API}/me/tasks", headers=h)).json()
    assert next(t for t in mine if t["ref"] == "T2")["alerts"]
    sched = (await client.get(f"{API}/projects/{pid}/schedule", headers=hc)).json()
    assert any("T2" in a and "recalculez" in a for a in sched["alerts"])

    # Le planning recalculé tient compte de l'indisponibilité : plus d'alerte.
    again = (await client.post(f"{API}/projects/{pid}/solve-constraints", headers=hc, json={})).json()
    assert again["status"] == "OK"
    assert (await client.get(f"{API}/projects/{pid}/schedule", headers=hc)).json()["alerts"] == []

    # Suppression.
    uid = created["unavailability"]["id"]
    assert (await client.delete(f"{API}/me/unavailability/{uid}", headers=h)).status_code == 204
    assert (await client.delete(f"{API}/me/unavailability/{uid}", headers=h)).status_code == 404
    bad = await client.post(f"{API}/me/unavailability", headers=h, json={"start": "2026-12-10", "end": "2026-12-01"})
    assert bad.status_code == 422


async def test_le_freelance_signale_un_retard(client: AsyncClient, demo: dict[str, Any]) -> None:
    _, pid, plan = await planned_project(client, demo)
    h = await login(client, *HASINA)
    t2 = next(a for a in plan["assignments"] if a["ref"] == "T2")
    r = await client.post(f"{API}/tasks/{t2['task_id']}/propagate-delay", headers=h, json={"delay_hours": 4})
    assert r.status_code == 200 and r.json()["repair"]["status"] == "OK"
    t3 = next(a for a in plan["assignments"] if a["ref"] == "T3")
    forbidden = await client.post(f"{API}/tasks/{t3['task_id']}/propagate-delay", headers=h, json={"delay_hours": 4})
    assert forbidden.status_code == 403


async def test_reserve_aux_freelances(client: AsyncClient, demo: dict[str, Any]) -> None:
    h = await login(client)  # cliente
    assert (await client.get(f"{API}/me/tasks", headers=h)).status_code == 403
    assert (await client.get(f"{API}/me/tasks")).status_code == 401
