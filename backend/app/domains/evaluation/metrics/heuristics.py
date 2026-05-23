"""Heuristic RAG evaluation metrics (deterministic, dependency-free).

Lexical-overlap approximations of the standard RAG metrics. They need no LLM or
external eval library, so they run in CI as fast regression gates. An LLM/RAGAS-based
metric set can be plugged in behind the same `evaluate_sample` contract for higher
fidelity.

- faithfulness     — fraction of answer content grounded in the retrieved contexts
- answer_relevancy — overlap between the answer and the question intent
- context_precision— fraction of retrieved contexts that are relevant
- context_recall   — fraction of the ground-truth answer covered by the contexts
- hallucination    — 1 − faithfulness
"""

from __future__ import annotations

import re

_TOKEN_RE = re.compile(r"[a-z0-9]+")
_STOPWORDS = {
    "the", "a", "an", "is", "are", "was", "were", "of", "to", "in", "on", "and", "or",
    "for", "with", "as", "by", "at", "be", "this", "that", "it", "from", "what", "which",
    "who", "how", "when", "where", "why", "i", "you", "based", "provided", "sources", "here",
}


def _tokens(text: str) -> set[str]:
    return {t for t in _TOKEN_RE.findall(text.lower()) if t not in _STOPWORDS and len(t) > 1}


def _coverage(target: set[str], source: set[str]) -> float:
    return len(target & source) / len(target) if target else 0.0


def faithfulness(answer: str, contexts: list[str]) -> float:
    ctx = set().union(*(_tokens(c) for c in contexts)) if contexts else set()
    return round(_coverage(_tokens(answer), ctx), 3)


def answer_relevancy(question: str, answer: str) -> float:
    return round(_coverage(_tokens(question), _tokens(answer)), 3)


def context_precision(reference: str, contexts: list[str], *, threshold: float = 0.1) -> float:
    if not contexts:
        return 0.0
    ref = _tokens(reference)
    relevant = sum(1 for c in contexts if _coverage(ref, _tokens(c)) >= threshold)
    return round(relevant / len(contexts), 3)


def context_recall(ground_truth: str, contexts: list[str]) -> float:
    ctx = set().union(*(_tokens(c) for c in contexts)) if contexts else set()
    return round(_coverage(_tokens(ground_truth), ctx), 3)


def evaluate_sample(
    *, question: str, answer: str, contexts: list[str], ground_truth: str | None
) -> dict[str, float]:
    faith = faithfulness(answer, contexts)
    scores = {
        "faithfulness": faith,
        "answer_relevancy": answer_relevancy(question, answer),
        "context_precision": context_precision(ground_truth or question, contexts),
        "hallucination": round(1.0 - faith, 3),
    }
    if ground_truth:
        scores["context_recall"] = context_recall(ground_truth, contexts)
    return scores
