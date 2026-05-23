"""Prompt construction for citation-grounded generation.

The system prompt constrains the model to answer ONLY from the supplied context and
to cite each claim with bracketed source markers ``[n]`` that map to the numbered
context blocks. This is the core of hallucination reduction + answer grounding.
"""

from __future__ import annotations

from app.domains.retrieval.schemas import RetrievedChunk
from app.integrations.llm.base import ChatMessage

SYSTEM_PROMPT = (
    "You are an enterprise knowledge assistant. Answer the user's question using ONLY "
    "the numbered sources provided. Cite every claim with bracketed markers like [1] or "
    "[2][3] that refer to the source numbers. If the sources do not contain the answer, "
    "say you don't have enough information — do not invent facts. Be concise and factual."
)


def build_context(chunks: list[RetrievedChunk]) -> str:
    blocks = []
    for i, chunk in enumerate(chunks, start=1):
        loc = f" (page {chunk.page_from})" if chunk.page_from else ""
        blocks.append(f"[{i}] Source {chunk.document_id}{loc}:\n{chunk.content}")
    return "\n\n".join(blocks)


def build_messages(question: str, chunks: list[RetrievedChunk]) -> list[ChatMessage]:
    context = build_context(chunks) or "(no sources found)"
    user = f"Sources:\n{context}\n\nQuestion: {question}\n\nAnswer with citations:"
    return [
        ChatMessage(role="system", content=SYSTEM_PROMPT),
        ChatMessage(role="user", content=user),
    ]
