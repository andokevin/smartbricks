# Plan du cours SmartBricks (31 leçons)

Ordre : celui de la construction du projet (voir `git log --reverse`), backend d'abord.

## Partie A — Les fondations
1. **Création du projet** — l'arborescence des dossiers, le rôle de chacun, et la règle « routeur → service → algorithme » qui organise tout le backend.
2. **Installation** — le venv Python, chaque paquet de `requirements.txt` et l'endroit où il sert, puis `pnpm install` côté frontend.
3. **Docker** — `docker-compose.yml` ligne par ligne (image, variables, port **5435**, volume, healthcheck) et les commandes pour piloter le conteneur.
4. **Configuration** — `.env`, `.env.example` et `config.py` : comment chaque variable est lue, typée et validée.
5. **Base de données** — `db.py` : le moteur asynchrone, la fabrique de sessions et `get_session`, qui ouvre puis ferme une session à chaque requête.
6. **Les modèles** — `models.py` table par table (colonnes, clés étrangères, relations), chacune reliée à un besoin du projet.
7. **Alembic** — `alembic.ini`, `env.py`, les 3 migrations du dossier `versions/` et les commandes `revision --autogenerate`, `upgrade`, `downgrade`, `history`, `current`.
8. **Le point d'entrée** — `main.py` : création de l'application, CORS, route `/health`, gestion des erreurs métier et inclusion des routeurs.

## Partie B — Les fonctionnalités du backend
9. **Authentification** — `security.py` (argon2, JWT, `get_current_user`, `require_role`) et le routeur `auth`.
10. **Les schémas Pydantic** — `schemas.py` : ce que l'API accepte en entrée et renvoie en sortie.
11. **Le seed de démonstration** — `demo_data.py`, `seed.py` et la route `POST /admin/reset-demo`.
12. **Le copilote LLM** — l'interface `LLMProvider`, les fournisseurs mock, Claude et Gemini, les consignes, le brouillon `Draft`, le suivi des coûts avec bascule en mock, puis le routeur `assistant` (leçon découpée en parties).
13. **Le périmètre** — route `POST /projects/{id}/scope` → `services/scoping.py` → sac à dos.
14. **Le matching** — route `GET /projects/{id}/matching` → `services/matching_service.py` → agrégation pondérée et Pareto.
15. **L'équipe et le planning** — routes `team` et `solve-constraints` → `services/scheduling.py` → CSP et `verify_schedule` (et la réparation après un retard, niveau B).
16. **La tournée** — route `POST /projects/{id}/tour` → `services/touring.py` → voyageur de commerce.
17. **L'explication et le benchmark** — `services/explaining.py` (explication vérifiée), `services/benchmark.py`, et l'export PDF du cahier des charges.

## Partie C — Les algorithmes
18. **`knapsack_md.py`** (n°29) — séparation et évaluation avec la borne « minimum des sacs fractionnaires », glouton, « et si ? ».
19. **`matching.py`** (n°22 et n°21) — normalisation min-max, score pondéré, fronts de Pareto, meilleur compromis, équipe suggérée.
20. **`calendar.py`** — jours ouvrés, indisponibilités, date de fin d'une tâche.
21. **`csp_scheduler.py`** (n°3) — chemin critique, MRV, forward checking, optimisation de la durée, diagnostic ; avec `min_conflicts.py` (n°11) en complément.
22. **`geo.py`** — formule de haversine, facteur routier 1,35, coût et durée d'un trajet.
23. **`tsp.py`** (n°30) — Held-Karp, plus proche voisin, 2-opt.
24. **`dependencies.py`** — tri topologique de Kahn et suppression des cycles dans le brouillon du copilote.
25. **`solver_selector.py`** (n°33) — choix exact ou approché selon la taille, avec la raison affichée.

## Partie D — Le frontend
26. **Configuration** — Vite (et son proxy `/api`), TypeScript strict, Tailwind.
27. **Le client API et l'authentification** — `api/client.ts`, `api/types.ts`, `auth/AuthContext.tsx`.
28. **La navigation** — `main.tsx`, `App.tsx`, `AppShell.tsx`, `lib/steps.ts` : routes et étapes du parcours.
29. **Chaque écran** — connexion, tableau de bord, copilote, périmètre, équipe, planning, tournée, synthèse, comparaison des méthodes, espace freelance (leçon découpée en parties).

## Partie E — Les tests et le lancement
30. **Les tests** — `pytest.ini`, `conftest.py`, les fixtures, les tests d'algorithmes et d'API, et comment lancer `pytest`.
31. **Le démarrage de zéro** — de la machine vide à l'application qui tourne, avec les problèmes fréquents.
