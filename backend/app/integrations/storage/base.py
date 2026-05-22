"""Object storage interface.

Implementations: `S3ObjectStorage` (S3/MinIO, production) and `InMemoryObjectStorage`
(tests/dev). All methods are async so the API/worker event loop is never blocked;
blocking SDK calls are dispatched to a thread.
"""

from __future__ import annotations

from typing import Protocol


class ObjectStorage(Protocol):
    async def put_object(self, key: str, data: bytes, content_type: str) -> None: ...
    async def get_object(self, key: str) -> bytes: ...
    async def delete_object(self, key: str) -> None: ...
    async def generate_presigned_url(self, key: str, expires_in: int = 3600) -> str: ...
