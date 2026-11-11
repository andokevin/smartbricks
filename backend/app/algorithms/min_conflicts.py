"""Module D, niveau B — Réparation du planning par Min-Conflict (algorithme n°11 de la liste du cours).

BUT
    Une tâche prend du retard (« l'API demande 8 h de plus »). Plutôt que de tout replanifier
    (le CSP pourrait tout bouleverser et réaffecter des freelances déjà prévenus), on RÉPARE le planning
    existant en changeant le moins de choses possible.

IDÉE (recherche locale de Minton et al., 1992)
    1. On part de l'affectation actuelle, complète mais devenue incohérente : la tâche retardée finit
       plus tard, ce qui crée des CONFLITS.
    2. Tant qu'il reste des conflits : on choisit au hasard une tâche en conflit, et on lui donne la
       valeur (freelance, début) qui crée le MOINS de conflits avec les autres tâches.
    3. On s'arrête quand il n'y a plus de conflit (succès) ou après un nombre maximal d'étapes (échec).
    4. Resserrement : Min-Conflict étant glouton, une tâche peut avoir été poussée trop loin ; on la
       ramène, dans l'ordre des dépendances, au plus près de sa valeur d'origine sans créer de conflit.

    Un CONFLIT est une contrainte dure violée entre la tâche et le reste du planning :
        - dépendance : la tâche commence avant la fin d'une tâche dont elle dépend (le conflit est
          compté pour la tâche qui attend : le retard se propage vers l'aval) ;
        - chevauchement : le même freelance a une autre tâche sur un de ces jours ;
        - date limite : la tâche finit après la date limite.
    Compétences et disponibilités ne peuvent pas être violées : on ne propose que des freelances
    compétents, et la fin est calculée sur les jours où le freelance est disponible.

« CHANGER LE MOINS DE CHOSES POSSIBLE »
    - seules les tâches EN CONFLIT sont déplacées ; les autres gardent leur valeur ;
    - à nombre de conflits égal, on préfère : garder le même freelance, puis le début le plus proche
      du début actuel, puis la fin la plus tôt ;
    - la tâche retardée garde son freelance et son début (elle est en cours) : seule sa fin change.

COMPLEXITÉ
    Une étape coûte O(F × D × T) : F freelances compétents × D jours de début possibles × T tâches pour
    compter les conflits. Le nombre d'étapes est borné (max_steps). Min-Conflict n'est pas complet :
    un échec ne PROUVE pas l'impossibilité (le CSP complet, lui, le pourrait), il signale un retard
    trop gros pour être absorbé localement.

Le tirage au hasard utilise une graine fixe : les résultats sont reproductibles.
"""

from __future__ import annotations

import dataclasses
import math
import random
import time
from collections.abc import Hashable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import date, timedelta

from app.algorithms.calendar import working_days
from app.algorithms.csp_scheduler import Assignment, SchedFreelancer, SchedTask

Id = Hashable
HORIZON_DAYS = 365  # jours calendaires au-delà de la date limite où l'on sait encore calculer une fin


@dataclass
class RepairResult:
    status: str  # "OK" (plus aucun conflit) ou "FAILED"
    assignments: dict[Id, Assignment]
    changed: list[Id] = field(default_factory=list)  # tâches déplacées (hors tâche retardée)
    reassigned: list[Id] = field(default_factory=list)  # parmi elles, celles qui changent de freelance
    steps: int = 0
    elapsed_ms: float = 0.0
    remaining_conflicts: int = 0
    makespan_days: int | None = None
    end_date: date | None = None
    delayed_end: date | None = None
    diagnostics: list[str] = field(default_factory=list)
    method: str = "Min-Conflict (réparation locale)"


def lengthen(tasks: Sequence[SchedTask], task_id: Id, extra_hours: int) -> list[SchedTask]:
    """Copie des tâches où `task_id` dure `extra_hours` heures de plus."""
    return [dataclasses.replace(t, hours=t.hours + extra_hours) if t.id == task_id else t for t in tasks]


def _topological(tasks: Sequence[SchedTask]) -> list[Id]:
    """Ordre de Kahn : chaque tâche après celles dont elle dépend (graphe supposé sans cycle)."""
    indeg = {t.id: len(t.depends_on) for t in tasks}
    succ: dict[Id, list[Id]] = {t.id: [] for t in tasks}
    for t in tasks:
        for d in t.depends_on:
            succ[d].append(t.id)
    queue = [t.id for t in tasks if indeg[t.id] == 0]
    order: list[Id] = []
    while queue:
        u = queue.pop(0)
        order.append(u)
        for v in succ[u]:
            indeg[v] -= 1
            if indeg[v] == 0:
                queue.append(v)
    return order


def _jours(n: int) -> str:
    return f"{n} jour ouvré" if n == 1 else f"{n} jours ouvrés"


def repair_schedule(
    tasks: Sequence[SchedTask],
    team: Sequence[SchedFreelancer],
    start: date,
    deadline: date,
    current: Mapping[Id, Assignment],
    delayed_id: Id,
    extra_hours: int,
    max_steps: int = 5_000,
    seed: int = 0,
) -> RepairResult:
    t0 = time.perf_counter()
    if extra_hours <= 0:
        raise ValueError("Le retard doit être un nombre d'heures strictement positif.")
    tasks = lengthen(tasks, delayed_id, extra_hours)
    by_id = {t.id: t for t in tasks}
    if delayed_id not in by_id:
        raise ValueError(f"Tâche inconnue : {delayed_id}")
    missing = [t.id for t in tasks if t.id not in current]
    if missing:
        raise ValueError(f"Planning actuel incomplet : {missing}")
    people = {f.id: f for f in team}
    team_index = {f.id: k for k, f in enumerate(team)}

    # ---------------------------------------------------------------- calendrier en index
    # Jours ouvrés du début du projet jusqu'à bien après la date limite : on doit pouvoir représenter
    # une fin trop tardive (c'est justement un conflit à réparer).
    horizon = working_days(start, deadline + timedelta(days=HORIZON_DAYS))
    index = {d: k for k, d in enumerate(horizon)}
    last = len(working_days(start, deadline)) - 1  # index du dernier jour ouvré avant la date limite
    avail = {f.id: [k for k, d in enumerate(horizon) if d not in f.unavailable] for f in team}
    pos = {fid: {k: p for p, k in enumerate(ks)} for fid, ks in avail.items()}

    def end_of(fid: Id, s: int, t: SchedTask) -> int | None:
        """Index du dernier jour de travail si t commence au jour s chez fid (None si hors horizon)."""
        p = pos[fid].get(s)
        if p is None:
            return None  # s n'est pas un jour où fid travaille
        dur = people[fid].duration(t)
        return avail[fid][p + dur - 1] if p + dur - 1 < len(avail[fid]) else None

    preds = {t.id: list(t.depends_on) for t in tasks}
    succs: dict[Id, list[Id]] = {t.id: [] for t in tasks}
    for t in tasks:
        for d in t.depends_on:
            succs[d].append(t.id)
    eligible = {t.id: [f.id for f in team if f.can_do(t)] for t in tasks}

    # ---------------------------------------------------------------- état initial
    val: dict[Id, tuple[Id, int, int]] = {}
    for t in tasks:
        a = current[t.id]
        s = index[a.start]
        val[t.id] = (a.freelancer_id, s, index[a.end])
    original = dict(val)
    fid0, s0, _ = val[delayed_id]
    e0 = end_of(fid0, s0, by_id[delayed_id])
    if e0 is None:
        raise ValueError("Retard trop long pour être représenté.")
    val[delayed_id] = (fid0, s0, e0)

    result = RepairResult(status="FAILED", assignments={}, delayed_end=horizon[e0])
    if e0 > last:  # la tâche retardée elle-même dépasse : aucune réparation ne peut l'éviter
        result.diagnostics.append(
            f"« {by_id[delayed_id].title} » finit désormais le {horizon[e0]}, après la date limite du "
            f"{deadline} : il faudrait repousser la date limite de {_jours(e0 - last)}."
        )
        result.elapsed_ms = (time.perf_counter() - t0) * 1000
        return result

    def conflicts(tid: Id, v: tuple[Id, int, int], with_successors: bool = False) -> int:
        """Nombre de contraintes violées par la tâche tid si elle prend la valeur v (les autres inchangées).

        Une dépendance « B après A » est attribuée à B, la tâche qui attend : un retard se propage vers
        l'aval, et c'est au successeur de se décaler. Sans cette convention, une tâche coincée entre
        un prédécesseur retardé et ses successeurs n'a que des valeurs à 1 conflit, et la recherche
        tourne en rond sur ce plateau. Le resserrement final, lui, compte aussi les successeurs.
        """
        fid, s, e = v
        n = 0
        for p in preds[tid]:
            if s <= val[p][2]:  # commence avant (ou le jour de) la fin d'un prédécesseur
                n += 1
        if with_successors:
            for q in succs[tid]:
                if val[q][1] <= e:  # un successeur commence avant notre fin
                    n += 1
        for u, (fu, su, eu) in val.items():
            if u != tid and fu == fid and not (eu < s or su > e):  # même freelance, jours communs
                n += 1
        if e > last:
            n += 1
        return n

    def conflicted() -> list[Id]:
        return [t.id for t in tasks if conflicts(t.id, val[t.id]) > 0]

    # ---------------------------------------------------------------- boucle Min-Conflict
    rng = random.Random(seed)
    steps = 0
    while steps < max_steps:
        movable = [t for t in conflicted() if t != delayed_id]
        if not movable:
            break
        steps += 1
        tid = rng.choice(movable)  # variable en conflit tirée au hasard
        t = by_id[tid]
        f_orig, s_orig, _ = original[tid]
        best: tuple[tuple[int, bool, int, int, int], tuple[Id, int, int]] | None = None
        for fid in eligible[tid]:
            for s in avail[fid]:
                if s > last:
                    break  # on ne commence jamais après la date limite
                e = end_of(fid, s, t)
                if e is None:
                    continue
                v = (fid, s, e)
                # min des conflits, puis même freelance, puis début proche de l'actuel, puis fin tôt
                key = (conflicts(tid, v), fid != f_orig, abs(s - s_orig), e, team_index[fid])
                if best is None or key < best[0]:
                    best = (key, v)
        if best is not None:
            val[tid] = best[1]

    # ---------------------------------------------------------------- phase 2 : resserrement
    # Min-Conflict est glouton : une tâche peut avoir été poussée plus loin que nécessaire (elle évitait
    # un conflit avec un successeur qui a bougé ensuite). Si le planning est réparé, on ramène chaque tâche
    # déplacée, dans l'ordre des dépendances, vers sa valeur d'origine, sans jamais recréer de conflit.
    # Libérer une place peut en libérer une autre : on recommence jusqu'à ce que plus rien ne bouge
    # (chaque mouvement rapproche strictement une tâche de son origine, donc la boucle s'arrête).
    moved = not [t for t in conflicted() if t != delayed_id]
    while moved:
        moved = False
        for tid in _topological(tasks):
            if tid == delayed_id or val[tid] == original[tid]:
                continue
            t = by_id[tid]
            f_orig, s_orig, _ = original[tid]
            current_key = (val[tid][0] != f_orig, abs(val[tid][1] - s_orig), val[tid][2])
            for key, v in sorted(
                ((fid != f_orig, abs(s - s_orig), e), (fid, s, e))
                for fid in eligible[tid]
                for s in avail[fid]
                if s <= last and (e := end_of(fid, s, t)) is not None
            ):
                if key >= current_key:
                    break  # rien de plus proche de l'origine
                if conflicts(tid, v, with_successors=True) == 0:
                    val[tid] = v
                    moved = True
                    break

    remaining = conflicted()
    result.steps = steps
    result.remaining_conflicts = sum(conflicts(t, val[t]) for t in remaining)
    result.assignments = {
        tid: Assignment(tid, fid, horizon[s], horizon[e], people[fid].duration(by_id[tid]))
        for tid, (fid, s, e) in val.items()
    }
    result.changed = [t.id for t in tasks if t.id != delayed_id and val[t.id][:2] != original[t.id][:2]]
    result.reassigned = [t for t in result.changed if val[t][0] != original[t][0]]
    max_e = max(e for _, _, e in val.values())
    result.makespan_days = max_e + 1
    result.end_date = horizon[max_e]
    if not remaining:
        result.status = "OK"
    else:
        late = [by_id[t].title for t in remaining if val[t][2] > last]
        if late and max_e > last:
            result.diagnostics.append(
                f"Le retard ne peut pas être absorbé avant la date limite du {deadline} : "
                f"{', '.join(late)} finirait trop tard ; il faudrait environ {_jours(max_e - last)} de plus, "
                "ou un renfort, ou une replanification complète."
            )
        result.diagnostics.append(
            f"Réparation locale arrêtée après {steps} étapes avec {math.ceil(result.remaining_conflicts / 2)} "
            f"conflit(s) restant(s) sur : {', '.join(by_id[t].title for t in remaining)}."
        )
    result.elapsed_ms = (time.perf_counter() - t0) * 1000
    return result
