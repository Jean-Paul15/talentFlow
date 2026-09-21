# Construction des requetes Elasticsearch

from typing import Any, Dict, List, Optional


def build_filter_clauses(filters: Dict[str, Any]) -> List[Dict]:
    """
    Construit les clauses de filtre ES.
    """
    clauses = []
    
    if filters.get("location"):
        clauses.append({"term": {"location": filters["location"]}})
    
    if filters.get("contract_type"):
        clauses.append({"term": {"contract_type": filters["contract_type"]}})
    
    if filters.get("skills"):
        clauses.append({"terms": {"hard_skills": filters["skills"]}})
    
    if filters.get("experience_max"):
        clauses.append({
            "range": {"experience_years": {"lte": filters["experience_max"]}}
        })
    
    return clauses


def build_hybrid_query(
    query: str,
    query_vector: List[float],
    filters: Optional[Dict[str, Any]],
    limit: int,
    lexical_weight: float,
    semantic_weight: float,
    k: int,
    num_candidates: int,
) -> Dict[str, Any]:
    """
    Construit la requete hybride ES (BM25 + kNN).
    """
    filter_clauses = build_filter_clauses(filters) if filters else []
    
    return {
        "size": limit,
        "query": {
            "bool": {
                "should": [
                    {
                        "multi_match": {
                            "query": query,
                            "fields": ["title^3", "description", "hard_skills^2"],
                            "boost": lexical_weight,
                        }
                    }
                ],
                "filter": filter_clauses,
            }
        },
        "knn": {
            "field": "description_vector",
            "query_vector": query_vector,
            "k": k,
            "num_candidates": num_candidates,
            "boost": semantic_weight,
        },
    }
