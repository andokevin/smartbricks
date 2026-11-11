"""Route POST /tasks/{id}/propagate-delay : réparation du planning par Min-Conflict (n°11, niveau B)."""

from typing import Any

from httpx import AsyncClient

from tests.test_api_flow import API, login


async def planned_project(client: AsyncClient, demo: dict[str, Any]) -> tuple[dict[str, str], int, dict[str, Any]]:
    """Projet de démonstration cadré, équipe suggérée, planning calculé."""
    h = await login(client)
    pid = demo["demo_project_id"]
    assert (await client.post(f"{API}/projects/{pid}/scope", headers=h)).status_code == 200
    assert (await client.post(f"{API}/projects/{pid}/team", headers=h, json={"suggested": True})).status_code == 200
    plan = (await client.post(f"{API}/projects/{pid}/solve-constraints", headers=h, json={})).json()
    assert plan["status"] == "OK"
    return h, pid, plan


async def test_retard_repare_et_enregistre(client: AsyncClient, demo: dict[str, Any]) -> None:
    h, pid, plan = await planned_project(client, demo)
    before = {a["ref"]: a for a in plan["assignments"]}
    t2 = before["T2"]  # API des produits : sur le chemin critique

    r = await client.post(f"{API}/tasks/{t2['task_id']}/propagate-delay", headers=h, json={"delay_hours": 8})
    assert r.status_code == 200, r.text
    body = r.json()
    repair, sched = body["repair"], body["schedule"]
    assert repair["status"] == "OK" and repair["method"]["course_number"] == 11
    assert sched["verification"]["constraints_passed"]
    after = {a["ref"]: a for a in sched["assignments"]}
    # La tâche retardée garde son freelance et son début, et dure plus longtemps.
    assert after["T2"]["freelancer_id"] == t2["freelancer_id"] and after["T2"]["start"] == t2["start"]
    assert after["T2"]["hours"] == t2["hours"] + 8 and after["T2"]["end"] > t2["end"]
    # « Tâches modifiées » = exactement celles dont le freelance ou le début a changé.
    moved = sorted(ref for ref in after if ref != "T2" and
                   (after[ref]["start"], after[ref]["freelancer_id"]) != (before[ref]["start"], before[ref]["freelancer_id"]))
    assert sorted(repair["changed"]) == moved
    # Comparaison avec une replanification complète : jamais plus courte que la borne, et au moins aussi bonne
    # en durée que la réparation (le CSP optimise la durée ; Min-Conflict minimise les changements).
    full = repair["full_replan"]
    assert full["status"] == "OK" and sched["lower_bound_days"] <= full["makespan_days"] <= sched["makespan_days"]

    # Le planning réparé devient le planning réel.
    again = (await client.get(f"{API}/projects/{pid}/schedule", headers=h)).json()
    assert again["run_id"] == sched["run_id"] and again["repair"]["task_ref"] == "T2"
    project = (await client.get(f"{API}/projects/{pid}", headers=h)).json()
    task = next(t for t in project["tasks"] if t["ref"] == "T2")
    assert task["estimated_hours"] == t2["hours"] + 8 and task["end_date"] == after["T2"]["end"]


async def test_retard_trop_grand_rien_n_est_modifie(client: AsyncClient, demo: dict[str, Any]) -> None:
    h, pid, plan = await planned_project(client, demo)
    t2 = next(a for a in plan["assignments"] if a["ref"] == "T2")
    r = await client.post(f"{API}/tasks/{t2['task_id']}/propagate-delay", headers=h, json={"delay_hours": 400})
    assert r.status_code == 200
    body = r.json()
    assert body["schedule"] is None and body["repair"]["status"] == "FAILED"
    assert "date limite" in " ".join(body["repair"]["diagnostics"])
    again = (await client.get(f"{API}/projects/{pid}/schedule", headers=h)).json()
    assert again["run_id"] == plan["run_id"]


async def test_erreurs(client: AsyncClient, demo: dict[str, Any]) -> None:
    h = await login(client)
    assert (await client.post(f"{API}/tasks/999999/propagate-delay", headers=h, json={"delay_hours": 8})).status_code == 404
    bad = await client.post(f"{API}/tasks/1/propagate-delay", headers=h, json={"delay_hours": 0})
    assert bad.status_code == 422
    # Pas encore de planning : 404 explicite.
    r = await client.post(f"{API}/tasks/1/propagate-delay", headers=h, json={"delay_hours": 8})
    assert r.status_code == 404 and "planning" in r.json()["detail"].lower()
