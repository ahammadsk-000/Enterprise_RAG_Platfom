"""AI writing assistance — inline autocomplete (Tier C).

Returns a short continuation of the user's text from the configured LLM. Real
suggestions require a live LLM (Ollama/full stack); in demo mode the deterministic
fake provider returns a stub continuation.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.api.deps import require_permission
from app.domains.identity.permissions import Permission
from app.integrations.llm.base import ChatMessage, LLMProvider
from app.integrations.llm.factory import get_llm_provider

router = APIRouter()

_SYSTEM = (
    "You are an inline writing autocomplete. Continue the user's text with a short, "
    "natural continuation (a few words up to one sentence). Output ONLY the text that "
    "should directly follow — no quotes, no preamble, no explanation."
)


class CompleteRequest(BaseModel):
    prefix: str = Field(min_length=1, max_length=8000)
    language: str | None = None


class CompleteResponse(BaseModel):
    completion: str


@router.post(
    "/complete",
    response_model=CompleteResponse,
    dependencies=[Depends(require_permission(Permission.CHAT_WRITE))],
)
async def complete(
    req: CompleteRequest, llm: Annotated[LLMProvider, Depends(get_llm_provider)]
) -> CompleteResponse:
    result = await llm.generate(
        [
            ChatMessage(role="system", content=_SYSTEM),
            ChatMessage(role="user", content=req.prefix[-4000:]),
        ],
        temperature=0.2,
        max_tokens=48,
    )
    # Keep it inline-friendly: first line, length-capped.
    completion = result.text.strip().splitlines()[0][:200] if result.text.strip() else ""
    return CompleteResponse(completion=completion)
