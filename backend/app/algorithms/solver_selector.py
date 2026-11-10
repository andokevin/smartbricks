"""Module A, partie sélecteur de méthode — hyper-heuristique (algorithme n°33 de la liste du cours).

BUT
    Choisir AUTOMATIQUEMENT la méthode de résolution la plus adaptée à chaque problème,
    selon sa taille et le temps disponible, et EXPLIQUER ce choix à l'utilisateur.

POURQUOI « HYPER-HEURISTIQUE »
    Une heuristique résout un problème. Une hyper-heuristique est une règle de niveau supérieur
    qui choisit QUELLE méthode appliquer : elle travaille sur l'espace des méthodes, pas sur
    l'espace des solutions. Ici la règle est simple et explicable :

    | Problème             | Méthode exacte si…                    | Sinon                                  |
    |----------------------|---------------------------------------|----------------------------------------|
    | Sac à dos (n°29)     | ≤ 40 fonctionnalités : séparation     | glouton par densité + échanges 1-1     |
    |                      | et évaluation                         |                                        |
    | Voyageur (n°30)      | ≤ 12 sites : Held-Karp                | plus proche voisin + 2-opt             |
    | CSP (n°3)            | retour arrière + propagation, 3 s     | Min-Conflict (niveau B)                |

    Les seuils viennent du coût des méthodes exactes : le sac à dos exact est exponentiel au pire
    mais l'élagage le rend instantané jusqu'à quelques dizaines d'objets ; Held-Karp coûte
    O(n² · 2ⁿ) : 12 sites ≈ 0,6 million d'opérations (quelques ms), 20 sites ≈ 400 millions.

COMPLEXITÉ : la décision elle-même est en O(1) ; seul compte le coût de la méthode choisie.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date

from app.algorithms import knapsack_md, tsp
from app.algorithms.csp_scheduler import ScheduleResult, SchedFreelancer, SchedTask, solve_schedule

KNAPSACK_EXACT_MAX = 40
TSP_EXACT_MAX_SITES = 12
CSP_TIME_LIMIT_S = 3.0


@dataclass(frozen=True)
class MethodChoice:
    problem: str
    method: str
    exact: bool
    reason: str  # affichée à l'utilisateur
    course_number: int


@dataclass
class TourSolution:
    order: list[int]
    length: float
    choice: MethodChoice
    nearest_neighbor_length: float | None = None  # pour mesurer l'apport de 2-opt


# =========================================================================== règles


def choose_knapsack_method(n_features: int, exact_threshold: int = KNAPSACK_EXACT_MAX) -> MethodChoice:
    if n_features <= exact_threshold:
        return MethodChoice(
            "Sac à dos", "Séparation et évaluation", True,
            f"{n_features} fonctionnalités (≤ {exact_threshold}) : la méthode exacte reste rapide, "
            "le périmètre proposé est donc le meilleur possible.",
            29,
        )
    return MethodChoice(
        "Sac à dos", "Glouton + échanges 1-1", False,
        f"{n_features} fonctionnalités (> {exact_threshold}) : la méthode exacte pourrait être trop longue ; "
        "on utilise un glouton par densité amélioré par échanges, rapide mais sans garantie d'optimum.",
        29,
    )


def choose_tsp_method(n_sites: int, exact_threshold: int = TSP_EXACT_MAX_SITES) -> MethodChoice:
    """`n_sites` : nombre de villes à visiter, sans compter la ville de départ."""
    if n_sites <= exact_threshold:
        return MethodChoice(
            "Voyageur de commerce", "Held-Karp", True,
            f"{n_sites} site(s) à visiter (≤ {exact_threshold}) : Held-Karp calcule la tournée la plus courte "
            "possible en quelques millisecondes.",
            30,
        )
    return MethodChoice(
        "Voyageur de commerce", "Plus proche voisin + 2-opt", False,
        f"{n_sites} sites (> {exact_threshold}) : Held-Karp demanderait trop de calculs (2ⁿ) ; "
        "on construit une tournée par plus proche voisin, puis on supprime les croisements avec 2-opt.",
        30,
    )


def choose_csp_method(n_tasks: int, time_limit: float = CSP_TIME_LIMIT_S) -> MethodChoice:
    return MethodChoice(
        "Planification", "Retour arrière + propagation (CSP)", True,
        f"{n_tasks} tâches : recherche avec retour arrière, propagation du chemin critique et "
        f"vérification anticipée, limitée à {time_limit:g} s ; on garde le planning le plus court trouvé.",
        3,
    )


# =========================================================================== exécution


def solve_knapsack(
    items: Sequence[knapsack_md.Item], budget: int, max_hours: int, exact_threshold: int = KNAPSACK_EXACT_MAX
) -> tuple[knapsack_md.KnapsackSolution, MethodChoice]:
    choice = choose_knapsack_method(len(items), exact_threshold)
    solver = knapsack_md.branch_and_bound if choice.exact else knapsack_md.greedy_with_swaps
    return solver(items, budget, max_hours), choice


def solve_tour(
    matrix: Sequence[Sequence[float]], closed: bool = True, exact_threshold: int = TSP_EXACT_MAX_SITES
) -> TourSolution:
    """Résout la tournée ; la ville 0 de la matrice est le départ."""
    choice = choose_tsp_method(max(len(matrix) - 1, 0), exact_threshold)
    if choice.exact:
        order, length = tsp.held_karp(matrix, closed)
        return TourSolution(order, length, choice)
    nn = tsp.nearest_neighbor(matrix)
    order = tsp.two_opt(matrix, nn, closed)
    return TourSolution(order, tsp.tour_length(matrix, order, closed), choice, tsp.tour_length(matrix, nn, closed))


def solve_schedule_auto(
    tasks: Sequence[SchedTask],
    team: Sequence[SchedFreelancer],
    start: date,
    deadline: date,
    time_limit: float = CSP_TIME_LIMIT_S,
) -> tuple[ScheduleResult, MethodChoice]:
    """Lance le CSP et complète la raison selon l'issue (optimal prouvé, limite atteinte, échec)."""
    base = choose_csp_method(len(tasks), time_limit)
    result = solve_schedule(tasks, team, start, deadline, time_limit=time_limit)
    if result.status == "OK" and result.optimal:
        outcome = "Le planning trouvé est optimal (durée minimale prouvée)."
    elif result.status == "OK":
        outcome = (
            f"Limite de {time_limit:g} s atteinte : meilleur planning trouvé, à au plus "
            f"{result.makespan_days - result.lower_bound_days} jour(s) de l'optimum théorique."
        )
    elif result.status == "INFEASIBLE":
        outcome = "Impossibilité prouvée : voir le diagnostic."
    else:
        outcome = (
            "Aucun planning trouvé dans le temps imparti. La réparation par Min-Conflict "
            "(n°11) est prévue au niveau B."
        )
    choice = MethodChoice(base.problem, result.method, base.exact, f"{base.reason} {outcome}", base.course_number)
    return result, choice
