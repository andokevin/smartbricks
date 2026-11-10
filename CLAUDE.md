# SmartBricks — spécification pour Claude Code

SmartBricks est une plateforme qui transforme le besoin flou d'un client non technique en un projet informatique réaliste : périmètre chiffré, équipe de freelances, planning respectant toutes les contraintes, et tournée optimisée pour les interventions sur site à Madagascar.

Philosophie : oser rêver, réaliser son imagination pour améliorer le quotidien, et faire en sorte que la technologie serve l'humain.

Un **copilote LLM** dialogue avec le client et explique les résultats ; des **algorithmes mathématiques** prennent les décisions chiffrées. Le LLM ne calcule jamais un budget, un planning ou une tournée.

Travaille phase par phase, vérifie chaque point de contrôle, et termine tout le **niveau A** avant le **niveau B**.

## Règles de travail

- L'étudiant doit comprendre et défendre chaque fichier devant un jury : **commente en français**, surtout les algorithmes (but, idée, complexité, numéro dans la liste du cours).
- Les algorithmes sont des **fonctions pures** dans `backend/app/algorithms/`, sans dépendance à FastAPI, à la base ou au LLM, et testées avec pytest.
- Chaque résultat d'algorithme est **vérifié par une fonction indépendante** (par exemple `verify_schedule`) avant d'être renvoyé.
- Typage partout (type hints Python, TypeScript strict).
- Textes visibles en français ; montants en Ariary (Ar), entiers.
- La démonstration doit fonctionner **sans clé d'API** grâce au fournisseur LLM simulé (voir module A).

## Les algorithmes de la liste du cours

| N° | Algorithme | Module | Rôle |
|---|---|---|---|
| 33 | Métaheuristique & IA | A — Copilote et sélecteur de méthode | Dialogue avec le client, extraction structurée, explication ; choix automatique de la méthode de résolution selon la taille du problème |
| 29 | Sac à dos multidimensionnel | B — Cadrage du sprint | Fonctionnalités à livrer sous les contraintes de budget **et** d'heures |
| 22 | Agrégation pondérée | C — Matching | Score des freelances selon les poids réglés par le client |
| 21 | Optimisation de Pareto | C — Matching | Meilleurs compromis coût / rapidité / qualité |
| 3 | Satisfaction de contraintes (CSP) | D — Planification | Calendrier des tâches : dépendances, disponibilités, compétences, date limite |
| 30 | Voyageur de commerce | E — Tournée sur site | Ordre optimal des visites entre villes de Madagascar |
| 11 | Min-Conflict (niveau B) | D — Replanification | Réparer le planning après un retard en changeant le moins de choses possible |

## Enchaînement

```
Client (texte libre)
  → A. Copilote LLM : questions de précision, puis extraction JSON
       (fonctionnalités, valeur métier, heures, compétences, tâches, dépendances, sites)
  → le client vérifie et corrige les estimations
  → B. Sac à dos multidimensionnel : périmètre du sprint 1 (budget Ar, heures)
  → C. Matching : agrégation pondérée + front de Pareto → le client choisit son équipe
  → D. CSP : planning des tâches retenues avec l'équipe choisie
  → E. Voyageur de commerce : tournée des interventions sur site
  → A. Copilote LLM : explication en français simple, à partir des seuls chiffres calculés
```

## Stack

| Partie | Technologie |
|---|---|
| Backend | Python 3.11+, FastAPI (asynchrone), Pydantic v2, SQLAlchemy 2 asynchrone + asyncpg, Alembic |
| Base | PostgreSQL 17 dans Docker, **port 5435** (5432, 5433 et 5434 sont déjà utilisés par d'autres projets) |
| LLM | Gemini API ou Claude API, interchangeables, sorties JSON structurées ; fournisseur simulé par défaut |
| Frontend | React 18 + TypeScript + Vite, React Router, Tailwind CSS, Recharts, react-leaflet |
| Authentification | JWT, mots de passe hachés avec argon2 |
| Tests | pytest, httpx |
| Environnement | WSL Ubuntu, Docker Desktop, Node 20+, pnpm, venv Python (créé avec `uv` si le module venv manque) |

### Docker

```yaml
services:
  db:
    image: postgres:17
    environment:
      POSTGRES_USER: smartbricks
      POSTGRES_PASSWORD: smartbricks
      POSTGRES_DB: smartbricks
    ports: ["5435:5432"]
    volumes: [smartbricks_pg:/var/lib/postgresql/data]
volumes:
  smartbricks_pg:
```

### `.env.example`

```
DATABASE_URL=postgresql+asyncpg://smartbricks:smartbricks@localhost:5435/smartbricks
JWT_SECRET=change-me
LLM_PROVIDER=mock            # mock | gemini | claude
GEMINI_API_KEY=
GEMINI_MODEL=gemini-2.5-flash
ANTHROPIC_API_KEY=
CLAUDE_MODEL=claude-haiku-5-5
```

## Structure

```
smartbricks/
  docker-compose.yml
  backend/
    app/
      main.py
      config.py
      db.py
      models.py
      schemas.py
      security.py
      seed.py
      routers/              auth, assistant, projects, features, freelancers, matching, schedule, tours, benchmark
      services/             lien base ↔ algorithms ↔ llm
      llm/
        base.py             interface commune
        gemini.py
        claude.py
        mock.py             réponses déterministes pour la démo
        prompts.py
      algorithms/
        knapsack_md.py      module B (n°29)
        matching.py         module C (n°22 et n°21)
        csp_scheduler.py    module D (n°3)
        min_conflicts.py    module D, niveau B (n°11)
        tsp.py              module E (n°30)
        solver_selector.py  module A, partie hyper-heuristique (n°33)
        calendar.py         jours ouvrés, indisponibilités
        geo.py              distances entre villes
    alembic/
    tests/
    requirements.txt
  frontend/
  README.md
```

## Modèle de données

À partir du schéma du cahier des charges, étendu pour les freelances, les fonctionnalités et les sites.

- **users** : id, name, email (unique), password_hash, role (`CLIENT`, `FREELANCER`, `ADMIN`), organization_name, created_at
- **skills** : id, name (unique) — React, Node.js, FastAPI, PostgreSQL, Flutter, UI/UX, DevOps, Tests/QA, Réseau, Maintenance matériel…
- **freelancer_profiles** : id, user_id, city_id, hourly_rate_mga, rating (0–5), completed_projects, on_time_rate (0–1), hours_per_day, bio
- **freelancer_skills** : freelancer_id, skill_id, level (1–5)
- **freelancer_unavailability** : freelancer_id, start_date, end_date, reason
- **cities** : id, name, latitude, longitude — Antananarivo, Toamasina, Antsirabe, Fianarantsoa, Mahajanga, Toliara, Antsiranana, Morondava, Ambatondrazaka, Manakara, Ambositra, Nosy Be
- **projects** : id, client_id, title, description, budget_mga, budget_hours, start_date, target_deadline, base_city_id, status (`DRAFT`, `SCOPED`, `TEAM_SELECTED`, `PLANNED`), created_at
- **features** (les exigences du cahier des charges) : id, project_id, title, description, req_type (`FUNCTIONAL`, `TECHNICAL`, `SECURITY`, `COMPLIANCE`), business_value (1–100), estimated_hours, estimated_cost_mga, is_mandatory, depends_on_feature_ids (int[]), selected_for_sprint (bool)
- **tasks** : id, project_id, feature_id, title, description, required_skill_id, min_level, estimated_hours, on_site_city_id (nullable), status (`BACKLOG`, `TODO`, `IN_PROGRESS`, `REVIEW`, `DONE`, `OVERDUE`), priority, assigned_freelancer_id, start_date, end_date, deadline
- **task_dependencies** : task_id, depends_on_task_id, avec contrainte `task_id <> depends_on_task_id`
- **project_team** : project_id, freelancer_id
- **schedule_runs** : id, project_id, method, status, makespan_days, report (JSONB), created_at
- **tour_runs** : id, project_id, freelancer_id, method, order (JSONB), distance_km, cost_mga, created_at
- **assistant_conversations / assistant_messages** : historique du copilote

Le coût d'une fonctionnalité est estimé par `estimated_hours × taux horaire moyen des freelances qui ont la compétence`, recalculé quand l'équipe est choisie.

## Module A — Copilote LLM et sélecteur de méthode (n°33)

### Copilote

- `llm/base.py` définit `LLMProvider` avec `chat(messages, system) -> str` et `extract(messages, json_schema) -> dict`.
- **Gemini** : `response_mime_type="application/json"` et `response_json_schema`. **Claude** : sorties structurées (`output_config.format` avec le schéma JSON) — et non un outil forcé, car `tool_choice` forcé renvoie une erreur 400 sur plusieurs modèles Claude récents. Modèle `CLAUDE_MODEL` (défaut `claude-haiku-5-5`), `CLAUDE_MAX_TOKENS`, `CLAUDE_EFFORT=low`.
- **Mock** : réponses déterministes pour le projet de démonstration (voir le seed), pour que la démo marche sans clé ni réseau.
- **Suivi des coûts** : chaque appel payant est enregistré dans `llm_usage` (tokens d'entrée et de sortie, coût calculé avec `CLAUDE_PRICE_INPUT_PER_MTOK` / `CLAUDE_PRICE_OUTPUT_PER_MTOK`). Au-delà de `LLM_BUDGET_USD` (4 $), ou sans clé ou sans prix, bascule automatique en mock, signalée dans les logs. `GET /admin/llm-usage` (administrateur) affiche la consommation. `reset-demo` ne vide pas `llm_usage`.
- **Explication vérifiée** : chaque nombre du texte du LLM doit figurer dans les données fournies ; sinon le texte est remplacé par une explication générée à partir des données.

Comportement du copilote, dans le rôle d'un chef de produit bienveillant :
1. Il pose des questions de précision tant qu'il manque le budget, la date limite, la ville de base ou des fonctionnalités clés. Une question à la fois, en français simple. Il demande aussi le nombre d'heures de travail maximal du sprint 1 (`budget_hours`, facultatif) ; s'il manque, défaut = jours ouvrés jusqu'à la date limite × 6 h × 2 personnes, modifiable par le client. Démo Boutique Soa : 200 h.
2. Quand il a assez d'informations, il produit un JSON validé par Pydantic :
   ```json
   {
     "project": {"title": "", "description": "", "budget_mga": 0, "budget_hours": null, "deadline": "AAAA-MM-JJ", "base_city": ""},
     "features": [{"ref": "F1", "title": "", "description": "", "req_type": "FUNCTIONAL",
                   "business_value": 80, "estimated_hours": 24, "is_mandatory": true, "depends_on": []}],
     "tasks": [{"ref": "T1", "feature_ref": "F1", "title": "", "required_skill": "React",
                "min_level": 3, "estimated_hours": 8, "depends_on": [], "on_site_city": null}],
     "sites": ["Antananarivo", "Antsirabe"]
   }
   ```
3. Contrôles après extraction, sans LLM : compétences et villes reconnues (correspondance approchée avec la table), **détection de cycles** dans les dépendances (tri topologique de Kahn ; en cas de cycle, l'arête la moins justifiée est retirée et signalée), heures strictement positives. Si le JSON est invalide : une seule nouvelle tentative avec le message d'erreur.
4. **Explication** (`/explain`) : le LLM reçoit uniquement les résultats calculés (sprint, équipe, planning, tournée) et les reformule pour le client, avec la consigne de ne citer aucun chiffre absent des données fournies.

La question du client est toujours transmise comme donnée, jamais comme instruction système.

### Sélecteur de méthode (hyper-heuristique)

`solver_selector.py` choisit la méthode selon la taille et le temps disponible, et renvoie la raison de son choix (affichée à l'utilisateur) :

| Problème | Méthode exacte si… | Sinon |
|---|---|---|
| Sac à dos | ≤ 40 fonctionnalités : séparation et évaluation | glouton par densité, puis amélioration locale par échanges 1-1 |
| Voyageur de commerce | ≤ 12 sites : Held-Karp | plus proche voisin, puis 2-opt |
| CSP | recherche avec retour arrière, limite de 3 s | Min-Conflict à partir de la meilleure affectation partielle (niveau B) |

## Module B — Sac à dos multidimensionnel (n°29)

**Problème** : le client a plus de fonctionnalités rêvées que de moyens. On choisit celles du sprint 1.

```
maximiser   Σ v_i x_i                         v_i = valeur métier
sous        Σ c_i x_i ≤ budget_mga            c_i = coût estimé
            Σ h_i x_i ≤ budget_hours          h_i = heures estimées
            x_i = 1 si la fonctionnalité i est obligatoire
            x_j ≤ x_i si j dépend de i        (pas de paiement sans panier)
            x_i ∈ {0, 1}
```

**Méthode exacte : séparation et évaluation (branch and bound)**, en profondeur :
- objets triés par densité `v_i / (c_i / budget + h_i / heures)` ;
- à chaque nœud : inclure ou exclure l'objet ; abandon si une contrainte est violée, si une dépendance est rompue ou si une fonctionnalité obligatoire est exclue ;
- **borne supérieure** : pour chaque dimension séparément, la valeur du sac à dos fractionnaire sur cette seule dimension ; on garde le minimum des bornes. Chacune est une relaxation du problème, donc leur minimum reste une borne valide. Commenter ce raisonnement ;
- élagage si borne ≤ meilleure valeur trouvée.

**Méthodes de comparaison** : glouton par densité avec réparation des dépendances, et force brute pour les tests (n ≤ 15).

**Sortie** :
- fonctionnalités retenues et écartées, avec la raison ;
- valeur totale et taux d'utilisation de chaque dimension ;
- **« et si ? »** : on relance avec +10 % et +25 % de budget pour indiquer ce qui deviendrait possible (« avec 500 000 Ar de plus, vous ajoutez le paiement MVola ») ;
- message clair si les fonctionnalités obligatoires dépassent déjà le budget, avec le montant manquant.

## Module C — Matching freelance ↔ projet (n°22 et n°21)

**Candidats** : freelances possédant au moins une compétence requise par les tâches retenues.

**Critères**, calculés pour ce projet :

| Critère | Calcul | Sens |
|---|---|---|
| Coût | taux horaire × heures des tâches correspondant à ses compétences | à minimiser |
| Rapidité | heures de ces tâches / (heures par jour × part de jours disponibles d'ici la date limite) | à minimiser |
| Qualité | note × (0,5 + 0,5 × taux de livraison à l'heure) | à maximiser |
| Disponibilité | jours disponibles d'ici la date limite | à maximiser |
| Couverture | heures de tâches qu'il peut faire / heures totales des tâches retenues | à maximiser |

**Agrégation pondérée (n°22)** : normalisation min-max sur [0, 1] (inversée pour les critères à minimiser), puis `score = Σ w_k × n_k`. Le client règle les poids avec des curseurs (normalisés pour sommer à 1) ou choisit un préréglage : Économique, Rapide, Qualité, Équilibré. L'interface montre la contribution de chaque critère au score.

**Pareto (n°21)** :
- tri non dominé (**fronts** 1, 2, 3…, comme dans NSGA-II) sur les critères choisis par le client (par défaut : coût, rapidité, qualité) ;
- **meilleur compromis** : le point du premier front le plus proche du point idéal dans l'espace normalisé ;
- nuage de points coût × rapidité, avec le front mis en évidence et la taille des points liée à la qualité.

**Composition de l'équipe** : le client sélectionne les freelances, ou clique sur « Équipe suggérée ». Celle-ci est obtenue de façon gloutonne : on prend le meilleur score pour chaque compétence requise non encore couverte, puis on vérifie que les heures sont absorbables avant la date limite.

## Module D — Planification par CSP (n°3)

**Variables** : pour chaque tâche `t`, le couple `(freelance_t, début_t)`.

**Domaines** :
- freelances de l'équipe ayant la compétence requise au niveau minimal ;
- jours ouvrés entre le début du projet et la date limite.

**Durée** : `ceil(heures_t / heures_par_jour du freelance)` jours ouvrés **disponibles** du freelance (week-ends et indisponibilités exclus). `calendar.py` calcule la date de fin.

**Contraintes dures** :
1. **Dépendances** : `début_B ≥ fin_A` si B dépend de A (on ne teste pas l'API avant de l'avoir codée).
2. **Compétences** : le freelance a la compétence au niveau requis.
3. **Disponibilité** : la tâche ne tombe pas sur ses jours d'indisponibilité.
4. **Pas de chevauchement** : un freelance fait une tâche à la fois.
5. **Date limite** : `fin_t ≤ date limite du projet`.
6. **Sur site** (niveau B) : les tâches sur site d'un même freelance suivent l'ordre de la tournée du module E, avec un jour de trajet entre deux villes différentes.

**Résolution : retour arrière avec propagation.**
- **Propagation de bornes** avant la recherche : méthode du chemin critique sur le graphe des dépendances (dates au plus tôt et au plus tard, avec la durée minimale possible de chaque tâche). On élague les débuts impossibles et l'on détecte tout de suite si le chemin critique dépasse la date limite.
- **Choix de la variable** : parmi les tâches dont tous les prédécesseurs sont placés, celle qui a le **plus petit domaine** (MRV), puis la plus faible marge.
- **Choix de la valeur** : couples (freelance, début) triés par date de fin la plus tôt, puis par meilleur score de matching.
- **Vérification anticipée** (forward checking) : après chaque affectation, mise à jour des dates au plus tôt des successeurs ; retour arrière si l'un d'eux ne peut plus finir avant la date limite.
- **Optimisation** : une fois une première solution trouvée, on continue à chercher une **durée totale plus courte** (séparation et évaluation sur la date de fin du projet) jusqu'à la limite de temps.
- Limite de 3 s ; on renvoie la meilleure solution trouvée et le nombre de nœuds explorés.

**`verify_schedule`** : fonction indépendante qui revérifie les 5 contraintes et produit le rapport `{constraints_passed: true, checks: [...]}`.

**Diagnostic en cas d'échec**, précis et actionnable :
- « Le chemin critique (API → Tests → Déploiement) demande 23 jours ouvrés, la date limite en laisse 18 : repoussez la date de 5 jours ouvrés ou réduisez le périmètre. »
- « Aucun freelance de l'équipe n'a la compétence Flutter au niveau 3. »
- « Charge de Rivo : 140 h pour 96 h disponibles d'ici la date limite. »

**Min-Conflict (n°11, niveau B)** : `POST /tasks/{id}/propagate-delay`. On allonge la tâche, on repère les tâches en conflit, puis on réaffecte de façon répétée la variable en conflit vers la valeur qui crée le moins de conflits, en préférant ne pas changer de freelance. Le résultat indique combien de tâches ont été modifiées.

## Module E — Tournée sur site (n°30)

**Usage** : installation réseau, maintenance de matériel ou réunions de cadrage dans plusieurs villes ou agences.

- **Distance** entre deux villes : formule de haversine × 1,35 (facteur routier approximatif, à commenter comme une approximation).
- **Coût** : km × coût par km (paramètre, 1 200 Ar/km par défaut) ; durée : km / 40 km/h de moyenne.
- **Exacte, ≤ 12 sites : Held-Karp** (programmation dynamique sur les sous-ensembles, O(n² 2ⁿ)).
- **Approchée, au-delà** : plus proche voisin, puis amélioration **2-opt** jusqu'à ce qu'aucun échange n'améliore.
- Options : tournée fermée (retour à la ville de base) ou chemin ouvert.
- Sortie : ordre des villes, distance totale, coût, durée, méthode utilisée et écart avec la tournée dans l'ordre saisi.
- **Carte** : react-leaflet avec les tuiles OpenStreetMap ; si internet est indisponible, affichage SVG des villes à partir de leurs coordonnées.

## API (`/api/v1`)

```
POST /auth/register, /auth/login

POST /assistant/chat                          { project_id?, message } → réponse du copilote, brouillon JSON quand il est prêt
POST /assistant/confirm                       { conversation_id } → crée le projet, les fonctionnalités, les tâches et les sites

GET  /projects, GET /projects/{id}
PATCH /features/{id}                          le client corrige valeur, heures, caractère obligatoire

POST /projects/{id}/scope                     module B → sprint 1 + « et si ? »
GET  /projects/{id}/matching?w_cost=&w_speed=&w_quality=&w_availability=&w_coverage=&pareto=cost,speed,quality
POST /projects/{id}/team                      { freelancer_ids } ou { suggested: true }
POST /projects/{id}/solve-constraints         module D → planning + rapport de vérification ou diagnostic
                                              { scenario: "impossible" } ou { deadline } : test non enregistré
POST /projects/{id}/tour                      { freelancer_id?, closed: true, cost_per_km? } → module E
POST /projects/{id}/explain                   module A → explication en français
POST /tasks/{id}/propagate-delay              { delay_hours } → module D Min-Conflict (niveau B)

GET  /freelancers?skill=&city=
GET  /cities, GET /skills
GET  /assistant/conversations/{id}            historique et brouillon d'une conversation
GET  /admin/llm-usage                         consommation du LLM (administrateur)
GET  /benchmark                               exact vs approché pour les modules B, D, E
POST /admin/reset-demo                        uniquement en développement
```

## Seed de démonstration

`random.seed(42)`, données reproductibles :
- 12 villes de Madagascar avec leurs coordonnées ;
- environ 25 freelances aux prénoms malgaches (Rivo, Fara, Tiana, Hery, Njaka, Volana, Mamy, Lalaina…), répartis entre Tana, Fianarantsoa, Antsirabe, Toamasina et Mahajanga, avec des taux horaires de 15 000 à 60 000 Ar, des notes, des compétences et quelques indisponibilités ;
- un compte client `client@smartbricks.mg` / `demo1234` et un compte administrateur.

**Projet de démonstration**, également servi par le fournisseur simulé :
« Boutique Soa veut un site e-commerce avec paiement MVola, une application mobile de suivi des commandes, et l'installation du réseau dans ses agences de Tana, Antsirabe, Toamasina et Fianarantsoa. Budget 6 000 000 Ar, livraison dans 8 semaines. »

- Environ 14 fonctionnalités dont la somme dépasse le budget, pour que le sac à dos fasse de vrais choix ; 3 obligatoires ; des dépendances (paiement MVola → panier → catalogue).
- Environ 30 tâches avec dépendances réalistes (maquettes → front → intégration API → tests → déploiement).
- 4 tâches sur site (une par agence).
- Un bouton « Scénario impossible » qui réduit la date limite à 3 semaines, pour montrer le diagnostic du CSP.

## Frontend

1. **Connexion.**
2. **Copilote** : conversation, puis aperçu du brouillon extrait (fonctionnalités, tâches, sites) modifiable avant confirmation.
3. **Périmètre (sac à dos)** : tableau des fonctionnalités (valeur, heures, coût, obligatoire, retenue ou non avec la raison), jauges budget et heures, encart « et si ? », méthode utilisée.
4. **Matching** : curseurs de poids et préréglages, classement avec barres de contribution, nuage de Pareto avec le front et le meilleur compromis, bouton « Équipe suggérée ».
5. **Planning (CSP)** : diagramme de Gantt (une ligne par freelance, flèches de dépendance si possible), rapport de vérification des contraintes, diagnostic en cas d'échec, statistiques (nœuds explorés, durée de résolution).
6. **Tournée (TSP)** : carte avec l'itinéraire numéroté, distance, coût et durée, comparaison avec l'ordre saisi.
7. **Explication** : texte du copilote résumant le plan pour le client.
8. **Benchmark** : exact contre approché pour le sac à dos, le CSP et le voyageur de commerce (valeur, écart, temps), avec le numéro de chaque algorithme dans la liste du cours.

Interface en français, sobre, utilisable sur mobile.

## Tests

- **Sac à dos** : égal à la force brute sur 200 instances aléatoires à 2 dimensions avec obligations et dépendances ; jamais de dépassement ; détection du cas impossible.
- **Matching** : aucun point du premier front n'est dominé ; chaque point d'un front k est dominé par au moins un point du front k−1 ; des poids 100 % coût classent par coût croissant.
- **CSP** : `verify_schedule` valide toutes les solutions sur des instances aléatoires ; une instance dont le chemin critique dépasse la date limite est déclarée impossible avec le bon diagnostic ; les indisponibilités sont respectées.
- **Voyageur de commerce** : Held-Karp égal à la force brute (n ≤ 8) ; 2-opt jamais meilleur que Held-Karp ; 2-opt jamais pire que le plus proche voisin.
- **Copilote** : avec le fournisseur simulé, l'extraction produit un JSON valide ; une dépendance cyclique est détectée et retirée.
- **API** : parcours complet sur le projet de démonstration.

## Phases

**Niveau A**
1. Docker, backend FastAPI qui démarre, Alembic, frontend Vite. *Contrôle : `/docs` et `pnpm dev` fonctionnent.*
2. Modèles, migrations, authentification, seed. *Contrôle : `POST /admin/reset-demo` remplit la base.*
3. Algorithmes : `knapsack_md`, `matching`, `calendar`, `csp_scheduler` (avec `verify_schedule`), `geo`, `tsp`, `solver_selector`, et leurs tests. *Contrôle : `pytest` passe.*
4. Copilote : fournisseurs mock, Gemini et Claude, extraction validée, détection de cycles, explication.
5. Routes des modules A à E. *Contrôle : parcours complet depuis `/docs` avec le projet de démonstration.*
6. Interface : copilote, périmètre, matching, planning, tournée, explication.
7. Benchmark et README (installation, lancement, tableau « fonctionnalité → algorithme → numéro », résultats mesurés).

**Niveau B** : Min-Conflict et `propagate-delay`, contrainte « sur site » reliée à la tournée dans le CSP, flèches de dépendance dans le Gantt, espace freelance (voir ses tâches), export PDF du cahier des charges généré.

## Définition de « terminé » (niveau A)

1. Le client décrit son projet au copilote, répond à ses questions et confirme le brouillon (fonctionne avec `LLM_PROVIDER=mock`).
2. Le périmètre du sprint 1 respecte le budget et les heures, et garde les obligatoires et les dépendances ; l'encart « et si ? » propose une option.
3. Le matching réagit aux curseurs ; le front de Pareto et le meilleur compromis sont visibles ; l'équipe suggérée est appliquée.
4. Le planning respecte toutes les contraintes (`constraints_passed: true`) et s'affiche en Gantt ; le scénario impossible produit un diagnostic chiffré.
5. La tournée entre Tana, Antsirabe, Toamasina et Fianarantsoa s'affiche sur la carte avec distance et coût, par Held-Karp.
6. Le copilote explique le plan en français simple.
7. `pytest` passe, et le README permet de tout lancer en moins de 10 minutes.
