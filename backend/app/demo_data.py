"""Données de démonstration : villes, compétences, freelances et projet « Boutique Soa ».

Ce module est la SOURCE UNIQUE de la démo :
- `seed.py` l'utilise pour remplir la base ;
- le fournisseur LLM simulé (phase 4) renverra le même brouillon `demo_draft()`.

Les dates sont calculées à partir de la date de début (le lundi qui suit le jour du reset),
pour que la démo fonctionne quel que soit le jour où on la lance.
"""

from datetime import date, timedelta
from typing import Any

# --------------------------------------------------------------------------- villes
# (nom, latitude, longitude) — coordonnées des centres-villes.
CITIES: list[tuple[str, float, float]] = [
    ("Antananarivo", -18.8792, 47.5079),
    ("Toamasina", -18.1443, 49.3958),
    ("Antsirabe", -19.8659, 47.0333),
    ("Fianarantsoa", -21.4527, 47.0857),
    ("Mahajanga", -15.7167, 46.3167),
    ("Toliara", -23.3500, 43.6667),
    ("Antsiranana", -12.2787, 49.2917),
    ("Morondava", -20.2833, 44.2833),
    ("Ambatondrazaka", -17.8333, 48.4167),
    ("Manakara", -22.1333, 48.0167),
    ("Ambositra", -20.5167, 47.2500),
    ("Nosy Be", -13.4000, 48.2667),
]

# --------------------------------------------------------------------------- compétences
SKILLS: list[str] = [
    "React",
    "Node.js",
    "FastAPI",
    "PostgreSQL",
    "Flutter",
    "UI/UX",
    "DevOps",
    "Tests/QA",
    "Réseau",
    "Maintenance matériel",
    "Sécurité",
]

# --------------------------------------------------------------------------- freelances
# (prénom, nom, ville, {compétence: niveau 1–5}).
# Les compétences sont fixées à la main pour que chaque besoin du projet soit couvert ;
# le taux horaire, la note, etc. sont tirés au hasard (graine 42) dans seed.py.
FREELANCERS: list[tuple[str, str, str, dict[str, int]]] = [
    ("Rivo", "Rakotomalala", "Fianarantsoa", {"React": 5, "Node.js": 4, "PostgreSQL": 3}),
    ("Fara", "Andriamihaja", "Antananarivo", {"UI/UX": 5, "React": 3}),
    ("Tiana", "Razafindrabe", "Antananarivo", {"Node.js": 5, "PostgreSQL": 4, "FastAPI": 3}),
    ("Hery", "Randriamampionona", "Antsirabe", {"Réseau": 5, "Maintenance matériel": 4}),
    ("Njaka", "Rasoanaivo", "Toamasina", {"Flutter": 5, "Node.js": 3}),
    ("Volana", "Rabearivelo", "Antananarivo", {"Tests/QA": 5, "React": 2}),
    ("Mamy", "Ratsimbazafy", "Mahajanga", {"DevOps": 5, "PostgreSQL": 4, "Sécurité": 3}),
    ("Lalaina", "Andrianarisoa", "Fianarantsoa", {"UI/UX": 4, "Flutter": 3}),
    ("Hasina", "Rakotondrabe", "Antananarivo", {"React": 4, "Node.js": 3}),
    ("Miora", "Raharison", "Antsirabe", {"Tests/QA": 4, "Sécurité": 3}),
    ("Toky", "Ramanantsoa", "Toamasina", {"Réseau": 4, "Maintenance matériel": 5}),
    ("Fanja", "Rasolofo", "Antananarivo", {"FastAPI": 5, "PostgreSQL": 4, "DevOps": 3}),
    ("Andry", "Rajaonarison", "Fianarantsoa", {"Node.js": 4, "React": 3, "Tests/QA": 2}),
    ("Nirina", "Rakotobe", "Mahajanga", {"Flutter": 4, "UI/UX": 3}),
    ("Haja", "Randrianarivelo", "Antananarivo", {"Sécurité": 5, "DevOps": 4, "Réseau": 3}),
    ("Sitraka", "Razafimahefa", "Antsirabe", {"React": 3, "UI/UX": 3}),
    ("Onja", "Ravelojaona", "Toamasina", {"Tests/QA": 3, "Node.js": 2}),
    ("Zo", "Rabemananjara", "Antananarivo", {"DevOps": 4, "Node.js": 3}),
    ("Lova", "Rakotoarisoa", "Fianarantsoa", {"Réseau": 3, "Maintenance matériel": 3}),
    ("Mialy", "Randrianasolo", "Antananarivo", {"React": 5, "UI/UX": 4}),
    ("Tojo", "Rasamoelina", "Mahajanga", {"Node.js": 4, "PostgreSQL": 3, "FastAPI": 4}),
    ("Hanitra", "Rakotomanga", "Antsirabe", {"Flutter": 3, "React": 3}),
    ("Fenitra", "Andriamanalina", "Antananarivo", {"PostgreSQL": 5, "FastAPI": 4}),
    ("Rado", "Ramaroson", "Toamasina", {"React": 2, "Node.js": 2, "Tests/QA": 2}),
    ("Soloniaina", "Razanakoto", "Fianarantsoa", {"Réseau": 4, "DevOps": 3}),
]

# --------------------------------------------------------------------------- comptes
DEMO_PASSWORD = "demo1234"
CLIENT_ACCOUNT = {
    "name": "Soa Rasoanirina",
    "email": "client@smartbricks.mg",
    "password": DEMO_PASSWORD,
    "organization_name": "Boutique Soa",
}
ADMIN_ACCOUNT = {
    "name": "Administrateur SmartBricks",
    "email": "admin@smartbricks.mg",
    "password": "admin1234",
}

# --------------------------------------------------------------------------- projet Boutique Soa

DEMO_DESCRIPTION = (
    "Boutique Soa veut un site e-commerce avec paiement MVola, une application mobile de suivi "
    "des commandes, et l'installation du réseau dans ses agences de Tana, Antsirabe, Toamasina "
    "et Fianarantsoa. Budget 6 000 000 Ar, livraison dans 8 semaines."
)
DEMO_BUDGET_MGA = 6_000_000
DEMO_BUDGET_HOURS = 200
DEMO_WEEKS = 8
DEMO_SITES = ["Antananarivo", "Antsirabe", "Toamasina", "Fianarantsoa"]

# (ref, titre, description, type, valeur métier, obligatoire, dépendances)
_FEATURES: list[tuple[str, str, str, str, int, bool, list[str]]] = [
    ("F1", "Catalogue produits", "Vitrine des vêtements avec photos, tailles et prix.",
     "FUNCTIONAL", 90, True, []),
    ("F2", "Panier et commande", "Ajouter au panier, valider une commande.",
     "FUNCTIONAL", 85, False, ["F1"]),
    ("F3", "Paiement MVola", "Payer la commande par Mobile Money MVola.",
     "FUNCTIONAL", 80, False, ["F2"]),
    ("F4", "Comptes clients sécurisés", "Inscription, connexion, mots de passe protégés.",
     "SECURITY", 70, True, []),
    ("F5", "Back-office des stocks", "Gérer les produits et les stocks des quatre agences.",
     "FUNCTIONAL", 65, False, ["F1"]),
    ("F6", "Application mobile de suivi", "Suivre l'état de ses commandes sur téléphone.",
     "FUNCTIONAL", 60, False, ["F2"]),
    ("F7", "Notifications SMS", "Prévenir le client par SMS à chaque étape de la commande.",
     "FUNCTIONAL", 35, False, ["F6"]),
    ("F8", "Programme de fidélité", "Points de fidélité et réductions pour les clients réguliers.",
     "FUNCTIONAL", 30, False, ["F4"]),
    ("F9", "Livraison à domicile", "Choisir la livraison et suivre le livreur.",
     "FUNCTIONAL", 45, False, ["F2"]),
    ("F10", "Tableau de bord des ventes", "Chiffre d'affaires et meilleures ventes par agence.",
     "FUNCTIONAL", 40, False, ["F5"]),
    ("F11", "Réseau des quatre agences", "Installer le réseau et la connexion dans chaque agence.",
     "TECHNICAL", 75, True, []),
    ("F12", "Hébergement et mise en production", "Serveur, sauvegardes, déploiement automatique.",
     "TECHNICAL", 70, False, ["F1", "F4"]),
    ("F13", "Protection des données personnelles", "Consentement, politique de confidentialité, audit.",
     "COMPLIANCE", 25, False, ["F4"]),
    ("F14", "Paiement Orange Money", "Deuxième moyen de paiement mobile.",
     "FUNCTIONAL", 20, False, ["F2"]),
]

# (ref, fonctionnalité, titre, compétence, niveau min., heures, dépendances, ville sur site)
_TASKS: list[tuple[str, str, str, str, int, int, list[str], str | None]] = [
    ("T1", "F1", "Maquettes du site", "UI/UX", 3, 12, [], None),
    ("T2", "F1", "API des produits", "Node.js", 3, 16, ["T3"], None),
    ("T3", "F1", "Base de données des produits", "PostgreSQL", 3, 8, [], None),
    ("T4", "F1", "Pages du catalogue", "React", 3, 20, ["T1", "T2"], None),
    ("T5", "F2", "API du panier et des commandes", "Node.js", 3, 16, ["T2"], None),
    ("T6", "F2", "Pages du panier", "React", 3, 12, ["T4", "T5"], None),
    ("T7", "F3", "Intégration de l'API MVola", "Node.js", 4, 16, ["T5"], None),
    ("T8", "F3", "Tests du paiement MVola", "Tests/QA", 3, 8, ["T6", "T7"], None),
    ("T9", "F4", "API d'authentification", "Node.js", 3, 12, ["T3"], None),
    ("T10", "F4", "Pages de connexion et d'inscription", "React", 2, 8, ["T1", "T9"], None),
    ("T11", "F5", "Maquettes du back-office", "UI/UX", 3, 8, [], None),
    ("T12", "F5", "Back-office des stocks", "React", 3, 24, ["T2", "T11"], None),
    ("T13", "F6", "Maquettes de l'application mobile", "UI/UX", 3, 10, [], None),
    ("T14", "F6", "Application Flutter de suivi", "Flutter", 3, 40, ["T5", "T13"], None),
    ("T15", "F6", "Tests de l'application mobile", "Tests/QA", 2, 8, ["T14"], None),
    ("T16", "F7", "Service de notifications SMS", "Node.js", 3, 12, ["T14"], None),
    ("T17", "F8", "API du programme de fidélité", "Node.js", 3, 12, ["T9"], None),
    ("T18", "F8", "Pages du programme de fidélité", "React", 2, 8, ["T17"], None),
    ("T19", "F9", "API de gestion des livraisons", "Node.js", 3, 14, ["T5"], None),
    ("T20", "F9", "Suivi de livraison côté client", "React", 2, 8, ["T19"], None),
    ("T21", "F10", "Tableau de bord des ventes", "React", 3, 16, ["T12"], None),
    ("T22", "F11", "Réseau de l'agence d'Antananarivo", "Réseau", 3, 8, [], "Antananarivo"),
    ("T23", "F11", "Réseau de l'agence d'Antsirabe", "Réseau", 3, 8, [], "Antsirabe"),
    ("T24", "F11", "Réseau de l'agence de Toamasina", "Réseau", 3, 8, [], "Toamasina"),
    ("T25", "F11", "Réseau de l'agence de Fianarantsoa", "Réseau", 3, 8, [], "Fianarantsoa"),
    ("T26", "F12", "Serveur et déploiement automatique", "DevOps", 3, 12, ["T3"], None),
    ("T27", "F12", "Tests de bout en bout", "Tests/QA", 3, 12, ["T4", "T10"], None),
    ("T28", "F12", "Mise en production", "DevOps", 3, 6, ["T26", "T27"], None),
    ("T29", "F13", "Audit sécurité et données personnelles", "Sécurité", 3, 10, ["T9"], None),
    ("T30", "F14", "Intégration de l'API Orange Money", "Node.js", 4, 14, ["T5"], None),
]


def next_monday(today: date) -> date:
    """Le lundi qui suit `today` (ou `today` lui-même si c'est un lundi)."""
    return today + timedelta(days=(7 - today.weekday()) % 7)


def demo_draft(start: date) -> dict[str, Any]:
    """Brouillon du projet Boutique Soa, au format JSON produit par le copilote.

    Les heures d'une fonctionnalité sont la somme des heures de ses tâches,
    pour que les deux niveaux restent cohérents.
    """
    hours_by_feature: dict[str, int] = {}
    for _ref, feature_ref, *_rest in _TASKS:
        hours_by_feature[feature_ref] = hours_by_feature.get(feature_ref, 0) + _rest[3]

    return {
        "project": {
            "title": "Boutique Soa — e-commerce, application mobile et réseau des agences",
            "description": DEMO_DESCRIPTION,
            "budget_mga": DEMO_BUDGET_MGA,
            "budget_hours": DEMO_BUDGET_HOURS,
            "deadline": (start + timedelta(weeks=DEMO_WEEKS) - timedelta(days=3)).isoformat(),
            "base_city": "Antananarivo",
        },
        "features": [
            {
                "ref": ref,
                "title": title,
                "description": description,
                "req_type": req_type,
                "business_value": value,
                "estimated_hours": hours_by_feature[ref],
                "is_mandatory": mandatory,
                "depends_on": deps,
            }
            for ref, title, description, req_type, value, mandatory, deps in _FEATURES
        ],
        "tasks": [
            {
                "ref": ref,
                "feature_ref": feature_ref,
                "title": title,
                "required_skill": skill,
                "min_level": level,
                "estimated_hours": hours,
                "depends_on": deps,
                "on_site_city": site,
            }
            for ref, feature_ref, title, skill, level, hours, deps, site in _TASKS
        ],
        "sites": list(DEMO_SITES),
    }
