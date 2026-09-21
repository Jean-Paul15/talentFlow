"""Preview and formatting helpers for the backend."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from .backend_utils import _project_vectors_2d, _truncate_text
from .filters_text import _to_plain_list


class QdrantBackendPreviewMixin:
    def sample_vectors(
        self,
        *,
        limit: int = 120,
        source_name: Optional[str] = None,
        country: Optional[str] = None,
    ) -> Dict[str, Any]:
        if self.client is None:
            raise RuntimeError("Qdrant backend indisponible")
        limit = max(10, min(int(limit or 120), 300))
        qdrant_filter = self._build_qdrant_filter({"source_name": source_name, "country": country})
        points = []
        next_offset = None
        remaining = limit
        while remaining > 0:
            batch_limit = min(remaining, 100)
            result = self.client.scroll(
                collection_name=self.collection_name,
                scroll_filter=qdrant_filter,
                limit=batch_limit,
                with_payload=True,
                with_vectors=True,
                offset=next_offset,
            )
            batch_points = result[0] if isinstance(result, tuple) else getattr(result, "points", [])
            next_offset = result[1] if isinstance(result, tuple) else getattr(result, "next_page_offset", None)
            if not batch_points:
                break
            points.extend(batch_points)
            remaining = limit - len(points)
            if next_offset is None:
                break
        dense_vectors: List[List[float]] = []
        rows: List[Dict[str, Any]] = []
        for point in points[:limit]:
            payload = getattr(point, "payload", None) or {}
            raw_vector = getattr(point, "vector", None)
            dense = raw_vector.get("dense") if isinstance(raw_vector, dict) else raw_vector
            dense = _to_plain_list(dense)
            if not dense:
                continue
            dense_vectors.append([float(v) for v in dense])
            rows.append(
                {
                    "id": str(getattr(point, "id", "") or payload.get("id") or ""),
                    "title": payload.get("title") or "",
                    "company": payload.get("company") or "",
                    "location": payload.get("location") or "",
                    "country": payload.get("country") or "",
                    "source_name": payload.get("source_name") or "",
                    "contract_type": payload.get("contract_type") or "",
                    "posted_date": payload.get("posted_date") or payload.get("posted_date_iso") or "",
                    "quality_score": payload.get("quality_score"),
                    "freshness_days": payload.get("freshness_days"),
                    "is_stale": payload.get("is_stale"),
                    "is_expired": payload.get("is_expired"),
                }
            )
        coords = _project_vectors_2d(dense_vectors)
        for row, xy in zip(rows, coords):
            row["x"] = round(float(xy[0]), 6)
            row["y"] = round(float(xy[1]), 6)
        return {
            "backend": self.name,
            "collection": self.collection_name,
            "count": len(rows),
            "points": rows,
        }

    def _format_qdrant_hit(self, hit: Any) -> Dict[str, Any]:
        payload = getattr(hit, "payload", None) or {}
        point_id = getattr(hit, "id", None)
        score = getattr(hit, "score", None)
        hard_skills = payload.get("hard_skills") or payload.get("skills") or []
        soft_skills = payload.get("soft_skills") or []
        full_description = str(payload.get("description") or "")
        rerank_text_parts = [
            payload.get("title"),
            payload.get("company"),
            payload.get("location"),
            payload.get("contract_type"),
            payload.get("sector"),
            " ".join(hard_skills if isinstance(hard_skills, list) else []),
            " ".join(soft_skills if isinstance(soft_skills, list) else []),
            full_description,
        ]
        rerank_text = " | ".join([str(part).strip() for part in rerank_text_parts if str(part or "").strip()])[:12000]
        return {
            "id": str(point_id) if point_id is not None else str(payload.get("id") or ""),
            "score": float(score or 0.0),
            "title": payload.get("title"),
            "company": payload.get("company"),
            "location": payload.get("location"),
            "country": payload.get("country"),
            "contract_type": payload.get("contract_type"),
            "description": _truncate_text(full_description, 300),
            "_description_full": full_description,
            "_rerank_text": rerank_text,
            "hard_skills": hard_skills if isinstance(hard_skills, list) else [],
            "required_skills": payload.get("required_skills") or (hard_skills if isinstance(hard_skills, list) else []),
            "soft_skills": soft_skills if isinstance(soft_skills, list) else [],
            "experience_years": payload.get("experience_years"),
            "required_experience_years": payload.get("required_experience_years") or payload.get("experience_years"),
            "salary_min": payload.get("salary_min"),
            "salary_max": payload.get("salary_max"),
            "remote_work": payload.get("remote_work"),
            "seniority_level": payload.get("seniority_level"),
            "company_reputation": payload.get("company_reputation"),
            "application_rate": payload.get("application_rate"),
            "source_url": payload.get("source_url"),
            "source_name": payload.get("source_name"),
            "posted_date": payload.get("posted_date") or payload.get("posted_date_iso"),
            "deadline_iso": payload.get("deadline_iso"),
            "is_expired": payload.get("is_expired"),
            "is_stale": payload.get("is_stale"),
            "stale_reason": payload.get("stale_reason"),
            "freshness_days": payload.get("freshness_days"),
            "freshness_source": payload.get("freshness_source"),
            "freshness_ttl_days": payload.get("freshness_ttl_days"),
            "quality_score": payload.get("quality_score"),
            "title_confidence": payload.get("title_confidence"),
            "location_confidence": payload.get("location_confidence"),
            "date_confidence": payload.get("date_confidence"),
            "apply_confidence": payload.get("apply_confidence"),
            "description_confidence": payload.get("description_confidence"),
        }
