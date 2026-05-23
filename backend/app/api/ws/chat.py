"""WebSocket streaming chat endpoint.

Client connects to `/api/v1/ws/chat/{conversation_id}?token=<access_token>` and sends
JSON `{ "query": "...", "top_k": 6, ... }` messages. The server streams events:
`{type: "token", content}` …then `{type: "done", message_id, citations, confidence}`.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.api.deps import build_chat_service, get_auth_service
from app.core.exceptions import AppError
from app.core.logging import get_logger
from app.db.session import AsyncSessionLocal
from app.domains.chat.schemas import ChatRequest

logger = get_logger(__name__)

router = APIRouter()


@router.websocket("/chat/{conversation_id}")
async def chat_ws(websocket: WebSocket, conversation_id: uuid.UUID) -> None:
    await websocket.accept()
    token = websocket.query_params.get("token")

    async with AsyncSessionLocal() as session:
        try:
            if not token:
                raise AppError("Missing access token.")
            principal = await get_auth_service(session).principal_from_access_token(token)
            chat = build_chat_service(session)
            conversation = await chat.get_conversation(conversation_id, principal.organization_id)  # type: ignore[arg-type]
        except AppError as exc:
            await websocket.send_json({"type": "error", "detail": exc.detail})
            await websocket.close()
            return

        while True:
            try:
                payload = await websocket.receive_json()
            except WebSocketDisconnect:
                break

            try:
                req = ChatRequest(**payload)
                async for event in chat.stream_answer(
                    conversation=conversation, user_id=principal.user_id, req=req
                ):
                    await websocket.send_json(event)
            except WebSocketDisconnect:
                break
            except Exception as exc:  # noqa: BLE001 - report and keep the socket open
                logger.warning("ws.chat.error", error=str(exc))
                await websocket.send_json({"type": "error", "detail": str(exc)})
