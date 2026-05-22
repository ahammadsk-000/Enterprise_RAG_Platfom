"""Object-storage provider selection.

Returns an `InMemoryObjectStorage` for the test environment and `S3ObjectStorage`
otherwise. Cached per process so the boto3 client is reused.
"""

from __future__ import annotations

from functools import lru_cache

from app.core.config import get_settings
from app.integrations.storage.base import ObjectStorage


@lru_cache(maxsize=1)
def get_object_storage() -> ObjectStorage:
    settings = get_settings()
    if settings.environment == "test":
        from app.integrations.storage.memory import InMemoryObjectStorage

        return InMemoryObjectStorage()

    from app.integrations.storage.s3 import S3ObjectStorage

    return S3ObjectStorage(settings.storage)
