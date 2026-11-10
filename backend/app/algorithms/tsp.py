"""Module E — Voyageur de commerce (algorithme n°30 de la liste du cours).

BUT
    Un technicien part de sa ville de base et doit intervenir dans plusieurs villes (agences).
    Dans quel ordre les visiter pour parcourir le moins de kilomètres ?

CONVENTIONS
    - `matrix[i][j]` : distance de la ville i à la ville j ; la ville 0 est la ville de DÉPART.
    - Un ordre est une liste d'index qui commence par 0 et contient chaque ville une fois.
    - closed=True  : tournée fermée, on revient à la ville de départ ;
      closed=False : chemin ouvert, on s'arrête à la dernière ville visitée.

MÉTHODES
    - held_karp          : EXACTE, programmation dynamique sur les sous-ensembles, O(n² · 2ⁿ).
                           Utilisée jusqu'à 12 sites (au-delà, 2ⁿ explose).
    - nearest_neighbor   : APPROCHÉE, toujours aller à la ville non visitée la plus proche, O(n²).
    - two_opt            : AMÉLIORATION LOCALE d'une tournée, en inversant des portions.
    - brute_force        : toutes les permutations (n − 1)!, pour les tests (n ≤ 9).
"""

from collections.abc import Sequence
from itertools import permutations

Matrix = Sequence[Sequence[float]]
EPS = 1e-9


def tour_length(matrix: Matrix, order: Sequence[int], closed: bool) -> float:
    """Longueur d'un ordre de visite (avec le retour au départ si la tournée est fermée)."""
    total = sum(matrix[a][b] for a, b in zip(order, order[1:]))
    if closed and len(order) > 1:
        total += matrix[order[-1]][order[0]]
    return total


# =========================================================================== méthode exacte


def held_karp(matrix: Matrix, closed: bool = True) -> tuple[list[int], float]:
    """Algorithme de Held-Karp (programmation dynamique).

    IDÉE
        C[S][j] = longueur du plus court chemin qui part de 0, visite EXACTEMENT les villes de
        l'ensemble S (0 non compris), et se termine en j ∈ S.
        Récurrence : C[S][j] = min sur k ∈ S∖{j} de  C[S∖{j}][k] + d(k, j)
        Cas de base : C[{j}][j] = d(0, j).
        Réponse : tournée fermée = min_j C[tout][j] + d(j, 0) ; chemin ouvert = min_j C[tout][j].
        On reconstruit l'ordre en mémorisant, pour chaque (S, j), la ville k qui précède j.

        Les ensembles S sont codés en BITS : la ville i (1 ≤ i < n) correspond au bit i − 1.

    POURQUOI C'EST EXACT
        Principe d'optimalité de Bellman : la fin d'un plus court chemin est elle-même un plus
        court chemin. Peu importe l'ordre dans lequel on a visité S∖{j}, seul compte le meilleur.

    COMPLEXITÉ
        2ⁿ⁻¹ ensembles × n villes de fin × n prédécesseurs = O(n² · 2ⁿ) en temps, O(n · 2ⁿ) en mémoire.
        Bien mieux que les (n − 1)! permutations de la force brute : pour 12 villes,
        ≈ 600 000 opérations contre ≈ 40 millions de permutations.
    """
    n = len(matrix)
    if n <= 1:
        return [0] * n, 0
    m = n - 1  # villes autres que le départ
    full = (1 << m) - 1
    INF = float("inf")
    cost = [[INF] * m for _ in range(1 << m)]
    parent = [[-1] * m for _ in range(1 << m)]
    for j in range(m):
        cost[1 << j][j] = matrix[0][j + 1]

    for S in range(1, full + 1):  # les sous-ensembles plus petits sont toujours traités avant
        for j in range(m):
            if not (S >> j) & 1 or cost[S][j] == INF:
                continue
            base = cost[S][j]
            for k in range(m):  # prolonger le chemin de j vers une ville k pas encore visitée
                if (S >> k) & 1:
                    continue
                T = S | (1 << k)
                candidate = base + matrix[j + 1][k + 1]
                if candidate < cost[T][k]:
                    cost[T][k] = candidate
                    parent[T][k] = j

    best_j = min(range(m), key=lambda j: cost[full][j] + (matrix[j + 1][0] if closed else 0))
    best = cost[full][best_j] + (matrix[best_j + 1][0] if closed else 0)

    # Reconstruction de l'ordre, de la fin vers le début.
    order = []
    S, j = full, best_j
    while j != -1:
        order.append(j + 1)
        S, j = S & ~(1 << j), parent[S][j]
    order.append(0)
    order.reverse()
    return order, best


def brute_force(matrix: Matrix, closed: bool = True) -> tuple[list[int], float]:
    """Toutes les permutations des villes 1..n−1 : référence pour les tests."""
    n = len(matrix)
    if n > 9:
        raise ValueError("Force brute limitée à 9 villes.")
    best_order, best = list(range(n)), float("inf")
    for perm in permutations(range(1, n)):
        order = [0, *perm]
        length = tour_length(matrix, order, closed)
        if length < best - EPS:
            best_order, best = order, length
    return best_order, (best if n > 1 else 0)


# =========================================================================== méthodes approchées


def nearest_neighbor(matrix: Matrix) -> list[int]:
    """Plus proche voisin : depuis la ville courante, aller à la ville non visitée la plus proche.

    Rapide (O(n²)) mais myope : les dernières villes, laissées pour la fin, coûtent souvent cher.
    """
    n = len(matrix)
    if n == 0:
        return []
    order = [0]
    left = set(range(1, n))
    while left:
        here = order[-1]
        nxt = min(left, key=lambda j: (matrix[here][j], j))
        order.append(nxt)
        left.remove(nxt)
    return order


def two_opt(matrix: Matrix, order: Sequence[int], closed: bool = True) -> list[int]:
    """Amélioration 2-opt, répétée jusqu'à ce qu'aucun échange n'améliore la tournée.

    IDÉE
        On retire deux arêtes (a→b) et (c→e) et on reconnecte en (a→c) et (b→e), ce qui revient
        à INVERSER la portion b…c. Si le gain d(a,b) + d(c,e) − d(a,c) − d(b,e) est positif,
        on garde l'inversion. Géométriquement, cela supprime les CROISEMENTS de la tournée.
        Pour un chemin ouvert, la dernière portion peut être inversée sans arête (c→e).

    COMPLEXITÉ : O(n²) échanges testés par passe, en O(1) chacun (on ne calcule que le gain).
    Le nombre de passes est fini car la longueur diminue strictement à chaque échange.
    La ville de départ (position 0) ne bouge jamais.
    """
    tour = list(order)
    n = len(tour)
    improved = True
    while improved:
        improved = False
        for i in range(1, n - 1):
            for k in range(i + 1, n):
                a, b, c = tour[i - 1], tour[i], tour[k]
                if k + 1 < n:
                    e = tour[k + 1]
                    delta = matrix[a][c] + matrix[b][e] - matrix[a][b] - matrix[c][e]
                elif closed:
                    e = tour[0]
                    delta = matrix[a][c] + matrix[b][e] - matrix[a][b] - matrix[c][e]
                else:
                    delta = matrix[a][c] - matrix[a][b]  # chemin ouvert : pas d'arête après c
                if delta < -EPS:
                    tour[i : k + 1] = reversed(tour[i : k + 1])
                    improved = True
    return tour
