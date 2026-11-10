"""Module C — Matching freelance ↔ projet.

Deux algorithmes de la liste du cours :
- n°22 AGRÉGATION PONDÉRÉE : un score unique = Σ poids × critère normalisé, réglé par le client ;
- n°21 OPTIMISATION DE PARETO : les compromis « non dominés » entre coût, rapidité, qualité…,
  rangés en fronts successifs (tri non dominé comme dans NSGA-II).

Les deux sont complémentaires : l'agrégation donne UN classement, qui dépend des poids choisis ;
Pareto montre TOUS les bons compromis, sans avoir à choisir de poids.

CRITÈRES (calculés pour chaque freelance par rapport aux tâches retenues)
    Coût          taux horaire × heures des tâches qu'il sait faire                      à minimiser
    Rapidité      ces heures / (heures par jour × part de jours disponibles)            à minimiser
                  = nombre de jours ouvrés de calendrier qu'il lui faudrait
    Qualité       note × (0,5 + 0,5 × taux de livraison à l'heure)                      à maximiser
    Disponibilité jours disponibles d'ici la date limite                                à maximiser
    Couverture    heures qu'il sait faire / heures totales des tâches retenues          à maximiser

« Savoir faire une tâche » = avoir la compétence AU NIVEAU MINIMAL demandé par la tâche.
"""

from __future__ import annotations

import math
from collections.abc import Hashable, Mapping, Sequence
from dataclasses import dataclass, field

Id = Hashable

CRITERIA: tuple[str, ...] = ("cost", "speed", "quality", "availability", "coverage")
# +1 : plus c'est grand, mieux c'est ; −1 : plus c'est petit, mieux c'est.
DIRECTION: dict[str, int] = {"cost": -1, "speed": -1, "quality": 1, "availability": 1, "coverage": 1}
LABELS: dict[str, str] = {
    "cost": "Coût",
    "speed": "Rapidité",
    "quality": "Qualité",
    "availability": "Disponibilité",
    "coverage": "Couverture",
}

# Préréglages proposés au client (chacun somme à 1).
PRESETS: dict[str, dict[str, float]] = {
    "Économique": {"cost": 0.50, "speed": 0.10, "quality": 0.15, "availability": 0.10, "coverage": 0.15},
    "Rapide": {"cost": 0.10, "speed": 0.45, "quality": 0.10, "availability": 0.20, "coverage": 0.15},
    "Qualité": {"cost": 0.10, "speed": 0.10, "quality": 0.50, "availability": 0.15, "coverage": 0.15},
    "Équilibré": {"cost": 0.20, "speed": 0.20, "quality": 0.20, "availability": 0.20, "coverage": 0.20},
}


@dataclass(frozen=True)
class TaskNeed:
    id: Id
    skill: str
    min_level: int
    hours: int


@dataclass(frozen=True)
class Candidate:
    id: Id
    name: str
    hourly_rate: int
    rating: float  # 0 à 5
    on_time_rate: float  # 0 à 1
    hours_per_day: int
    skills: Mapping[str, int]  # compétence → niveau 1 à 5
    available_days: int  # jours ouvrés disponibles d'ici la date limite (calculé par calendar.py)

    def can_do(self, task: TaskNeed) -> bool:
        return self.skills.get(task.skill, 0) >= task.min_level

    @property
    def capacity_hours(self) -> int:
        """Heures qu'il peut fournir d'ici la date limite."""
        return self.hours_per_day * self.available_days


@dataclass(frozen=True)
class Criteria:
    cost: float
    speed: float
    quality: float
    availability: float
    coverage: float

    def get(self, key: str) -> float:
        return float(getattr(self, key))


@dataclass
class Ranked:
    id: Id
    score: float
    contributions: dict[str, float]  # poids × critère normalisé, pour les barres de l'interface
    normalized: dict[str, float]


@dataclass
class TeamSuggestion:
    members: list[Id]
    assignment: dict[Id, Id]  # tâche → freelance (charge prévisionnelle, pas encore le planning)
    load_hours: dict[Id, int]
    uncovered_tasks: list[Id] = field(default_factory=list)
    absorbable: bool = True
    warnings: list[str] = field(default_factory=list)


# =========================================================================== critères


def compute_criteria(c: Candidate, tasks: Sequence[TaskNeed], total_days: int) -> Criteria:
    """Calcule les 5 critères bruts d'un freelance. Complexité O(nombre de tâches)."""
    my_hours = sum(t.hours for t in tasks if c.can_do(t))
    all_hours = sum(t.hours for t in tasks)
    share = c.available_days / total_days if total_days > 0 else 0.0  # part de jours disponibles
    speed = my_hours / (c.hours_per_day * share) if share > 0 and c.hours_per_day > 0 else math.inf
    return Criteria(
        cost=c.hourly_rate * my_hours,
        speed=speed,
        quality=c.rating * (0.5 + 0.5 * c.on_time_rate),
        availability=c.available_days,
        coverage=my_hours / all_hours if all_hours else 0.0,
    )


def evaluate(candidates: Sequence[Candidate], tasks: Sequence[TaskNeed], total_days: int) -> dict[Id, Criteria]:
    """Critères de chaque candidat capable de faire au moins une tâche (les autres sont écartés)."""
    return {
        c.id: compute_criteria(c, tasks, total_days)
        for c in candidates
        if any(c.can_do(t) for t in tasks)
    }


# =========================================================================== n°22 — agrégation pondérée


def normalize(criteria: Mapping[Id, Criteria]) -> dict[Id, dict[str, float]]:
    """Normalisation min-max sur [0, 1], où 1 = le meilleur candidat sur ce critère.

        à maximiser : n = (x − min) / (max − min)
        à minimiser : n = (max − x) / (max − min)      (inversion)

    Si tous les candidats sont égaux sur un critère, il ne départage personne : n = 1 pour tous.
    Une valeur infinie (rapidité d'un freelance sans aucun jour disponible) reçoit 0.
    """
    result: dict[Id, dict[str, float]] = {i: {} for i in criteria}
    for key in CRITERIA:
        finite = [c.get(key) for c in criteria.values() if math.isfinite(c.get(key))]
        lo, hi = (min(finite), max(finite)) if finite else (0.0, 0.0)
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
            result[i][key] = n
    return result


def normalize_weights(weights: Mapping[str, float]) -> dict[str, float]:
    """Ramène les poids des curseurs à une somme de 1 (tous nuls → poids égaux)."""
    raw = {k: max(0.0, float(weights.get(k, 0.0))) for k in CRITERIA}
    total = sum(raw.values())
    if total == 0:
        return {k: 1 / len(CRITERIA) for k in CRITERIA}
    return {k: v / total for k, v in raw.items()}


def weighted_ranking(criteria: Mapping[Id, Criteria], weights: Mapping[str, float]) -> list[Ranked]:
    """Classement par score = Σ w_k × n_k, du meilleur au moins bon.

    COMPLEXITÉ : O(N × K) pour les scores (N candidats, K = 5 critères) + O(N log N) pour le tri.
    """
    w = normalize_weights(weights)
    norm = normalize(criteria)
    ranking = []
    for i, n in norm.items():
        contributions = {k: w[k] * n[k] for k in CRITERIA}
        ranking.append(Ranked(id=i, score=sum(contributions.values()), contributions=contributions, normalized=n))
    ranking.sort(key=lambda r: (-r.score, str(r.id)))
    return ranking


# =========================================================================== n°21 — Pareto


def dominates(a: Criteria, b: Criteria, keys: Sequence[str]) -> bool:
    """A domine B : au moins aussi bon sur TOUS les critères, et strictement meilleur sur AU MOINS UN."""
    at_least_as_good = all(DIRECTION[k] * a.get(k) >= DIRECTION[k] * b.get(k) for k in keys)
    strictly_better = any(DIRECTION[k] * a.get(k) > DIRECTION[k] * b.get(k) for k in keys)
    return at_least_as_good and strictly_better


def non_dominated_sort(criteria: Mapping[Id, Criteria], keys: Sequence[str]) -> list[list[Id]]:
    """Tri non dominé (« fast non-dominated sort » de NSGA-II).

    IDÉE
        Pour chaque point p : S_p = les points que p domine, n_p = combien de points dominent p.
        Front 1 = les points avec n_p = 0 (personne ne les domine).
        On « retire » le front 1 : chaque point qu'il dominait perd 1 à son compteur ;
        ceux qui tombent à 0 forment le front 2, et ainsi de suite.

    COMPLEXITÉ : O(K × N²) — chaque paire de points est comparée une fois sur K critères.
    """
    ids = list(criteria)
    dominated_by_me: dict[Id, list[Id]] = {i: [] for i in ids}
    domination_count: dict[Id, int] = {i: 0 for i in ids}
    for idx, p in enumerate(ids):
        for q in ids[idx + 1 :]:
            if dominates(criteria[p], criteria[q], keys):
                dominated_by_me[p].append(q)
                domination_count[q] += 1
            elif dominates(criteria[q], criteria[p], keys):
                dominated_by_me[q].append(p)
                domination_count[p] += 1

    fronts: list[list[Id]] = []
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
    return fronts


def best_compromise(criteria: Mapping[Id, Criteria], front: Sequence[Id], keys: Sequence[str]) -> Id:
    """Point du front le plus proche du POINT IDÉAL (1, 1, …, 1) dans l'espace normalisé.

    Le point idéal serait un freelance à la fois le moins cher, le plus rapide et le meilleur :
    il n'existe généralement pas, mais le candidat qui s'en approche le plus (distance euclidienne)
    est un compromis équilibré entre les critères choisis.
    """
    norm = normalize(criteria)

    def distance(i: Id) -> float:
        return math.sqrt(sum((1.0 - norm[i][k]) ** 2 for k in keys))

    return min(front, key=lambda i: (distance(i), str(i)))


# =========================================================================== équipe suggérée


def suggest_team(
    candidates: Sequence[Candidate], tasks: Sequence[TaskNeed], ranking: Sequence[Ranked]
) -> TeamSuggestion:
    """Équipe suggérée, construite de façon gloutonne.

    1. COUVERTURE : tant qu'il reste des tâches que personne dans l'équipe ne sait faire, on prend
       la compétence qui a le plus d'heures non couvertes et on ajoute le candidat au MEILLEUR SCORE
       capable de faire au moins une de ces tâches.
    2. CHARGE : on vérifie que les heures sont absorbables avant la date limite, en répartissant
       les tâches (la plus longue d'abord) sur le membre capable le moins chargé.
       Si une tâche ne rentre chez personne, on ajoute en renfort le meilleur candidat suivant
       qui sait la faire, puis on recommence.

    COMPLEXITÉ : O(T × N) par membre ajouté (T tâches, N candidats).
    """
    by_id = {c.id: c for c in candidates}
    order = [r.id for r in ranking if r.id in by_id]  # du meilleur score au moins bon
    members: list[Id] = []
    warnings: list[str] = []

    # --- 1. couverture des compétences
    impossible = [t for t in tasks if not any(by_id[i].can_do(t) for i in order)]
    for t in impossible:
        warnings.append(f"Aucun freelance n'a la compétence {t.skill} au niveau {t.min_level} (tâche {t.id}).")
    to_cover = [t for t in tasks if t not in impossible]
    while True:
        uncovered = [t for t in to_cover if not any(by_id[m].can_do(t) for m in members)]
        if not uncovered:
            break
        hours_by_skill: dict[str, int] = {}
        for t in uncovered:
            hours_by_skill[t.skill] = hours_by_skill.get(t.skill, 0) + t.hours
        skill = max(sorted(hours_by_skill), key=lambda s: hours_by_skill[s])
        needed = [t for t in uncovered if t.skill == skill]
        pick = next(i for i in order if i not in members and any(by_id[i].can_do(t) for t in needed))
        members.append(pick)

    # --- 2. vérification de la charge, avec renforts si nécessaire
    while True:
        assignment, load, overflow = _assign_load(by_id, members, to_cover)
        if overflow is None:
            break
        reinforcement = next((i for i in order if i not in members and by_id[i].can_do(overflow)), None)
        if reinforcement is None:
            warnings.append(
                f"Charge trop forte : la tâche {overflow.id} ({overflow.skill}, {overflow.hours} h) "
                "ne tient dans la disponibilité d'aucun freelance d'ici la date limite."
            )
            return TeamSuggestion(members, assignment, load, [t.id for t in impossible], False, warnings)
        members.append(reinforcement)

    return TeamSuggestion(members, assignment, load, [t.id for t in impossible], not impossible, warnings)


def _assign_load(
    by_id: Mapping[Id, Candidate], members: Sequence[Id], tasks: Sequence[TaskNeed]
) -> tuple[dict[Id, Id], dict[Id, int], TaskNeed | None]:
    """Répartition gloutonne : plus longue tâche d'abord, vers le membre capable le moins chargé
    (en proportion de sa capacité). Renvoie la première tâche qui ne rentre nulle part, ou None."""
    load = {m: 0 for m in members}
    assignment: dict[Id, Id] = {}
    for t in sorted(tasks, key=lambda t: (-t.hours, str(t.id))):
        able = [m for m in members if by_id[m].can_do(t) and load[m] + t.hours <= by_id[m].capacity_hours]
        if not able:
            return assignment, load, t
        m = min(able, key=lambda m: (load[m] / max(by_id[m].capacity_hours, 1), members.index(m)))
        assignment[t.id] = m
        load[m] += t.hours
    return assignment, load, None
