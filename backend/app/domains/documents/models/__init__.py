"""Document domain ORM models (registers tables on Base.metadata)."""

from app.domains.documents.models.document import Document
from app.domains.documents.models.ingestion_job import IngestionJob

__all__ = ["Document", "IngestionJob"]
