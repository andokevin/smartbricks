"""Module D — Planification par satisfaction de contraintes, CSP (algorithme n°3 de la liste du cours).

BUT
    Décider QUI fait chaque tâche et QUAND, en respectant toutes les contraintes, puis chercher
    le planning le plus court possible.

MODÈLE CSP
    Variables  : pour chaque tâche t, le couple (freelance_t, début_t).
    Domaines   : freelances de l'équipe ayant la compétence au niveau requis
                 × jours ouvrés entre le début du projet et la date limite.
    Durée      : ceil(heures_t / heures_par_jour du freelance) jours où il est DISPONIBLE.
    Contraintes dures :
        1. Dépendances      : début_B > fin_A si B dépend de A (fin = dernier jour de travail)
        2. Compétences      : le freelance a la compétence au niveau minimal
        3. Disponibilité    : aucun jour de travail ne tombe sur une indisponibilité
        4. Non-chevauchement: un freelance fait une seule tâche à la fois
        5. Date limite      : fin_t ≤ date limite

RÉSOLUTION : retour arrière (backtracking) avec propagation
    a) Propagation de bornes AVANT la recherche (méthode du chemin critique, CPM) : avec la durée
       la plus courte possible de chaque tâche, on calcule les dates au plus tôt (ES) et au plus tard
       (LF). Si le chemin critique dépasse la date limite, l'impossibilité est prouvée tout de suite.
       On vérifie aussi les charges (heures à faire ≤ heures disponibles).
    b) Choix de la variable : parmi les tâches dont tous les prédécesseurs sont placés,
       celle qui a le PLUS PETIT DOMAINE (heuristique MRV), puis la plus faible marge (LS − ES).
    c) Choix de la valeur : couples (freelance, début) triés par fin la plus tôt,
       puis par meilleur score de matching.
    d) Vérification anticipée (forward checking) : après chaque affectation, on recalcule les dates
       au plus tôt des tâches restantes ; si l'une ne peut plus finir avant sa date au plus tard,
       on revient en arrière tout de suite.
    e) Optimisation (séparation et évaluation sur la durée totale) : après une solution de fin F,
       on impose « tout finir avant F » et on continue, jusqu'à prouver l'optimum (borne du chemin
       critique atteinte ou arbre épuisé) ou jusqu'à la limite de temps (3 s par défaut).

COMPLEXITÉ
    Pire cas exponentiel (le problème d'ordonnancement avec ressources est NP-difficile) ;
    la propagation et MRV rendent la première solution quasi immédiate sur des projets réels.
    Chaque nœud coûte O(T × F × D) (tâches prêtes × freelances × jours).

Les jours sont représentés par leur INDEX dans la liste des jours ouvrés du projet
(0 = premier jour ouvré), ce qui simplifie les calculs ; on reconvertit en dates à la fin.
"""

from __future__ import annotations

import math
import time
from collections.abc import Hashable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import date
from typing import Any

from app.algorithms.calendar import working_days

Id = Hashable


@dataclass(frozen=True)
class SchedTask:
    id: Id
    title: str
    skill: str
    min_level: int
    hours: int
    depends_on: tuple[Id, ...] = ()


@dataclass(frozen=True)
class SchedFreelancer:
    id: Id
    name: str
    skills: Mapping[str, int]
    hours_per_day: int
    unavailable: frozenset[date] = frozenset()
    score: float = 0.0  # score de matching, pour départager les valeurs

    def can_do(self, t: SchedTask) -> bool:
        return self.skills.get(t.skill, 0) >= t.min_level

    def duration(self, t: SchedTask) -> int:
        return max(1, math.ceil(t.hours / self.hours_per_day))


@dataclass(frozen=True)
class Assignment:
    task_id: Id
    freelancer_id: Id
    start: date
    end: date  # dernier jour de travail (inclus)
    days: int  # nombre de jours de travail


@dataclass
class ScheduleResult:
    status: str  # "OK", "INFEASIBLE" (impossibilité prouvée) ou "UNKNOWN" (rien trouvé à temps)
    assignments: dict[Id, Assignment] = field(default_factory=dict)
    makespan_days: int | None = None  # jours ouvrés entre le début du projet et la dernière fin
    end_date: date | None = None
    lower_bound_days: int = 0  # durée du chemin critique : aucun planning ne peut faire moins
    nodes: int = 0
    elapsed_ms: float = 0.0
    optimal: bool = False
    method: str = "Retour arrière + propagation (CSP)"
    diagnostics: list[str] = field(default_factory=list)
    critical_path: list[Id] = field(default_factory=list)


def _jours(n: int) -> str:
    return f"{n} jour ouvré" if n == 1 else f"{n} jours ouvrés"


class _Timeout(Exception):
    pass


# =========================================================================== solveur


def solve_schedule(
    tasks: Sequence[SchedTask],
    team: Sequence[SchedFreelancer],
    start: date,
    deadline: date,
    time_limit: float = 3.0,
    optimize: bool = True,
) -> ScheduleResult:
    t0 = time.perf_counter()
    result = ScheduleResult(status="UNKNOWN")

    def done(status: str) -> ScheduleResult:
        result.status = status
        result.elapsed_ms = (time.perf_counter() - t0) * 1000
        return result

    by_id = {t.id: t for t in tasks}
    for t in tasks:
        for d in t.depends_on:
            if d not in by_id:
                raise ValueError(f"La tâche {t.id} dépend d'une tâche inconnue : {d}")
    if not tasks:
        result.makespan_days = 0
        result.optimal = True
        return done("OK")

    days = working_days(start, deadline)
    D = len(days)  # nombre de jours ouvrés disponibles dans le projet
    succ: dict[Id, list[Id]] = {t.id: [] for t in tasks}
    for t in tasks:
        for d in t.depends_on:
            succ[d].append(t.id)

    # ---------------------------------------------------------------- ordre topologique (Kahn)
    indeg = {t.id: len(t.depends_on) for t in tasks}
    topo: list[Id] = []
    queue = [t.id for t in tasks if indeg[t.id] == 0]
    while queue:
        u = queue.pop(0)
        topo.append(u)
        for v in succ[u]:
            indeg[v] -= 1
            if indeg[v] == 0:
                queue.append(v)
    if len(topo) != len(tasks):
        cyc = [by_id[i].title for i in by_id if indeg[i] > 0]
        result.diagnostics.append(f"Les dépendances forment un cycle entre : {', '.join(cyc)}.")
        return done("INFEASIBLE")

    # ---------------------------------------------------------------- domaines : compétences
    eligible: dict[Id, list[SchedFreelancer]] = {}
    for t in tasks:
        eligible[t.id] = sorted((f for f in team if f.can_do(t)), key=lambda f: (-f.score, str(f.id)))
        if not eligible[t.id]:
            result.diagnostics.append(
                f"Aucun freelance de l'équipe n'a la compétence {t.skill} au niveau {t.min_level} "
                f"(tâche « {t.title} ») : ajoutez un freelance qui l'a, ou baissez le niveau demandé."
            )
    if result.diagnostics:
        return done("INFEASIBLE")

    # Jours disponibles de chaque freelance, en index.
    avail: dict[Id, list[int]] = {
        f.id: [k for k, d in enumerate(days) if d not in f.unavailable] for f in team
    }
    pos: dict[Id, dict[int, int]] = {fid: {k: p for p, k in enumerate(ks)} for fid, ks in avail.items()}

    # ---------------------------------------------------------------- a) chemin critique (CPM)
    dmin = {t.id: min(f.duration(t) for f in eligible[t.id]) for t in tasks}
    ES: dict[Id, int] = {}
    for u in topo:
        ES[u] = max((ES[p] + dmin[p] for p in by_id[u].depends_on), default=0)
    EF = {u: ES[u] + dmin[u] - 1 for u in topo}
    cp_len = max(EF.values()) + 1
    result.lower_bound_days = cp_len
    last = max(topo, key=lambda u: (EF[u], str(u)))
    path = [last]
    while by_id[path[-1]].depends_on:
        cur = path[-1]
        path.append(max(by_id[cur].depends_on, key=lambda p: (ES[p] + dmin[p], str(p))))
    result.critical_path = list(reversed(path))

    LF: dict[Id, int] = {}
    for u in reversed(topo):
        LF[u] = min((LF[s] - dmin[s] for s in succ[u]), default=D - 1)
    if cp_len > D:
        names = " → ".join(by_id[i].title for i in result.critical_path)
        result.diagnostics.append(
            f"Le chemin critique ({names}) demande {_jours(cp_len)}, la date limite en laisse {D} : "
            f"repoussez la date de {_jours(cp_len - D)} ou réduisez le périmètre."
        )
        return done("INFEASIBLE")

    # ---------------------------------------------------------------- charges (conditions nécessaires)
    # Deux conditions nécessaires sur les tâches qu'une SEULE personne de l'équipe sait faire :
    #   - en heures : leurs heures ≤ ses heures disponibles ;
    #   - en jours  : Σ ceil(heures / heures par jour) ≤ ses jours disponibles, car elle les fait
    #     l'une après l'autre et chaque tâche occupe des jours entiers (plus fin que le test en heures).
    capacity = {f.id: f.hours_per_day * len(avail[f.id]) for f in team}
    reported: set[Id] = set()
    for f in team:
        mine = [t for t in tasks if [e.id for e in eligible[t.id]] == [f.id]]
        forced = sum(t.hours for t in mine)
        forced_days = sum(f.duration(t) for t in mine)
        free_days = len(avail[f.id])
        if forced > capacity[f.id]:
            reported.add(f.id)
            result.diagnostics.append(
                f"Charge de {f.name} : {forced} h pour {capacity[f.id]} h disponibles d'ici la date limite "
                "(seule personne de l'équipe à pouvoir faire ces tâches) : ajoutez un renfort ou repoussez la date."
            )
        elif forced_days > free_days:
            reported.add(f.id)
            result.diagnostics.append(
                f"Charge de {f.name} : les {len(mine)} tâches que cette personne est seule à pouvoir faire "
                f"({forced} h à {f.hours_per_day} h par jour) demandent {_jours(forced_days)}, pour "
                f"{_jours(free_days)} disponibles d'ici la date limite : repoussez la date de "
                f"{_jours(forced_days - free_days)} ou ajoutez un renfort."
            )
    for skill in sorted({t.skill for t in tasks}):
        group = [t for t in tasks if t.skill == skill]
        people = {f.id for t in group for f in eligible[t.id]}
        need = sum(t.hours for t in group)
        cap = sum(capacity[i] for i in people)
        if need > cap and not (len(people) == 1 and people <= reported):
            result.diagnostics.append(
                f"Compétence {skill} : {need} h à faire pour {cap} h disponibles dans l'équipe "
                "d'ici la date limite."
            )
    if result.diagnostics:
        return done("INFEASIBLE")

    # ---------------------------------------------------------------- recherche
    team_index = {f.id: k for k, f in enumerate(team)}
    busy = {f.id: bytearray(D) for f in team}  # 1 = jour occupé par une tâche
    assigned: dict[Id, tuple[SchedFreelancer, int, int]] = {}  # tâche → (freelance, début, fin)
    best: dict[Id, tuple[SchedFreelancer, int, int]] = {}
    best_end = D  # fin (index) de la meilleure solution ; D = aucune encore
    limit = D - 1  # toute tâche doit finir au plus tard à cet index
    exhausted = True

    def lf(u: Id) -> int:
        """Date au plus tard, décalée quand on cherche plus court que la meilleure solution."""
        return LF[u] - (D - 1 - limit)

    def earliest_start(u: Id) -> int:
        return max((assigned[p][2] + 1 for p in by_id[u].depends_on), default=0)

    def values(u: Id) -> list[tuple[int, float, int, int, SchedFreelancer]]:
        """Domaine courant de u : couples (freelance, début) possibles, triés (fin, −score)."""
        t = by_id[u]
        est = earliest_start(u)
        out = []
        for f in eligible[u]:
            dur = f.duration(t)
            ks = avail[f.id]
            # premier jour disponible ≥ est
            p = next((pos[f.id][k] for k in ks if k >= est), None) if ks else None
            if p is None:
                continue
            row = busy[f.id]
            while p + dur - 1 < len(ks):
                s, e = ks[p], ks[p + dur - 1]
                if e > lf(u):
                    break  # les fins ne font qu'augmenter
                if not any(row[s : e + 1]):
                    out.append((e, -f.score, team_index[f.id], s, f))
                p += 1
        out.sort(key=lambda v: (v[0], v[1], v[2], v[3]))
        return out

    def forward_check() -> bool:
        """Dates au plus tôt des tâches non placées ; échec si l'une ne peut plus finir à temps."""
        es: dict[Id, int] = {}
        for u in topo:
            if u in assigned:
                es[u] = assigned[u][1]
                continue
            e = ES[u]
            for p in by_id[u].depends_on:
                e = max(e, assigned[p][2] + 1 if p in assigned else es[p] + dmin[p])
            es[u] = e
            if e + dmin[u] - 1 > lf(u):
                return False
        return True

    def search() -> bool:
        """Renvoie True s'il faut tout arrêter (optimum prouvé ou mode « première solution »)."""
        nonlocal best, best_end, limit, exhausted
        result.nodes += 1
        if result.nodes % 64 == 0 and time.perf_counter() - t0 > time_limit:
            raise _Timeout

        if len(assigned) == len(tasks):
            end = max(e for _, _, e in assigned.values())
            if end < best_end:
                best, best_end = dict(assigned), end
                limit = end - 1  # désormais on ne cherche que strictement mieux
            return (not optimize) or best_end + 1 <= cp_len

        ready = [u for u in topo if u not in assigned and all(p in assigned for p in by_id[u].depends_on)]
        # b) MRV : plus petit domaine, puis plus faible marge.
        candidates = []
        for u in ready:
            vals = values(u)
            if not vals:
                return False  # domaine vide : retour arrière
            candidates.append((len(vals), LF[u] - dmin[u] + 1 - ES[u], str(u), u, vals))
        _, _, _, u, vals = min(candidates, key=lambda c: c[:3])

        # c) valeurs : fin la plus tôt, puis meilleur score.
        for e, _, _, s, f in vals:
            if e > limit:
                break  # la limite a pu se resserrer entre-temps
            if any(busy[f.id][s : e + 1]):
                continue
            assigned[u] = (f, s, e)
            busy[f.id][s : e + 1] = b"\x01" * (e - s + 1)
            stop = forward_check() and search()  # d) vérification anticipée
            busy[f.id][s : e + 1] = bytes(e - s + 1)
            del assigned[u]
            if stop:
                return True
        return False

    try:
        search()
    except _Timeout:
        exhausted = False

    if best:
        result.assignments = {
            u: Assignment(u, f.id, days[s], days[e], len(range(pos[f.id][s], pos[f.id][e] + 1)))
            for u, (f, s, e) in best.items()
        }
        result.makespan_days = best_end + 1
        result.end_date = days[best_end]
        # Optimal si la borne du chemin critique est atteinte ou si l'arbre a été entièrement exploré.
        result.optimal = best_end + 1 <= cp_len or (exhausted and optimize)
        return done("OK")

    if exhausted:
        loads = ", ".join(
            f"{f.name} {capacity[f.id]} h" for f in team if any(f.can_do(t) for t in tasks)
        )
        result.diagnostics.append(
            "Aucun planning ne respecte toutes les contraintes : les indisponibilités et le "
            "non-chevauchement ne laissent pas assez de place avant la date limite "
            f"(capacités : {loads}). Repoussez la date ou ajoutez un freelance."
        )
        return done("INFEASIBLE")
    result.diagnostics.append(
        f"Aucun planning trouvé en {time_limit:g} s. Le problème est peut-être réalisable mais trop "
        "serré : repoussez la date ou ajoutez un freelance."
    )
    return done("UNKNOWN")


# =========================================================================== vérification indépendante


def verify_schedule(
    tasks: Sequence[SchedTask],
    team: Sequence[SchedFreelancer],
    start: date,
    deadline: date,
    assignments: Mapping[Id, Assignment],
) -> dict[str, Any]:
    """Revérifie un planning SANS réutiliser le solveur, et produit un rapport contrainte par contrainte.

    Format : {"constraints_passed": bool, "checks": [{"name", "passed", "details": [...]}, ...]}
    """
    people = {f.id: f for f in team}
    by_id = {t.id: t for t in tasks}
    issues: dict[str, list[str]] = {
        name: []
        for name in (
            "Toutes les tâches planifiées",
            "Dépendances",
            "Compétences",
            "Disponibilité",
            "Durées",
            "Pas de chevauchement",
            "Date limite",
        )
    }

    def free_day(f: SchedFreelancer, d: date) -> bool:
        return d.weekday() < 5 and d not in f.unavailable

    valid: dict[Id, Assignment] = {}
    for t in tasks:
        a = assignments.get(t.id)
        if a is None:
            issues["Toutes les tâches planifiées"].append(f"« {t.title} » n'est pas planifiée.")
        elif a.freelancer_id not in people:
            issues["Toutes les tâches planifiées"].append(f"« {t.title} » est confiée à un inconnu.")
        else:
            valid[t.id] = a

    for tid, a in valid.items():
        t, f = by_id[tid], people[a.freelancer_id]
        # 1. Dépendances
        for dep in t.depends_on:
            b = valid.get(dep)
            if b is not None and not a.start > b.end:
                issues["Dépendances"].append(
                    f"« {t.title} » commence le {a.start} alors que « {by_id[dep].title} » finit le {b.end}."
                )
        # 2. Compétences
        if f.skills.get(t.skill, 0) < t.min_level:
            issues["Compétences"].append(
                f"{f.name} n'a pas {t.skill} au niveau {t.min_level} pour « {t.title} »."
            )
        # 3. Disponibilité : début et fin sont des jours travaillés, et le nombre de jours
        #    disponibles entre les deux est exactement la durée annoncée.
        worked = 0
        d = a.start
        while d <= a.end:
            worked += free_day(f, d)
            d = date.fromordinal(d.toordinal() + 1)
        if a.start < start or not free_day(f, a.start) or not free_day(f, a.end) or worked != a.days:
            issues["Disponibilité"].append(
                f"« {t.title} » ({a.start} → {a.end}) tombe sur un jour non travaillé ou indisponible de {f.name}."
            )
        # Durée cohérente avec les heures et le rythme du freelance.
        if a.days != max(1, math.ceil(t.hours / f.hours_per_day)):
            issues["Durées"].append(f"« {t.title} » devrait durer {math.ceil(t.hours / f.hours_per_day)} jour(s).")
        # 5. Date limite
        if a.end > deadline:
            issues["Date limite"].append(f"« {t.title} » finit le {a.end}, après la date limite du {deadline}.")

    # 4. Pas de chevauchement
    per_person: dict[Id, list[Assignment]] = {}
    for a in valid.values():
        per_person.setdefault(a.freelancer_id, []).append(a)
    for fid, items in per_person.items():
        items.sort(key=lambda a: a.start)
        for x, y in zip(items, items[1:]):
            if y.start <= x.end:
                issues["Pas de chevauchement"].append(
                    f"{people[fid].name} a deux tâches en même temps : {x.task_id} et {y.task_id}."
                )

    checks = [{"name": n, "passed": not det, "details": det} for n, det in issues.items()]
    return {"constraints_passed": all(c["passed"] for c in checks), "checks": checks}
