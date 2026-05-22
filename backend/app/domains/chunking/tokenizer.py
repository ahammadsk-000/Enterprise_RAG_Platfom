"""Lightweight token estimation.

Uses tiktoken when available for accurate counts; otherwise falls back to a
~4-chars-per-token heuristic. Kept dependency-optional so the default path needs no
extra package.
"""

from __future__ import annotations

from functools import lru_cache


@lru_cache(maxsize=1)
def _encoder():  # type: ignore[no-untyped-def]
    try:
        import tiktoken  # noqa: PLC0415

        return tiktoken.get_encoding("cl100k_base")
    except Exception:  # noqa: BLE001 - tiktoken not installed / model unavailable
        return None


def estimate_tokens(text: str) -> int:
    enc = _encoder()
    if enc is not None:
        return len(enc.encode(text))
    return max(1, len(text) // 4)
