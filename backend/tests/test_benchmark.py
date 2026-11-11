"""Benchmark exact contre approché : cohérence des mesures et accès réservé à l'administrateur."""

from typing import Any

from httpx import AsyncClient

API = "/api/v1"


async def _token(client: AsyncClient, email: str, pwd: str) -> dict[str, str]:
    r = await client.post(f"{API}/auth/login", json={"email": email, "password": pwd})
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


async def test_benchmark_coherent(client: AsyncClient, demo: dict[str, Any]) -> None:
    soa = await _token(client, "client@smartbricks.mg", "demo1234")
    pid = demo["demo_project_id"]
    await client.post(f"{API}/projects/{pid}/scope", headers=soa)
    await client.post(f"{API}/projects/{pid}/team", headers=soa, json={"suggested": True})

    admin = await _token(client, "admin@smartbricks.mg", "admin1234")
    r = await client.get(f"{API}/benchmark?project_id={pid}", headers=admin)
    assert r.status_code == 200, r.text
    b = r.json()

    # Sac à dos : l'exact n'est jamais battu, les écarts sont ≥ 0.
    k = b["knapsack"]["project"]
    assert k["exact"]["optimal"] and k["greedy"]["value"] <= k["swaps"]["value"] <= k["exact"]["value"]
    assert all(s["greedy_gap_avg_pct"] >= s["swaps_gap_avg_pct"] >= 0 for s in b["knapsack"]["random"])

    # Planning : l'optimisation ne fait jamais pire que la première solution.
    c = b["csp"]["project"]
    assert c is not None and c["optimized"]["makespan_days"] <= c["first"]["makespan_days"]
    assert c["optimized"]["makespan_days"] >= c["lower_bound_days"]

    # Tournée : Held-Karp ≤ 2-opt ≤ plus proche voisin.
    for run in (b["tsp"]["project"], b["tsp"]["national"]):
        assert run["held_karp"]["km"] <= run["two_opt"]["km"] <= run["nearest_neighbor"]["km"] + 0.1
    assert len(b["tsp"]["national"]["cities"]) == 12
    assert [s["sites"] for s in b["tsp"]["random"]] == [6, 8, 10, 12, 13]


async def test_benchmark_reserve_admin(client: AsyncClient, demo: dict[str, Any]) -> None:
    soa = await _token(client, "client@smartbricks.mg", "demo1234")
    assert (await client.get(f"{API}/benchmark", headers=soa)).status_code == 403
