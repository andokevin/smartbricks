# 02 — Plan de test

Ce document décrit un **scénario de test manuel complet** de SmartBricks, écran par écran et route par route, puis le **rapport de son exécution** (fin du document). Il suppose l'installation décrite dans `01_GUIDE_LANCEMENT.md`, avec `LLM_PROVIDER=mock` : aucun appel à une API payante n'est fait.

Conventions :
- **Action** : ce que fait le testeur ; **Attendu** : ce qui doit se produire ; **Vérifier** : comment s'en assurer (dans l'interface, dans `/docs`, ou dans la base).
- Les chiffres indiqués (coûts, jours, kilomètres) sont ceux obtenus avec les données de démonstration (graine 42) : ils sont **reproductibles** après `POST /admin/reset-demo`. Seuls les temps de calcul varient d'une machine à l'autre.
- `/docs` désigne la documentation interactive de l'API : <http://localhost:8000/docs>. Pour les routes protégées, cliquer sur **Authorize** et coller le jeton obtenu par `POST /auth/login`.

---

## 0. Préparation

| # | Action | Attendu | Vérifier |
|---|---|---|---|
| 0.1 | Lancer PostgreSQL, le backend et le frontend (guide § 2) | Les trois répondent | `GET /api/v1/health` → `{"status":"ok","database":"ok","llm_provider":"mock","environment":"development"}` ; <http://localhost:5173> affiche la page de connexion |
| 0.2 | `POST /api/v1/admin/reset-demo` (dans `/docs`, sans jeton) | `200` avec `demo_project_id: 1, freelancers: 25, features: 14, tasks: 30` | La réponse liste aussi les comptes de démonstration |

---

## 1. Connexion (`/connexion`)

| # | Action | Attendu | Vérifier |
|---|---|---|---|
| 1.1 | Saisir `client@smartbricks.mg` avec un mauvais mot de passe | Message « Email ou mot de passe incorrect. » | La route `POST /auth/login` renvoie `401` |
| 1.2 | Cliquer sur le bouton « Cliente — Soa (Boutique Soa) » | Redirection vers le tableau de bord, « Bonjour Soa » | Le jeton est dans `localStorage` (`smartbricks_token`) ; `GET /auth/me` renvoie `role: CLIENT`, `organization_name: Boutique Soa` |
| 1.3 | Ouvrir <http://localhost:5173/> dans un onglet privé (sans jeton) | Redirection vers `/connexion` | `GET /projects` sans jeton → `401` |
| 1.4 | Dans `/docs`, `POST /auth/register` avec `role: "ADMIN"` | Refus | `403 Impossible de créer un compte administrateur.` |

---

## 2. Tableau de bord (`/`)

| # | Action | Attendu | Vérifier |
|---|---|---|---|
| 2.1 | Observer les quatre cartes du haut | « Projets : 1 », « Budget total déclaré : 6 000 000 Ar », « Copilote : Simulé — Démo sans clé ni réseau » | Les valeurs viennent de `GET /projects` et `GET /health` |
| 2.2 | Carte du projet « Boutique Soa » | Statut **Brouillon**, barre de progression avec 1 segment vert (copilote), bouton « Continuer : Périmètre » | `GET /projects` → `status: DRAFT` |
| 2.3 | Encadré « Qui décide quoi ? » | 6 étapes avec leur numéro d'algorithme (33, 29, 22·21, 3, 30, 33) | — |
| 2.4 | Bouton « Réinitialiser la démo », confirmer | Déconnexion, retour à la page de connexion ; les projets créés à la main ont disparu | `GET /projects` après reconnexion : un seul projet |

---

## 3. Copilote (`/copilote`, étape 1)

| # | Action | Attendu | Vérifier |
|---|---|---|---|
| 3.1 | Menu « Nouveau projet », cliquer sur « Utiliser l'exemple Boutique Soa » | Le copilote répond par **une seule question** : « …faut-il prévoir la livraison à domicile… ? ». Badge « Simulé ». Deux réponses rapides apparaissent | `POST /assistant/chat` → `ready: false`, `provider: "mock"` |
| 3.2 | Cliquer « Oui, livraison à domicile » | Le copilote résume et annonce le brouillon ; la colonne de droite affiche **14 briques**, 30 tâches, 4 sites, 374 h estimées | `POST /assistant/chat` → `ready: true`, `draft.features` a 14 éléments |
| 3.3 | Recharger la page (l'URL contient `?conversation=N`) | La conversation et le brouillon sont retrouvés | `GET /assistant/conversations/{N}` |
| 3.4 | Dans le brouillon, passer la valeur de F3 « Paiement MVola » à 95, puis les heures de F1 à 60 | Le curseur et le champ changent ; le total d'heures des tâches de F1 vaut 60 (tâches mises à l'échelle, visibles dans « Tâches (30) ») | — |
| 3.5 | Cliquer « Valider le brouillon et passer au Périmètre » | Redirection vers `/projets/2/perimetre` ; nouveau projet n°2 au statut Brouillon | `POST /assistant/confirm` → `201`, `project_id: 2`, `tasks: 30`, `sites` = les 4 villes |
| 3.6 | Rappeler `POST /assistant/confirm` avec la même conversation (dans `/docs`) | Refus | `409 Projet déjà créé (n°2).` |
| 3.7 | Ouvrir `/projets/2/copilote` | Conversation d'origine en lecture seule + brouillon confirmé | `GET /assistant/projects/2/conversation` → `status: CONFIRMED`, 4 messages |
| 3.8 | Ouvrir `/projets/1/copilote` (projet du seed) | Encart « Projet de démonstration » (pas de conversation), brouillon affiché | `GET /assistant/projects/1/conversation` → `404` |
| 3.9 | Dans `/docs`, envoyer au copilote un message court (« bonjour ») | Il demande de décrire le projet ; puis, sans budget, il demande le budget | Réponses successives `ready: false` |

**Contrôles sans LLM** (dans `/docs`, `POST /assistant/confirm` avec un `draft` modifié) :

| # | Modification du brouillon | Attendu |
|---|---|---|
| 3.10 | Une tâche avec `estimated_hours: 0` | `422` « Schéma non respecté : tasks.0.estimated_hours … » |
| 3.11 | Une tâche avec `required_skill: "Cobol"` | `422` « Compétences inconnues : T1 (Cobol)… » |
| 3.12 | `required_skill: "react.js"` et `on_site_city: "Tamatave"` | `201` et `warnings` : « reconnue comme React », « reconnue comme Toamasina » |
| 3.13 | T3 avec `depends_on: ["T5"]` (T5 → T2 → T3 → T5 = cycle) | `201` et un avertissement « Dépendance circulaire détectée : la dépendance « T3 dépend de T5 » a été retirée » |

---

## 4. Périmètre — sac à dos n°29 (`/projets/1/perimetre`)

| # | Action | Attendu | Vérifier |
|---|---|---|---|
| 4.1 | Ouvrir l'écran avant tout calcul | Encart « Le périmètre n'a pas encore été calculé » | `GET /projects/1/scope` → `404` ; `GET /projects/1/matching` → `409` |
| 4.2 | Cliquer « Calculer le périmètre » | Jauges : **5 541 000 Ar / 6 000 000 (92 %)** et **136 h / 200 h (68 %)**. Briques retenues : **F1, F2, F4, F11** (4/14), valeur **320**. Bandeau « Séparation et évaluation · 18 nœuds ». Badge « Optimum prouvé » | `POST /projects/1/scope` → `feasible: true`, `optimal: true`, `verification: []` |
| 4.3 | Lire les lignes écartées | Chaque brique écartée a une raison chiffrée, ex. F3 : « Ne tient pas dans le budget restant : il faudrait 464 000 Ar de plus. » | `features[].reason` non vide pour `selected: false` |
| 4.4 | Encart « Et si ? » | +10 % (+600 000 Ar) : « vous ajoutez : Paiement MVola » ; +25 % : Paiement MVola, Protection des données, Orange Money | `what_if[0].added == ["F3"]` |
| 4.5 | Recharger la page | Même résultat, sans recalcul | `GET /projects/1/scope` identique au `POST` |
| 4.6 | « Corriger les estimations » → heures de F3 : 48 | Le calcul se relance ; le coût de F3 augmente ; dans `/projets/1`, les tâches T7+T8 totalisent 48 h | `PATCH /features/{id}` → `estimated_hours: 48` ; le projet repasse en `DRAFT`, puis `SCOPED` après le recalcul |
| 4.7 | Cocher « obligatoire » pour F13 | F13 devient **Retenue** au recalcul | `selected: true` pour F13 |
| 4.8 | Remettre F3 à 24 h et F13 non obligatoire | Retour au périmètre de 4.2 | — |
| 4.9 | (API) `PATCH /features/{id}` d'une fonctionnalité d'un projet d'un autre client | `403` | — |

---

## 5. Équipe — agrégation n°22 et Pareto n°21 (`/projets/1/equipe`)

| # | Action | Attendu | Vérifier |
|---|---|---|---|
| 5.1 | Ouvrir l'écran | Chiffres : 136 h à réaliser (12 tâches), 40 jours ouvrés, 23 freelances classés dont 9 sur le front 1. Préréglage « Équilibré » | `GET /projects/1/matching?preset=Équilibré` |
| 5.2 | Cliquer « Économique » puis « Rapide » | Le classement change (en Économique, Rado Ramaroson est premier ; en Rapide, Nirina Rakotobe) | `ranking[0].name` diffère entre les deux appels |
| 5.3 | Mettre le curseur Coût au maximum et les autres à zéro | Le classement est trié par coût croissant ; les barres de contribution ne montrent plus que le bleu | `GET …?w_cost=1` → `criteria.cost` croissant |
| 5.4 | Carte d'un freelance | Score /100, taux horaire, barre de contribution avec légende chiffrée, 5 valeurs brutes, compétences avec niveau, badge « Front de Pareto » pour le front 1 | `contributions` somme au `score` |
| 5.5 | Nuage de Pareto | 23 points ; front 1 en bleu, autres en gris ; étoile « Meilleur compromis » (Toky Ramanantsoa avec les critères par défaut) ; taille = qualité | `best_compromise` ∈ `fronts[0]` |
| 5.6 | Retirer « Qualité » des critères de Pareto | Le front est recalculé sur coût + rapidité | `GET …?pareto=cost,speed` |
| 5.7 | Essayer de retirer un deuxième critère | Impossible : il en faut au moins 2 | API : `pareto=cost` → `422` |
| 5.8 | Cliquer « Équipe suggérée » | 4 membres cochés : Hasina (React, Node.js), Soloniaina (Réseau), Nirina (UI/UX), Fanja (PostgreSQL, FastAPI) ; message « charge absorbable » ; sélection en direct « 12/12 tâches couvertes » | `POST /projects/1/team {"suggested": true}` → `absorbable: true`, `warnings: []` ; statut `TEAM_SELECTED` |
| 5.9 | Décocher Soloniaina | Encadré « Compétences non couvertes : Réseau niv. 3 » | — |
| 5.10 | (API) `POST /team {"freelancer_ids": [999]}` | `422 Freelances inconnus : [999].` | — |
| 5.11 | Cliquer « Confirmer l'équipe et passer au planning » (équipe suggérée recochée) | Redirection vers le planning | — |

---

## 6. Planning — CSP n°3 (`/projets/1/planning`)

| # | Action | Attendu | Vérifier |
|---|---|---|---|
| 6.1 | Ouvrir l'écran avant calcul | Encart « Le planning n'a pas encore été calculé » | `GET /projects/1/schedule` → `404` |
| 6.2 | Cliquer « Calculer le planning » | **18 jours ouvrés** (borne du chemin critique : 11), fin le **9 décembre 2026**, marge 22 j, 4 freelances, 136 h sur 12 tâches, « Optimale », ≈ 24 400 nœuds | `POST /projects/1/solve-constraints {"scenario":"normal"}` → `status: OK`, `optimal: true`, `makespan_days: 18` |
| 6.3 | Diagramme de Gantt | Une ligne par freelance, axe en jours ouvrés par semaine, barres colorées, tâches du chemin critique entourées (T3 → T2 → T4 → T6), icône sur les 4 tâches sur site, trait rouge « Date limite » ; survol = détail | `assignments` : 12 lignes avec `start`, `end`, `days` |
| 6.4 | Panneau « Vérification des contraintes » | **7/7 validées** : toutes planifiées, dépendances, compétences, disponibilité, durées, pas de chevauchement, date limite | `verification.constraints_passed: true` |
| 6.5 | « Voir le planning en tableau » | 12 lignes, dates cohérentes avec le Gantt | — |
| 6.6 | Tableau de bord | Le projet est **Planifié** ; étapes 1 à 4 « Fait » | `GET /projects/1` → `PLANNED`, tâches retenues avec `start_date`/`end_date` |

---

## 7. Scénario impossible (date limite à 3 semaines)

| # | Action | Attendu | Vérifier |
|---|---|---|---|
| 7.1 | Cliquer « Scénario impossible (3 semaines) » | Bandeau orange « Scénario de test — Planning impossible avec une date limite au 4 décembre 2026 (15 jours ouvrés) » puis le diagnostic : « Charge de Hasina Rakotondrabe : les 6 tâches que cette personne est seule à pouvoir faire (84 h à 6 h par jour) demandent 16 jours ouvrés, pour 15 jours ouvrés disponibles d'ici la date limite : repoussez la date de 1 jour ouvré ou ajoutez un renfort. » et « Impossibilité détectée avant toute recherche » | `POST …/solve-constraints {"scenario":"impossible"}` → `status: INFEASIBLE`, `nodes: 0`, `diagnostics` non vide |
| 7.2 | Le planning réel sous le bandeau | Inchangé (18 jours, 9 décembre) | `GET /projects/1/schedule` → même `run_id` qu'en 6.2 ; les tâches gardent leurs dates |
| 7.3 | Ouvrir `/projets/1/planning?scenario=impossible` | Le scénario se lance tout seul à l'ouverture | — |
| 7.4 | (API) `{"deadline": "2026-11-20"}` (5 jours ouvrés) | Diagnostic de chemin critique : « Le chemin critique (…) demande 11 jours ouvrés, la date limite en laisse 5 : repoussez la date de 6 jours ouvrés ou réduisez le périmètre. » | `scenario: "date de test"` |

---

## 8. Tournée — voyageur de commerce n°30 (`/projets/1/tournee`)

| # | Action | Attendu | Vérifier |
|---|---|---|---|
| 8.1 | Ouvrir l'écran | Carte OpenStreetMap avec 4 étapes numérotées ; départ **Fianarantsoa** (ville de Soloniaina, qui fait les tâches sur site) ; encart « Méthode exacte · Held-Karp » ; **1 286 km, 1 542 777 Ar, 32,1 h** ; bandeau « −18 % par rapport à l'ordre saisi (285 km et 342 471 Ar économisés) » | `GET /projects/1/tour?closed=true` → `saved: false`, `method.method: "Held-Karp"` |
| 8.2 | Basculer « Schéma hors ligne » | Les 4 villes placées d'après leurs coordonnées sur le contour de l'île, itinéraire tracé | Lien direct `?vue=schema` |
| 8.3 | Choisir le technicien « Hery … — Antsirabe » | Le départ devient Antsirabe ; feuille de route recalculée | `GET …/tour?freelancer_id=4` → `start.name: "Antsirabe"` |
| 8.4 | Décocher « Retour à la ville de départ » | Chemin ouvert, plus court (ex. 692 km depuis Fianarantsoa ; 951 km depuis Tana) | `closed=false` → `distance_km` inférieure |
| 8.5 | Mettre 1 500 Ar/km | Le coût est recalculé : km × 1 500 | `cost_per_km=1500` |
| 8.6 | Cliquer « Valider la tournée » | Badge « Tournée enregistrée » | `POST /projects/1/tour` → `saved: true` ; `GET /projects/1/tour-run` renvoie le même ordre |
| 8.7 | Couper internet (ou bloquer `tile.openstreetmap.org`) et recharger | Bascule automatique sur le schéma avec le message « Carte en ligne indisponible » | — |

---

## 9. Synthèse et explication — copilote n°33 (`/projets/1/synthese`)

| # | Action | Attendu | Vérifier |
|---|---|---|---|
| 9.1 | Ouvrir l'écran | Chiffres clés (valeur 320, budget engagé, livraison 9 décembre 2026, 4 freelances) ; l'explication du copilote s'affiche en 5 paragraphes avec le badge **« Chaque chiffre vérifié dans les données »** | `POST /projects/1/explain {}` → `provider: "mock"`, `replaced: false`, `unknown_numbers: []` |
| 9.2 | Lire le texte | Il ne cite que des chiffres présents dans les résultats (budget, coût du sprint, heures, dates, km, Ar de la tournée validée) | Comparer avec les écrans précédents |
| 9.3 | Poser la question « Pourquoi le paiement MVola n'est pas retenu ? » et « Demander » | Une nouvelle explication est produite (en mode mock, le texte est le même : le fournisseur simulé ne lit pas la question) | `POST …/explain {"question": "…"}` → `200` |
| 9.4 | Sections 1 à 4 | 1 : les 4 briques livrées avec leur date de fin tirée du planning, puis les 10 reportées ; 2 : l'équipe avec heures planifiées × taux ; 3 : calendrier et tournée validée ; 4 : tableau du budget avec le total | Les montants sont heures × taux des `assignments` et `cost_mga` de `tour-run` |
| 9.5 | Encart sous le budget | Si le total dépasse 6 000 000 Ar : message « Dépassement de … : le cadrage portait sur le coût des fonctionnalités… » (voir le rapport, point à connaître) | — |
| 9.6 | « Imprimer / PDF » | La boîte d'impression s'ouvre sans la navigation | — |

---

## 10. Comparaison des méthodes — benchmark (`/admin/benchmark`)

| # | Action | Attendu | Vérifier |
|---|---|---|---|
| 10.1 | Connecté comme **client**, ouvrir `/admin/benchmark` | Message « réservé à l'administrateur » | `GET /benchmark` avec un jeton client → `403` |
| 10.2 | Se déconnecter, se connecter comme **Administrateur** ; menu « Comparaison des méthodes » | Après ≈ 5 s : trois sections (n°29, n°3, n°30) et la matrice du sélecteur n°33 | `GET /benchmark?project_id=1` → `200` en ≈ 4,5 s |
| 10.3 | Section sac à dos, ligne « Projet » | Exact 350 contre glouton 345 (+1,43 % d'écart) et échanges 350 (optimum) ; 20 nœuds | `knapsack.project.greedy.gap_pct ≈ 1.43` |
| 10.4 | Section planning | Optimisé 18 j = première solution 18 j ; borne 11 j ; l'optimisation prend ≈ 370 ms contre ≈ 2 ms | `csp.project.optimized.optimal: true` |
| 10.5 | Section tournée, « Les 12 villes » | Held-Karp 4 320 km ; plus proche voisin 5 114 km (+18,4 %) ; 2-opt 4 320 km | `tsp.national` |
| 10.6 | Barres « Temps de Held-Karp selon le nombre de sites » | Croissance forte entre 12 et 13 sites (la barre 13 est en orange) | `tsp.random` |
| 10.7 | « Exporter (JSON) » | Un fichier `smartbricks_benchmark.json` est téléchargé | — |
| 10.8 | Choisir « Instances aléatoires seulement » | Les lignes « Projet » disparaissent, les tableaux aléatoires restent | `GET /benchmark` sans `project_id` |

---

## 11. Administration du copilote et contrôle d'accès

| # | Action | Attendu | Vérifier |
|---|---|---|---|
| 11.1 | Administrateur, `GET /admin/llm-usage` dans `/docs` | `effective_provider: "mock"`, `budget_usd: 4.0`, `spent_usd: 0.0`, listes vides | — |
| 11.2 | Client, même route | `403` | — |
| 11.3 | Créer un second compte client (`POST /auth/register`) et appeler `GET /projects/1` avec son jeton | `403 Ce projet appartient à un autre client.` ; `GET /projects` renvoie `[]` | — |
| 11.4 | Administrateur, `GET /projects/1` | `200` (l'administrateur voit tout) | — |

---

## 12. Tests automatisés

| # | Action | Attendu |
|---|---|---|
| 12.1 | `cd backend && .venv/bin/pytest -q` | Tous les tests passent (voir le rapport pour le nombre) ; durée ≈ 20 s |
| 12.2 | `cd frontend && pnpm build` | Compilation TypeScript stricte sans erreur |

Ce que couvrent les tests (`backend/tests/`) :

| Fichier | Vérifie |
|---|---|
| `algorithms/test_knapsack_md.py` | égalité avec la force brute sur 200 instances ; obligatoires, dépendances, deux dimensions, cas impossible, raisons, « et si ? » |
| `algorithms/test_matching.py` | critères, normalisation, poids 100 % coût, propriétés des fronts sur 150 instances, meilleur compromis, équipe suggérée |
| `algorithms/test_calendar.py`, `test_csp_scheduler.py` | jours ouvrés ; `verify_schedule` sur 60 instances ; les 3 diagnostics ; congés ; optimisation jamais dégradante |
| `algorithms/test_geo.py`, `test_tsp.py` | haversine ; Held-Karp = force brute ; Held-Karp ≤ 2-opt ≤ plus proche voisin |
| `algorithms/test_solver_selector.py`, `test_dependencies.py` | seuils du sélecteur ; cycles cassés (Kahn) sur 200 graphes |
| `test_copilot.py`, `test_llm_usage.py` | dialogue simulé, extraction, correspondance approchée, nouvelle tentative, explication vérifiée ; coût, budget, bascule en mock, client Claude simulé |
| `test_auth.py`, `test_seed.py`, `test_api_flow.py`, `test_benchmark.py`, `test_health.py` | authentification ; seed reproductible ; parcours complet de l'API ; cohérence du benchmark et accès |

---

## Rapport d'exécution (11 novembre 2026)

**Comment le scénario a été exécuté.** Les sections 0 à 11 ont été rejouées par un script HTTP (`httpx`) contre l'API lancée localement, après `reset-demo` ; la section 12 par `pytest` et `pnpm build`. Les écrans ont été vérifiés visuellement dans Chrome (ordinateur et mobile) lors de la phase 6 ; ce rapport porte sur les routes.

### Ce qui marche

- **45 vérifications sur 45** réussies par les routes (sections 0 à 11), dont : les 5 contrôles sans LLM du copilote ; `GET /scope` identique au `POST` ; le changement de classement entre préréglages (Rado Ramaroson premier en Économique, Nirina Rakotobe en Rapide) ; le planning optimal prouvé en 18 jours (24 399 nœuds, 369 ms) avec 7/7 contrôles indépendants ; le scénario impossible détecté **avant toute recherche** (0 nœud) sans altérer le planning réel ; la tournée Held-Karp (1 285,6 km, 1 542 777 Ar, gain de 285,4 km) ; l'explication vérifiée sans chiffre inventé ; les refus `401`/`403`/`409`/`422` attendus ; le benchmark cohérent en 4,5 s.
- **`pytest` : 124 tests passés en 19,5 s** (les 5 plus lents : benchmark 4,8 s, CSP aléatoire 1,9 s, choix du fournisseur Claude 1,2 s, optimisation CSP 0,9 s, parcours API 0,8 s).
- **`pnpm build`** : compilation sans erreur.

### Ce qui échoue

Aucune vérification en échec.

### Points à connaître (comportements réels, documentés et non corrigés)

1. **Budget et tournée (9.5).** Le sac à dos respecte le budget sur le coût des fonctionnalités (5 541 000 Ar au cadrage). Mais la synthèse additionne les heures planifiées × les taux réels de l'équipe (5 216 000 Ar) et les frais de la tournée (1 542 777 Ar) : le total, 6 758 777 Ar, dépasse les 6 000 000 Ar. L'écran l'indique honnêtement. Trois options ont été proposées (réserver les frais de tournée avant le sac à dos ; intégrer le déplacement aux tâches sur site au niveau B ; présenter la tournée comme budget logistique distinct) ; la décision est en attente.
2. **Barre latérale.** L'étape « Tournée » reste « En cours » après validation de la tournée : l'état des étapes ne dépend que du statut du projet, qui s'arrête à `PLANNED`.
3. **Explication avec question (9.3).** En mode mock, le fournisseur simulé ignore la question et renvoie l'explication standard ; avec Claude ou Gemini, la question est transmise comme donnée.
4. **Gemini** : écrit, jamais testé (ni clé, ni client simulé).

### Ce qui a été corrigé pendant la rédaction

Rien n'a dû être corrigé pour que le scénario passe. Les corrections faites plus tôt dans le projet et vérifiées ici : condition de charge **en jours** dans le CSP (sans elle, le scénario impossible produisait un diagnostic vague) ; routes `GET` de relecture (`/scope`, `/schedule`, `/tour-run`) pour que l'affichage ne relance pas les calculs ; aperçu `GET /tour` sans enregistrement.
