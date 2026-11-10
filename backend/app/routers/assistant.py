"""Module A — copilote : dialogue, brouillon, confirmation."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.models import User
from app.schemas import ChatIn, ChatOut, ConfirmIn, ConfirmOut, ConversationOut
from app.security import get_current_user
from app.services import assistant

router = APIRouter(prefix="/assistant", tags=["A · copilote (n°33)"])


@router.post("/chat", response_model=ChatOut)
async def chat(data: ChatIn, session: AsyncSession = Depends(get_session),
               user: User = Depends(get_current_user)) -> ChatOut:
    """Envoie un message au copilote. Laissez `conversation_id` vide pour commencer.

    Quand le copilote a assez d'informations (`ready: true`), la réponse contient le brouillon
    extrait et contrôlé (`draft`) et les corrections automatiques (`warnings`).
    """
    return await assistant.chat(session, user, data)


@router.get("/conversations/{conversation_id}", response_model=ConversationOut)
async def conversation(conversation_id: int, session: AsyncSession = Depends(get_session),
                       user: User = Depends(get_current_user)) -> ConversationOut:
    return await assistant.get_conversation(session, user, conversation_id)


@router.post("/confirm", response_model=ConfirmOut, status_code=201)
async def confirm(data: ConfirmIn, session: AsyncSession = Depends(get_session),
                  user: User = Depends(get_current_user)) -> ConfirmOut:
    """Crée le projet, ses fonctionnalités, ses tâches et ses sites à partir du brouillon
    (éventuellement corrigé par le client : il est alors entièrement revérifié)."""
    return await assistant.confirm(session, user, data)
