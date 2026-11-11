"""Lecture d'un projet complet et correction d'une fonctionnalité par le client."""

import math

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.errors import AppError, not_found
from app.models import Feature, Project, ProjectStatus, Role, Task, User
from app.schemas import FeatureOut, FeaturePatch, ProjectOut, ProjectSummary, TaskOut
from app.services.costing import recompute_feature_costs
from app.services.project_data import (
    get_project,
    load_features,
    load_sites,
    load_task_dependencies,
    load_tasks,
    load_team_ids,
)


def summary(p: Project) -> ProjectSummary:
    return ProjectSummary(id=p.id, title=p.title, status=p.status, budget_mga=p.budget_mga,
                          budget_hours=p.budget_hours, start_date=p.start_date, target_deadline=p.target_deadline,
                          base_city=p.base_city.name if p.base_city else None)


async def list_projects(session: AsyncSession, user: User) -> list[ProjectSummary]:
    from sqlalchemy.orm import selectinload

    query = select(Project).options(selectinload(Project.base_city)).order_by(Project.id)
    if user.role != Role.ADMIN:
        query = query.where(Project.client_id == user.id)
    return [summary(p) for p in (await session.scalars(query)).all()]


async def project_detail(session: AsyncSession, project: Project) -> ProjectOut:
    features = await load_features(session, project.id)
    tasks = await load_tasks(session, project.id)
    deps = await load_task_dependencies(session, [t.id for t in tasks])
    f_ref = {f.id: f.ref for f in features}
    t_ref = {t.id: t.ref for t in tasks}
    return ProjectOut(
        **summary(project).model_dump(),
        description=project.description,
        features=[
            FeatureOut(id=f.id, ref=f.ref, title=f.title, description=f.description, req_type=f.req_type.value,
                       business_value=f.business_value, estimated_hours=f.estimated_hours,
                       estimated_cost_mga=f.estimated_cost_mga, is_mandatory=f.is_mandatory,
                       depends_on=[f_ref[d] for d in f.depends_on_feature_ids if d in f_ref],
                       selected_for_sprint=f.selected_for_sprint)
            for f in features
        ],
        tasks=[
            TaskOut(id=t.id, ref=t.ref, feature_ref=f_ref[t.feature_id], title=t.title,
                    required_skill=t.required_skill.name, min_level=t.min_level, estimated_hours=t.estimated_hours,
                    depends_on=[t_ref[d] for d in deps[t.id]],
                    on_site_city=t.on_site_city.name if t.on_site_city else None, status=t.status.value,
                    assigned_freelancer_id=t.assigned_freelancer_id, start_date=t.start_date, end_date=t.end_date)
            for t in tasks
        ],
        sites=[s.city.name for s in await load_sites(session, project.id)],
        team=await load_team_ids(session, project.id),
    )


async def patch_feature(session: AsyncSession, user: User, feature_id: int, data: FeaturePatch) -> FeatureOut:
    """Le client corrige la valeur, les heures ou le caractère obligatoire d'une fonctionnalité.

    Heures : les tâches de la fonctionnalité sont mises à l'échelle proportionnellement (au moins 1 h
    chacune), pour que fonctionnalité et tâches restent cohérentes ; puis les coûts sont recalculés.
    Le cadrage précédent n'est plus valable : le projet repasse en brouillon.
    """
    feature = await session.get(Feature, feature_id)
    if feature is None:
        raise not_found("Fonctionnalité")
    project = await get_project(session, feature.project_id, user)
    if data.business_value is not None:
        feature.business_value = data.business_value
    if data.is_mandatory is not None:
        feature.is_mandatory = data.is_mandatory
    if data.estimated_hours is not None:
        tasks = list((await session.scalars(select(Task).where(Task.feature_id == feature.id))).all())
        old = sum(t.estimated_hours for t in tasks)
        if tasks and old > 0:
            for t in tasks:
                t.estimated_hours = max(1, math.ceil(t.estimated_hours * data.estimated_hours / old))
            feature.estimated_hours = sum(t.estimated_hours for t in tasks)
        else:
            feature.estimated_hours = data.estimated_hours
    if not any(v is not None for v in data.model_dump().values()):
        raise AppError(422, "Rien à modifier.")

    for f in await load_features(session, project.id):
        f.selected_for_sprint = False
    project.status = ProjectStatus.DRAFT
    project.scope_report = None  # le cadrage affiché n'est plus valable
    await session.flush()
    await recompute_feature_costs(session, project.id)
    await session.commit()
    await session.refresh(feature)
    refs = {f.id: f.ref for f in await load_features(session, project.id)}
    return FeatureOut(id=feature.id, ref=feature.ref, title=feature.title, description=feature.description,
                      req_type=feature.req_type.value, business_value=feature.business_value,
                      estimated_hours=feature.estimated_hours, estimated_cost_mga=feature.estimated_cost_mga,
                      is_mandatory=feature.is_mandatory,
                      depends_on=[refs[d] for d in feature.depends_on_feature_ids if d in refs],
                      selected_for_sprint=feature.selected_for_sprint)
