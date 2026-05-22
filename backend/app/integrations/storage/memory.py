"""In-memory object storage for tests and local development."""

from __future__ import annotations

from app.core.exceptions import NotFoundError


class InMemoryObjectStorage:
    def __init__(self) -> None:
        self._store: dict[str, bytes] = {}

    async def put_object(self, key: str, data: bytes, content_type: str) -> None:
        self._store[key] = data

    async def get_object(self, key: str) -> bytes:
        if key not in self._store:
            raise NotFoundError(f"Object not found: {key}")
        return self._store[key]

    async def delete_object(self, key: str) -> None:
        self._store.pop(key, None)

    async def generate_presigned_url(self, key: str, expires_in: int = 3600) -> str:
        return f"memory://{key}"
