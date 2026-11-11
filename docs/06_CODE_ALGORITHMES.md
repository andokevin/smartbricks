# 06 — Lecture commentée du code des algorithmes

Ce document parcourt **chaque fichier de `backend/app/algorithms/`**, bloc par bloc. Les fonctions centrales sont lues ligne par ligne. Suivent les **tests** associés, puis **trois questions de jury** avec leur réponse.

Numéros de ligne : ceux du dépôt au moment de la rédaction ; le lien `fichier:ligne` mène au bon endroit.

Rappel des règles communes à tous les fichiers :
- **Fonctions pures** : aucune importation de FastAPI, de SQLAlchemy ni du LLM. Les données arrivent sous forme de `dataclass` immuables (`frozen=True`), les résultats repartent de la même façon.
- **Vérification indépendante** : `verify_selection` (sac à dos) et `verify_schedule` (CSP) recontrôlent un résultat sans réutiliser le code du solveur.
- Identifiants génériques (`Hashable`) : les tests utilisent des chaînes (`"A"`, `"T1"`), l'application des entiers (identifiants de base).

| Fichier | Lignes | Algorithme | Tests |
|---|---|---|---|
| `knapsack_md.py` | 529 | n°29 | `test_knapsack_md.py` (14 tests) |
| `matching.py` | 322 | n°22 et n°21 | `test_matching.py` (16) |
| `calendar.py` | 80 | outil du n°3 | `test_calendar.py` (7) |
| `csp_scheduler.py` | 464 | n°3 | `test_csp_scheduler.py` (13) |
| `geo.py` | 58 | outil du n°30 | `test_geo.py` (5) |
| `tsp.py` | 167 | n°30 | `test_tsp.py` (9) |
| `dependencies.py` | 83 | contrôle du n°33 | `test_dependencies.py` (5) |
| `solver_selector.py` | 151 | n°33 | `test_solver_selector.py` (7) |
| `formatting.py` | 25 | mise en forme | (indirect) |

Soit **76 tests d'algorithmes**, sur les 124 du projet.

---

## 1. `knapsack_md.py` — sac à dos multidimensionnel (n°29)

### 1.1 En-tête (l. 1-27)

La docstring donne le **modèle mathématique** (maximiser Σ vᵢxᵢ sous deux capacités, avec obligations et dépendances), la liste des méthodes, et la règle commune de traitement des dépendances :
- **fermeture amont** : inclure i, c'est inclure tout ce dont i dépend (directement ou non) ;
- **fermeture aval** : exclure i, c'est exclure tout ce qui dépend de i ;
- **ensemble forcé** : les obligatoires et leur fermeture amont.

Conséquence clé : à tout instant, l'ensemble inclus respecte les dépendances. On n'a jamais à « réparer » en fin de recherche.

### 1.2 Structures de données (l. 41-82)

- `Item` (immuable) : `id`, `value`, `cost`, `hours`, `mandatory`, `depends_on`, `name`. La propriété `label` affiche le nom ou, à défaut, l'identifiant.
- `KnapsackSolution` : `feasible`, `selected`, les totaux, `method`, `optimal` (vrai **seulement** si l'optimalité est prouvée), `nodes`, `elapsed_ms`, et pour le cas impossible `missing_cost` / `missing_hours`.
- `WhatIfScenario` : hausse en %, budget ajouté, fonctionnalités gagnées ou perdues, gain de valeur, message.

### 1.3 La classe `_Problem` (l. 88-195) : préparation commune

Elle traduit les identifiants en indices `0..n-1` et précalcule tout ce que les méthodes partagent.

- **l. 96-98** : dictionnaire `id → indice` ; un doublon d'identifiant lève une erreur.
- **l. 99-104** : `self.deps[k]` = indices dont k dépend ; une dépendance inconnue lève une erreur, plutôt que d'être ignorée en silence.
- **l. 105-108** : graphe inverse `self.dependents` (qui dépend de k).
- **l. 111-112** : `up[k]` et `down[k]`, les deux fermetures, calculées par `_closure`.
- **l. 114-117** : `forced` = union des fermetures amont des obligatoires.

`_closure` (l. 119-128) est un **parcours en profondeur avec pile**. L'ensemble `seen` empêche de boucler, même si le graphe contenait un cycle.

`density` (l. 130-137) calcule `v / (c / budget + h / heures)`. On divise chaque ressource par sa capacité pour additionner des Ariary et des heures sans que l'unité la plus grande (l'Ariary) écrase l'autre.

`infeasible` (l. 167-195) détecte le cas impossible **avant toute recherche** : si l'ensemble forcé ne tient pas, on renvoie le montant et les heures qui manquent. On renvoie alors `optimal=True` : l'impossibilité est prouvée.

### 1.4 `branch_and_bound` (l. 201-318), lecture ligne par ligne

```python
t0 = time.perf_counter()
p = _Problem(items, budget, max_hours)
impossible = p.infeasible("Séparation et évaluation", t0)
if impossible:
    return impossible
```
Préparation, puis sortie immédiate si les obligatoires débordent.

```python
state: list[int | None] = [None] * p.n
for k in p.forced:
    state[k] = 1
base_value, base_cost, base_hours = p.totals(p.forced)
```
`state[k]` vaut 1 (inclus), 0 (exclu) ou `None` (pas encore décidé). L'ensemble forcé est inclus d'office ; on part de ses totaux.

```python
order = sorted((k for k in range(p.n) if state[k] is None), key=lambda k: (-p.density(k), k))
by_cost_ratio = sorted(range(p.n), key=lambda k: -(p.items[k].value / max(p.items[k].cost, 1e-9)))
by_hours_ratio = sorted(range(p.n), key=lambda k: -(p.items[k].value / max(p.items[k].hours, 1e-9)))
```
- `order` : l'ordre de branchement, par densité décroissante. On décide d'abord les objets les plus rentables, ce qui donne vite une bonne solution.
- `by_cost_ratio` et `by_hours_ratio` : les deux ordres utilisés par les bornes fractionnaires, triés **une seule fois**. Le `1e-9` évite une division par zéro.

```python
start = greedy(items, budget, max_hours)
best_value = start.total_value
best_set = {index[i] for i in start.selected}
```
**Solution initiale gloutonne.** Une bonne valeur de départ permet d'élaguer dès les premiers nœuds.

`fractional(order_by_ratio, capacity, weight_of)` (l. 253-267) : sac à dos **fractionnaire** sur une seule dimension. On ignore les objets déjà décidés, on prend les autres par ratio décroissant, et le dernier en fraction (`it.value * capacity / w`). C'est l'algorithme glouton exact du sac à dos fractionnaire.

La récursion `dfs(pos, value, cost, hours)` :

```python
nodes += 1
if nodes > max_nodes:
    aborted = True
    return
```
Garde-fou à 2 millions de nœuds. S'il se déclenche, la solution n'est plus déclarée optimale (`optimal=not aborted`).

```python
if value > best_value:
    best_value = value
    best_set = {k for k in range(p.n) if state[k] == 1}
```
**Tout nœud est une solution admissible** : les objets non décidés valent 0, les contraintes ont été vérifiées à chaque inclusion, et les dépendances sont garanties par les fermetures. On met donc à jour la meilleure solution à chaque nœud, pas seulement aux feuilles.

```python
while pos < len(order) and state[order[pos]] is not None:
    pos += 1
if pos == len(order):
    return
```
On saute les objets déjà décidés par une fermeture. S'il n'en reste plus, on est sur une feuille.

```python
bound = value + min(
    fractional(by_cost_ratio, budget - cost, "cost"),
    fractional(by_hours_ratio, max_hours - hours, "hours"),
)
if bound <= best_value:
    return
```
**L'évaluation.** Chaque sac fractionnaire est une **relaxation** : on a retiré l'autre dimension, les dépendances et le caractère entier de x. Toute vraie solution du sous-arbre est donc admissible pour chacune des deux relaxations, et sa valeur est inférieure ou égale à chacune. Elle est donc aussi inférieure ou égale à leur **minimum**, qui est une borne plus serrée. Si cette borne ne dépasse pas le meilleur connu, aucune solution du sous-arbre ne peut faire mieux : on **élague**.

```python
k = order[pos]
if all(state[j] != 0 for j in p.up[k]):
    new = [j for j in p.up[k] if state[j] is None]
    dc = sum(p.items[j].cost for j in new)
    dh = sum(p.items[j].hours for j in new)
    if cost + dc <= budget and hours + dh <= max_hours:
        for j in new:
            state[j] = 1
        dfs(pos + 1, value + sum(p.items[j].value for j in new), cost + dc, hours + dh)
        for j in new:
            state[j] = None
```
**Branche « inclure k ».** Elle n'est possible que si aucune dépendance de k n'a été exclue. On ajoute k **et** ses dépendances non encore décidées, on vérifie les deux capacités, on descend, puis on **défait** (retour arrière) en remettant `None`.

```python
new = [j for j in p.down[k] if state[j] is None]
for j in new:
    state[j] = 0
dfs(pos + 1, value, cost, hours)
for j in new:
    state[j] = None
```
**Branche « exclure k ».** On exclut k **et** tout ce qui dépend de k : un paiement sans panier n'a pas de sens. Le commentaire l. 308 justifie qu'aucun de ces éléments n'est déjà inclus : s'il l'était, k aurait été inclus par sa fermeture amont.

Fin (l. 316-318) : appel initial avec les totaux de l'ensemble forcé, puis construction de la solution.

### 1.5 Heuristiques (l. 324-392)

- `greedy` / `_greedy_fill` : on part de l'ensemble forcé, on parcourt par densité décroissante, et on ajoute `up[k] - chosen` (k et ses dépendances manquantes) si l'ensemble tient encore. C'est la « réparation des dépendances » demandée par la spécification.
- `greedy_with_swaps` : recherche locale. Pour chaque fonctionnalité retirable r (et pour « rien », `None`), on retire r avec sa fermeture aval, on essaie d'ajouter chaque a avec sa fermeture amont, et on accepte le premier échange admissible qui augmente la valeur. Après un échange, `_greedy_fill` comble la place libérée. La boucle s'arrête car la valeur augmente **strictement** à chaque passe et ne peut pas croître indéfiniment.

### 1.6 Référence et vérification (l. 395-444)

- `brute_force` : toutes les combinaisons (`itertools.combinations`), filtrées par `verify_selection`. Limité à n ≤ 20.
- `verify_selection` : recompte **indépendamment** budget, heures, obligatoires et dépendances. Elle renvoie la liste des violations ; une liste vide signifie que la sélection est valide.

### 1.7 Explications (l. 447-529)

- `explain_exclusions` : pour chaque écartée k, `needed = up[k] - chosen` (elle et ses dépendances manquantes), puis le manque en Ar et en heures par rapport au **reste** du sprint. D'où « il faudrait 464 000 Ar de plus ». Le dernier cas (« pourrait encore être ajoutée ») n'arrive qu'avec une méthode approchée.
- `what_if` : relance `branch_and_bound` avec +10 % et +25 % de budget, puis compare les ensembles (`added`, `removed`). Une hausse de budget peut faire **remplacer** une fonctionnalité, d'où le cas « en remplaçant : … ».

### 1.8 Tests (`tests/algorithms/test_knapsack_md.py`)

| Test | Ce qu'il prouve |
|---|---|
| `test_egal_a_la_force_brute_sur_200_instances` | 200 instances aléatoires (graine 2026, n de 1 à 12, 2 dimensions, ~10 % d'obligatoires, dépendances vers des indices plus petits, donc sans cycle) : même faisabilité et **même valeur** que la force brute, `optimal` vrai, `verify_selection` vide |
| `test_heuristiques_toujours_admissibles_et_jamais_meilleures` | sur 200 instances : glouton ≤ échanges ≤ exact, et toujours admissibles |
| `test_exemple_a_la_main` | A seul (60) contre B + C (70) : le glouton par valeur se tromperait, le B&B prend B + C |
| `test_les_deux_dimensions_comptent` | A tient en budget, pas en heures : il est écarté |
| `test_dependance_paiement_panier_catalogue` | le paiement très rentable entraîne panier et catalogue ; une sélection sans catalogue est refusée par `verify_selection` |
| `test_obligatoire_toujours_retenue`, `test_obligatoire_entraine_ses_dependances` | obligations et fermeture amont |
| `test_cas_impossible_avec_montant_manquant` | 700 000 Ar d'obligatoires pour 600 000 : `missing_cost == 100 000`, message chiffré |
| `test_raisons_d_exclusion`, `test_et_si_plus_de_budget` | textes des raisons et du « et si ? » |
| `test_liste_vide` (×4) | les 4 solveurs acceptent une liste vide |

### 1.9 Questions de jury

**Q1. Pourquoi prendre le minimum de deux bornes, et pas une seule borne sur la somme des ressources ?**
Chaque sac fractionnaire mono-dimension est une relaxation du vrai problème, donc une borne supérieure valide ; leur minimum l'est aussi et il est plus serré, donc il élague plus. Une borne unique sur une ressource « agrégée » demanderait de prouver que l'agrégation est une relaxation, ce qui n'est pas immédiat. Ici, le raisonnement tient en une phrase.

**Q2. Comment garantissez-vous qu'une fonctionnalité n'est jamais retenue sans ce dont elle dépend ?**
Par construction : inclure k inclut sa fermeture amont, exclure k exclut sa fermeture aval. Donc à tout nœud de l'arbre, l'ensemble inclus est fermé vers l'amont. En plus, `verify_selection` revérifie chaque dépendance indépendamment, et le test sur 200 instances le contrôle.

**Q3. Pourquoi ne pas faire de la programmation dynamique ?**
La DP classique est pseudo-polynomiale en O(n × B × H). Avec un budget en Ariary de l'ordre de 6 × 10⁶ et 200 heures, le tableau aurait environ 10¹⁰ cases. Le B&B, lui, explore 18 nœuds sur Boutique Soa et au plus 2 106 nœuds sur les instances aléatoires à 40 fonctionnalités.

---

## 2. `matching.py` — agrégation pondérée (n°22) et Pareto (n°21)

### 2.1 En-tête et constantes (l. 1-47)

- `CRITERIA` : les 5 critères, dans un ordre fixe.
- `DIRECTION` : +1 pour un critère à maximiser, −1 pour un critère à minimiser. Une seule table, utilisée à la fois par la normalisation et par la dominance.
- `PRESETS` : 4 préréglages dont la somme des poids vaut 1 (vérifié par un test).

### 2.2 Structures (l. 50-105)

- `TaskNeed` : compétence, niveau minimal, heures.
- `Candidate` : profil réduit à ce qui sert au calcul. `can_do(t)` compare le niveau du freelance au niveau minimal ; `capacity_hours` = heures par jour × jours disponibles.
- `Criteria`, `Ranked` (score, contributions, valeurs normalisées), `TeamSuggestion`.

### 2.3 Critères (l. 111-132)

```python
my_hours = sum(t.hours for t in tasks if c.can_do(t))
all_hours = sum(t.hours for t in tasks)
share = c.available_days / total_days if total_days > 0 else 0.0
speed = my_hours / (c.hours_per_day * share) if share > 0 and c.hours_per_day > 0 else math.inf
```
- `my_hours` : heures des tâches qu'il sait faire **au niveau requis**.
- `share` : part de jours où il est disponible. Diviser par `hours_per_day × share` revient à compter les jours de calendrier nécessaires : un freelance disponible un jour sur deux met deux fois plus de temps.
- Sans aucun jour disponible, la rapidité est infinie (`math.inf`) ; la normalisation la traite à part.

Puis `cost = taux × my_hours`, `quality = note × (0,5 + 0,5 × taux à l'heure)` (une note de 5 avec 0 % de ponctualité ne vaut que 2,5), `availability`, et `coverage = my_hours / all_hours`.

`evaluate` ne garde que les candidats capables d'**au moins une** tâche.

### 2.4 `normalize` (l. 138-162), ligne par ligne

```python
for key in CRITERIA:
    finite = [c.get(key) for c in criteria.values() if math.isfinite(c.get(key))]
    lo, hi = (min(finite), max(finite)) if finite else (0.0, 0.0)
```
Pour chaque critère, le minimum et le maximum **parmi les valeurs finies**, afin qu'un infini n'écrase pas l'échelle.

```python
    for i, c in criteria.items():
        x = c.get(key)
        if not math.isfinite(x):
            n = 0.0
        elif hi == lo:
            n = 1.0
        elif DIRECTION[key] > 0:
            n = (x - lo) / (hi - lo)
        else:
            n = (hi - x) / (hi - lo)
```
- Valeur infinie : 0, le pire possible.
- Critère constant : 1 pour tous. Il ne départage personne, et cela évite une division par zéro.
- À maximiser : `(x − min) / (max − min)`.
- À minimiser : formule **inversée** `(max − x) / (max − min)`, pour que 1 désigne toujours le meilleur.

### 2.5 `normalize_weights` et `weighted_ranking` (l. 165-186)

- Les poids négatifs sont ramenés à 0, puis tous les poids sont divisés par leur somme. Si tout vaut 0, les poids sont égaux (0,2 chacun).
- `contributions = {k: w[k] * n[k]}` et `score = Σ contributions`. Ce sont exactement les barres affichées à l'écran.
- Le tri `(-score, str(id))` est **déterministe** : à score égal, l'ordre ne dépend pas du hasard.

### 2.6 `dominates` et `non_dominated_sort` (l. 192-233), ligne par ligne

```python
at_least_as_good = all(DIRECTION[k] * a.get(k) >= DIRECTION[k] * b.get(k) for k in keys)
strictly_better = any(DIRECTION[k] * a.get(k) > DIRECTION[k] * b.get(k) for k in keys)
```
Multiplier par la direction ramène tout à « plus grand = mieux ». A domine B s'il est au moins aussi bon partout **et** strictement meilleur quelque part. Donc A ne se domine pas lui-même.

```python
for idx, p in enumerate(ids):
    for q in ids[idx + 1 :]:
        if dominates(criteria[p], criteria[q], keys):
            dominated_by_me[p].append(q)
            domination_count[q] += 1
        elif dominates(criteria[q], criteria[p], keys):
            dominated_by_me[q].append(p)
            domination_count[p] += 1
```
Chaque **paire** est examinée une seule fois (`ids[idx + 1:]`). Pour chaque point on retient S_p (les points qu'il domine) et n_p (le nombre de points qui le dominent).

```python
current = [i for i in ids if domination_count[i] == 0]
while current:
    fronts.append(current)
    nxt = []
    for p in current:
        for q in dominated_by_me[p]:
            domination_count[q] -= 1
            if domination_count[q] == 0:
                nxt.append(q)
    current = nxt
```
Le front 1 regroupe les points que personne ne domine. On le « retire » en décrémentant le compteur des points qu'il domine ; ceux qui tombent à 0 ne sont plus dominés que par des points déjà retirés : ils forment le front suivant. C'est le *fast non-dominated sort* de NSGA-II, en O(K × N²).

### 2.7 `best_compromise` (l. 236-248)

On calcule la distance euclidienne de chaque point du front au point idéal (1, …, 1), dans l'espace normalisé et sur les critères choisis. On garde le plus proche ; à distance égale, l'identifiant départage pour rester déterministe.

### 2.8 `suggest_team` et `_assign_load` (l. 254-322)

1. **Tâches impossibles** (l. 275-278) : celles que personne ne sait faire sont signalées et mises de côté.
2. **Couverture** (l. 279-289) : tant qu'il reste des tâches non couvertes, on prend la compétence qui a **le plus d'heures** non couvertes (`max(sorted(...))`, avec le tri alphabétique pour départager), puis le **meilleur score** capable d'en faire au moins une.
3. **Charge** (l. 292-305) : `_assign_load` répartit les tâches, la plus longue d'abord, vers le membre capable **le moins chargé en proportion de sa capacité**. Si une tâche ne rentre nulle part, on ajoute en renfort le meilleur candidat suivant qui sait la faire, puis on recommence. S'il n'y en a pas, l'équipe est déclarée non absorbable, avec un avertissement.

C'est une estimation de charge, **pas un planning** : le planning réel est le travail du CSP.

### 2.9 Tests (`tests/algorithms/test_matching.py`)

| Test | Ce qu'il prouve |
|---|---|
| `test_calcul_des_criteres_a_la_main` | Rivo (React 4, Node.js 3) fait T1 et T2 (80 h), pas T3 (React 5) ; rapidité 80 / (8 × 15/20) = 13,3 j ; qualité 4 × 0,95 ; couverture 0,8 |
| `test_candidat_sans_tache_faisable_exclu`, `test_aucune_disponibilite_vitesse_infinie` | cas limites |
| `test_normalisation_min_max_et_inversion`, `test_critere_constant_vaut_1` | formules de normalisation, valeurs dans [0, 1] |
| `test_poids_normalises` | somme à 1, tous nuls → égaux, préréglages sommant à 1 |
| `test_poids_100_pourcent_cout_classe_par_cout_croissant` | **exigence de la spécification** : avec 100 % sur le coût, le classement suit le coût croissant (30 candidats aléatoires) |
| `test_contributions_somment_au_score` | les barres affichées sont exactes |
| `test_dominance` | définition, dont « A ne se domine pas » |
| `test_proprietes_des_fronts` (×3 jeux de critères, 50 instances chacun) | les fronts **partitionnent** les candidats ; aucun point du front 1 n'est dominé ; chaque point du front k est dominé par un point du front k−1 |
| `test_meilleur_compromis_exemple` | A pas cher mais lent, B rapide mais cher, C bon partout : C |
| `test_equipe_suggeree_*` (×3) | couverture (React 5 impose l'expert), compétence introuvable signalée, renfort quand 120 h dépassent 80 h de capacité |

### 2.10 Questions de jury

**Q1. Pourquoi normaliser, et pourquoi inverser certains critères ?**
Le coût est en millions d'Ariary et la qualité est sur 5 : sans normalisation, le coût écraserait tout. La normalisation min-max met chaque critère sur [0, 1]. L'inversion pour les critères à minimiser garantit que 1 signifie toujours « le meilleur », ce qui rend la somme pondérée cohérente.

**Q2. Quelle est la différence entre le meilleur score pondéré et le meilleur compromis de Pareto ?**
Le score dépend des poids que choisit le client et porte sur les 5 critères. Le meilleur compromis ne dépend d'aucun poids : c'est le point du front 1 le plus proche du point idéal, sur les critères choisis pour Pareto. Sur Boutique Soa, en Équilibré, Hanitra a le meilleur score et Toky est le meilleur compromis : les deux informations sont complémentaires.

**Q3. Pourquoi le tri non dominé est-il en O(K × N²), et est-ce gênant ?**
Chaque paire de candidats est comparée une fois sur K critères ; le retrait des fronts est linéaire dans le nombre de relations de dominance. Avec N = 23 candidats et K = 3, cela fait environ 750 comparaisons : instantané. Ce ne serait gênant qu'avec des dizaines de milliers de candidats.

---

## 3. `calendar.py` — jours ouvrés

Fichier court, mais toutes les dates du CSP en dépendent.

- **Conventions (l. 1-9)** : lundi à vendredi (jours fériés **non gérés**) ; une tâche de d jours occupe d jours **disponibles** du freelance (un congé la met en pause) ; la date de fin est le **dernier jour travaillé, inclus**.
- `next_monday` : le projet commence le lundi suivant.
- `working_days`, `count_working_days`, `available_days` : listes de jours ouvrés, avec ou sans les congés.
- `unavailable_dates` : transforme des périodes (début, fin) en un ensemble de dates, pour des tests d'appartenance en O(1).
- `add_working_days(start, duration, unavailable)` : on se place sur le premier jour disponible, puis on avance de `duration − 1` jours disponibles. Exemple de la docstring : un vendredi pour 3 jours donne vendredi, lundi, mardi.

**Tests** (`test_calendar.py`, 7 tests) : jours ouvrés, périodes en dates, jours disponibles, fin qui saute le week-end, fin qui saute les congés, une tâche d'un jour finit le jour même, prochain jour disponible.

**Question de jury : pourquoi « fin incluse » ?**
C'est la date qu'un client comprend (« finit le 9 décembre »). La contrainte de dépendance s'écrit alors `début_B > fin_A`, ce qui équivaut au `début_B ≥ fin_A` de la spécification si la fin est comprise comme exclusive.

---

## 4. `csp_scheduler.py` — planification par contraintes (n°3)

### 4.1 En-tête (l. 1-42)

Variables `(freelance_t, début_t)`, domaines, durée `ceil(heures / heures par jour)` en jours **disponibles**, les 5 contraintes dures, et les 5 étapes de résolution (a à e). Les jours sont manipulés par leur **indice** dans la liste des jours ouvrés du projet : additionner et comparer des entiers est plus simple et plus rapide que des dates.

### 4.2 Structures (l. 58-113)

- `SchedTask`, `SchedFreelancer` (avec `can_do` et `duration`), `Assignment`, `ScheduleResult`.
- `status` vaut `"OK"`, `"INFEASIBLE"` (impossibilité **prouvée**) ou `"UNKNOWN"` (rien trouvé dans le temps imparti, sans preuve d'impossibilité).
- `_Timeout` : exception interne pour sortir de la récursion d'un coup quand la limite de temps est atteinte.

### 4.3 `solve_schedule` (l. 119-374), bloc par bloc

**Contrôles de départ (l. 135-143)** : une dépendance inconnue lève une erreur ; une liste vide est un planning de 0 jour.

**Préparation (l. 145-150)** : `days` = jours ouvrés du projet, `D` = leur nombre, `succ` = successeurs de chaque tâche.

**Ordre topologique de Kahn (l. 153-166)** : si toutes les tâches ne sont pas placées, il y a un cycle → `INFEASIBLE` avec la liste des tâches concernées.

**Domaines de compétence (l. 169-178)** : `eligible[t]` = membres qui ont la compétence au niveau requis, triés par score de matching décroissant. Si un domaine est vide → diagnostic « Aucun freelance de l'équipe n'a la compétence … ».

**Jours disponibles (l. 181-184)** : `avail[f]` = indices des jours où f est disponible ; `pos[f][k]` = rang du jour k dans cette liste. On trouve ainsi le d-ième jour disponible suivant en O(1).

**a) Chemin critique (l. 187-210)**

```python
dmin = {t.id: min(f.duration(t) for f in eligible[t.id]) for t in tasks}
ES: dict[Id, int] = {}
for u in topo:
    ES[u] = max((ES[p] + dmin[p] for p in by_id[u].depends_on), default=0)
EF = {u: ES[u] + dmin[u] - 1 for u in topo}
cp_len = max(EF.values()) + 1
```
- `dmin` : la durée **la plus courte possible** de chaque tâche (avec le freelance le plus rapide qui sait la faire). C'est une relaxation : on ignore les congés et le non-chevauchement.
- `ES` (début au plus tôt) : on parcourt dans l'ordre topologique ; une tâche commence après la fin la plus tardive de ses prédécesseurs.
- `cp_len` : longueur du chemin critique = **borne inférieure** de tout planning.

On reconstruit ensuite le chemin (l. 194-199) en remontant, depuis la tâche qui finit le plus tard, vers le prédécesseur qui finit le plus tard.

```python
for u in reversed(topo):
    LF[u] = min((LF[s] - dmin[s] for s in succ[u]), default=D - 1)
if cp_len > D:
    ... diagnostic « Le chemin critique (…) demande X, la date limite en laisse D … »
    return done("INFEASIBLE")
```
- `LF` (fin au plus tard) : parcours inverse ; une tâche doit finir avant le début au plus tard de ses successeurs.
- Si le chemin critique dépasse la fenêtre, l'impossibilité est **prouvée sans recherche**, avec l'écart en jours.

**Conditions nécessaires de charge (l. 213-249)**

Elles portent sur les tâches qu'**une seule** personne de l'équipe sait faire (`mine`) :
- en heures : leurs heures doivent tenir dans ses heures disponibles ;
- en jours : `Σ ceil(heures / heures par jour)` doit tenir dans ses jours disponibles. C'est plus fin que le test en heures, car chaque tâche occupe des jours entiers. C'est ce test qui détecte le scénario impossible de Boutique Soa : 84 h, à 6 h par jour, font 16 jours pour 15 disponibles, alors que 84 h ≤ 90 h.

Puis, par compétence : les heures à faire doivent tenir dans la capacité de **toutes** les personnes qui l'ont. On évite de répéter un diagnostic déjà émis pour une personne seule (`reported`).

**Recherche (l. 252-342)**

Variables d'état : `busy[f]` (un `bytearray` d'un octet par jour, 1 = occupé), `assigned` (affectation en cours), `best` / `best_end` (meilleure solution), `limit` (indice de fin à ne pas dépasser, resserré après chaque solution).

`lf(u)` décale la fin au plus tard quand `limit` se resserre : chercher « strictement mieux que F » revient à avancer la date limite.

`values(u)`, ligne par ligne :

```python
est = earliest_start(u)                     # après la fin réelle des prédécesseurs placés
for f in eligible[u]:
    dur = f.duration(t)
    ks = avail[f.id]
    p = next((pos[f.id][k] for k in ks if k >= est), None) if ks else None
```
Pour chaque freelance compétent, on cherche son premier jour disponible à partir de `est`.

```python
    while p + dur - 1 < len(ks):
        s, e = ks[p], ks[p + dur - 1]
        if e > lf(u):
            break
        if not any(row[s : e + 1]):
            out.append((e, -f.score, team_index[f.id], s, f))
        p += 1
```
- Début `s` = p-ième jour disponible ; fin `e` = (p + dur − 1)-ième. Les congés sont donc **sautés par construction** (contrainte 3).
- Si `e` dépasse la fin au plus tard, on s'arrête : les fins suivantes sont encore plus tardives.
- `not any(row[s:e+1])` : aucun jour occupé entre s et e (contrainte 4).

```python
out.sort(key=lambda v: (v[0], v[1], v[2], v[3]))
```
**Ordre des valeurs** : la fin la plus tôt d'abord, puis le meilleur score de matching, puis un ordre stable.

`forward_check()` : on recalcule les débuts au plus tôt de **toutes** les tâches non placées, à partir des fins réelles des tâches placées. Si l'une ne peut plus finir avant `lf(u)`, cette branche est sans issue : on revient en arrière immédiatement, sans l'explorer.

`search()`, ligne par ligne :

```python
result.nodes += 1
if result.nodes % 64 == 0 and time.perf_counter() - t0 > time_limit:
    raise _Timeout
```
On ne lit l'horloge qu'un nœud sur 64, ce qui coûte moins cher.

```python
if len(assigned) == len(tasks):
    end = max(e for _, _, e in assigned.values())
    if end < best_end:
        best, best_end = dict(assigned), end
        limit = end - 1
    return (not optimize) or best_end + 1 <= cp_len
```
Quand toutes les tâches sont placées, on a une solution. Si elle est meilleure, on la garde et on resserre `limit` : on ne cherche plus que **strictement mieux** (séparation et évaluation sur la durée). On arrête tout si l'on est en mode « première solution » ou si la borne du chemin critique est atteinte : **optimum prouvé**.

```python
ready = [u for u in topo if u not in assigned and all(p in assigned for p in by_id[u].depends_on)]
candidates = []
for u in ready:
    vals = values(u)
    if not vals:
        return False
    candidates.append((len(vals), LF[u] - dmin[u] + 1 - ES[u], str(u), u, vals))
_, _, _, u, vals = min(candidates, key=lambda c: c[:3])
```
- On ne considère que les tâches **prêtes** (tous leurs prédécesseurs sont placés) : la contrainte 1 est garantie par construction.
- Un domaine vide signifie un échec immédiat.
- **MRV** : le plus petit domaine, puis la plus faible marge (LS − ES), puis l'identifiant.

```python
for e, _, _, s, f in vals:
    if e > limit:
        break
    if any(busy[f.id][s : e + 1]):
        continue
    assigned[u] = (f, s, e)
    busy[f.id][s : e + 1] = b"\x01" * (e - s + 1)
    stop = forward_check() and search()
    busy[f.id][s : e + 1] = bytes(e - s + 1)
    del assigned[u]
    if stop:
        return True
return False
```
- `limit` a pu se resserrer pendant l'exploration d'une valeur précédente, d'où le nouveau test.
- On affecte, on marque les jours, on vérifie en avant, on descend, puis on **défait** (retour arrière).
- `forward_check() and search()` : si la vérification échoue, `search()` n'est même pas appelé (évaluation paresseuse de `and`).

**Fin (l. 344-374)** :
- en cas de dépassement du temps, `exhausted = False` ;
- si une solution existe, on reconvertit les indices en dates ; `optimal` est vrai si la borne est atteinte **ou** si l'arbre a été entièrement exploré ;
- sans solution et arbre épuisé : `INFEASIBLE`, avec les capacités ;
- sans solution et temps dépassé : `UNKNOWN`, avec un message prudent (« peut-être réalisable mais trop serré »).

### 4.4 `verify_schedule` (l. 380-464)

Elle ne réutilise **rien** du solveur : ni les indices, ni `avail`, ni `busy`. Elle travaille directement sur les dates.
- tâches non planifiées ou confiées à un inconnu ;
- **dépendances** : `a.start > b.end` ;
- **compétences** : niveau du freelance ≥ niveau requis ;
- **disponibilité** : début ≥ début du projet, début et fin sur des jours travaillés, et le nombre de jours disponibles entre les deux **égal** à la durée annoncée (aucun jour de travail ne tombe sur un congé) ;
- **durées** : `days == ceil(heures / heures par jour)` ;
- **date limite** : `end ≤ deadline` ;
- **pas de chevauchement** : tâches de chaque freelance triées par début, puis comparaison des voisines (`y.start <= x.end` = conflit).

Elle renvoie 7 contrôles nommés ; `constraints_passed` est vrai si tous passent.

### 4.5 Tests (`tests/algorithms/test_csp_scheduler.py`)

| Test | Ce qu'il prouve |
|---|---|
| `test_chaine_sequentielle` | A → B → C : lundi, mardi, mercredi ; durée 3 = borne → optimal |
| `test_taches_paralleles_reparties` | 2 freelances : 2 jours au lieu de 4 |
| `test_duree_depend_des_heures_par_jour` | 10 h à 4 h/j = 3 jours |
| `test_indisponibilites_respectees` | absent lundi et mardi → mercredi-jeudi |
| `test_competence_et_niveau` | Flutter 3 exige le senior (niveau 4), pas le junior (niveau 2) |
| `test_chemin_critique_trop_long` | diagnostic exact : « chemin critique (API → Tests → Déploiement) », 3 jours, « en laisse 2 », « 1 jour ouvré » |
| `test_competence_absente` | diagnostic de compétence |
| `test_surcharge_d_un_freelance` | « Charge de Rivo : 140 h pour 96 h disponibles » (l'exemple de la spécification) |
| `test_surcharge_en_jours_malgre_des_heures_suffisantes` | 78 h ≤ 90 h mais 18 jours > 15 : `INFEASIBLE` avec **0 nœud** |
| `test_verify_schedule_detecte_les_violations` | un planning faux viole exactement 5 contrôles, tous détectés |
| `test_verify_schedule_tache_manquante` | tâche absente → échec |
| `test_verify_valide_toutes_les_solutions_aleatoires` | 60 instances aléatoires (graine 42) : toute solution passe `verify_schedule`, durée ≥ borne, et tout échec a un diagnostic ; au moins 30 instances résolues |
| `test_optimisation_ne_degrade_jamais` | sur 20 instances, la durée optimisée est ≤ la première solution |

### 4.6 Questions de jury

**Q1. Qu'apporte la propagation par le chemin critique ?**
Trois choses : une **preuve d'impossibilité immédiate** quand le chemin dépasse la date limite (0 nœud exploré) ; des dates au plus tard qui coupent les domaines (`e > lf(u)`) ; et une **borne inférieure** qui permet de déclarer un planning optimal. Sur Boutique Soa, la borne vaut 11 jours ; le planning de 18 jours est prouvé optimal parce que l'arbre a été épuisé (24 399 nœuds).

**Q2. Pourquoi MRV ?**
Choisir la variable qui a le moins de valeurs possibles, c'est affronter les échecs le plus tôt possible (*fail-first*). Si une tâche n'a qu'un créneau, autant la placer tout de suite ; si elle n'en a aucun, on le découvre avant d'avoir développé un grand sous-arbre inutile.

**Q3. Comment savez-vous que le planning renvoyé respecte vraiment les contraintes ?**
Par `verify_schedule`, une fonction indépendante qui recontrôle les 7 points sur les dates réelles, sans réutiliser les structures du solveur. Elle est appelée avant chaque réponse de l'API, et testée sur 60 instances aléatoires ainsi que sur un planning volontairement faux.

---

## 5. `geo.py` — distances

- **Docstring (l. 1-14)** : la distance routière est une **approximation assumée** : haversine × 1,35. Exemple : Tana–Antsirabe ≈ 162 km, pour environ 170 km réels.
- Constantes : rayon terrestre 6 371 km, facteur 1,35, 1 200 Ar/km, 40 km/h.
- `haversine_km` : la formule de la docstring, avec les angles en radians. `atan2(√h, √(1 − h))` est numériquement plus stable que `asin` pour les petites distances.
- `distance_matrix` : matrice **symétrique** ; on calcule seulement la moitié (`j > i`), en O(n²).
- `travel_cost_mga` arrondit à l'Ariary entier ; `travel_hours` = km / vitesse.

**Tests** (`test_geo.py`, 5) : un degré de latitude vaut environ 111 km ; distance nulle et symétrique ; ordre de grandeur Tana–Antsirabe ; matrice ; coût et durée.

**Question de jury : pourquoi 1,35 et pas une vraie matrice routière ?**
Il n'existe pas de matrice routière libre et à jour pour ces 12 villes. Le facteur corrige la ligne droite (relief des Hautes Terres, RN7, RN2) et donne un ordre de grandeur correct sur Tana–Antsirabe. L'algorithme est indépendant de cette matrice : la remplacer par de vraies distances ne changerait que `distance_matrix`.

---

## 6. `tsp.py` — voyageur de commerce (n°30)

### 6.1 Conventions (l. 1-19)

La ville 0 est le **départ** ; un ordre commence toujours par 0. `closed=True` pour une tournée avec retour, `False` pour un chemin ouvert.

### 6.2 `tour_length` (l. 28-33)

Somme des arêtes consécutives, plus l'arête de retour si la tournée est fermée.

### 6.3 `held_karp` (l. 39-97), ligne par ligne

```python
m = n - 1
full = (1 << m) - 1
cost = [[INF] * m for _ in range(1 << m)]
parent = [[-1] * m for _ in range(1 << m)]
for j in range(m):
    cost[1 << j][j] = matrix[0][j + 1]
```
- On numérote les villes **autres que le départ** de 0 à m−1 ; la ville i (dans la matrice) correspond au bit i−1.
- Un ensemble S est un entier dont les bits à 1 sont les villes visitées ; `full` contient toutes les villes.
- `cost[S][j]` = plus court chemin qui part de 0, visite exactement S et finit en j. Cas de base : S = {j}, coût = d(0, j).

```python
for S in range(1, full + 1):
    for j in range(m):
        if not (S >> j) & 1 or cost[S][j] == INF:
            continue
        base = cost[S][j]
        for k in range(m):
            if (S >> k) & 1:
                continue
            T = S | (1 << k)
            candidate = base + matrix[j + 1][k + 1]
            if candidate < cost[T][k]:
                cost[T][k] = candidate
                parent[T][k] = j
```
- Les ensembles sont parcourus par entier croissant. Or `T = S | bit` est toujours **plus grand** que S, donc `cost[S][·]` est définitif quand on le lit.
- La récurrence est écrite « vers l'avant » : on prolonge un chemin optimal finissant en j vers chaque ville k non visitée. C'est équivalent à `C[T][k] = min_j C[T∖{k}][j] + d(j, k)`.
- `parent[T][k] = j` mémorise le prédécesseur, pour reconstruire l'ordre.

```python
best_j = min(range(m), key=lambda j: cost[full][j] + (matrix[j + 1][0] if closed else 0))
```
Choix de la dernière ville, en ajoutant le retour au départ si la tournée est fermée.

```python
S, j = full, best_j
while j != -1:
    order.append(j + 1)
    S, j = S & ~(1 << j), parent[S][j]
order.append(0)
order.reverse()
```
**Reconstruction** à rebours : on retire j de l'ensemble et on passe à son prédécesseur, jusqu'à la première ville (parent −1). On ajoute ensuite le départ, puis on inverse la liste.

Complexité : 2^m ensembles × m × m = O(n² 2ⁿ) en temps, O(n 2ⁿ) en mémoire.

### 6.4 `brute_force` (l. 100-111)

Toutes les permutations de 1..n−1, limitées à 9 villes. Le `EPS` évite qu'un écart d'arrondi fasse préférer un ordre de même longueur.

### 6.5 `nearest_neighbor` (l. 117-132)

Depuis la ville courante, on va à la ville non visitée la plus proche (à égalité, la plus petite). En O(n²). La docstring nomme son défaut : il est **myope**, et les dernières villes, laissées pour la fin, coûtent cher.

### 6.6 `two_opt` (l. 135-167), ligne par ligne

```python
while improved:
    improved = False
    for i in range(1, n - 1):
        for k in range(i + 1, n):
            a, b, c = tour[i - 1], tour[i], tour[k]
```
On envisage d'inverser la portion `tour[i..k]`. `i` commence à 1 : le départ ne bouge jamais.

```python
            if k + 1 < n:
                e = tour[k + 1]
                delta = matrix[a][c] + matrix[b][e] - matrix[a][b] - matrix[c][e]
            elif closed:
                e = tour[0]
                delta = ...même formule avec le retour au départ...
            else:
                delta = matrix[a][c] - matrix[a][b]
```
- On retire les arêtes (a→b) et (c→e), on ajoute (a→c) et (b→e). Les arêtes intérieures sont inversées mais gardent leur longueur, car la matrice est symétrique. Calculer le gain coûte donc O(1).
- Chemin ouvert, portion finale : il n'y a pas d'arête après c ; seule (a→b) devient (a→c).

```python
            if delta < -EPS:
                tour[i : k + 1] = reversed(tour[i : k + 1])
                improved = True
```
On n'accepte qu'une amélioration **stricte** (avec une tolérance d'arrondi). La longueur diminue strictement à chaque échange et il y a un nombre fini d'ordres, donc la boucle termine.

### 6.7 Tests (`tests/algorithms/test_tsp.py`)

| Test | Ce qu'il prouve |
|---|---|
| `test_longueur` | carré de côté 1 : tour 4, chemin 3, tour croisé 2 + 2√2 |
| `test_carre_held_karp` | optimum 4 sur le carré |
| `test_held_karp_egal_force_brute` (fermé et ouvert) | 60 instances chacun, 1 à 8 villes : même longueur que la force brute, ordre valide, longueur recalculée cohérente |
| `test_two_opt_encadre` (fermé et ouvert) | 60 instances chacun, 2 à 11 villes : **Held-Karp ≤ 2-opt ≤ plus proche voisin** |
| `test_two_opt_defait_un_croisement` | le tour croisé du carré redevient 4 |
| `test_grande_instance_reste_valide` | 60 villes : 2-opt renvoie une permutation valide |
| `test_cas_degeneres` | une seule ville |

### 6.8 Questions de jury

**Q1. Pourquoi Held-Karp est-il exact ?**
Par le principe d'optimalité de Bellman : si le meilleur chemin qui visite S et finit en j passe par k juste avant, sa partie jusqu'à k est le meilleur chemin qui visite S∖{j} et finit en k. Il suffit donc de garder, pour chaque couple (ensemble, dernière ville), le meilleur coût ; l'ordre interne n'importe plus. Le test contre la force brute le confirme sur 120 instances.

**Q2. Pourquoi le seuil de 12 sites ?**
Le coût est en n² 2ⁿ. Mesuré dans le benchmark : 38 ms en moyenne à 12 sites, 89 ms à 13. En extrapolant (×2 à ×2,5 par site), on dépasse la seconde vers 16 sites. Au-delà de 12, 2-opt donne un résultat à moins de 2 % en moyenne, en moins d'une milliseconde.

**Q3. Que fait 2-opt géométriquement ?**
Il supprime les croisements : si deux arêtes se coupent, les « décroiser » en inversant la portion entre elles raccourcit toujours la tournée (inégalité triangulaire). À la fin, aucune inversion de portion ne raccourcit plus : c'est un optimum **local**, pas forcément global. Les tests vérifient seulement qu'il n'est jamais meilleur que Held-Karp et jamais pire que le point de départ.

---

## 7. `dependencies.py` — contrôle des dépendances du copilote (n°33)

### 7.1 En-tête (l. 1-19)

On ne fait pas confiance au LLM : ses dépendances sont vérifiées mathématiquement. L'en-tête justifie la règle de l'« arête la moins justifiée » : une dépendance qui va **à rebours** de l'ordre de déclaration. Tout cycle en contient au moins une, car on ne peut pas faire une boucle dans une liste en avançant toujours.

### 7.2 `topological_order` (l. 24-46)

Kahn classique :
- degré entrant = nombre de dépendances connues (`set()` élimine les doublons) ;
- file des éléments de degré 0 ;
- on retire un élément, on décrémente ses dépendants, on enfile ceux qui tombent à 0.

Il renvoie `(ordre, restants)` : les restants sont exactement les éléments bloqués par un cycle (ou en aval d'un cycle). Complexité O(V + E).

### 7.3 `find_cycle` (l. 49-64)

Depuis un élément bloqué, on suit une dépendance **elle aussi bloquée**. Il en existe toujours une, sinon l'élément aurait été libéré. Comme le nombre d'éléments est fini, on finit par revisiter un élément ; la portion du chemin entre les deux visites est un cycle.

### 7.4 `break_cycles` (l. 67-83), ligne par ligne

```python
position = {r: k for k, r in enumerate(refs)}
clean = {r: [d for d in dict.fromkeys(deps.get(r, [])) if d in position] for r in refs}
```
Position de déclaration de chaque élément ; dépendances nettoyées (doublons retirés avec `dict.fromkeys`, inconnues ignorées).

```python
while (cycle := find_cycle(refs, clean)) is not None:
    edges = [(cycle[k], cycle[(k + 1) % len(cycle)]) for k in range(len(cycle))]
    u, v = max(edges, key=lambda e: (position[e[1]] - position[e[0]], position[e[0]]))
    clean[u].remove(v)
    removed.append((u, v))
```
Tant qu'un cycle existe, on liste ses arêtes (u dépend de v) et on retire celle où v est déclaré **le plus loin après** u. On recommence, car plusieurs cycles peuvent exister. La boucle termine : chaque tour retire une arête, et il y en a un nombre fini.

### 7.5 Tests (`test_dependencies.py`, 5)

Ordre sans cycle ; cycle A-B-C détecté (D reste ordonnable) ; arête retirée = « T1 dépend de T3 » ; auto-dépendance « A dépend de A » retirée ; **200 graphes aléatoires** : après réparation, plus aucun cycle, et seules des arêtes qui reculaient ou restaient sur place ont été retirées. Un graphe sans cycle n'est pas modifié.

### 7.6 Questions de jury

**Q1. Pourquoi Kahn plutôt qu'un parcours en profondeur ?** Kahn donne directement deux choses utiles : un ordre (réutilisé par le CSP) et l'ensemble des éléments bloqués, sans récursion. Les deux sont en O(V + E).

**Q2. Retirer une arête, n'est-ce pas trahir le client ?** L'arête retirée est **signalée** en avertissement dans le brouillon, que le client relit avant de confirmer. Sans ce retrait, aucun planning ne serait possible.

**Q3. Le résultat est-il minimal ?** Non : trouver le plus petit ensemble d'arêtes à retirer (*feedback arc set*) est NP-difficile. La règle choisie est simple, explicable et garantie de terminer ; sur les brouillons réels, les cycles sont rares et courts.

---

## 8. `solver_selector.py` — sélecteur de méthode (n°33)

### 8.1 Blocs

- **En-tête (l. 1-24)** : la définition d'une hyper-heuristique (elle choisit une méthode, pas une solution), le tableau des règles et la justification des seuils.
- **Constantes (l. 35-37)** : `KNAPSACK_EXACT_MAX = 40`, `TSP_EXACT_MAX_SITES = 12`, `CSP_TIME_LIMIT_S = 3.0`.
- **`MethodChoice` (l. 40-46)** : problème, méthode, exacte ou non, **raison en français** (affichée à l'écran), numéro du cours.
- **Règles (l. 60-99)** : `choose_knapsack_method`, `choose_tsp_method` (le départ n'est pas compté comme site), `choose_csp_method`. Les seuils sont des paramètres, ce qui permet de les tester.
- **Exécution (l. 105-151)** :
  - `solve_knapsack` choisit puis appelle `branch_and_bound` ou `greedy_with_swaps` ;
  - `solve_tour` appelle `held_karp`, ou bien plus proche voisin puis `two_opt`, en gardant la longueur du plus proche voisin pour mesurer l'apport de 2-opt ;
  - `solve_schedule_auto` lance le CSP puis **complète la raison selon l'issue** : optimal prouvé, limite atteinte avec l'écart maximal à la borne (`makespan − borne`), impossibilité, ou rien trouvé (Min-Conflict « prévu au niveau B »).

### 8.2 Tests (`test_solver_selector.py`, 7)

Règles et raisons (40 contre 41, 12 contre 13) ; seuils paramétrables ; un petit sac à dos est résolu exactement (`optimal`), un grand de façon approchée en moins de 3 s et **admissible** (`verify_selection` vide) ; une petite tournée donne exactement la longueur de Held-Karp, une tournée à 40 villes une permutation valide avec 2-opt ≤ plus proche voisin ; le CSP automatique renvoie une raison qui mentionne l'optimalité.

### 8.3 Questions de jury

**Q1. En quoi est-ce une hyper-heuristique, et pas un simple `if` ?** Formellement, c'est un `if`. Mais il opère sur l'**espace des méthodes** à partir d'une caractéristique de l'instance (sa taille), avec des seuils justifiés par des mesures. C'est la forme la plus simple d'hyper-heuristique de sélection, et elle a l'avantage d'être explicable à l'utilisateur.

**Q2. D'où viennent les seuils ?** De mesures : le sac à dos exact reste sous 31 ms au pire jusqu'à 30-40 fonctionnalités, Held-Karp sous 40 ms en moyenne à 12 sites (`docs/benchmark_resultats.json`). Les seuils sont des paramètres modifiables.

**Q3. Que se passe-t-il si le CSP atteint 3 s ?** On renvoie la meilleure solution trouvée, marquée `optimal: false`, avec dans la raison l'écart maximal à la borne du chemin critique. Si aucune solution n'a été trouvée, le statut est `UNKNOWN` et non `INFEASIBLE` : on ne prétend pas avoir prouvé l'impossibilité.

---

## 9. `formatting.py`

Trois fonctions de présentation, utilisées dans les messages :
- `format_ar` : 1234567 → « 1 234 567 Ar » (le séparateur des milliers est remplacé par une espace) ;
- `format_date_fr` : « 8 janvier 2027 » ;
- `format_pct` : 0,1 → « 10 % ».

Elles sont testées indirectement par les messages vérifiés dans les autres tests (« 100 000 Ar » dans le cas impossible du sac à dos, par exemple).
