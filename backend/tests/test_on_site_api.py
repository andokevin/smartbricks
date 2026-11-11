"""Contrainte 6 dans l'API : le planning du projet de démonstration suit l'ordre de la tournée,
avec un jour de trajet entre deux agences ; l'écran Tournée sait si le planning suit sa tournée."""

from datetime import date
from typing import Any

from httpx import AsyncClient

from app.algorithms.calendar import working_days
from tests.test_propagate_delay import planned_project
from tests.test_api_flow import API


async def test_planning_suit_la_tournee(client: AsyncClient, demo: dict[str, Any]) -> None:
    h, pid, plan = await planned_project(client, demo)
    sites = plan["site_order"]
    assert sites and sites["travel_days"] == 1 and "tournée optimale" in sites["source"]
    rank = {c: k for k, c in enumerate(sites["cities"])}
    check = next(c for c in plan["verification"]["checks"] if c["name"].startswith("Sur site"))
    assert check["passed"] and len(plan["verification"]["checks"]) == 8

    start = date.fromisoformat(plan["start_date"])

    def idx(d: str) -> int:
        return len(working_days(start, date.fromisoformat(d))) - 1

    on_site = sorted((a for a in plan["assignments"] if a["on_site_city"]), key=lambda a: a["start"])
    assert len(on_site) == 4
    by_person: dict[int, list[dict[str, Any]]] = {}
    for a in on_site:
        by_person.setdefault(a["freelancer_id"], []).append(a)
    for visits in by_person.values():
        for x, y in zip(visits, visits[1:]):
            assert rank[x["on_site_city"]] < rank[y["on_site_city"]]  # ordre de la tournée
            assert idx(y["start"]) - idx(x["end"]) >= 2  # au moins un jour ouvré de trajet entre les deux

    # L'aperçu de tournée par défaut (même technicien) correspond à l'ordre suivi par le planning.
    tour = (await client.get(f"{API}/projects/{pid}/tour", headers=h)).json()
    assert tour["planning_order"]["matches"]


async def test_tournee_validee_fait_foi(client: AsyncClient, demo: dict[str, Any]) -> None:
    h, pid, plan = await planned_project(client, demo)
    # On valide une tournée au départ d'Antsirabe (Hery, id 4) : son ordre diffère de celui du planning…
    saved = (await client.post(f"{API}/projects/{pid}/tour", headers=h, json={"freelancer_id": 4, "closed": True})).json()
    assert saved["planning_order"]["matches"] is False
    # … et le planning recalculé suit désormais la tournée validée.
    again = (await client.post(f"{API}/projects/{pid}/solve-constraints", headers=h, json={})).json()
    assert again["status"] == "OK" and again["site_order"]["source"] == "tournée validée"
    assert again["site_order"]["cities"] == [s["name"] for s in saved["order"]]
    assert again["verification"]["constraints_passed"]
