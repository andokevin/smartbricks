"""Module E — tournée des interventions sur site (voyageur de commerce, n°30).

Ville de départ, par ordre de priorité :
1. la ville du freelance demandé (`freelancer_id`) ;
2. sinon celle du freelance à qui le planning a confié le plus de tâches sur site ;
3. sinon la ville de base du projet ; 4. sinon le premier site.
Les sites sont visités dans l'ordre optimal ; on compare avec l'ordre saisi par le client.
"""

from collections import Counter
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.algorithms.formatting import format_ar
from app.algorithms.geo import distance_matrix, travel_cost_mga, travel_hours
from app.algorithms.solver_selector import solve_tour
from app.algorithms.tsp import tour_length
from app.errors import AppError, conflict
from app.models import City, Project, TourRun
from app.schemas import TourIn
from app.services.project_data import load_freelancers, load_sites, load_tasks


async def latest_tour_run(session: AsyncSession, project: Project) -> dict[str, Any]:
    """Dernière tournée VALIDÉE (POST /tour), telle qu'enregistrée ; 404 si aucune."""
    run = await session.scalar(
        select(TourRun).where(TourRun.project_id == project.id).order_by(TourRun.id.desc()).limit(1)
    )
    if run is None:
        raise AppError(404, "Aucune tournée validée pour ce projet.")
    technician = None
    if run.freelancer_id is not None:
        found = await load_freelancers(session, [run.freelancer_id])
        if found:
            technician = {"id": found[0].id, "name": found[0].user.name, "city": found[0].city.name}
    return {
        "id": run.id,
        "method": run.method,
        "order": list(run.order),
        "distance_km": run.distance_km,
        "cost_mga": run.cost_mga,
        "technician": technician,
        "created_at": run.created_at.isoformat(),
    }


async def compute_tour(session: AsyncSession, project: Project, data: TourIn, persist: bool = True) -> dict[str, Any]:
    """Calcule la tournée. `persist=False` (GET) : aperçu, rien n'est enregistré dans tour_runs."""
    sites = [s.city for s in await load_sites(session, project.id)]
    if not sites:
        raise conflict("Ce projet ne demande aucune intervention sur site.")

    freelancer_id = data.freelancer_id
    if freelancer_id is None:
        on_site = [t for t in await load_tasks(session, project.id) if t.on_site_city_id and t.assigned_freelancer_id]
        if on_site:
            freelancer_id = Counter(t.assigned_freelancer_id for t in on_site).most_common(1)[0][0]

    technician: dict[str, Any] | None = None
    start: City
    if freelancer_id is not None:
        found = await load_freelancers(session, [freelancer_id])
        if not found:
            raise AppError(404, "Freelance introuvable.")
        start = found[0].city
        technician = {"id": found[0].id, "name": found[0].user.name, "city": start.name}
        start_reason = f"ville de {found[0].user.name}"
    elif project.base_city is not None:
        start, start_reason = project.base_city, "ville de base du projet"
    else:
        start, start_reason = sites[0], "premier site saisi"

    nodes = [start] + [c for c in sites if c.id != start.id]  # nœud 0 = départ
    matrix = distance_matrix([(c.latitude, c.longitude) for c in nodes])
    tour = solve_tour(matrix, closed=data.closed)
    entered = tour_length(matrix, list(range(len(nodes))), data.closed)  # ordre saisi par le client

    order = [nodes[i] for i in tour.order]
    path = order + ([order[0]] if data.closed and len(order) > 1 else [])
    legs = [
        {"from": a.name, "to": b.name, "km": round(matrix[nodes.index(a)][nodes.index(b)], 1)}
        for a, b in zip(path, path[1:])
    ]
    km = tour.length
    cost = travel_cost_mga(km, data.cost_per_km)
    gain_km = max(0.0, entered - km)

    if persist:
        session.add(TourRun(project_id=project.id, freelancer_id=freelancer_id, method=tour.choice.method,
                            order=[c.name for c in order], distance_km=round(km, 1), cost_mga=cost))
        await session.commit()

    return {
        "saved": persist,
        "algorithm": {"number": 30, "name": "Voyageur de commerce"},
        "method": tour.choice.__dict__,
        "technician": technician,
        "start": {"name": start.name, "reason": start_reason},
        "closed": data.closed,
        "order": [{"step": k + 1, "name": c.name, "latitude": c.latitude, "longitude": c.longitude}
                  for k, c in enumerate(order)],
        "legs": legs,
        "distance_km": round(km, 1),
        "cost_mga": cost,
        "duration_h": round(travel_hours(km), 1),
        "cost_per_km": data.cost_per_km,
        "entered_order": [c.name for c in nodes],
        "entered_distance_km": round(entered, 1),
        "gain_km": round(gain_km, 1),
        "gain_mga": travel_cost_mga(gain_km, data.cost_per_km),
        "message": (
            f"Tournée de {round(km)} km ({format_ar(cost)}) contre {round(entered)} km dans l'ordre saisi : "
            f"{round(gain_km)} km économisés."
        ),
    }
