"""Query expansion.

The default expander is identity (returns the original query). An optional
LLM-backed multi-query/HyDE expander can be layered in by passing an `LLMProvider`;
it generates paraphrases to widen recall. Kept dependency-light and opt-in so the
default retrieval path makes no extra LLM calls.
"""

from __future__ import annotations

from app.integrations.llm.base import ChatMessage, LLMProvider

_MULTI_QUERY_PROMPT = (
    "Generate {n} alternative search queries that capture the same intent as the "
    "user question. Return one query per line, no numbering.\n\nQuestion: {q}"
)


class QueryExpander:
    def expand(self, query: str) -> list[str]:
        return [query]


class LLMMultiQueryExpander:
    def __init__(self, llm: LLMProvider, *, variants: int = 2) -> None:
        self._llm = llm
        self._variants = variants

    async def expand_async(self, query: str) -> list[str]:
        prompt = _MULTI_QUERY_PROMPT.format(n=self._variants, q=query)
        result = await self._llm.generate([ChatMessage(role="user", content=prompt)], temperature=0.3)
        extra = [line.strip() for line in result.text.splitlines() if line.strip()]
        return [query, *extra[: self._variants]]
