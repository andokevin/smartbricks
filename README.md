# SmartBricks

SmartBricks transforme le besoin flou d'un client non technique en un projet informatique réaliste : un périmètre chiffré, une équipe de freelances, un planning qui respecte toutes les contraintes, et une tournée optimisée pour les interventions sur site à Madagascar.

Un **copilote LLM** dialogue avec le client et explique les résultats. Des **algorithmes mathématiques** prennent toutes les décisions chiffrées : le LLM ne calcule jamais un budget, un planning ou une tournée.

La démonstration fonctionne **sans clé d'API ni réseau** grâce au fournisseur simulé (`LLM_PROVIDER=mock`).

## Lancement rapide (moins de 10 minutes)

Prérequis : WSL Ubuntu, Docker Desktop (intégration WSL activée), Python 3.11+, Node 20+, pnpm.

```bash
cd ~/projets/smartbricks && cp .env.example .env && docker compose up -d      # PostgreSQL 17 sur le port 5435
cd backend && python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/alembic upgrade head && .venv/bin/python -m app.seed               # tables + données de démonstration
.venv/bin/uvicorn app.main:app --reload &                                     # API : http://localhost:8000/docs
cd ../frontend && pnpm install && pnpm dev                                    # interface : http://localhost:5173
```

Comptes : `client@smartbricks.mg` / `demo1234` (cliente Soa) et `admin@smartbricks.mg` / `admin1234`. Les deux sont accessibles en un clic depuis la page de connexion.

Tests : `cd backend && .venv/bin/pytest -q`.

Le détail (venv créé avec `uv`, port 5435, activation de Claude, problèmes fréquents) est dans [docs/01_GUIDE_LANCEMENT.md](docs/01_GUIDE_LANCEMENT.md).

## Fonctionnalité → algorithme → numéro du cours

| Fonctionnalité | Algorithme | N° | Code |
|---|---|---|---|
| Copilote : questions, brouillon JSON, explication vérifiée | Métaheuristique & IA (LLM + contrôles sans IA, tri de Kahn) | 33 | `backend/app/llm/`, `services/copilot.py`, `algorithms/dependencies.py` |
| Choix automatique exact / approché | Sélecteur de méthode (hyper-heuristique) | 33 | `algorithms/solver_selector.py` |
| Périmètre du sprint 1 sous budget (Ar) et heures, « et si ? » | Sac à dos multidimensionnel (séparation et évaluation) | 29 | `algorithms/knapsack_md.py` |
| Classement des freelances selon les curseurs | Agrégation pondérée | 22 | `algorithms/matching.py` |
| Fronts de compromis et meilleur compromis | Optimisation de Pareto (tri non dominé) | 21 | `algorithms/matching.py` |
| Planning, vérification, diagnostic d'impossibilité | Satisfaction de contraintes (retour arrière, chemin critique, MRV) | 3 | `algorithms/csp_scheduler.py`, `algorithms/calendar.py` |
| Tournée des agences | Voyageur de commerce (Held-Karp ; plus proche voisin + 2-opt) | 30 | `algorithms/tsp.py`, `algorithms/geo.py` |
| Réparation après un retard | Min-Conflict | 11 | **non réalisé** (niveau B) |

## Résultats mesurés

Les mesures portent sur le projet de démonstration « Boutique Soa » et sur des instances aléatoires reproductibles. Les temps dépendent de la machine. Les données brutes sont dans [docs/benchmark_resultats.json](docs/benchmark_resultats.json), et la page « Comparaison des méthodes » (administrateur) les recalcule en direct.

| Mesure | Résultat |
|---|---|
| Tests automatisés | **153 passent** (≈ 40 s), dont 93 sur les algorithmes ; toujours en mode simulé |
| Sac à dos, projet | 4 fonctionnalités sur 14, 5 541 000 Ar sur 6 000 000 (92 %), 136 h sur 200 ; **18 nœuds**, optimum prouvé |
| Sac à dos, aléatoire | même valeur que la force brute sur 200 instances ; 40 fonctionnalités : 8,8 ms en moyenne, 28,4 ms au pire (2 106 nœuds) ; écart moyen du glouton 5,3 % (au pire 13,1 %) |
| Planning (CSP), projet | 18 jours ouvrés (borne du chemin critique : 11), **optimum prouvé** ; 1re solution en 13 nœuds ; 8/8 contrôles (dont l'ordre des visites sur site) |
| Planning impossible (3 semaines) | détecté **sans recherche** (0 nœud), avec un diagnostic chiffré de charge |
| Tournée, projet | Held-Karp : 1 285,6 km, 1 542 777 Ar, soit 18 % de moins que l'ordre saisi |
| Tournée, 12 villes | Held-Karp 4 320 km en ≈ 36 ms ; plus proche voisin +18,4 % ; 2-opt 0 % |
| Held-Karp selon la taille | 43 ms en moyenne à 12 sites, 185 ms à 13 (seuil du sélecteur : 12) |

## Documentation

| Document | Contenu |
|---|---|
| [01_GUIDE_LANCEMENT.md](docs/01_GUIDE_LANCEMENT.md) | installation, lancement, tests, activation de Claude |
| [02_PLAN_DE_TEST.md](docs/02_PLAN_DE_TEST.md) | scénario de test écran par écran et route par route, et rapport d'exécution |
| [03_FONCTIONNALITES.md](docs/03_FONCTIONNALITES.md) | chaque fonctionnalité : besoin, écran, données, enchaînement |
| [04_ALGORITHMES_DANS_L_APP.md](docs/04_ALGORITHMES_DANS_L_APP.md) | chaque algorithme avec des données réelles, sa complexité et un exemple à la main |
| [05_RAPPEL_FASTAPI_ALEMBIC.md](docs/05_RAPPEL_FASTAPI_ALEMBIC.md) | rappel de cours illustré par le code du projet |
| [06_CODE_ALGORITHMES.md](docs/06_CODE_ALGORITHMES.md) | lecture commentée du code, tests, questions de jury |
| [07_PRESENTATION.md](docs/07_PRESENTATION.md) | soutenance : 15 diapositives, script oral, questions du jury |
| [SmartBricks_presentation.pptx](docs/SmartBricks_presentation.pptx) / [.pdf](docs/SmartBricks_presentation.pdf) | diaporama, généré par `docs/build_slides.py` |

## État du projet

- **Niveau A** : terminé. Parcours complet avec le fournisseur simulé, de la conversation à l'explication.
- **Niveau B** : non commencé (Min-Conflict, contrainte « sur site » reliée à la tournée, flèches de dépendance dans le Gantt, espace freelance, export PDF du cahier des charges).
- **Copilote Claude** : codé et testé avec un client simulé ; non testé avec une vraie clé. **Gemini** : codé, non testé.
- **Limite connue** : les frais de tournée ne sont pas réservés dans le budget du sac à dos. La synthèse le signale quand le total dépasse le budget.

## Stack

FastAPI (asynchrone), Pydantic v2, SQLAlchemy 2 asynchrone + asyncpg, Alembic, PostgreSQL 17 (Docker), JWT + argon2, pytest + httpx ; React 18 + TypeScript + Vite, Tailwind CSS, React Router, Recharts, react-leaflet.
