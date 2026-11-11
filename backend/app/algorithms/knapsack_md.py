"""Module B — Sac à dos multidimensionnel (algorithme n°29 de la liste du cours).

BUT
    Le client a plus de fonctionnalités rêvées que de moyens. On choisit celles du sprint 1
    qui apportent le plus de valeur métier sans dépasser NI le budget en Ariary, NI les heures.

MODÈLE
    maximiser   Σ v_i x_i                      v_i = valeur métier (1 à 100)
    sous        Σ c_i x_i ≤ budget             c_i = coût estimé (Ar)
                Σ h_i x_i ≤ heures             h_i = heures estimées
                x_i = 1 si i est obligatoire
                x_j ≤ x_i si j dépend de i     (pas de paiement sans panier)
                x_i ∈ {0, 1}

MÉTHODES
    - branch_and_bound   : exacte (séparation et évaluation), utilisée jusqu'à 40 fonctionnalités.
    - greedy             : glouton par densité, avec réparation des dépendances.
    - greedy_with_swaps  : glouton puis amélioration locale par échanges 1-1 (au-delà de 40).
    - brute_force        : énumère les 2^n combinaisons ; sert de référence dans les tests (n ≤ 20).
    - verify_selection   : vérification INDÉPENDANTE d'une sélection (ne réutilise rien du solveur).

TRAITEMENT DES DÉPENDANCES (commun à toutes les méthodes)
    - Inclure i  ⇒ inclure aussi tout ce dont i dépend, directement ou non (« fermeture amont »).
    - Exclure i  ⇒ exclure aussi tout ce qui dépend de i (« fermeture aval »).
    - Les obligatoires et leur fermeture amont sont inclus d'office (« ensemble forcé »).
    Ainsi, à chaque instant, l'ensemble des fonctionnalités incluses respecte toutes les dépendances.
"""

from __future__ import annotations

import time
from collections.abc import Hashable, Sequence
from dataclasses import dataclass, field
from itertools import combinations

from app.algorithms.formatting import format_ar, format_pct

ItemId = Hashable


@dataclass(frozen=True)
class Item:
    """Une fonctionnalité candidate (un objet du sac à dos)."""

    id: ItemId
    value: int  # valeur métier v_i
    cost: int  # coût c_i en Ar
    hours: int  # heures h_i
    mandatory: bool = False
    depends_on: tuple[ItemId, ...] = ()
    name: str = ""

    @property
    def label(self) -> str:
        return self.name or str(self.id)


@dataclass
class KnapsackSolution:
    feasible: bool
    selected: list[ItemId]
    total_value: int
    total_cost: int
    total_hours: int
    method: str
    optimal: bool  # True seulement si l'optimalité est prouvée
    nodes: int = 0  # nœuds explorés (séparation et évaluation)
    elapsed_ms: float = 0.0
    missing_cost: int = 0  # si impossible : ce qui manque au budget
    missing_hours: int = 0  # si impossible : ce qui manque aux heures
    message: str = ""


@dataclass
class WhatIfScenario:
    increase: float  # 0.10 pour +10 %
    extra_budget: int
    new_budget: int
    added: list[ItemId] = field(default_factory=list)
    removed: list[ItemId] = field(default_factory=list)
    value_gain: int = 0
    message: str = ""


# =========================================================================== préparation


class _Problem:
    """Représentation interne par indices 0..n-1, avec les fermetures de dépendances précalculées."""

    def __init__(self, items: Sequence[Item], budget: int, max_hours: int) -> None:
        self.items = list(items)
        self.n = len(self.items)
        self.budget = budget
        self.max_hours = max_hours
        index = {it.id: k for k, it in enumerate(self.items)}
        if len(index) != self.n:
            raise ValueError("Deux fonctionnalités ont le même identifiant.")
        self.deps: list[list[int]] = []
        for it in self.items:
            unknown = [d for d in it.depends_on if d not in index]
            if unknown:
                raise ValueError(f"{it.label} dépend d'une fonctionnalité inconnue : {unknown}")
            self.deps.append([index[d] for d in it.depends_on])
        self.dependents: list[list[int]] = [[] for _ in range(self.n)]
        for j, ds in enumerate(self.deps):
            for i in ds:
                self.dependents[i].append(j)

        # Fermetures (parcours en profondeur ; un éventuel cycle ne fait pas boucler).
        self.up = [self._closure(k, self.deps) for k in range(self.n)]  # k + ce dont k dépend
        self.down = [self._closure(k, self.dependents) for k in range(self.n)]  # k + ce qui dépend de k

        self.forced: set[int] = set()
        for k, it in enumerate(self.items):
            if it.mandatory:
                self.forced |= self.up[k]

    @staticmethod
    def _closure(start: int, graph: list[list[int]]) -> frozenset[int]:
        seen = {start}
        stack = [start]
        while stack:
            for nxt in graph[stack.pop()]:
                if nxt not in seen:
                    seen.add(nxt)
                    stack.append(nxt)
        return frozenset(seen)

    def density(self, k: int) -> float:
        """Densité v_i / (c_i / budget + h_i / heures) : valeur par « part de ressources » consommée.

        On divise chaque ressource par sa capacité pour pouvoir additionner des Ariary et des heures.
        """
        it = self.items[k]
        use = it.cost / max(self.budget, 1) + it.hours / max(self.max_hours, 1)
        return it.value / use if use > 0 else float("inf")

    def totals(self, chosen: set[int] | frozenset[int]) -> tuple[int, int, int]:
        value = sum(self.items[k].value for k in chosen)
        cost = sum(self.items[k].cost for k in chosen)
        hours = sum(self.items[k].hours for k in chosen)
        return value, cost, hours

    def fits(self, cost: int, hours: int) -> bool:
        return cost <= self.budget and hours <= self.max_hours

    def solution(self, chosen: set[int], method: str, optimal: bool, nodes: int, t0: float) -> KnapsackSolution:
        value, cost, hours = self.totals(chosen)
        return KnapsackSolution(
            feasible=True,
            selected=[self.items[k].id for k in sorted(chosen)],
            total_value=value,
            total_cost=cost,
            total_hours=hours,
            method=method,
            optimal=optimal,
            nodes=nodes,
            elapsed_ms=(time.perf_counter() - t0) * 1000,
            message=(
                f"{len(chosen)} fonctionnalité(s) retenue(s) sur {self.n} : valeur {value}, "
                f"coût {format_ar(cost)} sur {format_ar(self.budget)}, "
                f"{hours} h sur {self.max_hours} h."
            ),
        )

    def infeasible(self, method: str, t0: float) -> KnapsackSolution | None:
        """Si les obligatoires (avec leurs dépendances) dépassent déjà les moyens : message chiffré."""
        _, cost, hours = self.totals(self.forced)
        if self.fits(cost, hours):
            return None
        missing_cost = max(0, cost - self.budget)
        missing_hours = max(0, hours - self.max_hours)
        parts = []
        if missing_cost:
            parts.append(f"il manque {format_ar(missing_cost)} au budget")
        if missing_hours:
            parts.append(f"il manque {missing_hours} h")
        return KnapsackSolution(
            feasible=False,
            selected=[],
            total_value=0,
            total_cost=cost,
            total_hours=hours,
            method=method,
            optimal=True,  # l'impossibilité est prouvée
            elapsed_ms=(time.perf_counter() - t0) * 1000,
            missing_cost=missing_cost,
            missing_hours=missing_hours,
            message=(
                f"Les fonctionnalités obligatoires coûtent déjà {format_ar(cost)} et {hours} h : "
                + " et ".join(parts)
                + ". Augmentez les moyens ou retirez le caractère obligatoire d'une fonctionnalité."
            ),
        )


# =========================================================================== méthode exacte


def branch_and_bound(
    items: Sequence[Item], budget: int, max_hours: int, max_nodes: int = 2_000_000
) -> KnapsackSolution:
    """Séparation et évaluation en profondeur d'abord.

    IDÉE
        On parcourt les fonctionnalités par densité décroissante. À chaque nœud on « sépare » :
        branche 1 = inclure la fonctionnalité (avec ses dépendances), branche 2 = l'exclure
        (avec ce qui dépend d'elle). On « évalue » chaque nœud par une BORNE SUPÉRIEURE de la
        valeur atteignable ; si cette borne ne dépasse pas la meilleure solution déjà trouvée,
        la branche ne peut pas faire mieux : on l'élague.

    BORNE SUPÉRIEURE (le point clé à défendre)
        Pour la dimension « budget » seule, on résout le sac à dos FRACTIONNAIRE sur les
        fonctionnalités non encore décidées : on les prend par valeur/coût décroissant, la dernière
        en fraction. C'est une RELAXATION : on a enlevé la contrainte des heures, les dépendances
        et l'intégralité (x ∈ {0,1} devient 0 ≤ x ≤ 1). Toute vraie solution est donc aussi une
        solution de ce problème relâché ⇒ sa valeur est ≤ la valeur fractionnaire.
        Même raisonnement pour la dimension « heures ». Les deux bornes sont valides, donc leur
        MINIMUM l'est aussi, et il est plus serré (meilleur élagage).

    COMPLEXITÉ
        Pire cas O(2^n) nœuds (le problème est NP-difficile), chaque nœud coûte O(n) pour la borne.
        En pratique l'élagage réduit énormément l'arbre : 14 fonctionnalités (Boutique Soa) ⇒ une
        vingtaine de nœuds au lieu de 2^14 = 16 384 ; au plus 2 106 nœuds mesurés à 40 fonctionnalités.
        Au-delà de 40 fonctionnalités, le sélecteur de méthode passe à l'heuristique.
    """
    t0 = time.perf_counter()
    p = _Problem(items, budget, max_hours)
    impossible = p.infeasible("Séparation et évaluation", t0)
    if impossible:
        return impossible

    # state[k] : 1 = inclus, 0 = exclu, None = pas encore décidé.
    state: list[int | None] = [None] * p.n
    for k in p.forced:
        state[k] = 1
    base_value, base_cost, base_hours = p.totals(p.forced)

    order = sorted((k for k in range(p.n) if state[k] is None), key=lambda k: (-p.density(k), k))
    # Ordres précalculés pour les deux bornes fractionnaires.
    by_cost_ratio = sorted(range(p.n), key=lambda k: -(p.items[k].value / max(p.items[k].cost, 1e-9)))
    by_hours_ratio = sorted(range(p.n), key=lambda k: -(p.items[k].value / max(p.items[k].hours, 1e-9)))

    # Solution initiale = glouton : une bonne valeur de départ élague beaucoup plus tôt.
    start = greedy(items, budget, max_hours)
    best_value = start.total_value
    index = {it.id: k for k, it in enumerate(p.items)}
    best_set = {index[i] for i in start.selected}
    nodes = 0
    aborted = False

    def fractional(order_by_ratio: list[int], capacity: int, weight_of: str) -> float:
        """Valeur du sac à dos fractionnaire sur les objets non décidés, pour une seule dimension."""
        total = 0.0
        for k in order_by_ratio:
            if state[k] is not None:
                continue
            it = p.items[k]
            w = getattr(it, weight_of)
            if w <= capacity:
                capacity -= w
                total += it.value
            else:
                total += it.value * capacity / w  # dernier objet pris en fraction
                break
        return total

    def dfs(pos: int, value: int, cost: int, hours: int) -> None:
        nonlocal best_value, best_set, nodes, aborted
        nodes += 1
        if nodes > max_nodes:
            aborted = True
            return

        # Les objets non décidés valent 0 ici : l'ensemble inclus est déjà une solution admissible.
        if value > best_value:
            best_value = value
            best_set = {k for k in range(p.n) if state[k] == 1}

        while pos < len(order) and state[order[pos]] is not None:
            pos += 1  # déjà décidé par une fermeture de dépendances
        if pos == len(order):
            return

        bound = value + min(
            fractional(by_cost_ratio, budget - cost, "cost"),
            fractional(by_hours_ratio, max_hours - hours, "hours"),
        )
        if bound <= best_value:
            return  # élagage : cette branche ne peut pas battre la meilleure solution

        k = order[pos]

        # Branche 1 : inclure k et tout ce dont k dépend.
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

        # Branche 2 : exclure k et tout ce qui dépend de k.
        # (Aucun de ces éléments n'est inclus : s'il l'était, k serait inclus par fermeture.)
        new = [j for j in p.down[k] if state[j] is None]
        for j in new:
            state[j] = 0
        dfs(pos + 1, value, cost, hours)
        for j in new:
            state[j] = None

    dfs(0, base_value, base_cost, base_hours)
    sol = p.solution(best_set, "Séparation et évaluation", optimal=not aborted, nodes=nodes, t0=t0)
    return sol


# =========================================================================== heuristiques


def greedy(items: Sequence[Item], budget: int, max_hours: int) -> KnapsackSolution:
    """Glouton par densité avec réparation des dépendances.

    IDÉE : on part des obligatoires, puis on parcourt les autres par densité décroissante ;
    on ajoute une fonctionnalité AVEC ses dépendances manquantes si l'ensemble tient encore.
    COMPLEXITÉ : O(n log n) pour le tri + O(n²) pour les fermetures. Rapide, mais sans garantie.
    """
    t0 = time.perf_counter()
    p = _Problem(items, budget, max_hours)
    impossible = p.infeasible("Glouton par densité", t0)
    if impossible:
        return impossible
    chosen = _greedy_fill(p, set(p.forced))
    return p.solution(chosen, "Glouton par densité", optimal=False, nodes=0, t0=t0)


def _greedy_fill(p: _Problem, chosen: set[int]) -> set[int]:
    _, cost, hours = p.totals(chosen)
    for k in sorted(range(p.n), key=lambda k: (-p.density(k), k)):
        if k in chosen:
            continue
        new = p.up[k] - chosen
        dc = sum(p.items[j].cost for j in new)
        dh = sum(p.items[j].hours for j in new)
        if p.fits(cost + dc, hours + dh):
            chosen |= new
            cost += dc
            hours += dh
    return chosen


def greedy_with_swaps(items: Sequence[Item], budget: int, max_hours: int) -> KnapsackSolution:
    """Glouton, puis amélioration locale par échanges 1-1.

    IDÉE : tant qu'on trouve mieux, on essaie de RETIRER une fonctionnalité non forcée
    (avec ce qui dépend d'elle) et d'en AJOUTER une autre (avec ses dépendances) ;
    on accepte l'échange s'il reste admissible et augmente la valeur. On complète ensuite
    par le glouton si de la place s'est libérée.
    COMPLEXITÉ : O(n²) échanges testés par passe ; le nombre de passes est borné car la
    valeur augmente strictement à chaque échange accepté.
    """
    t0 = time.perf_counter()
    p = _Problem(items, budget, max_hours)
    impossible = p.infeasible("Glouton + échanges 1-1", t0)
    if impossible:
        return impossible
    chosen = _greedy_fill(p, set(p.forced))
    value = p.totals(chosen)[0]

    improved = True
    while improved:
        improved = False
        removable = [r for r in chosen if r not in p.forced]
        for r in [None, *removable]:
            base = chosen - (p.down[r] if r is not None else frozenset())
            for a in range(p.n):
                if a in base or (r is not None and a == r):
                    continue
                candidate = base | p.up[a]
                if p.forced - candidate:
                    continue
                v, c, h = p.totals(candidate)
                if v > value and p.fits(c, h):
                    chosen, value, improved = _greedy_fill(p, set(candidate)), v, True
                    value = p.totals(chosen)[0]
                    break
            if improved:
                break
    return p.solution(chosen, "Glouton + échanges 1-1", optimal=False, nodes=0, t0=t0)


def brute_force(items: Sequence[Item], budget: int, max_hours: int) -> KnapsackSolution:
    """Énumère toutes les combinaisons (2^n). Référence pour les tests, n ≤ 20."""
    t0 = time.perf_counter()
    if len(items) > 20:
        raise ValueError("Force brute limitée à 20 fonctionnalités.")
    p = _Problem(items, budget, max_hours)
    impossible = p.infeasible("Force brute", t0)
    if impossible:
        return impossible
    best: set[int] = set()
    best_value = -1
    for size in range(p.n + 1):
        for combo in combinations(range(p.n), size):
            ids = [p.items[k].id for k in combo]
            if verify_selection(items, ids, budget, max_hours):
                continue
            v = sum(p.items[k].value for k in combo)
            if v > best_value:
                best_value, best = v, set(combo)
    return p.solution(best, "Force brute", optimal=True, nodes=2**p.n, t0=t0)


# =========================================================================== vérification et explications


def verify_selection(items: Sequence[Item], selected: Sequence[ItemId], budget: int, max_hours: int) -> list[str]:
    """Vérification indépendante d'une sélection. Renvoie la liste des violations (vide = valide)."""
    by_id = {it.id: it for it in items}
    chosen = set(selected)
    problems: list[str] = []
    if len(chosen) != len(selected):
        problems.append("Une fonctionnalité est sélectionnée deux fois.")
    unknown = chosen - by_id.keys()
    if unknown:
        problems.append(f"Fonctionnalités inconnues : {sorted(map(str, unknown))}")
        return problems
    cost = sum(by_id[i].cost for i in chosen)
    hours = sum(by_id[i].hours for i in chosen)
    if cost > budget:
        problems.append(f"Budget dépassé : {format_ar(cost)} > {format_ar(budget)}.")
    if hours > max_hours:
        problems.append(f"Heures dépassées : {hours} h > {max_hours} h.")
    for it in items:
        if it.mandatory and it.id not in chosen:
            problems.append(f"Fonctionnalité obligatoire absente : {it.label}.")
    for i in chosen:
        for d in by_id[i].depends_on:
            if d not in chosen:
                problems.append(f"{by_id[i].label} est retenue sans {by_id[d].label}, dont elle dépend.")
    return problems


def explain_exclusions(
    items: Sequence[Item], solution: KnapsackSolution, budget: int, max_hours: int
) -> dict[ItemId, str]:
    """Raison, en français, de chaque fonctionnalité écartée."""
    p = _Problem(items, budget, max_hours)
    index = {it.id: k for k, it in enumerate(p.items)}
    chosen = {index[i] for i in solution.selected}
    reasons: dict[ItemId, str] = {}
    if not solution.feasible:
        for it in p.items:
            reasons[it.id] = "Non calculé : les fonctionnalités obligatoires dépassent déjà les moyens."
        return reasons

    remaining_cost = budget - solution.total_cost
    remaining_hours = max_hours - solution.total_hours
    for k, it in enumerate(p.items):
        if k in chosen:
            continue
        needed = p.up[k] - chosen  # elle-même + ses dépendances non retenues
        _, dc, dh = p.totals(needed)
        with_deps = ""
        others = [p.items[j].label for j in sorted(needed) if j != k]
        if others:
            with_deps = f" (avec ce dont elle dépend : {', '.join(others)})"
        lack_cost, lack_hours = dc - remaining_cost, dh - remaining_hours
        if lack_cost > 0 and lack_hours > 0:
            reasons[it.id] = (
                f"Ne tient ni dans le budget restant ni dans les heures restantes{with_deps} : "
                f"il faudrait {format_ar(lack_cost)} et {lack_hours} h de plus."
            )
        elif lack_cost > 0:
            reasons[it.id] = (
                f"Ne tient pas dans le budget restant{with_deps} : il faudrait {format_ar(lack_cost)} de plus. "
                "La combinaison retenue apporte plus de valeur pour ce budget."
            )
        elif lack_hours > 0:
            reasons[it.id] = (
                f"Ne tient pas dans les heures restantes{with_deps} : il faudrait {lack_hours} h de plus. "
                "La combinaison retenue apporte plus de valeur pour ces heures."
            )
        else:
            reasons[it.id] = "Pourrait encore être ajoutée (la méthode approchée ne l'a pas retenue)."
    return reasons


def what_if(
    items: Sequence[Item],
    budget: int,
    max_hours: int,
    increases: Sequence[float] = (0.10, 0.25),
) -> list[WhatIfScenario]:
    """« Et si ? » : on relance l'optimisation avec plus de budget et on compare au plan actuel."""
    labels = {it.id: it.label for it in items}
    base = branch_and_bound(items, budget, max_hours)
    base_set = set(base.selected)
    scenarios: list[WhatIfScenario] = []
    for inc in increases:
        extra = int(round(budget * inc))
        sol = branch_and_bound(items, budget + extra, max_hours)
        sc = WhatIfScenario(increase=inc, extra_budget=extra, new_budget=budget + extra)
        if not sol.feasible:
            sc.message = f"Même avec {format_ar(extra)} de plus (+{format_pct(inc)}), les obligatoires ne tiennent pas."
        else:
            new_set = set(sol.selected)
            sc.added = [it.id for it in items if it.id in new_set - base_set]
            sc.removed = [it.id for it in items if it.id in base_set - new_set]
            sc.value_gain = sol.total_value - (base.total_value if base.feasible else 0)
            if not base.feasible:
                sc.message = f"Avec {format_ar(extra)} de plus (+{format_pct(inc)}), le projet devient réalisable."
            elif sc.added:
                sc.message = (
                    f"Avec {format_ar(extra)} de plus (+{format_pct(inc)}), vous ajoutez : "
                    + ", ".join(labels[i] for i in sc.added)
                    + (f" (en remplaçant : {', '.join(labels[i] for i in sc.removed)})" if sc.removed else "")
                    + f". Valeur métier : +{sc.value_gain}."
                )
            else:
                sc.message = (
                    f"Avec {format_ar(extra)} de plus (+{format_pct(inc)}), aucune fonctionnalité "
                    "supplémentaire ne devient possible (les heures ou les dépendances bloquent)."
                )
        scenarios.append(sc)
    return scenarios
