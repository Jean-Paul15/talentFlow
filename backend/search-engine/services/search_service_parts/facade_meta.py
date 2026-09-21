"""Metadata helpers for the hybrid search facade."""

from __future__ import annotations

from typing import Any, Dict, Optional


class HybridSearchServiceMetaMixin:
    def vector_preview(
        self,
        *,
        limit: int = 120,
        source_name: Optional[str] = None,
        country: Optional[str] = None,
    ) -> Dict[str, Any]:
        if not hasattr(self.backend, "sample_vectors"):
            raise RuntimeError(f"Backend '{self.backend_name}' ne supporte pas la previsualisation vectorielle")
        return self.backend.sample_vectors(limit=limit, source_name=source_name, country=country)

    def health(self) -> Dict[str, Any]:
        data = self.backend.health()
        data["reranker_available"] = self.reranker.is_available(load=False)
        data["reranker_loaded"] = bool(getattr(self.reranker, "_model", None))
        data["reranker_enabled_default"] = self.reranker.enabled_by_default
        data["reranker_model"] = self.reranker.model_name
        return data
