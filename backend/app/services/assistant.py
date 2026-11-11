"""Module A — conversation avec le copilote, enregistrée en base, puis création du projet.

Déroulé : POST /assistant/chat (plusieurs fois) → quand le copilote est prêt, le brouillon est
extrait et contrôlé → le client le relit et le corrige → POST /assistant/confirm crée le projet.
"""

from datetime import date
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.algorithms.calendar import next_monday
from app.errors import AppError, conflict, not_found
from app.llm.base import LLMError, LLMUnavailable, Message
from app.llm.draft import Draft
from app.models import AssistantConversation, AssistantMessage, City, Role, Skill, User
from app.schemas import ChatIn, ChatOut, ConfirmIn, ConfirmOut, ConversationOut, MessageOut
from app.services.copilot import DraftError, converse, extract_draft, validate_draft
from app.services.llm_usage import get_provider
from app.services.project_builder import create_project_from_draft


async def _known(session: AsyncSession) -> tuple[list[str], list[str]]:
    skills = list((await session.scalars(select(Skill.name).order_by(Skill.id))).all())
    cities = list((await session.scalars(select(City.name).order_by(City.id))).all())
    return skills, cities


async def _conversation(session: AsyncSession, conversation_id: int, user: User) -> AssistantConversation:
    conv = await session.scalar(
        select(AssistantConversation)
        .where(AssistantConversation.id == conversation_id)
        .options(selectinload(AssistantConversation.messages))
    )
    if conv is None:
        raise not_found("Conversation")
    if conv.user_id != user.id and user.role != Role.ADMIN:
        raise AppError(403, "Cette conversation appartient à un autre utilisateur.")
    return conv


def _stored_draft(conv: AssistantConversation) -> tuple[Draft | None, list[str]]:
    if not conv.draft:
        return None, []
    return Draft.model_validate(conv.draft["draft"]), list(conv.draft.get("warnings", []))


async def chat(session: AsyncSession, user: User, data: ChatIn) -> ChatOut:
    if data.conversation_id is None:
        conv = AssistantConversation(user_id=user.id, status="OPEN", messages=[])
        session.add(conv)
        await session.flush()
    else:
        conv = await _conversation(session, data.conversation_id, user)
        if conv.status == "CONFIRMED":
            raise conflict("Cette conversation a déjà donné un projet : commencez-en une nouvelle.")

    conv.messages.append(AssistantMessage(role="user", content=data.message))
    history: list[Message] = [{"role": m.role, "content": m.content} for m in conv.messages]  # type: ignore[misc]
    provider = await get_provider(session)
    try:
        turn = await converse(provider, history)
    except LLMUnavailable as e:
        raise AppError(503, f"Le copilote est momentanément indisponible : {e}") from e
    except LLMError as e:
        raise AppError(502, f"Réponse du copilote inexploitable : {e}") from e
    conv.messages.append(AssistantMessage(role="assistant", content=turn.reply))

    draft: Draft | None = None
    warnings: list[str] = []
    if turn.ready:
        history.append({"role": "assistant", "content": turn.reply})
        skills, cities = await _known(session)
        try:
            result = await extract_draft(provider, history, skills, cities, date.today())
        except (DraftError, LLMError) as e:
            await session.commit()  # on garde la conversation
            raise AppError(422, f"Le brouillon n'a pas pu être extrait : {e}") from e
        draft, warnings = result.draft, result.warnings
        conv.draft = {"draft": draft.model_dump(mode="json"), "warnings": warnings}
        conv.status = "DRAFT_READY"
    await session.commit()
    return ChatOut(conversation_id=conv.id, reply=turn.reply, ready=turn.ready, draft=draft, warnings=warnings,
                   provider=provider.name, fallback_reason=provider.fallback_reason)


async def get_conversation(session: AsyncSession, user: User, conversation_id: int) -> ConversationOut:
    conv = await _conversation(session, conversation_id, user)
    draft, warnings = _stored_draft(conv)
    return ConversationOut(id=conv.id, status=conv.status, project_id=conv.project_id,
                           messages=[MessageOut(role=m.role, content=m.content) for m in conv.messages],
                           draft=draft, warnings=warnings)


async def project_conversation(session: AsyncSession, user: User, project_id: int) -> ConversationOut:
    """Conversation qui a donné naissance à un projet (404 pour un projet créé par le seed)."""
    conv_id = await session.scalar(
        select(AssistantConversation.id)
        .where(AssistantConversation.project_id == project_id)
        .order_by(AssistantConversation.id.desc())
        .limit(1)
    )
    if conv_id is None:
        raise not_found("Conversation de ce projet")
    return await get_conversation(session, user, conv_id)


async def confirm(session: AsyncSession, user: User, data: ConfirmIn) -> ConfirmOut:
    conv = await _conversation(session, data.conversation_id, user)
    if conv.status == "CONFIRMED":
        raise conflict(f"Projet déjà créé (n°{conv.project_id}).")
    skills, cities = await _known(session)
    if data.draft is not None:  # brouillon corrigé par le client : on refait TOUS les contrôles
        try:
            draft, warnings = validate_draft(data.draft.model_dump(mode="json"), skills, cities)
        except DraftError as e:
            raise AppError(422, str(e)) from e
    else:
        stored, warnings = _stored_draft(conv)
        if stored is None:
            raise conflict("Le brouillon n'est pas encore prêt : poursuivez la conversation.")
        draft = stored

    start = next_monday(date.today())
    if draft.project.deadline <= start:
        raise AppError(422, f"La date limite ({draft.project.deadline}) doit être après le début du projet ({start}).")
    raw: dict[str, Any] = draft.model_dump(mode="json")
    project = await create_project_from_draft(session, user.id, raw, start)
    conv.project_id, conv.status = project.id, "CONFIRMED"
    conv.draft = {"draft": raw, "warnings": warnings}
    await session.commit()
    return ConfirmOut(project_id=project.id, title=project.title, features=len(draft.features),
                      tasks=len(draft.tasks), sites=draft.sites, warnings=warnings)
