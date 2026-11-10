"""Authentification : inscription, connexion, jeton, rôles."""

from httpx import AsyncClient

API = "/api/v1/auth"


async def test_connexion_client_demo(client: AsyncClient, demo: dict[str, object]) -> None:
    r = await client.post(f"{API}/login", json={"email": "client@smartbricks.mg", "password": "demo1234"})
    assert r.status_code == 200
    token = r.json()["access_token"]

    me = await client.get(f"{API}/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert me.json()["role"] == "CLIENT"
    assert me.json()["organization_name"] == "Boutique Soa"


async def test_mauvais_mot_de_passe(client: AsyncClient, demo: dict[str, object]) -> None:
    r = await client.post(f"{API}/login", json={"email": "client@smartbricks.mg", "password": "faux"})
    assert r.status_code == 401


async def test_me_sans_jeton_ou_jeton_invalide(client: AsyncClient) -> None:
    assert (await client.get(f"{API}/me")).status_code == 401
    r = await client.get(f"{API}/me", headers={"Authorization": "Bearer pas-un-jwt"})
    assert r.status_code == 401


async def test_inscription_puis_doublon(client: AsyncClient, demo: dict[str, object]) -> None:
    data = {"name": "Nouveau Client", "email": "Nouveau@Exemple.mg", "password": "motdepasse1"}
    r = await client.post(f"{API}/register", json=data)
    assert r.status_code == 201
    assert r.json()["user"]["email"] == "nouveau@exemple.mg"  # email normalisé en minuscules

    doublon = await client.post(f"{API}/register", json={**data, "email": "nouveau@exemple.mg"})
    assert doublon.status_code == 409


async def test_inscription_admin_interdite(client: AsyncClient) -> None:
    data = {"name": "Pirate", "email": "pirate@exemple.mg", "password": "motdepasse1", "role": "ADMIN"}
    assert (await client.post(f"{API}/register", json=data)).status_code == 403


async def test_mot_de_passe_hache_avec_argon2() -> None:
    from app.security import hash_password, verify_password

    h = hash_password("secret123")
    assert h.startswith("$argon2")
    assert verify_password("secret123", h)
    assert not verify_password("autre", h)
