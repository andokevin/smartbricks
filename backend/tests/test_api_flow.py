"""Parcours complet de l'API sur le projet de démonstration Boutique Soa (fournisseur LLM simulé)."""

from typing import Any

import pytest
from httpx import AsyncClient

API = "/api/v1"


async def login(client: AsyncClient, email: str = "client@smartbricks.mg", pwd: str = "demo1234") -> dict[str, str]:
    r = await client.post(f"{API}/auth/login", json={"email": email, "password": pwd})
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


# --------------------------------------------------------------------------- module A : copilote


async def test_copilote_puis_confirmation(client: AsyncClient, demo: dict[str, Any]) -> None:
    h = await login(client)
    r = await client.post(f"{API}/assistant/chat", headers=h, json={
        "message": "Boutique Soa veut un site e-commerce avec paiement MVola, une application mobile de suivi "
                   "des commandes, et le réseau dans ses agences de Tana, Antsirabe, Toamasina et Fianarantsoa. "
                   "Budget 6 000 000 Ar, livraison dans 8 semaines."})
    assert r.status_code == 200
    first = r.json()
    assert not first["ready"] and first["provider"] == "mock"

    r = await client.post(f"{API}/assistant/chat", headers=h,
                          json={"conversation_id": first["conversation_id"], "message": "Oui"})
    second = r.json()
    assert second["ready"] and len(second["draft"]["features"]) == 14

    # Le client corrige une estimation avant de confirmer : le brouillon est revérifié.
    draft = second["draft"]
    draft["features"][2]["business_value"] = 95
    r = await client.post(f"{API}/assistant/confirm", headers=h,
                          json={"conversation_id": first["conversation_id"], "draft": draft})
    assert r.status_code == 201, r.text
    created = r.json()
    assert created["tasks"] == 30 and created["sites"] == ["Antananarivo", "Antsirabe", "Toamasina", "Fianarantsoa"]

    p = (await client.get(f"{API}/projects/{created['project_id']}", headers=h)).json()
    assert p["status"] == "DRAFT" and len(p["features"]) == 14
    assert next(f for f in p["features"] if f["ref"] == "F3")["business_value"] == 95
    assert all(f["estimated_cost_mga"] > 0 for f in p["features"])

    again = await client.post(f"{API}/assistant/confirm", headers=h, json={"conversation_id": first["conversation_id"]})
    assert again.status_code == 409


# --------------------------------------------------------------------------- modules B à E


async def test_parcours_complet_boutique_soa(client: AsyncClient, demo: dict[str, Any]) -> None:
    h = await login(client)
    pid = demo["demo_project_id"]

    # Avant le cadrage, pas de matching.
    assert (await client.get(f"{API}/projects/{pid}/matching", headers=h)).status_code == 409

    # B — sac à dos
    s = (await client.post(f"{API}/projects/{pid}/scope", headers=h)).json()
    assert s["feasible"] and s["optimal"] and s["method"]["course_number"] == 29
    assert s["total_cost_mga"] <= s["budget_mga"] and s["total_hours"] <= s["budget_hours"]
    assert s["verification"] == []
    chosen = {f["ref"] for f in s["features"] if f["selected"]}
    assert {"F1", "F4", "F11"} <= chosen  # obligatoires
    assert all(f["reason"] for f in s["features"] if not f["selected"])
    assert any(w["added"] for w in s["what_if"])

    # C — matching : les curseurs changent le classement ; 100 % coût = coût croissant.
    eco = (await client.get(f"{API}/projects/{pid}/matching?preset=Économique", headers=h)).json()
    fast = (await client.get(f"{API}/projects/{pid}/matching?preset=Rapide", headers=h)).json()
    assert [x["id"] for x in eco["ranking"]] != [x["id"] for x in fast["ranking"]]
    cost_only = (await client.get(f"{API}/projects/{pid}/matching?w_cost=1", headers=h)).json()
    costs = [x["criteria"]["cost"] for x in cost_only["ranking"]]
    assert costs == sorted(costs)
    assert eco["best_compromise"] in eco["fronts"][0]
    assert all(x["front"] >= 1 for x in eco["ranking"])

    t = (await client.post(f"{API}/projects/{pid}/team", headers=h, json={"suggested": True})).json()
    assert t["members"] and t["absorbable"] and t["warnings"] == []

    # D — CSP : planning vérifié
    plan = (await client.post(f"{API}/projects/{pid}/solve-constraints", headers=h, json={})).json()
    assert plan["status"] == "OK", plan["diagnostics"]
    assert plan["verification"]["constraints_passed"]
    assert {c["name"] for c in plan["verification"]["checks"]} >= {
        "Dépendances", "Compétences", "Disponibilité", "Pas de chevauchement", "Date limite"}
    assert plan["makespan_days"] >= plan["lower_bound_days"]
    assert plan["elapsed_ms"] < 3500
    detail = (await client.get(f"{API}/projects/{pid}", headers=h)).json()
    assert detail["status"] == "PLANNED"
    assert all(t["start_date"] for t in detail["tasks"] if t["feature_ref"] in chosen)

    # D — scénario impossible : diagnostic chiffré, rien n'est enregistré dans les tâches.
    bad = (await client.post(f"{API}/projects/{pid}/solve-constraints", headers=h,
                             json={"scenario": "impossible"})).json()
    assert bad["status"] == "INFEASIBLE" and bad["working_days_available"] == 15
    assert any(("jours ouvrés" in d) for d in bad["diagnostics"])
    after = (await client.get(f"{API}/projects/{pid}", headers=h)).json()
    assert after["status"] == "PLANNED" and after["tasks"] == detail["tasks"]

    # E — tournée exacte entre les 4 agences
    tour = (await client.post(f"{API}/projects/{pid}/tour", headers=h, json={"closed": True})).json()
    assert tour["method"]["method"] == "Held-Karp"
    assert sorted(o["name"] for o in tour["order"]) == ["Antananarivo", "Antsirabe", "Fianarantsoa", "Toamasina"]
    assert tour["distance_km"] <= tour["entered_distance_km"]
    assert abs(tour["cost_mga"] - tour["distance_km"] * 1200) < 100  # 1 200 Ar/km (distance arrondie)

    # A — explication à partir des seuls chiffres calculés
    e = (await client.post(f"{API}/projects/{pid}/explain", headers=h, json={})).json()
    assert e["provider"] == "mock" and not e["replaced"]
    assert "premier sprint" in e["text"] and "Held-Karp" not in e["text"]


async def test_tournee_de_hery(client: AsyncClient, demo: dict[str, Any]) -> None:
    """La tournée peut partir de la ville d'un technicien donné (Hery, Antsirabe)."""
    h = await login(client)
    hery = next(f for f in (await client.get(f"{API}/freelancers?skill=Réseau")).json() if f["name"].startswith("Hery"))
    tour = (await client.post(f"{API}/projects/{demo['demo_project_id']}/tour", headers=h,
                              json={"freelancer_id": hery["id"]})).json()
    assert tour["start"]["name"] == "Antsirabe" and tour["order"][0]["name"] == "Antsirabe"
    assert len(tour["order"]) == 4  # Antsirabe + les 3 autres agences


# --------------------------------------------------------------------------- règles d'accès et corrections


async def test_projet_d_un_autre_client_interdit(client: AsyncClient, demo: dict[str, Any]) -> None:
    r = await client.post(f"{API}/auth/register", json={"name": "Autre", "email": "autre@exemple.mg",
                                                       "password": "motdepasse1"})
    other = {"Authorization": f"Bearer {r.json()['access_token']}"}
    assert (await client.get(f"{API}/projects/{demo['demo_project_id']}", headers=other)).status_code == 403
    assert (await client.get(f"{API}/projects", headers=other)).json() == []
    assert (await client.get(f"{API}/projects")).status_code == 401


async def test_correction_d_une_fonctionnalite(client: AsyncClient, demo: dict[str, Any]) -> None:
    h = await login(client)
    pid = demo["demo_project_id"]
    await client.post(f"{API}/projects/{pid}/scope", headers=h)
    p = (await client.get(f"{API}/projects/{pid}", headers=h)).json()
    f3 = next(f for f in p["features"] if f["ref"] == "F3")
    r = await client.patch(f"{API}/features/{f3['id']}", headers=h, json={"estimated_hours": 48})
    assert r.status_code == 200
    patched = r.json()
    assert patched["estimated_hours"] == 48
    assert patched["estimated_cost_mga"] > f3["estimated_cost_mga"]  # coût recalculé
    p = (await client.get(f"{API}/projects/{pid}", headers=h)).json()
    assert p["status"] == "DRAFT"  # cadrage à relancer
    assert sum(t["estimated_hours"] for t in p["tasks"] if t["feature_ref"] == "F3") == 48  # tâches à l'échelle

    f13 = next(f for f in p["features"] if f["ref"] == "F13")
    assert not f13["selected_for_sprint"]
    await client.patch(f"{API}/features/{f13['id']}", headers=h, json={"is_mandatory": True})
    s = (await client.post(f"{API}/projects/{pid}/scope", headers=h)).json()
    assert "F13" in {f["ref"] for f in s["features"] if f["selected"]}  # devenue obligatoire


@pytest.mark.parametrize("path", ["/cities", "/skills", "/freelancers?city=Fianarantsoa"])
async def test_referentiels(client: AsyncClient, demo: dict[str, Any], path: str) -> None:
    r = await client.get(f"{API}{path}")
    assert r.status_code == 200 and r.json()
