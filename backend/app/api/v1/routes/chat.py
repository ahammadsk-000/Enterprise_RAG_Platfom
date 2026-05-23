"""Conversation + message endpoints (non-streaming; WS streaming in api/ws/chat.py)."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends

from fastapi import status
from pydantic import BaseModel, Field

from app.api.deps import ChatServiceDep, CurrentPrincipal, require_permission
from app.domains.chat.schemas import (
    ChatRequest,
    ChatResponse,
    ConversationCreate,
    ConversationRead,
    MessageRead,
)
from app.domains.identity.permissions import Permission

router = APIRouter()


class ConversationRename(BaseModel):
    title: str = Field(min_length=1, max_length=512)


@router.post(
    "/conversations",
    response_model=ConversationRead,
    dependencies=[Depends(require_permission(Permission.CHAT_WRITE))],
)
async def create_conversation(
    data: ConversationCreate, principal: CurrentPrincipal, service: ChatServiceDep
) -> ConversationRead:
    assert principal.organization_id is not None
    convo = await service.create_conversation(
        organization_id=principal.organization_id, user_id=principal.user_id, data=data
    )
    return ConversationRead.model_validate(convo)


@router.get(
    "/conversations",
    response_model=list[ConversationRead],
    dependencies=[Depends(require_permission(Permission.CHAT_READ))],
)
async def list_conversations(principal: CurrentPrincipal, service: ChatServiceDep) -> list[ConversationRead]:
    assert principal.organization_id is not None
    convos = await service.list_conversations(principal.organization_id, principal.user_id)
    return [ConversationRead.model_validate(c) for c in convos]


@router.get(
    "/conversations/{conversation_id}/messages",
    response_model=list[MessageRead],
    dependencies=[Depends(require_permission(Permission.CHAT_READ))],
)
async def list_messages(
    conversation_id: uuid.UUID, principal: CurrentPrincipal, service: ChatServiceDep
) -> list[MessageRead]:
    assert principal.organization_id is not None
    msgs = await service.list_messages(conversation_id, principal.organization_id)
    return [MessageRead.model_validate(m) for m in msgs]


@router.post(
    "/conversations/{conversation_id}/messages",
    response_model=ChatResponse,
    dependencies=[Depends(require_permission(Permission.CHAT_WRITE))],
)
async def send_message(
    conversation_id: uuid.UUID, req: ChatRequest, principal: CurrentPrincipal, service: ChatServiceDep
) -> ChatResponse:
    assert principal.organization_id is not None
    conversation = await service.get_conversation(conversation_id, principal.organization_id)
    return await service.answer(conversation=conversation, user_id=principal.user_id, req=req)


@router.patch(
    "/conversations/{conversation_id}",
    response_model=ConversationRead,
    dependencies=[Depends(require_permission(Permission.CHAT_WRITE))],
)
async def rename_conversation(
    conversation_id: uuid.UUID, body: ConversationRename, principal: CurrentPrincipal, service: ChatServiceDep
) -> ConversationRead:
    assert principal.organization_id is not None
    convo = await service.rename_conversation(
        conversation_id, principal.organization_id, principal.user_id, body.title
    )
    return ConversationRead.model_validate(convo)


@router.delete(
    "/conversations/{conversation_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_permission(Permission.CHAT_WRITE))],
)
async def delete_conversation(
    conversation_id: uuid.UUID, principal: CurrentPrincipal, service: ChatServiceDep
) -> None:
    assert principal.organization_id is not None
    await service.delete_conversation(conversation_id, principal.organization_id, principal.user_id)
