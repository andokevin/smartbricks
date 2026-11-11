# 07 — Présentation orale (15 à 20 minutes)

Vingt-quatre diapositives en quatre parties. Pour chacune : le titre, le contenu affiché (court) et le **script oral complet**. La durée est indiquée entre crochets ; le total fait environ 19 minutes, dont 4 de démonstration.

**Origine des chiffres** : tous viennent de l'exécution réelle.
- Le projet de démonstration « Boutique Soa » (données reproductibles, graine 42), lu par l'API.
- `docs/benchmark_resultats.json`, remesuré après le niveau B.
- `pytest` : 153 tests passés.
- Le temps de calcul dépend de la machine ; les valeurs, les coûts, les distances et les nombres de nœuds, non.

Le fichier `SmartBricks_presentation.pptx` (même dossier) est généré à partir de ce document par `build_slides.py` : le script de chaque diapositive est copié dans les notes de l'orateur.

---

# Partie 1 — Le projet et la problématique

## Diapositive 1 — Couverture [0:20]

**Affiché**
- SmartBricks
- Du besoin flou au projet informatique réaliste
- Copilote IA + algorithmes d'optimisation
- Auteur, formation, novembre 2026

**Script**
> Bonjour à toutes et à tous. Je vais vous présenter SmartBricks, une plateforme qui transforme l'idée d'un client non technique en un vrai projet informatique : ce qu'on livre, avec qui, quand, et pour combien.

---

## Diapositive 2 — Pourquoi ce projet [0:40]

**Affiché**
- « Oser rêver, réaliser son imagination pour améliorer le quotidien. »
- Commerçants et PME : des idées, pas d'équipe technique
- Freelances : des compétences dispersées, des missions incertaines
- Agences en région : Tana, Antsirabe, Toamasina, Fianarantsoa

**Script**
> Le point de départ, c'est une conviction : oser rêver, et faire en sorte que la technologie serve l'humain. À Madagascar, beaucoup de commerçants et de PME ont des idées numériques : vendre en ligne, suivre leurs commandes, relier leurs agences en région. Mais ils n'ont pas d'équipe technique. En face, il y a des freelances compétents, répartis dans plusieurs villes, qui cherchent des missions claires. SmartBricks veut relier les deux.

---

## Diapositive 3 — Présentation du projet [0:45]

**Affiché**
- SmartBricks transforme une idée en projet réalisable : périmètre, équipe, planning, tournée.
- Le client : décrit son besoin et décide
- Le copilote IA : comprend et explique
- Les algorithmes : calculent et garantissent

**Script**
> SmartBricks tient en une phrase : on part d'une idée exprimée avec des mots simples, et on arrive à un projet réalisable, avec un périmètre chiffré, une équipe, un planning et une tournée sur le terrain. Trois acteurs y participent. Le client décrit son besoin et garde la décision. Le copilote, un modèle de langage, comprend ce qu'il dit et lui explique les résultats. Et les algorithmes du cours font tous les calculs. La règle est stricte : l'IA ne calcule jamais un budget, un planning ou une tournée.

---

## Diapositive 4 — La problématique [0:40]

**Affiché**
- « Comment transformer l'idée d'un client non technique en projet réalisable, en garantissant le respect de son budget, de ses délais et des contraintes de l'équipe ? »

**Script**
> D'où la question centrale de mon travail : comment transformer l'idée d'un client non technique en projet réalisable, en garantissant le respect de son budget, de ses délais et des contraintes de l'équipe ? J'insiste sur le mot « garantissant » : il ne s'agit pas de proposer une estimation plausible, mais un plan dont on peut prouver qu'il respecte les contraintes.

---

## Diapositive 5 — Les difficultés concrètes [0:45]

**Affiché**
- Côté client : ne sait pas découper ni chiffrer ; budget limité et délai fixé ; ne sait pas qui recruter
- Côté freelance : disponibilités et compétences ignorées ; planning irréaliste, déplacements mal organisés

**Script**
> Concrètement, les difficultés sont des deux côtés. Le client ne sait pas découper son idée en fonctionnalités ni la chiffrer ; il a un budget limité et une date imposée ; et il ne sait pas qui recruter. Prenons notre cliente de démonstration, Boutique Soa : son rêve représente 14 fonctionnalités, soit 15,2 millions d'Ariary, pour 6 millions de budget. Côté freelance, on ignore souvent ses disponibilités et son niveau réel, on lui impose des plannings irréalistes, et quand il faut intervenir dans plusieurs agences, les déplacements sont mal organisés.

---

# Partie 2 — Les algorithmes

## Diapositive 6 — Vue d'ensemble des algorithmes [1:00]

**Affiché** (tableau)

| N° | Algorithme | Problème résolu | Fonctionnalité |
|---|---|---|---|
| 33 | IA : copilote + sélecteur | Comprendre le besoin, choisir la méthode | Copilote, partout |
| 29 | Sac à dos multidimensionnel | Que livrer sous budget et heures ? | Périmètre |
| 22 | Agrégation pondérée | Classer selon les priorités | Équipe |
| 21 | Optimisation de Pareto | Montrer les meilleurs compromis | Équipe |
| 3 | Satisfaction de contraintes | Qui fait quoi, et quand ? | Planning |
| 30 | Voyageur de commerce | Dans quel ordre visiter les agences ? | Tournée |
| 11 | Min-Conflict | Réparer après un retard | Planning |

**Script**
> Voici la vue d'ensemble. Chaque question du client correspond à un problème classique du cours, et donc à un algorithme précis. Le numéro 33, l'IA, comprend le besoin et choisit la méthode de calcul. Le sac à dos multidimensionnel, numéro 29, choisit ce qu'on livre. L'agrégation pondérée, numéro 22, et l'optimisation de Pareto, numéro 21, aident à choisir l'équipe. La satisfaction de contraintes, numéro 3, construit le planning. Le voyageur de commerce, numéro 30, ordonne les visites. Et Min-Conflict, numéro 11, répare le planning quand une tâche prend du retard.

---

## Diapositive 7 — L'enchaînement [0:40]

**Affiché** : six étapes, chacune avec son numéro.
Copilote (33) → Périmètre (29) → Équipe (22 · 21) → Planning (3) → Tournée (30) → Explication (33)

**Script**
> Les étapes s'enchaînent dans cet ordre. Le copilote produit un brouillon que le client corrige. Le sac à dos choisit le sprint 1. Le matching propose l'équipe. Le CSP construit le planning. Le voyageur de commerce optimise la tournée. Et le copilote revient à la fin pour expliquer le tout. Chaque étape consomme le résultat de la précédente. Voyons maintenant chaque algorithme, à chaque fois en deux temps : pourquoi et comment, puis ce qu'il fait réellement dans SmartBricks.

---

## Diapositive 8 — Copilote et sélecteur (n°33) : pourquoi et comment [0:50]

**Affiché**
- Pourquoi : seul un modèle de langage comprend le français courant ; mais il calcule mal, donc il ne décide rien.
- Comment : 1 Dialogue (une question à la fois) → 2 Extraction (JSON au schéma imposé) → 3 Contrôles sans IA (compétences, villes, cycles) → 4 Explication (chaque chiffre vérifié)
- Sélecteur : exact si la taille le permet, sinon approché, et il dit pourquoi.

**Script**
> Pourquoi une IA ? Parce que le client parle en langage courant, et qu'aucun formulaire technique ne remplacerait un dialogue. Mais un modèle de langage n'est ni exact ni reproductible : il peut inventer un total. Je l'utilise donc en quatre temps encadrés. Un, il dialogue et pose une seule question à la fois. Deux, il produit un JSON qui doit respecter un schéma imposé. Trois, un programme vérifie ce JSON sans IA : les compétences et les villes existent, et le tri topologique de Kahn détecte les dépendances circulaires. Quatre, quand il explique le plan, chaque nombre de son texte est comparé aux résultats ; un seul chiffre inventé, et le texte est remplacé. Le numéro 33 a une deuxième facette, le sélecteur de méthode : une hyper-heuristique qui choisit l'algorithme exact quand la taille le permet, sinon une méthode approchée, et qui affiche sa raison.

---

## Diapositive 9 — Copilote et sélecteur (n°33) : dans SmartBricks [0:50]

**Affiché**
- Reçoit : « Boutique Soa veut un site e-commerce… 6 000 000 Ar, 8 semaines. »
- Renvoie : brouillon de 14 fonctionnalités, 30 tâches, 4 sites (mode simulé)
- Avec Claude (essai réel) : 2 échanges, 8 fonctionnalités, 18 tâches, ≈ 0,002 $
- Sélecteur : ≤ 40 fonctionnalités → exact ; ≤ 12 sites → Held-Karp ; planning : 3 s au plus

**Script**
> Dans l'application, le copilote reçoit le texte libre du client, par exemple celui de Boutique Soa. En mode simulé, qui sert pour la démonstration sans réseau, il renvoie un brouillon de 14 fonctionnalités, 30 tâches et 4 sites. Avec Claude, que j'ai testé pour de vrai, il a suffi de deux échanges pour obtenir un brouillon de 8 fonctionnalités et 18 tâches, pour environ deux millièmes de dollar ; chaque appel est compté, avec un plafond de 4 dollars. Le sélecteur, lui, décide de la méthode : jusqu'à 40 fonctionnalités, le sac à dos est exact ; jusqu'à 12 sites, la tournée est exacte ; le planning a trois secondes au plus. Pour Boutique Soa, 14 fonctionnalités : la méthode exacte est choisie.

---

## Diapositive 10 — Sac à dos multidimensionnel (n°29) : pourquoi et comment [0:50]

**Affiché**
- Pourquoi : choisir des fonctionnalités sous deux limites (Ariary et heures), avec obligatoires et dépendances.
- Comment : 1 Trier par densité → 2 Brancher : inclure ou exclure, avec les dépendances → 3 Borner : minimum des deux sacs fractionnaires → 4 Élaguer si la borne ne bat pas le meilleur
- Plutôt que la programmation dynamique : plus de 10 milliards de cases.

**Script**
> Le choix du sprint 1 est exactement un sac à dos : on maximise la valeur métier sous deux capacités à la fois, le budget en Ariary et les heures, avec des fonctionnalités obligatoires et des dépendances ; pas de paiement sans panier. Je le résous par séparation et évaluation. Un, on trie les fonctionnalités par densité. Deux, on branche : inclure ou exclure, en emportant les dépendances. Trois, on calcule une borne : le sac à dos fractionnaire sur le budget seul, celui sur les heures seules, et on garde le minimum ; chacun est une relaxation, donc une borne valide. Quatre, si la borne ne bat pas la meilleure solution connue, on coupe la branche. Pourquoi pas la programmation dynamique ? Avec un budget en Ariary de six millions et deux cents heures, le tableau dépasserait dix milliards de cases.

---

## Diapositive 11 — Sac à dos (n°29) : dans SmartBricks [0:50]

**Affiché**
- Retenues : Catalogue, Panier, Comptes, Réseau
- Budget 5 541 000 / 6 000 000 Ar (92 %) — Heures 136 / 200 h (68 %)
- MVola écarté : il manque 464 000 Ar
- Et si +600 000 Ar ? ⇒ + Paiement MVola (valeur +80)
- 18 nœuds au lieu de 16 384 — optimum prouvé

**Script**
> Dans SmartBricks, c'est l'écran Périmètre. Il reçoit les 14 fonctionnalités avec leur valeur, leurs heures et leur coût, plus les deux capacités. Pour Boutique Soa, il retient le catalogue, le panier, les comptes clients et le réseau des agences : 5 541 000 Ariary, soit 92 % du budget, et 136 heures sur 200. Pour chaque fonctionnalité écartée, il renvoie une raison chiffrée : il manque 464 000 Ariary pour le paiement MVola. Et l'encart « et si ? » relance le calcul : avec 600 000 Ariary de plus, on ajoute MVola ; avec 1 500 000, on ajoute aussi la protection des données et Orange Money. Le tout en 18 nœuds, au lieu des 16 384 combinaisons possibles, avec un optimum prouvé.

---

## Diapositive 12 — Agrégation pondérée (n°22) et Pareto (n°21) : pourquoi et comment [0:50]

**Affiché**
- Pourquoi : le moins cher n'est ni le plus rapide ni le mieux noté ; il faut arbitrer.
- Comment : 1 Mesurer 5 critères → 2 Normaliser entre 0 et 1 → 3 Pondérer : score = Σ poids × critère (n°22) → 4 Comparer : fronts de Pareto, sans poids (n°21)
- Le score suit les priorités du client ; Pareto montre tous les bons compromis.

**Script**
> Pour l'équipe, aucun freelance n'est meilleur partout : le moins cher n'est pas le plus rapide ni le mieux noté. J'utilise donc deux méthodes complémentaires. D'abord, on mesure cinq critères pour ce projet : coût, rapidité, qualité, disponibilité et couverture des tâches. On les ramène entre zéro et un, en inversant ceux qu'on veut minimiser. Puis l'agrégation pondérée, numéro 22, fait une somme pondérée selon les priorités du client. Mais un score dépend des poids. L'optimisation de Pareto, numéro 21, n'en utilise aucun : un freelance en domine un autre s'il est au moins aussi bon partout et meilleur quelque part, et le premier front regroupe ceux que personne ne domine.

---

## Diapositive 13 — Matching (n°22 et n°21) : dans SmartBricks [0:50]

**Affiché**
- 23 candidats, dont 9 sur le front 1
- Économique → Rado 1er ; Rapide → Nirina 1er
- ★ Toky : le plus proche de l'idéal
- Rivo : 4,3 M Ar, 21 j, note 2,7 → dominé (front 5)
- (nuage coût × durée, front relié, taille du point = qualité)

**Script**
> Dans l'écran Équipe, le matching reçoit les tâches retenues et les profils des freelances. Pour Boutique Soa, 23 freelances savent faire au moins une tâche, et 9 sont sur le premier front. Le client règle ses priorités : en « Économique », Rado est premier ; en « Rapide », c'est Nirina. Sur le nuage, Rado, Nirina et Toky ne se dominent pas : l'un est moins cher, l'autre plus rapide, le troisième mieux noté. Rivo, lui, coûte 4,3 millions pour 21 jours avec une note de 2,7 : il est dominé, au cinquième front. Le meilleur compromis, le plus proche du point idéal, c'est Toky. Enfin, la plateforme suggère une équipe complète, quatre personnes pour Boutique Soa, que le client valide en un clic.

---

## Diapositive 14 — Satisfaction de contraintes (n°3) : pourquoi et comment [0:50]

**Affiché**
- Pourquoi : un planning, ce sont des règles qui doivent toutes être vraies.
- Comment : 1 Propager : chemin critique, borne, impossibilités → 2 Choisir la tâche la plus contrainte (MRV) → 3 Anticiper : vérifier les suivantes → 4 Améliorer : chercher plus court, 3 s au plus
- Puis verify_schedule revérifie les 8 contraintes, indépendamment du solveur.

**Script**
> Un planning, c'est un ensemble de règles qui doivent toutes être vraies en même temps : les dépendances, les compétences, les congés, une seule tâche à la fois par personne, la date limite, et l'ordre des visites sur site. C'est exactement un problème de satisfaction de contraintes. Je le résous en quatre temps. Un, je propage : la méthode du chemin critique donne une borne inférieure et détecte certaines impossibilités sans chercher. Deux, je place d'abord la tâche qui a le moins de créneaux possibles, c'est l'heuristique MRV. Trois, après chaque choix, je vérifie qu'aucune tâche suivante n'est condamnée. Quatre, une fois une solution trouvée, je cherche strictement plus court, dans la limite de trois secondes. Et une fonction indépendante, verify_schedule, revérifie les huit contraintes sur les vraies dates.

---

## Diapositive 15 — CSP (n°3) : dans SmartBricks [0:50]

**Affiché**
- 18 jours ouvrés, fin le 9 décembre 2026 — optimum prouvé — 8/8 contraintes
- Chemin critique : borne de 11 jours
- Scénario 3 semaines : Hasina, 84 h à 6 h/jour = 16 jours pour 15 → impossible
- Retard de 8 h sur T2 : Min-Conflict (n°11) déplace 2 tâches

**Script**
> Dans l'écran Planning, le CSP reçoit les 12 tâches retenues et les 4 membres de l'équipe. Il renvoie, pour chaque tâche, qui la fait et à quelles dates. Pour Boutique Soa : 18 jours ouvrés, fin le 9 décembre, optimum prouvé, et 8 contraintes sur 8 vérifiées. Le chemin critique ne demande que 11 jours ; les 7 jours de plus viennent du fait que Hasina est la seule à faire le React et le Node.js. Si l'on ramène la date limite à 3 semaines, le diagnostic tombe sans aucune recherche : 84 heures à 6 heures par jour, c'est 16 jours pour 15 disponibles ; il faut repousser d'un jour ou ajouter un renfort. Et quand une tâche prend du retard, Min-Conflict, numéro 11, répare le planning : 8 heures de plus sur l'API, et seules 2 tâches bougent, sans changer de freelance.

---

## Diapositive 16 — Voyageur de commerce (n°30) : pourquoi et comment [0:50]

**Affiché**
- Pourquoi : visiter les agences une fois chacune, en parcourant le moins de kilomètres.
- Comment : 1 Mesurer : haversine × 1,35 → 2 Mémoriser le meilleur chemin par (villes visitées, dernière ville) → 3 Reconstruire l'ordre optimal → 4 Au-delà de 12 sites : plus proche voisin + 2-opt
- 12 sites : 39 916 800 ordres possibles ; Held-Karp ≈ 590 000 opérations

**Script**
> Pour les interventions sur site, il faut visiter chaque agence une fois en parcourant le moins de kilomètres : c'est le voyageur de commerce. Un, on estime les distances par la formule de haversine, multipliée par un facteur routier de 1,35 ; c'est une approximation assumée. Deux, Held-Karp, une programmation dynamique, retient pour chaque ensemble de villes visitées et chaque ville d'arrivée seulement le meilleur chemin ; c'est le principe d'optimalité de Bellman. Trois, on reconstruit l'ordre. Quatre, au-delà de 12 sites, le sélecteur passe au plus proche voisin amélioré par 2-opt. À 12 sites, il y a près de 40 millions d'ordres possibles, contre environ 590 000 opérations pour Held-Karp.

---

## Diapositive 17 — Voyageur de commerce (n°30) : dans SmartBricks [0:45]

**Affiché**
- Fianarantsoa → Toamasina → Antananarivo → Antsirabe → retour
- 1 286 km — 1 542 777 Ar — 32,1 h de route
- −18 % par rapport à l'ordre saisi (285 km de moins)
- Held-Karp, tournée exacte

**Script**
> Dans l'écran Tournée, l'algorithme reçoit la ville du technicien, ici Soloniaina à Fianarantsoa, et les quatre agences. Il renvoie l'ordre optimal : Fianarantsoa, Toamasina, Antananarivo, Antsirabe, puis retour. Soit 1 286 kilomètres, 1 542 777 Ariary à 1 200 Ariary le kilomètre, et 32 heures de route. L'ordre saisi par la cliente faisait 1 571 kilomètres : on économise 285 kilomètres, 18 %. Et cet ordre est imposé au planning : les visites sur site suivent la tournée, avec un jour de trajet entre deux villes.

---

# Partie 3 — Le système

## Diapositive 18 — Architecture du système [0:45]

**Affiché**
- React + TypeScript → API FastAPI asynchrone → services → algorithmes (Python pur)
- Copilote LLM : Claude, Gemini ou simulé — PostgreSQL 17
- Déploiement avec Docker : PostgreSQL dans un conteneur (docker compose, port 5435), installation identique partout ; Alembic gère les migrations

**Script**
> Côté système, l'interface en React et TypeScript appelle une API FastAPI asynchrone. Les routes délèguent à des services, qui lisent la base et appellent les algorithmes. Les algorithmes sont du Python pur : ni base, ni web, ni IA ; c'est ce qui les rend testables un par un. Le copilote est derrière une interface commune, avec Claude, Gemini ou un fournisseur simulé. La base PostgreSQL 17 tourne dans un conteneur Docker, lancé par docker compose sur le port 5435 : l'installation est la même sur toutes les machines. Et Alembic versionne le schéma de la base, comme git versionne le code.

---

## Diapositive 19 — Les technologies [0:40]

**Affiché** (tableau couche · technologie · rôle)
- Frontend : React 18, TypeScript, Vite, Tailwind, Recharts, Leaflet — les écrans
- API : FastAPI, Pydantic v2, SQLAlchemy 2 asynchrone — routes, validation
- Algorithmes : Python pur — les décisions chiffrées
- LLM : Claude (claude-haiku-5-5), Gemini, simulé — dialogue et explication
- Base de données : PostgreSQL 17 + Alembic — données et migrations
- Docker : docker compose — base identique partout
- Tests : pytest + httpx — algorithmes et parcours API

**Script**
> Voici les technologies, couche par couche. Le frontend utilise React 18 et TypeScript strict, avec Vite, Tailwind, Recharts pour le nuage de Pareto et Leaflet pour la carte. L'API est en FastAPI avec Pydantic pour la validation et SQLAlchemy asynchrone. Les algorithmes sont en Python pur. Le copilote utilise Claude, le modèle claude-haiku-5-5, ou Gemini, ou le mode simulé. PostgreSQL et Alembic gèrent les données, Docker la base, et pytest avec httpx les tests.

---

## Diapositive 20 — Qualité et fiabilité [0:50]

**Affiché**
- 153 tests pytest passent, dont 93 sur les algorithmes
- Vérification indépendante : verify_selection, verify_schedule (8 contrôles)
- Égal à la force brute : 200 sacs à dos, 120 tournées
- Mode simulé et plafond de 4 $ pour le LLM

**Script**
> Pour la fiabilité, trois garde-fous. D'abord, 153 tests automatisés passent, dont 93 sur les algorithmes. Ensuite, chaque résultat est revérifié par une fonction indépendante du solveur : verify_selection pour le sac à dos, verify_schedule pour le planning, avec ses huit contrôles ; un planning faux n'est jamais renvoyé. Enfin, les méthodes exactes sont comparées à la force brute : le sac à dos donne la même valeur sur 200 instances aléatoires, Held-Karp la même longueur sur 120 tournées. Côté IA, le mode simulé permet une démonstration sans réseau ni clé, et un plafond de 4 dollars bascule automatiquement en mode simulé au-delà.

---

# Partie 4 — Démonstration et bilan

## Diapositive 21 — Démonstration (4 minutes) [4:00]

**Affiché**
- 0:00 Connexion ou inscription — 0:30 Copilote (Claude), brouillon — 1:30 Périmètre, « et si ? » — 2:00 Équipe, Pareto — 2:45 Planning, scénario impossible, retard — 3:30 Tournée, synthèse, PDF

**Script (à dire pendant les manipulations)**
> **[0:00]** Je me connecte comme Boutique Soa ; un nouveau client pourrait aussi créer son compte ici.
> **[0:30]** Nouveau projet : je colle la description. Claude pose une question, je réponds, et le brouillon apparaît : fonctionnalités, tâches, sites, que je peux corriger avant de valider.
> **[1:30]** Périmètre : les jauges, les raisons de chaque report, l'encart « et si ? ».
> **[2:00]** Équipe : je passe d'« Économique » à « Rapide », le classement change ; voici le nuage de Pareto et l'étoile du meilleur compromis ; j'accepte l'équipe proposée.
> **[2:45]** Planning : le Gantt avec ses flèches de dépendance, 8 contraintes sur 8 ; le scénario impossible et son diagnostic ; puis je signale un retard, et Min-Conflict répare.
> **[3:30]** Tournée sur la carte, puis la synthèse : Claude explique le plan, chaque chiffre vérifié, et je télécharge le cahier des charges en PDF.

*Plan B : en cas de problème de réseau, `LLM_PROVIDER=mock` rejoue la démonstration à l'identique, et la carte bascule sur un schéma hors ligne.*

---

## Diapositive 22 — Résultats mesurés [1:00]

**Affiché**
- 18 nœuds : sac à dos de Boutique Soa, optimum prouvé (au lieu de 16 384)
- ≤ 28,4 ms : 40 fonctionnalités, au pire (2 106 nœuds)
- 13 nœuds : première solution du planning ; optimum prouvé ensuite
- 4 320 km en ≈ 36 ms : Held-Karp, 12 villes ; plus proche voisin seul +18,4 %
- ≤ 1,92 % : écart moyen de 2-opt à l'optimum
- 153 tests passés

**Script**
> Ce que j'ai mesuré. Le sac à dos de Boutique Soa est résolu en 18 nœuds, avec un optimum prouvé ; sur des instances de 40 fonctionnalités, il reste sous 29 millisecondes au pire. Le planning trouve sa première solution en 13 nœuds, puis prouve qu'il n'existe pas plus court. Held-Karp traite les 12 villes de la base en environ 36 millisecondes, pour 4 320 kilomètres ; le plus proche voisin seul ferait 18 % de plus, et 2-opt retrouve l'optimum. Sur les instances aléatoires, l'écart moyen de 2-opt reste sous 2 %. Et les 153 tests passent. Ces mesures se recalculent en direct dans la page « Comparaison des méthodes ».

---

## Diapositive 23 — Limites et perspectives [0:45]

**Affiché**
- Limites : distances approchées (vol d'oiseau × 1,35) ; jours fériés non gérés ; frais de tournée hors du sac à dos
- Perspectives : vraies distances routières et paiement Mobile Money réel ; Min-Conflict étendu aux absences imprévues

**Script**
> Je préfère vous montrer moi-même les limites. Les distances sont approchées, à vol d'oiseau multiplié par 1,35. Les jours fériés ne sont pas gérés. Et les frais de tournée ne sont pas réservés dans le budget du sac à dos ; la synthèse le signale. En perspective : utiliser de vraies distances routières, brancher un vrai paiement Mobile Money, MVola ou Orange Money, et étendre Min-Conflict aux absences déclarées par les freelances, qui aujourd'hui demandent un recalcul complet.

---

## Diapositive 24 — Conclusion [0:30]

**Affiché**
- « Le copilote comprend et explique ; les algorithmes décident et garantissent. »
- Merci — vos questions

**Script**
> Pour conclure : SmartBricks montre qu'on peut combiner les deux mondes. Le copilote comprend et explique ; les algorithmes décident et garantissent. Boutique Soa sait maintenant ce qu'elle aura, avec qui, quand, et pour combien. Merci de votre attention ; je suis prêt pour vos questions.

---

## Dix questions probables du jury

**1. Pourquoi ne pas laisser l'IA tout faire ?**
Un modèle de langage n'est ni exact ni reproductible. Les algorithmes donnent un optimum prouvé ou un diagnostic vérifiable ; l'IA est réservée à la compréhension et à la reformulation, et sa sortie est contrôlée (schéma, cycles, chiffres cités).

**2. Comment prouvez-vous que le sac à dos est optimal ?**
La borne, minimum des deux sacs fractionnaires, est une relaxation : on ne coupe jamais une branche qui contient mieux. Arbre épuisé = optimum. Le test le confirme : même valeur que la force brute sur 200 instances.

**3. Que se passe-t-il avec 100 fonctionnalités ?**
Le sélecteur passe au glouton avec échanges 1-1, marqué « approché ». À 40 fonctionnalités, ce glouton s'écarte de 2,62 % en moyenne de l'optimum (benchmark).

**4. Pourquoi 18 jours alors que le chemin critique en fait 11 ?**
Le chemin critique ignore les ressources : Hasina est la seule pour le React et le Node.js, ses tâches s'enchaînent. Le solveur a exploré tout l'arbre pour prouver qu'aucun planning plus court n'existe.

**5. Et si le CSP ne trouve rien en 3 secondes ?**
Il renvoie la meilleure solution trouvée, marquée non optimale ; s'il n'en a aucune, le statut est « inconnu », pas « impossible ».

**6. Min-Conflict ne risque-t-il pas de tout bouleverser ?**
Non : seules les tâches en conflit bougent ; à égalité, il garde le même freelance et les dates les plus proches, puis une phase de resserrement ramène chaque tâche au plus près de sa date d'origine. Il affiche aussi, pour comparaison, ce que donnerait une replanification complète.

**7. Vos distances sont-elles fiables ?**
Ce sont des estimations (vol d'oiseau × 1,35). L'ordre de visite y est peu sensible, puisque le facteur multiplie toutes les distances ; une vraie matrice routière ne remplacerait qu'une fonction.

**8. Combien coûte l'IA, et sans réseau ?**
Chaque appel est enregistré (tokens, coût) ; le parcours testé a coûté environ 0,002 $. Au-delà de 4 $, sans clé ou sans prix, bascule automatique en mode simulé, qui fonctionne sans réseau.

**9. Comment empêchez-vous l'injection de consignes ?**
Le texte du client est transmis comme donnée, jamais comme consigne système ; la sortie doit respecter un schéma JSON, puis passer les contrôles sans IA ; l'explication est rejetée si elle cite un chiffre inconnu.

**10. Que voit un freelance ?**
Un espace à lui : ses tâches, ce qu'il attend, ses indisponibilités, qu'il déclare lui-même et que le planning respecte ; s'il en déclare une sur une tâche déjà planifiée, le client reçoit une alerte.
