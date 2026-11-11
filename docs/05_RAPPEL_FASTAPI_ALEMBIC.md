# 05 — Rappel de cours : FastAPI et Alembic, à partir du code de SmartBricks

Ce rappel n'utilise **que des extraits du projet** : chaque notion est illustrée par le code réellement exécuté. Les chemins sont relatifs à `backend/`.

---

## Partie 1 — FastAPI

### 1.1 L'application et le routeur racine

Une application FastAPI est un objet `FastAPI()` ; les routes sont regroupées dans des `APIRouter` qu'on « inclut » avec un préfixe.

`app/main.py` :

```python
app = FastAPI(
    title="SmartBricks API",
    description=(
        "Du besoin flou du client au projet informatique réaliste : "
        "copilote IA et algorithmes d'optimisation."
    ),
    version="0.1.0",
)

api = APIRouter(prefix="/api/v1")
...
api.include_router(auth.router)
api.include_router(assistant.router)
api.include_router(projects.router)
api.include_router(catalog.router)
api.include_router(benchmark.router)
api.include_router(admin.router)

app.include_router(api)
```

- Toutes les routes commencent donc par `/api/v1`.
- Chaque module de `app/routers/` déclare son propre routeur. Par exemple `app/routers/auth.py` : `router = APIRouter(prefix="/auth", tags=["authentification"])`. Ses routes sont alors `/api/v1/auth/register`, `/api/v1/auth/login` et `/api/v1/auth/me`.
- Les `tags` regroupent les routes dans la documentation `/docs`, générée automatiquement à partir des types (OpenAPI). C'est ce qui donne les sections « B · sac à dos (n°29) », « D · planning CSP (n°3) », etc.

Le middleware CORS autorise le frontend Vite (port 5173) :

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### 1.2 Déclarer une route : méthode, chemin, paramètres

Le décorateur fixe la méthode HTTP et le chemin. Les paramètres de la fonction sont lus automatiquement :
- un nom présent dans le chemin (`{project_id}`) devient un **paramètre de chemin** ;
- un type simple absent du chemin devient un **paramètre de requête** (`?closed=true`) ;
- un modèle Pydantic devient le **corps JSON**.

`app/routers/projects.py` :

```python
@router.get("/projects/{project_id}/tour", tags=["E · tournée (n°30)"])
async def tour_preview(
    project_id: int,                                   # chemin
    freelancer_id: int | None = None,                  # requête, facultatif
    closed: bool = True,                               # requête, défaut True
    cost_per_km: int = Query(default=1_200, gt=0),     # requête, validé > 0
    session: AsyncSession = Depends(get_session),      # dépendance
    user: User = Depends(get_current_user),            # dépendance
) -> dict[str, Any]:
    """Même calcul que POST, sans rien enregistrer : aperçu pendant que le client règle les options."""
    data = TourIn(freelancer_id=freelancer_id, closed=closed, cost_per_km=cost_per_km)
    return await touring.compute_tour(session, await get_project(session, project_id, user), data, persist=False)
```

- `project_id: int` : si on appelle `/projects/abc/tour`, FastAPI répond `422` sans exécuter la fonction.
- `Query(default=1_200, gt=0)` ajoute une contrainte : `cost_per_km=0` → `422`.
- La docstring apparaît dans `/docs`.

Le statut de réponse se règle dans le décorateur (`app/routers/auth.py`) :

```python
@router.post("/register", response_model=TokenOut, status_code=status.HTTP_201_CREATED)
```

### 1.3 La séparation route / service / algorithme

Les routes de SmartBricks sont volontairement **minces**. Elles lisent la requête, vérifient l'accès, puis délèguent à un service :

```python
@router.post("/projects/{project_id}/scope", response_model=ScopeOut, tags=["B · sac à dos (n°29)"])
async def scope(project_id: int, session: AsyncSession = Depends(get_session),
                user: User = Depends(get_current_user)) -> ScopeOut:
    """Sprint 1 optimal sous le budget en Ar ET les heures, avec raisons et scénarios « et si ? »."""
    return await scoping.run_scope(session, await get_project(session, project_id, user))
```

- `app/routers/` : HTTP (FastAPI).
- `app/services/` : lien entre la base, les algorithmes et le LLM (SQLAlchemy).
- `app/algorithms/` : fonctions pures (ni FastAPI, ni base). C'est ce qui permet de les tester seules avec pytest.

---

## Partie 2 — Validation avec Pydantic v2

### 2.1 Modèles d'entrée

Un modèle hérite de `BaseModel`. `Field` ajoute des contraintes. FastAPI valide le corps JSON **avant** d'appeler la route.

`app/schemas.py` :

```python
class RegisterIn(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    # On ne peut pas s'inscrire soi-même comme administrateur.
    role: Role = Role.CLIENT
    organization_name: str | None = Field(default=None, max_length=200)


class FeaturePatch(BaseModel):
    business_value: int | None = Field(default=None, ge=1, le=100)
    estimated_hours: int | None = Field(default=None, gt=0)
    is_mandatory: bool | None = None


class SolveIn(BaseModel):
    scenario: Literal["normal", "impossible"] = Field(
        default="normal", description="« impossible » : date limite ramenée à 3 semaines (non enregistrée)."
    )
    deadline: date | None = Field(default=None, description="Autre date limite à tester (non enregistrée).")
```

| Entrée envoyée | Réponse |
|---|---|
| `PATCH /features/1 {"business_value": 150}` | `422` : `le=100` violé |
| `PATCH /features/1 {"estimated_hours": 0}` | `422` : `gt=0` violé |
| `POST /solve-constraints {"scenario": "facile"}` | `422` : valeur hors du `Literal` |
| `POST /solve-constraints {"deadline": "2026-11-20"}` | chaîne convertie en `date` |
| `POST /auth/register` avec un email invalide | `422` (`EmailStr`) |

Les champs `| None = None` rendent `FeaturePatch` partiel : on ne corrige que ce qu'on envoie. Le service détecte le cas où rien n'est envoyé (`app/services/projects_view.py`) :

```python
if not any(v is not None for v in data.model_dump().values()):
    raise AppError(422, "Rien à modifier.")
```

### 2.2 Modèles de sortie et `from_attributes`

`response_model` filtre et documente la réponse. `from_attributes=True` permet de construire le modèle directement depuis un objet SQLAlchemy. C'est ce qui garantit que `password_hash` ne sort **jamais** :

```python
class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    email: str
    role: Role
    organization_name: str | None
```

et dans `app/routers/auth.py` : `UserOut.model_validate(user)`.

### 2.3 Pydantic pour la configuration et pour le LLM

- `app/config.py` utilise `pydantic_settings.BaseSettings` : chaque champ est lu depuis une variable d'environnement ou depuis `.env`. Par exemple, `llm_provider: Literal["mock", "gemini", "claude"] = "mock"` refuse toute autre valeur au démarrage. `env_ignore_empty=True` fait qu'une ligne vide comme `CLAUDE_PRICE_INPUT_PER_MTOK=` garde la valeur par défaut `None`.
- Le brouillon produit par le LLM est validé par le modèle `Draft` (`app/llm/draft.py`). Un JSON mal formé donne une `ValidationError`, dont le message est renvoyé une fois au LLM pour une nouvelle tentative.

---

## Partie 3 — L'injection de dépendances : `Depends`

`Depends(f)` demande à FastAPI d'appeler `f` avant la route et de passer son résultat en paramètre. Les dépendances peuvent elles-mêmes avoir des dépendances.

### 3.1 La session de base de données par requête

`app/db.py` :

```python
engine = create_async_engine(get_settings().database_url, pool_pre_ping=True)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False)


async def get_session() -> AsyncIterator[AsyncSession]:
    async with SessionLocal() as session:
        yield session
```

- C'est un **générateur** : ce qui précède `yield` s'exécute avant la route (ouverture de la session), ce qui suit s'exécute après (fermeture automatique par `async with`, même en cas d'erreur).
- `engine` est un pool de connexions asyncpg, partagé par toute l'application. `pool_pre_ping=True` teste une connexion avant de la réutiliser.
- `expire_on_commit=False` : après `commit()`, les objets restent lisibles sans nouvelle requête (important en asynchrone, voir 4.2).

### 3.2 L'utilisateur courant

`app/security.py` :

```python
_bearer = HTTPBearer(auto_error=False)

async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    session: AsyncSession = Depends(get_session),
) -> User:
    """Dépendance FastAPI : renvoie l'utilisateur du jeton « Authorization: Bearer … »."""
    if credentials is None:
        raise _NON_AUTHENTIFIE
    try:
        payload = jwt.decode(credentials.credentials, get_settings().jwt_secret, algorithms=[ALGORITHM])
        user_id = int(payload["sub"])
    except (jwt.PyJWTError, KeyError, ValueError):
        raise _NON_AUTHENTIFIE from None
    user = await session.get(User, user_id)
    if user is None:
        raise _NON_AUTHENTIFIE
    return user
```

- Chaîne de dépendances : `HTTPBearer` lit l'en-tête, `get_session` ouvre la session, `get_current_user` décode le JWT (signature et expiration vérifiées par `jwt.decode`) puis charge l'utilisateur.
- FastAPI **met en cache** une dépendance pendant une requête : la route et `get_current_user` reçoivent **la même** session.
- `HTTPBearer` fait aussi apparaître le bouton « Authorize » dans `/docs`.

### 3.3 Restreindre par rôle : une fabrique de dépendances

```python
def require_role(*roles: Role) -> Callable[..., Awaitable[User]]:
    """Dépendance qui n'autorise que certains rôles, par exemple `require_role(Role.ADMIN)`."""

    async def checker(user: User = Depends(get_current_user)) -> User:
        if user.role not in roles:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Accès réservé : rôle insuffisant.")
        return user

    return checker
```

Elle est utilisée par les routes d'administration (`GET /admin/llm-usage`, `GET /benchmark`) sous la forme `Depends(require_role(Role.ADMIN))`. Un client reçoit `403`, un visiteur sans jeton `401`.

### 3.4 Le contrôle d'accès au projet

Ce n'est pas une dépendance mais une fonction de service, appelée par chaque route de projet (`app/services/project_data.py`) :

```python
async def get_project(session: AsyncSession, project_id: int, user: User) -> Project:
    """Projet du client connecté (l'administrateur voit tout)."""
    project = await session.scalar(
        select(Project).where(Project.id == project_id).options(selectinload(Project.base_city))
    )
    if project is None:
        raise not_found("Projet")
    if user.role != Role.ADMIN and project.client_id != user.id:
        raise AppError(403, "Ce projet appartient à un autre client.")
    return project
```

---

## Partie 4 — Asynchrone et SQLAlchemy 2 asynchrone

### 4.1 `async` / `await`

Une fonction `async def` est une coroutine. `await` rend la main à la boucle d'événements pendant une attente d'entrée/sortie (réseau, base de données, appel au LLM), ce qui permet au serveur (uvicorn) de traiter d'autres requêtes pendant ce temps. Dans SmartBricks, toutes les routes sont `async`, et toute requête SQL est attendue :

```python
user = await session.scalar(select(User).where(func.lower(User.email) == data.email.lower()))
```

Les algorithmes, eux, sont **synchrones**. Ce sont des calculs purs, qui ne font aucune entrée/sortie. Pendant ce temps, la boucle est occupée, d'où la limite de 3 s du CSP.

### 4.2 Requêtes avec le style SQLAlchemy 2

| Besoin | Code du projet |
|---|---|
| Un objet par clé primaire | `await session.get(User, user_id)` |
| Un seul résultat | `await session.scalar(select(Project).where(Project.id == project_id))` |
| Une liste | `(await session.scalars(select(Feature).where(Feature.project_id == project_id).order_by(Feature.id))).all()` |
| Jointure et filtre | `query.join(Feature, Feature.id == Task.feature_id).where(Feature.selected_for_sprint.is_(True))` |
| Filtre sur une liste | `select(TaskDependency).where(TaskDependency.task_id.in_(ids))` |

**Chargement des relations.** En asynchrone, accéder à une relation non chargée (`task.required_skill`) déclencherait une requête implicite *synchrone* : c'est une erreur (`MissingGreenlet`). Le projet charge donc toutes les relations d'avance avec `selectinload` (`app/services/project_data.py`) :

```python
query = (
    select(Task)
    .where(Task.project_id == project_id)
    .options(selectinload(Task.required_skill), selectinload(Task.on_site_city))
    .order_by(Task.id)
)
```

et en chaîne pour les freelances : `selectinload(FreelancerProfile.skills).selectinload(FreelancerSkill.skill)`.

### 4.3 Écrire : `add`, `flush`, `commit`, `refresh`

Inscription (`app/routers/auth.py`) :

```python
user = User(name=data.name, email=email, password_hash=hash_password(data.password),
            role=data.role, organization_name=data.organization_name)
session.add(user)          # l'objet est suivi par la session
await session.commit()     # INSERT puis COMMIT
await session.refresh(user)  # relit l'id et created_at générés par la base
```

Correction d'une fonctionnalité (`app/services/projects_view.py`) :

```python
project.status = ProjectStatus.DRAFT
project.scope_report = None  # le cadrage affiché n'est plus valable
await session.flush()                              # envoie les UPDATE sans valider la transaction
await recompute_feature_costs(session, project.id) # relit les tâches modifiées
await session.commit()                             # tout ou rien
```

`flush` envoie les modifications à la base dans la transaction en cours, pour que les requêtes suivantes les voient. `commit` les valide définitivement. Si une exception survient avant le `commit`, la session est fermée par `get_session` et rien n'est enregistré.

### 4.4 Les modèles (tables)

`app/models.py`, style SQLAlchemy 2 typé (`Mapped`, `mapped_column`) :

```python
class Feature(Base):
    """Fonctionnalité (exigence du cahier des charges) : un objet du sac à dos."""

    __tablename__ = "features"
    __table_args__ = (
        CheckConstraint("business_value BETWEEN 1 AND 100", name="ck_business_value"),
        CheckConstraint("estimated_hours > 0", name="ck_feature_hours"),
        CheckConstraint("estimated_cost_mga >= 0", name="ck_feature_cost"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    ...
    depends_on_feature_ids: Mapped[list[int]] = mapped_column(ARRAY(Integer), default=list)
    selected_for_sprint: Mapped[bool] = mapped_column(Boolean, default=False)

    project: Mapped[Project] = relationship(back_populates="features")
```

- Les `CheckConstraint` sont une seconde barrière, côté base, en plus de Pydantic.
- `ARRAY(Integer)` et `JSONB` (pour `Project.scope_report`) sont des types propres à PostgreSQL.
- `Mapped[str | None]` rend la colonne nullable. `Mapped[int]` la rend `NOT NULL`.

### 4.5 Tester l'API asynchrone

`tests/conftest.py` appelle l'application **sans lancer de serveur**, grâce au transport ASGI de httpx :

```python
@pytest.fixture
async def client() -> AsyncIterator[AsyncClient]:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


@pytest.fixture
async def demo(client: AsyncClient) -> dict[str, object]:
    """Base remise à l'état de démonstration ; renvoie le résumé du seed."""
    reponse = await client.post("/api/v1/admin/reset-demo")
    assert reponse.status_code == 200, reponse.text
    return reponse.json()
```

---

## Partie 5 — Gestion des erreurs

Le projet utilise deux mécanismes.

**1. `HTTPException` dans les routes et la sécurité**, qui dépendent déjà de FastAPI :

```python
if user is None or not verify_password(data.password, user.password_hash):
    raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Email ou mot de passe incorrect.")
```

Le message est le même que l'email existe ou non, pour ne pas révéler les comptes existants.

**2. `AppError` dans les services**, qui ne doivent pas dépendre de FastAPI (`app/errors.py`) :

```python
class AppError(Exception):
    def __init__(self, status_code: int, detail: str) -> None:
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


def not_found(what: str) -> AppError:
    return AppError(404, f"{what} introuvable.")


def conflict(detail: str) -> AppError:
    return AppError(409, detail)
```

Un **gestionnaire d'exceptions** global la transforme en réponse HTTP (`app/main.py`) :

```python
@app.exception_handler(AppError)
async def app_error_handler(_request: Request, exc: AppError) -> JSONResponse:
    """Les erreurs métier des services deviennent des réponses HTTP avec un message en français."""
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})
```

Les deux mécanismes produisent le même format `{"detail": "..."}`, que le frontend affiche tel quel. Codes utilisés dans le projet :

| Code | Signification | Exemple réel |
|---|---|---|
| 401 | non authentifié | « Authentification requise ou jeton invalide. » |
| 403 | interdit | « Ce projet appartient à un autre client. » |
| 404 | introuvable | « Projet introuvable. », `GET /scope` avant le cadrage |
| 409 | conflit d'état | « Projet déjà créé (n°2). », matching avant le cadrage |
| 422 | données invalides | erreurs Pydantic, « Rien à modifier. », compétences inconnues |

Un planning impossible **n'est pas** une erreur HTTP : la route répond `200` avec `status: "INFEASIBLE"` et un diagnostic. C'est un résultat métier normal, que l'interface doit afficher.

---

## Partie 6 — Alembic

### 6.1 Rôle

Alembic **versionne le schéma de la base**, comme git versionne le code. Chaque changement de schéma est un fichier de migration avec une fonction `upgrade()` (appliquer) et `downgrade()` (annuler). Les fichiers forment une chaîne : chacun connaît son parent (`down_revision`). La base garde, dans la table `alembic_version`, l'identifiant de la dernière migration appliquée.

Pourquoi ne pas utiliser `Base.metadata.create_all()` ? Parce que `create_all` ne crée que les tables absentes. Il ne sait ni ajouter une colonne à une table existante, ni revenir en arrière. Il ne laisse pas non plus d'historique.

### 6.2 Configuration : `alembic.ini` et `env.py`

`alembic.ini` (lignes utiles) :

```ini
script_location = alembic
prepend_sys_path = .
file_template = %%(year)d%%(month).2d%%(day).2d_%%(rev)s_%%(slug)s
```

- `prepend_sys_path = .` permet à `env.py` d'importer `app` depuis `backend/`.
- `file_template` donne des noms datés, comme `20261111_e5b4f7c775e5_rapport_de_cadrage.py`.

`alembic/env.py`, en version asynchrone :

```python
from app.config import get_settings
from app.models import Base

target_metadata = Base.metadata
DATABASE_URL = get_settings().database_url

def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()

async def run_migrations_online() -> None:
    """Se connecte à la base et applique les migrations."""
    engine = create_async_engine(DATABASE_URL)
    async with engine.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await engine.dispose()

if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
```

- `target_metadata = Base.metadata` est le **schéma voulu**, décrit par les modèles. L'autogénération le compare au schéma réel de la base.
- L'URL vient de la même configuration que l'application (`.env`, port 5435). Il n'y a pas de doublon dans `alembic.ini`.
- Alembic est synchrone : `connection.run_sync(...)` exécute les migrations dans une connexion asyncpg.

### 6.3 Les commandes, avec les migrations du projet

Toutes les commandes se lancent depuis `backend/`, avec le venv : `.venv/bin/alembic …`, ou `alembic …` si le venv est activé.

**Créer une migration par autogénération** (après avoir modifié `app/models.py`) :

```bash
.venv/bin/alembic revision --autogenerate -m "rapport de cadrage"
```

Alembic compare `Base.metadata` à la base et écrit le fichier. Pour l'ajout de `Project.scope_report`, cela a produit :

```python
revision: str = 'e5b4f7c775e5'
down_revision: str | None = '766faa1a8da4'

def upgrade() -> None:
    op.add_column('projects', sa.Column('scope_report', postgresql.JSONB(astext_type=sa.Text()), nullable=True))

def downgrade() -> None:
    op.drop_column('projects', 'scope_report')
```

Il faut **toujours relire** une migration autogénérée. Alembic ne détecte pas tout : renommages (vus comme une suppression puis un ajout), certains changements de type, et les types `Enum` PostgreSQL, qui doivent être supprimés à la main dans `downgrade`.

`alembic revision -m "..."`, sans `--autogenerate`, crée un fichier vide à remplir à la main (migration de données, par exemple).

**Appliquer les migrations :**

```bash
.venv/bin/alembic upgrade head      # jusqu'à la dernière
.venv/bin/alembic upgrade +1        # une seule étape
```

**Revenir en arrière :**

```bash
.venv/bin/alembic downgrade -1             # annule la dernière (supprime scope_report)
.venv/bin/alembic downgrade 77f1eb594797   # revient au schéma initial
.venv/bin/alembic downgrade base           # tout annuler
```

**Consulter l'état.** Sortie réelle sur la base du projet :

```text
$ .venv/bin/alembic history
766faa1a8da4 -> e5b4f7c775e5 (head), rapport de cadrage
77f1eb594797 -> 766faa1a8da4, suivi des couts llm
<base> -> 77f1eb594797, schema initial

$ .venv/bin/alembic current
e5b4f7c775e5 (head)

$ .venv/bin/alembic heads
e5b4f7c775e5 (head)
```

| Migration | Contenu |
|---|---|
| `77f1eb594797` schéma initial | toutes les tables du cahier des charges, types enum, contraintes de vérification |
| `766faa1a8da4` suivi des coûts LLM | table `llm_usage` (tokens, coût) et index sur `created_at` |
| `e5b4f7c775e5` rapport de cadrage | colonne `projects.scope_report` (JSONB) |

**Voir le SQL sans l'exécuter (mode hors ligne) :** `alembic upgrade head --sql` (branche `run_migrations_offline` de `env.py`).

### 6.4 Cycle de travail suivi dans le projet

1. Modifier `app/models.py`.
2. `alembic revision --autogenerate -m "..."`.
3. Relire le fichier généré dans `alembic/versions/`.
4. `alembic upgrade head`.
5. Tester `alembic downgrade -1` puis `alembic upgrade head`, pour vérifier que l'aller-retour fonctionne.
6. Commiter le modèle **et** la migration ensemble.

`POST /admin/reset-demo` vide et remplit les tables (seed). Il ne touche pas au schéma, qui reste la responsabilité d'Alembic.

---

## Partie 7 — Auto-évaluation : 10 questions

**1. Que se passe-t-il si un client envoie `{"business_value": 150}` à `PATCH /features/3` ?**
Pydantic refuse avant l'appel de la fonction, car `FeaturePatch.business_value` a `le=100`. La réponse est `422`, avec le champ en cause. La base a de toute façon une deuxième barrière : `CheckConstraint("business_value BETWEEN 1 AND 100")`.

**2. Pourquoi `get_session` utilise-t-il `yield` et non `return` ?**
Le code après `yield` s'exécute une fois la réponse produite. Ici, c'est la sortie du `async with`, qui ferme la session et rend la connexion au pool, même si la route a levé une exception.

**3. Une route reçoit `session` et appelle `get_current_user`, qui reçoit aussi `session`. Combien de sessions sont ouvertes ?**
Une seule. FastAPI met en cache le résultat d'une dépendance pendant toute la requête.

**4. Comment `password_hash` est-il empêché de sortir dans les réponses ?**
Les routes renvoient `UserOut`, construit par `UserOut.model_validate(user)`, qui ne déclare pas ce champ. Le `response_model` filtre de toute façon la sortie.

**5. Pourquoi les services lèvent-ils `AppError` plutôt que `HTTPException` ?**
Pour ne pas dépendre de FastAPI : ils restent utilisables dans les tests ou un script. Le gestionnaire `@app.exception_handler(AppError)` de `main.py` fait la traduction en HTTP avec le même format `{"detail": ...}`.

**6. Pourquoi `selectinload` est-il indispensable en SQLAlchemy asynchrone ?**
Accéder à une relation non chargée déclencherait une requête implicite synchrone, interdite dans une coroutine (erreur `MissingGreenlet`). On charge donc les relations d'avance, en une requête `SELECT … WHERE id IN (...)` par relation.

**7. Quelle différence entre `flush()` et `commit()` dans `patch_feature` ?**
`flush` envoie les `UPDATE` dans la transaction ouverte : `recompute_feature_costs` voit ainsi les nouvelles heures des tâches. `commit` valide la transaction. Si une erreur survient entre les deux, rien n'est enregistré.

**8. Un planning impossible renvoie-t-il une erreur HTTP ?**
Non : `200` avec `status: "INFEASIBLE"` et `diagnostics`. Ce n'est pas une erreur du client ni du serveur, c'est une réponse métier à afficher.

**9. Que fait `alembic revision --autogenerate`, et que faut-il faire ensuite ?**
Il compare `target_metadata = Base.metadata` (modèles) au schéma réel de la base, puis écrit un fichier avec `upgrade()` et `downgrade()`. Il faut le relire (renommages, enums, types), puis l'appliquer avec `alembic upgrade head` et tester le retour avec `downgrade -1`.

**10. La base est à `766faa1a8da4`. Que donne `alembic upgrade head`, puis `alembic downgrade -1` ?**
`upgrade head` applique `e5b4f7c775e5` : la colonne `projects.scope_report` est ajoutée, et `alembic current` affiche `e5b4f7c775e5 (head)`. `downgrade -1` exécute son `downgrade()` : la colonne est supprimée et la base revient à `766faa1a8da4`.
