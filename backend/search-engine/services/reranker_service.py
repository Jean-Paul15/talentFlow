# Reranker cross-encoder (optionnel)
# Améliore la précision sur un top-k de candidats issus du retrieval.

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

from loguru import logger

try:
    from sentence_transformers import CrossEncoder
except Exception:  # pragma: no cover - optional heavy dependency path
    CrossEncoder = None  # type: ignore


def _env_flag(name: str, default: bool = False) -> bool:
    return str(os.getenv(name, "true" if default else "false")).strip().lower() in {
        "1", "true", "yes", "on"
    }


class RerankerService:
    """
    Cross-encoder reranker sur les résultats de recherche.
    - désactivé par défaut pour limiter la charge CPU
    - activable via env / requête API
    """

    def __init__(self):
        self.enabled_by_default = _env_flag("RERANK_ENABLED", False)
        self.model_name = os.getenv("RERANK_MODEL", "BAAI/bge-reranker-base")
        self.top_k_default = int(os.getenv("RERANK_TOP_K", "50"))
        self.max_candidates = int(os.getenv("RERANK_MAX_CANDIDATES", "100"))
        self.batch_size = int(os.getenv("RERANK_BATCH_SIZE", "16"))
        self.blend_alpha = float(os.getenv("RERANK_BLEND_ALPHA", "0.75"))
        self.min_query_tokens = int(os.getenv("RERANK_MIN_QUERY_TOKENS", "2"))
        self.max_text_chars = int(os.getenv("RERANK_MAX_TEXT_CHARS", "12000"))
        self.min_raw_score_spread = float(os.getenv("RERANK_MIN_RAW_SCORE_SPREAD", "0.05"))
        self._model = None
        self._load_attempted = False

    def is_available(self, *, load: bool = True) -> bool:
        if load:
            self._ensure_model_loaded()
        return self._model is not None

    def should_rerank(self, request_flag: Optional[bool]) -> bool:
        if request_flag is None:
            return self.enabled_by_default
        return bool(request_flag)

    def rerank(
        self,
        *,
        query: str,
        results: List[Dict[str, Any]],
        top_k: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        if not results:
            return results
        if len([t for t in str(query or "").strip().split() if t]) < self.min_query_tokens:
            return results
        self._ensure_model_loaded()
        if self._model is None:
            return results

        top_k_eff = max(1, min(int(top_k or self.top_k_default), self.max_candidates, len(results)))
        head = list(results[:top_k_eff])
        tail = list(results[top_k_eff:])

        pairs = []
        for row in head:
            doc_text = self._build_rerank_text(row)
            pairs.append((query, doc_text))

        try:
            scores = self._model.predict(pairs, batch_size=self.batch_size, show_progress_bar=False)
        except TypeError:
            # Older sentence-transformers versions may not accept show_progress_bar
            scores = self._model.predict(pairs, batch_size=self.batch_size)
        except Exception as err:
            logger.warning(f"Reranker predict failed: {err}")
            return results

        for row, score in zip(head, scores):
            # Preserve retrieval score for observability.
            if "base_score" not in row:
                row["base_score"] = row.get("score")
            try:
                row["rerank_score_raw"] = float(score)
            except Exception:
                row["rerank_score_raw"] = None

        raw_scores = [
            float(r["rerank_score_raw"])
            for r in head
            if r.get("rerank_score_raw") is not None
        ]
        if len(raw_scores) >= 2:
            spread = max(raw_scores) - min(raw_scores)
            if spread < self.min_raw_score_spread:
                # Signal trop faible: on conserve l'ordre retrieval.
                for row in head:
                    row["rerank_score"] = None
                return head + tail

        rerank_norm = _minmax_normalize(
            [r.get("rerank_score_raw") for r in head]
        )
        base_norm = _minmax_normalize(
            [r.get("base_score") for r in head]
        )
        alpha = min(max(self.blend_alpha, 0.0), 1.0)
        for row, rrn, bsn in zip(head, rerank_norm, base_norm):
            if row.get("rerank_score_raw") is None:
                row["rerank_score"] = None
                continue
            blended = (alpha * rrn) + ((1.0 - alpha) * bsn)
            row["rerank_score"] = float(blended)

        head.sort(
            key=lambda r: (
                float(r.get("rerank_score") if r.get("rerank_score") is not None else -1e9),
                float(r.get("base_score") or 0.0),
            ),
            reverse=True,
        )

        # Expose final score as rerank score when available (API clients already sort by score visually).
        for row in head:
            if row.get("rerank_score") is not None:
                row["score"] = float(row["rerank_score"])

        return head + tail

    def _build_rerank_text(self, row: Dict[str, Any]) -> str:
        if row.get("_rerank_text"):
            return str(row["_rerank_text"])[: self.max_text_chars]
        description_full = row.get("_description_full") or row.get("description") or ""
        parts = [
            row.get("title") or "",
            row.get("company") or "",
            row.get("location") or "",
            row.get("contract_type") or "",
            " ".join(row.get("hard_skills") or []),
            " ".join(row.get("soft_skills") or []),
            description_full,
        ]
        text = " | ".join([str(p).strip() for p in parts if str(p).strip()])
        return text[: self.max_text_chars]

    def _ensure_model_loaded(self) -> None:
        if self._load_attempted:
            return
        self._load_attempted = True
        if CrossEncoder is None:
            logger.warning("Reranker indisponible: CrossEncoder non importable")
            return
        try:
            logger.info(f"Chargement reranker: {self.model_name}")
            self._model = CrossEncoder(self.model_name)
            logger.info("✓ Reranker charge")
        except Exception as err:
            logger.warning(f"Reranker non charge ({self.model_name}): {err}")
            self._model = None


def _minmax_normalize(values: List[Optional[float]]) -> List[float]:
    usable = [float(v) for v in values if v is not None]
    if not usable:
        return [0.0 for _ in values]
    vmin = min(usable)
    vmax = max(usable)
    if vmax - vmin <= 1e-12:
        return [0.5 if v is not None else 0.0 for v in values]
    out: List[float] = []
    for v in values:
        if v is None:
            out.append(0.0)
        else:
            out.append((float(v) - vmin) / (vmax - vmin))
    return out
