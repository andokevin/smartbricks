# 07 — Présentation orale (15 à 20 minutes)

Vingt-deux diapositives en quatre parties (le voyageur de commerce n'est plus présenté ; aucun numéro d'algorithme n'est affiché). Pour chacune : le titre, le contenu affiché et un script oral de référence. La durée est indiquée entre crochets.

**Origine des chiffres** : tous viennent de l'exécution réelle.
- Le projet de démonstration « Boutique Soa » (données reproductibles, graine 42), lu par l'API.
- `docs/benchmark_resultats.json`, remesuré après le niveau B.
- `pytest` : 153 tests passés.
- Le temps de calcul dépend de la machine ; les valeurs, les coûts, les distances et les nombres de nœuds, non.

Le fichier `SmartBricks_presentation.pptx` (même dossier) est généré par `build_slides.py` : transition en fondu, apparition au clic dans l'ordre de lecture, et seulement 2 ou 3 mots-clés de secours dans les notes de l'orateur.

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
- SmartBricks transforme une idée en projet réalisable : un périmètre chiffré, une équipe et un planning garanti.
- Le client : décrit son besoin et décide
- Le copilote IA : comprend et explique
- Les algorithmes : calculent et garantissent

**Script**
> SmartBricks tient en une phrase : on part d'une idée exprimée avec des mots simples, et on arrive à un projet réalisable, avec un périmètre chiffré, une équipe et un planning garanti. Trois acteurs y participent. Le client décrit son besoin et garde la décision. Le copilote, un modèle de langage, comprend ce qu'il dit et lui explique les résultats. Et les algorithmes du cours font tous les calculs. La règle est stricte : l'IA ne calcule jamais un budget ni un planning.

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
- Côté freelance : disponibilités et compétences ignorées ; planning irréaliste, retards mal absorbés

**Script**
> Concrètement, les difficultés sont des deux côtés. Le client ne sait pas découper son idée en fonctionnalités ni la chiffrer ; il a un budget limité et une date imposée ; et il ne sait pas qui recruter. Prenons notre cliente de démonstration, Boutique Soa : son rêve représente 14 fonctionnalités, soit 15,2 millions d'Ariary, pour 6 millions de budget. Côté freelance, on ignore souvent ses disponibilités et son niveau réel, on lui impose des plannings irréalistes, et un retard désorganise tout.

---

# Partie 2 — Les algorithmes

## Diapositive 6 — Vue d'ensemble des algorithmes [1:00]

**Affiché** (tableau)

| Algorithme | À quoi il sert | Fonctionnalité |
|---|---|---|
| Satisfaction de contraintes (CSP) | Décider qui fait chaque tâche, et quand | Planning |
| Min-Conflict | Réparer le planning après un retard | Planning |
| Optimisation de Pareto | Montrer les meilleurs compromis | Équipe |
| Agrégation pondérée | Classer selon les priorités du client | Équipe |
| Sac à dos multidimensionnel | Choisir quoi livrer sous budget et heures | Périmètre |
| Copilote LLM + sélecteur | Comprendre, choisir la méthode, expliquer | Copilote, synthèse |

**Script**
> Voici la vue d'ensemble. Chaque question du client correspond à un problème classique, et donc à un algorithme précis. La satisfaction de contraintes construit le planning, et Min-Conflict le répare quand une tâche prend du retard. L'optimisation de Pareto et l'agrégation pondérée aident à choisir l'équipe. Le sac à dos multidimensionnel choisit ce qu'on livre. Et le copilote comprend le besoin, choisit la méthode de calcul et explique les résultats.

---

## Diapositive 7 — L'enchaînement [0:40]

**Affiché** : cinq étapes, qui apparaissent une à une.
Copilote → Périmètre → Équipe → Planning → Explication

**Script**
> Les étapes s'enchaînent dans cet ordre. Le copilote produit un brouillon que le client corrige. Le sac à dos choisit le sprint 1. Le matching propose l'équipe. Le CSP construit le planning. Et le copilote revient à la fin pour expliquer le tout. Chaque étape consomme le résultat de la précédente. Voyons maintenant chaque algorithme, à chaque fois en deux temps : pourquoi et comment, puis ce qu'il fait réellement dans SmartBricks.

---

## Diapositive 8 — Copilote et sélecteur : pourquoi et comment [0:50]

**Affiché**
- Pourquoi : seul un modèle de langage comprend le français courant ; mais il calcule mal, donc il ne décide rien.
- Comment : 1 Dialogue (une question à la fois) → 2 Extraction (JSON au schéma imposé) → 3 Contrôles sans IA (compétences, villes, cycles) → 4 Explication (chaque chiffre vérifié)
- Sélecteur : exact si la taille le permet, sinon approché, et il dit pourquoi.

**Script**
> Pourquoi une IA ? Parce que le client parle en langage courant, et qu'aucun formulaire technique ne remplacerait un dialogue. Mais un modèle de langage n'est ni exact ni reproductible : il peut inventer un total. Je l'utilise donc en quatre temps encadrés. Un, il dialogue et pose une seule question à la fois. Deux, il produit un JSON qui doit respecter un schéma imposé. Trois, un programme vérifie ce JSON sans IA : les compétences et les villes existent, et le tri topologique de Kahn détecte les dépendances circulaires. Quatre, quand il explique le plan, chaque nombre de son texte est comparé aux résultats ; un seul chiffre inventé, et le texte est remplacé. Le copilote a une deuxième facette, le sélecteur de méthode : une hyper-heuristique qui choisit l'algorithme exact quand la taille le permet, sinon une méthode approchée, et qui affiche sa raison.

---

## Diapositive 9 — Copilote et sélecteur : dans SmartBricks [0:50]

**Affiché**
- Reçoit : « Boutique Soa veut un site e-commerce… 6 000 000 Ar, 8 semaines. »
- Renvoie : brouillon de 14 fonctionnalités, 30 tâches (mode simulé)
- Avec Claude (essai réel) : 2 échanges, 8 fonctionnalités, 18 tâches, ≈ 0,002 $

**Script**
> Dans l'application, le copilote reçoit le texte libre du client, par exemple celui de Boutique Soa. En mode simulé, qui sert pour la démonstration sans réseau, il renvoie un brouillon de 14 fonctionnalités et 30 tâches. Avec Claude, que j'ai testé pour de vrai, il a suffi de deux échanges pour obtenir un brouillon de 8 fonctionnalités et 18 tâches, pour environ deux millièmes de dollar ; chaque appel est compté, avec un plafond de 4 dollars. Le sélecteur, lui, décide de la méthode : jusqu'à 40 fonctionnalités, le sac à dos est exact ; le planning a trois secondes au plus ; après un retard, Min-Conflict répare au lieu de tout recalculer. Pour Boutique Soa, 14 fonctionnalités : la méthode exacte est choisie.

---

## Diapositive 10 — Sac à dos multidimensionnel : pourquoi et comment [0:50]

**Affiché**
- Pourquoi : choisir des fonctionnalités sous deux limites (Ariary et heures), avec obligatoires et dépendances.
- Comment : 1 Trier par densité → 2 Brancher : inclure ou exclure, avec les dépendances → 3 Borner : minimum des deux sacs fractionnaires → 4 Élaguer si la borne ne bat pas le meilleur
- Plutôt que la programmation dynamique : plus de 10 milliards de cases.

**Script**
> Le choix du sprint 1 est exactement un sac à dos : on maximise la valeur métier sous deux capacités à la fois, le budget en Ariary et les heures, avec des fonctionnalités obligatoires et des dépendances ; pas de paiement sans panier. Je le résous par séparation et évaluation. Un, on trie les fonctionnalités par densité. Deux, on branche : inclure ou exclure, en emportant les dépendances. Trois, on calcule une borne : le sac à dos fractionnaire sur le budget seul, celui sur les heures seules, et on garde le minimum ; chacun est une relaxation, donc une borne valide. Quatre, si la borne ne bat pas la meilleure solution connue, on coupe la branche. Pourquoi pas la programmation dynamique ? Avec un budget en Ariary de six millions et deux cents heures, le tableau dépasserait dix milliards de cases.

---

## Diapositive 11 — Sac à dos : dans SmartBricks [0:50]

**Affiché**
- Retenues : Catalogue, Panier, Comptes, Réseau
- Budget 5 541 000 / 6 000 000 Ar (92 %) — Heures 136 / 200 h (68 %)
- MVola écarté : il manque 464 000 Ar
- Et si +600 000 Ar ? ⇒ + Paiement MVola (valeur +80)
- 18 nœuds au lieu de 16 384 — optimum prouvé

**Script**
> Dans SmartBricks, c'est l'écran Périmètre. Il reçoit les 14 fonctionnalités avec leur valeur, leurs heures et leur coût, plus les deux capacités. Pour Boutique Soa, il retient le catalogue, le panier, les comptes clients et le réseau des agences : 5 541 000 Ariary, soit 92 % du budget, et 136 heures sur 200. Pour chaque fonctionnalité écartée, il renvoie une raison chiffrée : il manque 464 000 Ariary pour le paiement MVola. Et l'encart « et si ? » relance le calcul : avec 600 000 Ariary de plus, on ajoute MVola ; avec 1 500 000, on ajoute aussi la protection des données et Orange Money. Le tout en 18 nœuds, au lieu des 16 384 combinaisons possibles, avec un optimum prouvé.

---

## Diapositive 12 — Agrégation pondérée et Pareto : pourquoi et comment [0:50]

**Affiché**
- Pourquoi : le moins cher n'est ni le plus rapide ni le mieux noté ; il faut arbitrer.
- Comment : 1 Mesurer 5 critères → 2 Normaliser entre 0 et 1 → 3 Pondérer : score = Σ poids × critère → 4 Comparer : fronts de Pareto, sans poids
- Le score suit les priorités du client ; Pareto montre tous les bons compromis.

**Script**
> Pour l'équipe, aucun freelance n'est meilleur partout : le moins cher n'est pas le plus rapide ni le mieux noté. J'utilise donc deux méthodes complémentaires. D'abord, on mesure cinq critères pour ce projet : coût, rapidité, qualité, disponibilité et couverture des tâches. On les ramène entre zéro et un, en inversant ceux qu'on veut minimiser. Puis l'agrégation pondérée, numéro 22, fait une somme pondérée selon les priorités du client. Mais un score dépend des poids. L'optimisation de Pareto, numéro 21, n'en utilise aucun : un freelance en domine un autre s'il est au moins aussi bon partout et meilleur quelque part, et le premier front regroupe ceux que personne ne domine.

---

## Diapositive 13 — Matching : dans SmartBricks [0:50]

**Affiché**
- 23 candidats, dont 9 sur le front 1
- Économique → Rado 1er ; Rapide → Nirina 1er
- ★ Toky : le plus proche de l'idéal
- Rivo : 4,3 M Ar, 21 j, note 2,7 → dominé (front 5)
- (nuage coût × durée, front relié, taille du point = qualité)

**Script**
> Dans l'écran Équipe, le matching reçoit les tâches retenues et les profils des freelances. Pour Boutique Soa, 23 freelances savent faire au moins une tâche, et 9 sont sur le premier front. Le client règle ses priorités : en « Économique », Rado est premier ; en « Rapide », c'est Nirina. Sur le nuage, Rado, Nirina et Toky ne se dominent pas : l'un est moins cher, l'autre plus rapide, le troisième mieux noté. Rivo, lui, coûte 4,3 millions pour 21 jours avec une note de 2,7 : il est dominé, au cinquième front. Le meilleur compromis, le plus proche du point idéal, c'est Toky. Enfin, la plateforme suggère une équipe complète, quatre personnes pour Boutique Soa, que le client valide en un clic.

---

## Diapositive 14 — Satisfaction de contraintes : pourquoi et comment [0:50]

**Affiché**
- Pourquoi : un planning, ce sont des règles qui doivent toutes être vraies.
- Comment : 1 Propager : chemin critique, borne, impossibilités → 2 Choisir la tâche la plus contrainte (MRV) → 3 Anticiper : vérifier les suivantes → 4 Améliorer : chercher plus court, 3 s au plus
- Puis verify_schedule revérifie les 8 contraintes, indépendamment du solveur.

**Script**
> Un planning, c'est un ensemble de règles qui doivent toutes être vraies en même temps : les dépendances, les compétences, les congés, une seule tâche à la fois par personne, la date limite, et l'ordre des visites sur site. C'est exactement un problème de satisfaction de contraintes. Je le résous en quatre temps. Un, je propage : la méthode du chemin critique donne une borne inférieure et détecte certaines impossibilités sans chercher. Deux, je place d'abord la tâche qui a le moins de créneaux possibles, c'est l'heuristique MRV. Trois, après chaque choix, je vérifie qu'aucune tâche suivante n'est condamnée. Quatre, une fois une solution trouvée, je cherche strictement plus court, dans la limite de trois secondes. Et une fonction indépendante, verify_schedule, revérifie les huit contraintes sur les vraies dates.

---

## Diapositive 15 — CSP : dans SmartBricks [0:50]

**Affiché**
- 18 jours ouvrés, fin le 9 décembre 2026 — optimum prouvé — 8/8 contraintes
- Chemin critique : borne de 11 jours
- Scénario 3 semaines : Hasina, 84 h à 6 h/jour = 16 jours pour 15 → impossible
- Retard de 8 h sur T2 : Min-Conflict déplace 2 tâches

**Script**
> Dans l'écran Planning, le CSP reçoit les 12 tâches retenues et les 4 membres de l'équipe. Il renvoie, pour chaque tâche, qui la fait et à quelles dates. Pour Boutique Soa : 18 jours ouvrés, fin le 9 décembre, optimum prouvé, et 8 contraintes sur 8 vérifiées. Le chemin critique ne demande que 11 jours ; les 7 jours de plus viennent du fait que Hasina est la seule à faire le React et le Node.js. Si l'on ramène la date limite à 3 semaines, le diagnostic tombe sans aucune recherche : 84 heures à 6 heures par jour, c'est 16 jours pour 15 disponibles ; il faut repousser d'un jour ou ajouter un renfort. Et quand une tâche prend du retard, Min-Conflict, numéro 11, répare le planning : 8 heures de plus sur l'API, et seules 2 tâches bougent, sans changer de freelance.

---

# Partie 3 — Le système

## Diapositive 16 — Architecture du système [0:45]

**Affiché**
- React + TypeScript → API FastAPI asynchrone → services → algorithmes (Python pur)
- Copilote LLM : Claude, Gemini ou simulé — PostgreSQL 17
- Déploiement avec Docker : PostgreSQL dans un conteneur (docker compose, port 5435), installation identique partout ; Alembic gère les migrations

**Script**
> Côté système, l'interface en React et TypeScript appelle une API FastAPI asynchrone. Les routes délèguent à des services, qui lisent la base et appellent les algorithmes. Les algorithmes sont du Python pur : ni base, ni web, ni IA ; c'est ce qui les rend testables un par un. Le copilote est derrière une interface commune, avec Claude, Gemini ou un fournisseur simulé. La base PostgreSQL 17 tourne dans un conteneur Docker, lancé par docker compose sur le port 5435 : l'installation est la même sur toutes les machines. Et Alembic versionne le schéma de la base, comme git versionne le code.

---

## Diapositive 17 — Les technologies [0:40]

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

## Diapositive 18 — Qualité et fiabilité [0:50]

**Affiché**
- 153 tests pytest passent, dont 93 sur les algorithmes
- Vérification indépendante : verify_selection, verify_schedule (8 contrôles)
- Égal à la force brute : sac à dos sur 200 instances aléatoires
- Mode simulé et plafond de 4 $ pour le LLM

**Script**
> Pour la fiabilité, trois garde-fous. D'abord, 153 tests automatisés passent, dont 93 sur les algorithmes. Ensuite, chaque résultat est revérifié par une fonction indépendante du solveur : verify_selection pour le sac à dos, verify_schedule pour le planning, avec ses huit contrôles ; un planning faux n'est jamais renvoyé. Enfin, les méthodes exactes sont comparées à la force brute : le sac à dos donne la même valeur sur 200 instances aléatoires. Côté IA, le mode simulé permet une démonstration sans réseau ni clé, et un plafond de 4 dollars bascule automatiquement en mode simulé au-delà.

---

# Partie 4 — Démonstration et bilan

## Diapositive 19 — Démonstration (4 minutes) [4:00]

**Affiché**
- 0:00 Connexion ou inscription — 0:30 Copilote (Claude), brouillon — 1:30 Périmètre, « et si ? » — 2:00 Équipe, Pareto — 2:45 Planning, scénario impossible, retard — 3:30 Synthèse, explication, PDF

**Script (à dire pendant les manipulations)**
> **[0:00]** Je me connecte comme Boutique Soa ; un nouveau client pourrait aussi créer son compte ici.
> **[0:30]** Nouveau projet : je colle la description. Claude pose une question, je réponds, et le brouillon apparaît : fonctionnalités et tâches, que je peux corriger avant de valider.
> **[1:30]** Périmètre : les jauges, les raisons de chaque report, l'encart « et si ? ».
> **[2:00]** Équipe : je passe d'« Économique » à « Rapide », le classement change ; voici le nuage de Pareto et l'étoile du meilleur compromis ; j'accepte l'équipe proposée.
> **[2:45]** Planning : le Gantt avec ses flèches de dépendance, 8 contraintes sur 8 ; le scénario impossible et son diagnostic ; puis je signale un retard, et Min-Conflict répare.
> **[3:30]** La synthèse : Claude explique le plan, chaque chiffre vérifié, et je télécharge le cahier des charges en PDF.

*Plan B : en cas de problème de réseau, `LLM_PROVIDER=mock` rejoue la démonstration à l'identique, avec les mêmes résultats calculés.*

---

## Diapositive 20 — Résultats mesurés [1:00]

**Affiché**
- 18 nœuds : sac à dos de Boutique Soa, optimum prouvé (au lieu de 16 384)
- ≤ 28,4 ms : 40 fonctionnalités, au pire (2 106 nœuds)
- 13 nœuds : première solution du planning ; optimum prouvé ensuite
- 0 nœud : planning impossible (3 semaines) prouvé sans recherche
- 5,3 % : écart moyen du glouton seul (40 fonctionnalités)
- 153 tests passés

**Script**
> Ce que j'ai mesuré. Le sac à dos de Boutique Soa est résolu en 18 nœuds, avec un optimum prouvé ; sur des instances de 40 fonctionnalités, il reste sous 29 millisecondes au pire. Le planning trouve sa première solution en 13 nœuds, puis prouve qu'il n'existe pas plus court. Le scénario impossible, trois semaines, est prouvé sans explorer un seul nœud, grâce aux tests de charge. Sans la méthode exacte, le glouton seul perdrait en moyenne 5,3 % de valeur sur 40 fonctionnalités. Et les 153 tests passent. Ces mesures se recalculent en direct dans la page « Comparaison des méthodes ».

---

## Diapositive 21 — Limites et perspectives [0:45]

**Affiché**
- Limites : coûts estimés par des taux moyens ; jours fériés non gérés ; messages de validation en anglais
- Perspectives : vraies distances routières et paiement Mobile Money réel ; Min-Conflict étendu aux absences imprévues

**Script**
> Je préfère vous montrer moi-même les limites. Les coûts sont estimés avec des taux moyens, et les jours fériés ne sont pas gérés. En perspective : brancher un vrai paiement Mobile Money, MVola ou Orange Money, et étendre Min-Conflict aux absences déclarées par les freelances, qui aujourd'hui demandent un recalcul complet.

---

## Diapositive 22 — Conclusion [0:30]

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
