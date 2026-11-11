# 01 — Guide de lancement

Ce guide permet d'installer et de lancer SmartBricks sur une machine Windows avec WSL Ubuntu, puis d'activer (si on le souhaite) le copilote Claude. Toutes les commandes se tapent **dans un terminal WSL Ubuntu**, depuis le dossier du projet `~/projets/smartbricks`.

> Par défaut, l'application fonctionne **sans clé d'API et sans internet** : le copilote utilise un fournisseur simulé (`LLM_PROVIDER=mock`).

---

## 1. Prérequis

| Outil | Version testée | Vérifier avec |
|---|---|---|
| Windows + WSL 2, distribution Ubuntu | Windows 11 | `wsl -l -v` (dans PowerShell) |
| Docker Desktop, avec l'intégration WSL activée pour Ubuntu | — | `docker version` (dans WSL) |
| Python | 3.11 ou plus (le projet tourne en 3.14) | `python3 --version` |
| Node.js | 20 ou plus (le projet tourne en 24) | `node --version` |
| pnpm | 10 ou plus (le projet tourne en 12) | `pnpm --version` |
| `uv` (facultatif) | — | `uv --version` |

**Intégration WSL de Docker** : Docker Desktop → *Settings* → *Resources* → *WSL integration* → cocher **Ubuntu** → *Apply & restart*. Sans cela, la commande `docker` n'existe pas dans WSL.

---

## 2. Installation pas à pas

### 2.1 Fichier de configuration

```bash
cd ~/projets/smartbricks
cp .env.example .env
```

`.env` contient les réglages locaux (base, secret JWT, copilote). Il est listé dans `.gitignore` : **il n'est jamais commité**.

### 2.2 Base PostgreSQL (Docker)

```bash
docker compose up -d
docker ps --filter name=smartbricks_db      # doit afficher « (healthy) » après quelques secondes
```

> **Port 5435 et non 5433.** La spécification initiale prévoyait le port 5433, mais sur la machine de développement 5432, 5433 et 5434 étaient déjà utilisés par d'autres projets. Le projet utilise donc **5435** (`docker-compose.yml`, `.env.example`, `backend/app/config.py`). Pour changer de port, modifier ces trois endroits (voir § 6).

### 2.3 Backend Python

```bash
cd backend
python3 -m venv .venv                         # ou : uv venv .venv  (si le module venv manque)
.venv/bin/pip install -r requirements.txt     # ou : uv pip install --python .venv/bin/python -r requirements.txt
```

> Sur Ubuntu avec Python 3.14, le module `venv` peut manquer (« ensurepip is not available »). Deux solutions : `sudo apt install python3.14-venv`, ou utiliser `uv` comme ci-dessus (c'est ce qui a été fait pendant le développement).

### 2.4 Migrations Alembic (création des tables)

```bash
.venv/bin/alembic upgrade head
.venv/bin/alembic current        # doit afficher e5b4f7c775e5 (head)
```

Trois migrations sont appliquées dans l'ordre : `77f1eb594797` (schéma initial), `766faa1a8da4` (suivi des coûts LLM), `e5b4f7c775e5` (rapport de cadrage).

### 2.5 Chargement des données de démonstration

```bash
.venv/bin/python -m app.seed
```

Résultat attendu : 12 villes, 11 compétences, 25 freelances, 27 comptes, le projet « Boutique Soa » (14 fonctionnalités, 30 tâches). La même opération est disponible par l'API : `POST /api/v1/admin/reset-demo` (et par le bouton « Réinitialiser la démo » du tableau de bord).

Comptes créés :

| Rôle | Email | Mot de passe |
|---|---|---|
| Client (Soa, Boutique Soa) | `client@smartbricks.mg` | `demo1234` |
| Administrateur | `admin@smartbricks.mg` | `admin1234` |
| Freelances | `<prénom>@freelance.mg` (ex. `rivo@freelance.mg`) | `demo1234` |

### 2.6 Lancer le backend

```bash
cd ~/projets/smartbricks/backend
.venv/bin/uvicorn app.main:app --reload --port 8000
```

- Documentation interactive : <http://localhost:8000/docs>
- Test rapide : <http://localhost:8000/api/v1/health> → `{"status":"ok","database":"ok","llm_provider":"mock","environment":"development"}`

### 2.7 Lancer le frontend (second terminal)

```bash
cd ~/projets/smartbricks/frontend
pnpm install
pnpm dev
```

Ouvrir <http://localhost:5173> et se connecter avec un compte de démonstration (boutons en un clic sur la page de connexion). Vite redirige les appels `/api` vers le backend (port 8000) : il n'y a rien à configurer pour CORS.

Pour une version de production : `pnpm build` (vérifie aussi les types TypeScript), puis `pnpm preview`.

### 2.8 Lancer les tests

```bash
cd ~/projets/smartbricks/backend
.venv/bin/pytest -q                       # toute la suite
.venv/bin/pytest tests/algorithms -v      # les algorithmes seuls
```

> **Attention** : les tests d'API utilisent la base de développement et appellent `reset-demo`. Les projets créés à la main sont donc effacés (les données de démonstration sont recréées à l'identique). La table `llm_usage` (consommation réelle du LLM) n'est jamais effacée.

### 2.9 Récapitulatif (moins de 10 minutes)

```bash
cd ~/projets/smartbricks && cp .env.example .env && docker compose up -d
cd backend && python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/alembic upgrade head && .venv/bin/python -m app.seed
.venv/bin/uvicorn app.main:app --reload &
cd ../frontend && pnpm install && pnpm dev
```

---

## 3. Ajouter la clé API Claude

Le copilote peut utiliser Claude (Anthropic) au lieu du fournisseur simulé. Les algorithmes restent les mêmes : Claude ne sert qu'à dialoguer, extraire le brouillon et rédiger l'explication.

### 3.1 Créer la clé

1. Se connecter sur <https://console.anthropic.com>.
2. Menu **API Keys** → **Create Key** → donner un nom (par exemple `smartbricks-dev`) → copier la clé (`sk-ant-…`). Elle n'est affichée qu'une fois.

### 3.2 Fixer une limite de dépense dans la console

Dans la console Anthropic, section **Limits** (paramètres de l'organisation ou de l'espace de travail) : définir une **limite de dépense mensuelle** basse (quelques dollars). C'est la protection côté fournisseur ; SmartBricks ajoute sa propre protection (`LLM_BUDGET_USD`, § 3.3).

### 3.3 Remplir `.env`

```dotenv
LLM_PROVIDER=claude
ANTHROPIC_API_KEY=sk-ant-...
CLAUDE_MODEL=claude-haiku-5-5
CLAUDE_MAX_TOKENS=8000
CLAUDE_EFFORT=low
CLAUDE_PRICE_INPUT_PER_MTOK=0.10
CLAUDE_PRICE_OUTPUT_PER_MTOK=0.50
LLM_BUDGET_USD=4
```

| Variable | Rôle |
|---|---|
| `LLM_PROVIDER` | `mock`, `claude` ou `gemini` |
| `CLAUDE_MODEL` | modèle utilisé (par défaut le Haiku le plus récent, `claude-haiku-5-5`) |
| `CLAUDE_MAX_TOKENS` | plafond de tokens générés par appel |
| `CLAUDE_EFFORT` | profondeur de réflexion (`low` par défaut, pour limiter le coût) |
| `CLAUDE_PRICE_INPUT_PER_MTOK`, `CLAUDE_PRICE_OUTPUT_PER_MTOK` | prix en dollars **par million de tokens**, utilisés pour calculer le coût de chaque appel. **Obligatoires** : sans prix, Claude reste désactivé (le budget ne pourrait pas être contrôlé) |
| `LLM_BUDGET_USD` | budget total en dollars ; une fois atteint, l'application **repasse automatiquement en mode mock** et l'écrit dans les logs |

> Les prix indiqués (0,10 $ et 0,50 $ par million de tokens pour `claude-haiku-5-5`, requêtes jusqu'à 100 000 tokens) sont ceux connus au moment du développement. **Vérifier les prix en vigueur sur la page de tarifs d'Anthropic** avant de les saisir.

**Redémarrer uvicorn** après toute modification de `.env` : la configuration est lue une seule fois au démarrage.

### 3.4 Tester avec un seul appel

1. Au démarrage, les logs ne doivent **pas** contenir « passage automatique en mode mock ». Sinon, le message indique la cause (clé absente, prix non renseignés, budget atteint).
2. `GET /api/v1/health` doit répondre `"llm_provider": "claude"`.
3. Envoyer **un seul** message au copilote, par l'interface (« Nouveau projet ») ou par `/docs` :
   `POST /api/v1/assistant/chat` avec `{"message": "Je veux un site vitrine pour ma boulangerie à Antsirabe."}`
   La réponse contient `"provider": "claude"`.
4. Les logs affichent une ligne du type :
   `Appel claude (claude-haiku-5-5, chat) : 412 tokens en entrée, 85 en sortie, 0.000084 $`

### 3.5 Consulter la consommation

Se connecter en administrateur, puis `GET /api/v1/admin/llm-usage` (bouton « Authorize » de `/docs` avec le jeton administrateur). La réponse donne : fournisseur configuré et fournisseur effectif, raison d'une éventuelle bascule, budget, dépense, reste, tokens d'entrée et de sortie, détail par modèle et les 20 derniers appels.

### 3.6 Revenir en mode mock

Dans `.env` : `LLM_PROVIDER=mock`, puis redémarrer uvicorn. La consommation déjà enregistrée est conservée (table `llm_usage`).

### 3.7 État de l'intégration Claude (vérifié dans le code)

- [x] Fournisseur Claude présent : `backend/app/llm/claude.py` (SDK officiel `anthropic`)
- [x] Sélection par `LLM_PROVIDER` : `get_provider()` dans `backend/app/services/llm_usage.py`
- [x] Modèle configurable dans `.env` : `CLAUDE_MODEL` (défaut `claude-haiku-5-5`), `CLAUDE_MAX_TOKENS`, `CLAUDE_EFFORT`
- [x] Sortie JSON structurée pour l'extraction du brouillon : `output_config.format` avec le schéma `DRAFT_JSON_SCHEMA` (`backend/app/llm/draft.py`)
- [x] Une seule nouvelle tentative si le JSON est invalide, avec le message d'erreur : `extract_draft()` dans `backend/app/services/copilot.py`
- [x] Détection et suppression des cycles de dépendances : `break_cycles()` dans `backend/app/algorithms/dependencies.py`
- [x] Route d'explication : `POST /api/v1/projects/{id}/explain`, avec contrôle des nombres cités (`explain()` dans `copilot.py`)
- [x] Suivi des tokens et du coût : table `llm_usage`, `record_usage()` dans `llm_usage.py`
- [x] Plafond `LLM_BUDGET_USD` avec retour automatique en mode mock, signalé dans les logs
- [x] Route `GET /api/v1/admin/llm-usage` (administrateur)
- [x] `.env` dans `.gitignore`, jamais commité
- [x] Tests sans appel réseau (client Claude simulé) : `backend/tests/test_llm_usage.py`, `backend/tests/test_copilot.py`
- [ ] **Non testé avec une vraie clé** : aucun appel réel à Claude n'a été fait pendant le développement. Le fournisseur **Gemini** (`backend/app/llm/gemini.py`) est écrit mais n'a été testé ni avec une clé, ni avec un client simulé.

---

## 4. Problèmes fréquents

### Port déjà utilisé

| Symptôme | Cause et solution |
|---|---|
| `Bind for 127.0.0.1:5435 failed: port is already allocated` | Un autre conteneur utilise le port. `docker ps` pour l'identifier ; soit l'arrêter, soit changer le port (§ 6). |
| `password authentication failed for user "smartbricks"` lors des migrations | Le port configuré est servi par **une autre** base PostgreSQL (cas réel rencontré avec 5433). Vérifier `docker ps` et le port de `DATABASE_URL`. |
| `[Errno 98] address already in use` sur le port 8000 | Un uvicorn tourne déjà : `pkill -f "uvicorn app.main:app"`, ou lancer avec `--port 8001` (et adapter `frontend/vite.config.ts`). |
| Vite démarre sur 5174 au lieu de 5173 | Le port 5173 est pris. Vite fonctionne quand même ; seule l'URL change. |

### Migration en échec

- `Connection refused` : la base n'est pas démarrée → `docker compose up -d`, attendre l'état `healthy`.
- `relation "..." already exists` : la base contient des tables créées hors Alembic. En développement, repartir de zéro : `docker compose down -v` (supprime le volume), `docker compose up -d`, `alembic upgrade head`, puis recharger la démo.
- Vérifier la version appliquée : `alembic current` et `alembic history`.

### CORS

En développement, le frontend passe par le proxy de Vite (`/api` → `http://localhost:8000`) : il n'y a pas de requête inter-origines. Si le frontend appelle directement l'API depuis une autre origine que `http://localhost:5173` ou `http://127.0.0.1:5173`, ajouter cette origine dans `allow_origins` de `backend/app/main.py`.

### Clé Claude invalide ou copilote resté en mock

- Logs « passage automatique en mode mock — aucune clé d'API claude » : `ANTHROPIC_API_KEY` vide ou mal nommée.
- Logs « … prix de Claude non renseignés » : remplir `CLAUDE_PRICE_INPUT_PER_MTOK` et `CLAUDE_PRICE_OUTPUT_PER_MTOK`.
- Logs « … budget LLM atteint » : augmenter `LLM_BUDGET_USD` (ou revenir en mock).
- Réponse 503 « Claude : clé d'API invalide » : la clé est refusée par Anthropic (révoquée, faute de frappe).
- Dans tous les cas : **redémarrer uvicorn** après avoir modifié `.env`.

### Autres

- `pnpm install` signale « Ignored build scripts: esbuild » : déjà réglé par `frontend/pnpm-workspace.yaml` (`allowBuilds: esbuild: true`).
- La carte de la tournée reste grise sans internet : l'écran bascule automatiquement sur le **schéma hors ligne** (ou ouvrir `/projets/1/tournee?vue=schema`).

---

## 5. Raccourcis utiles pendant une démonstration

| Lien | Effet |
|---|---|
| `/projets/1/planning?scenario=impossible` | lance le scénario « date limite à 3 semaines » et affiche son diagnostic |
| `/projets/1/tournee?vue=schema` | affiche la tournée sur le schéma hors ligne |
| `/copilote` puis « Utiliser l'exemple Boutique Soa » | rejoue la conversation de démonstration |

---

## 6. Changer le port de PostgreSQL

Modifier les trois endroits suivants, puis `docker compose down && docker compose up -d` :

1. `docker-compose.yml` : `ports: ["5435:5432"]`
2. `.env` (et `.env.example`) : `DATABASE_URL=postgresql+asyncpg://smartbricks:smartbricks@localhost:5435/smartbricks`
3. `backend/app/config.py` : valeur par défaut de `database_url`
