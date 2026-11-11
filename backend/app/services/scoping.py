"""Module B — cadrage du sprint 1 : lien entre la base et le sac à dos multidimensionnel (n°29)."""

from sqlalchemy.ext.asyncio import AsyncSession

from app.algorithms.knapsack_md import Item, KnapsackSolution, explain_exclusions, verify_selection, what_if
from app.algorithms.solver_selector import solve_knapsack
from app.errors import AppError, conflict
from app.models import Feature, Project, ProjectStatus
from app.schemas import MethodOut, ScopeFeature, ScopeOut, WhatIfOut
from app.services.project_data import load_features


def to_items(features: list[Feature]) -> list[Item]:
    ids = {f.id for f in features}
    return [
        Item(
            id=f.id,
            name=f.title,
            value=f.business_value,
            cost=f.estimated_cost_mga,
            hours=f.estimated_hours,
            mandatory=f.is_mandatory,
            depends_on=tuple(d for d in f.depends_on_feature_ids if d in ids),
        )
        for f in features
    ]


async def run_scope(session: AsyncSession, project: Project) -> ScopeOut:
    features = await load_features(session, project.id)
    if not features:
        raise conflict("Ce projet n'a aucune fonctionnalité.")
    items = to_items(features)
    budget, hours = project.budget_mga, project.budget_hours

    solution, choice = solve_knapsack(items, budget, hours)
    selected = set(solution.selected)
    violations = verify_selection(items, solution.selected, budget, hours) if solution.feasible else []
    if violations:  # ne devrait jamais arriver : la vérification indépendante bloque tout résultat faux
        raise AppError(500, "Résultat du sac à dos refusé par la vérification : " + " ".join(violations))

    reasons = explain_exclusions(items, solution, budget, hours)
    scenarios = what_if(items, budget, hours)
    refs = {f.id: f.ref for f in features}

    for f in features:
        f.selected_for_sprint = f.id in selected
    project.status = ProjectStatus.SCOPED if solution.feasible else ProjectStatus.DRAFT

    out = ScopeOut(
        feasible=solution.feasible,
        message=solution.message,
        method=MethodOut(**choice.__dict__),
        optimal=solution.optimal,
        nodes=solution.nodes,
        elapsed_ms=round(solution.elapsed_ms, 2),
        total_value=solution.total_value,
        total_cost_mga=solution.total_cost,
        total_hours=solution.total_hours,
        budget_mga=budget,
        budget_hours=hours,
        budget_usage=round(solution.total_cost / budget, 4) if budget else 0.0,
        hours_usage=round(solution.total_hours / hours, 4) if hours else 0.0,
        missing_cost_mga=solution.missing_cost,
        missing_hours=solution.missing_hours,
        features=[
            ScopeFeature(
                id=f.id, ref=f.ref, title=f.title, business_value=f.business_value,
                estimated_hours=f.estimated_hours, estimated_cost_mga=f.estimated_cost_mga,
                is_mandatory=f.is_mandatory, depends_on=[refs[d] for d in f.depends_on_feature_ids if d in refs],
                selected=f.id in selected, reason=reasons.get(f.id),
            )
            for f in features
        ],
        what_if=[
            WhatIfOut(
                increase_pct=round(s.increase * 100), extra_budget_mga=s.extra_budget, new_budget_mga=s.new_budget,
                added=[refs[i] for i in s.added], removed=[refs[i] for i in s.removed],  # type: ignore[index]
                value_gain=s.value_gain, message=s.message,
            )
            for s in scenarios
        ],
        verification=violations,
    )
    # On fige le rapport complet : les coûts seront recalculés au choix de l'équipe, mais l'écran
    # Périmètre et l'explication doivent montrer le cadrage tel qu'il a été présenté au client.
    project.scope_report = out.model_dump(mode="json")
    await session.commit()
    return out


def stored_scope(project: Project) -> ScopeOut:
    """Dernier cadrage calculé, relu sans rien recalculer (GET /projects/{id}/scope)."""
    if not project.scope_report or "features" not in project.scope_report:
        raise AppError(404, "Aucun cadrage calculé pour ce projet : lancez-le (POST /projects/{id}/scope).")
    return ScopeOut.model_validate(project.scope_report)


def sprint_summary(features: list[Feature], solution: KnapsackSolution | None = None) -> dict[str, object]:
    """Résumé du sprint retenu (pour l'explication)."""
    chosen = [f for f in features if f.selected_for_sprint]
    return {
        "retenues": [f.title for f in chosen],
        "valeur": sum(f.business_value for f in chosen),
        "cout_mga": sum(f.estimated_cost_mga for f in chosen),
        "heures": sum(f.estimated_hours for f in chosen),
    }
