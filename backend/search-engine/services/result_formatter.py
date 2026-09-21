# Utilitaires de formatage des resultats de recherche

from typing import Any, Dict, List


def format_search_results(es_response: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Formate la reponse Elasticsearch en liste de resultats.
    """
    hits = es_response.get("hits", {}).get("hits", [])
    
    results = []
    for hit in hits:
        source = hit.get("_source", {})
        full_description = source.get("description", "") or ""
        rerank_text = _build_rerank_text_from_source(source)
        
        result = {
            "id": hit.get("_id"),
            "score": hit.get("_score"),
            "title": source.get("title"),
            "company": source.get("company"),
            "location": source.get("location"),
            "country": source.get("country"),
            "contract_type": source.get("contract_type"),
            "description": _truncate(full_description, 300),
            "_description_full": full_description,
            "_rerank_text": rerank_text,
            "hard_skills": source.get("hard_skills", []),
            "required_skills": source.get("required_skills") or source.get("hard_skills", []),
            "soft_skills": source.get("soft_skills", []),
            "experience_years": source.get("experience_years"),
            "required_experience_years": source.get("required_experience_years") or source.get("experience_years"),
            "salary_min": source.get("salary_min"),
            "salary_max": source.get("salary_max"),
            "remote_work": source.get("remote_work"),
            "seniority_level": source.get("seniority_level"),
            "company_reputation": source.get("company_reputation"),
            "application_rate": source.get("application_rate"),
            "source_url": source.get("source_url"),
            "source_name": source.get("source_name"),
            "posted_date": source.get("posted_date"),
            "deadline_iso": source.get("deadline_iso"),
            "is_expired": source.get("is_expired"),
            "is_stale": source.get("is_stale"),
            "stale_reason": source.get("stale_reason"),
            "freshness_days": source.get("freshness_days"),
            "freshness_source": source.get("freshness_source"),
            "freshness_ttl_days": source.get("freshness_ttl_days"),
            "quality_score": source.get("quality_score"),
            "title_confidence": source.get("title_confidence"),
            "location_confidence": source.get("location_confidence"),
            "date_confidence": source.get("date_confidence"),
            "apply_confidence": source.get("apply_confidence"),
            "description_confidence": source.get("description_confidence"),
        }
        
        results.append(result)
    
    return results


def _build_rerank_text_from_source(source: Dict[str, Any]) -> str:
    parts = [
        source.get("title"),
        source.get("company"),
        source.get("location"),
        source.get("contract_type"),
        source.get("sector"),
        " ".join(source.get("hard_skills") or []),
        " ".join(source.get("soft_skills") or []),
        source.get("description"),
    ]
    text = " | ".join([str(p).strip() for p in parts if str(p or "").strip()])
    return text[:12000]


def _truncate(text: str, max_length: int) -> str:
    """
    Tronque le texte avec ellipsis.
    """
    if len(text) <= max_length:
        return text
    return text[:max_length].rsplit(" ", 1)[0] + "..."
