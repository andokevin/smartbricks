"""Contrôle des dépendances extraites par le copilote : tri topologique de Kahn et suppression des cycles.

Utilisé par le module A (n°33) APRÈS l'extraction du LLM : un LLM peut produire
« A dépend de B » et « B dépend de A », ce qui rendrait le planning impossible.
On ne fait pas confiance au LLM : on vérifie mathématiquement.

TRI TOPOLOGIQUE DE KAHN
    On retire successivement les éléments qui ne dépendent de plus rien (degré entrant 0).
    S'il reste des éléments à la fin, ils sont tous pris dans au moins un cycle.
    Complexité : O(V + E) (V éléments, E dépendances).

QUELLE DÉPENDANCE RETIRER ? « l'arête la moins justifiée »
    Dans un brouillon, les éléments sont déclarés dans l'ordre logique (catalogue avant panier,
    maquettes avant pages). Une dépendance « u dépend de v » où v est déclaré APRÈS u va donc
    « à rebours » de cet ordre : c'est la moins justifiée.
    Propriété garantie : tout cycle contient au moins une telle arête (on ne peut pas faire une
    boucle en ne revenant jamais en arrière dans une liste). On retire celle qui remonte le plus
    loin, puis on recommence jusqu'à ce qu'il n'y ait plus de cycle.
"""

from collections.abc import Mapping, Sequence


def topological_order(refs: Sequence[str], deps: Mapping[str, Sequence[str]]) -> tuple[list[str], list[str]]:
    """Kahn. Renvoie (ordre trouvé, éléments restants pris dans un cycle).

    `deps[u]` = liste des éléments dont u dépend. Les références inconnues sont ignorées.
    """
    known = set(refs)
    indegree = {r: sum(1 for d in set(deps.get(r, [])) if d in known) for r in refs}
    dependents: dict[str, list[str]] = {r: [] for r in refs}
    for r in refs:
        for d in set(deps.get(r, [])):
            if d in known:
                dependents[d].append(r)
    queue = [r for r in refs if indegree[r] == 0]
    order: list[str] = []
    while queue:
        u = queue.pop(0)
        order.append(u)
        for v in dependents[u]:
            indegree[v] -= 1
            if indegree[v] == 0:
                queue.append(v)
    remaining = [r for r in refs if indegree[r] > 0]
    return order, remaining


def find_cycle(refs: Sequence[str], deps: Mapping[str, Sequence[str]]) -> list[str] | None:
    """Renvoie un cycle [u1, u2, …] (u1 dépend de u2, …, le dernier dépend de u1), ou None."""
    _, remaining = topological_order(refs, deps)
    if not remaining:
        return None
    stuck = set(remaining)
    # Depuis un élément bloqué, on suit des dépendances bloquées : on finit par revenir sur un
    # élément déjà vu, et la portion entre les deux visites est un cycle.
    path: list[str] = []
    seen: dict[str, int] = {}
    u = remaining[0]
    while u not in seen:
        seen[u] = len(path)
        path.append(u)
        u = next(d for d in deps.get(u, []) if d in stuck)
    return path[seen[u] :]


def break_cycles(
    refs: Sequence[str], deps: Mapping[str, Sequence[str]]
) -> tuple[dict[str, list[str]], list[tuple[str, str]]]:
    """Retire les dépendances nécessaires pour supprimer tous les cycles.

    Renvoie (dépendances nettoyées, liste des arêtes retirées (u, v) = « u dépendait de v »).
    """
    position = {r: k for k, r in enumerate(refs)}
    clean = {r: [d for d in dict.fromkeys(deps.get(r, [])) if d in position] for r in refs}
    removed: list[tuple[str, str]] = []
    while (cycle := find_cycle(refs, clean)) is not None:
        edges = [(cycle[k], cycle[(k + 1) % len(cycle)]) for k in range(len(cycle))]
        # Arête qui remonte le plus loin dans l'ordre de déclaration (v déclaré après u).
        u, v = max(edges, key=lambda e: (position[e[1]] - position[e[0]], position[e[0]]))
        clean[u].remove(v)
        removed.append((u, v))
    return clean, removed
