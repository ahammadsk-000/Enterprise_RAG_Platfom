"""S3 / MinIO object storage (boto3).

boto3 is imported lazily so the module loads without the dependency present.
Blocking SDK calls run in a worker thread via `asyncio.to_thread`.
"""

from __future__ import annotations

import asyncio
from typing import Any

from app.core.config import StorageSettings
from app.core.exceptions import NotFoundError, ProviderError


class S3ObjectStorage:
    def __init__(self, settings: StorageSettings) -> None:
        self._settings = settings
        self._bucket = settings.bucket
        self._client = self._build_client(settings)

    @staticmethod
    def _build_client(settings: StorageSettings) -> Any:
        try:
            import boto3  # noqa: PLC0415 - lazy optional dependency
        except ImportError as exc:  # pragma: no cover
            raise ProviderError("boto3 is not installed; cannot use S3 storage.") from exc
        return boto3.client(
            "s3",
            endpoint_url=settings.endpoint_url,
            aws_access_key_id=settings.access_key,
            aws_secret_access_key=settings.secret_key,
            region_name=settings.region,
            use_ssl=settings.secure,
        )

    async def put_object(self, key: str, data: bytes, content_type: str) -> None:
        await asyncio.to_thread(
            self._client.put_object, Bucket=self._bucket, Key=key, Body=data, ContentType=content_type
        )

    async def get_object(self, key: str) -> bytes:
        def _get() -> bytes:
            try:
                resp = self._client.get_object(Bucket=self._bucket, Key=key)
            except self._client.exceptions.NoSuchKey as exc:
                raise NotFoundError(f"Object not found: {key}") from exc
            return resp["Body"].read()

        return await asyncio.to_thread(_get)

    async def delete_object(self, key: str) -> None:
        await asyncio.to_thread(self._client.delete_object, Bucket=self._bucket, Key=key)

    async def generate_presigned_url(self, key: str, expires_in: int = 3600) -> str:
        return await asyncio.to_thread(
            self._client.generate_presigned_url,
            "get_object",
            Params={"Bucket": self._bucket, "Key": key},
            ExpiresIn=expires_in,
        )
