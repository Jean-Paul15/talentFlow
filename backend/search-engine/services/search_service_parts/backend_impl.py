"""Backend implementation aggregator."""

from __future__ import annotations

from services.embedding_service import EmbeddingService

from .backend_dense import QdrantBackendDenseMixin
from .backend_init import QdrantBackendInitMixin
from .backend_preview import QdrantBackendPreviewMixin
from .backend_sparse import QdrantBackendSparseMixin
from .backend_utils import _project_vectors_2d, _truncate_text


class QdrantSearchBackend(
    QdrantBackendInitMixin,
    QdrantBackendDenseMixin,
    QdrantBackendSparseMixin,
    QdrantBackendPreviewMixin,
):
    """Qdrant backend (dense vectors + payload filters)."""


__all__ = ["QdrantSearchBackend", "_project_vectors_2d", "_truncate_text"]
