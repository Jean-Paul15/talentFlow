# Schemas Pydantic pour l'API de recherche

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class SearchRequest(BaseModel):
    """
    Requete de recherche hybride.
    """
    query: str = Field(..., min_length=2, description="Texte de recherche")
    location: Optional[str] = Field(None, description="Filtrer par ville")
    contract_type: Optional[str] = Field(None, description="CDI, CDD, Stage, etc.")
    skills: Optional[List[str]] = Field(None, description="Competences requises")
    limit: int = Field(20, ge=1, le=100, description="Nombre de resultats")
    rerank: Optional[bool] = Field(
        None,
        description="Active le reranking cross-encoder (si disponible)",
    )
    rerank_top_k: Optional[int] = Field(
        None,
        ge=1,
        le=200,
        description="Nombre de candidats rerankes (top-k du pool initial)",
    )
    candidate_pool_size: Optional[int] = Field(
        None,
        ge=1,
        le=500,
        description="Taille du pool initial avant reranking",
    )


class JobResult(BaseModel):
    """
    Resultat de recherche.
    """
    id: str
    score: float
    title: str
    company: Optional[str]
    location: Optional[str]
    country: Optional[str] = None
    contract_type: Optional[str]
    description: str
    hard_skills: List[str]
    soft_skills: List[str]
    experience_years: Optional[int]
    salary_min: Optional[float] = None
    salary_max: Optional[float] = None
    remote_work: Optional[Any] = None
    seniority_level: Optional[str] = None
    company_reputation: Optional[float] = None
    application_rate: Optional[float] = None
    required_skills: Optional[List[str]] = None
    required_experience_years: Optional[int] = None
    source_url: Optional[str]
    source_name: Optional[str]
    posted_date: Optional[str]
    deadline_iso: Optional[str] = None
    is_expired: Optional[bool] = None
    is_stale: Optional[bool] = None
    stale_reason: Optional[str] = None
    freshness_days: Optional[int] = None
    freshness_source: Optional[str] = None
    freshness_ttl_days: Optional[int] = None
    quality_score: Optional[float] = None
    title_confidence: Optional[float] = None
    location_confidence: Optional[float] = None
    date_confidence: Optional[float] = None
    apply_confidence: Optional[float] = None
    description_confidence: Optional[float] = None
    base_score: Optional[float] = None
    rerank_score: Optional[float] = None


class SearchResponse(BaseModel):
    """
    Reponse de recherche.
    """
    query: str
    total: int
    results: List[JobResult]
    backend: str = "qdrant"
    reranked: bool = False
    candidate_pool_size: Optional[int] = None
    rerank_top_k: Optional[int] = None
    search_mode: Optional[str] = None
    hybrid_strategy: Optional[str] = None


class SearchCompareResponse(BaseModel):
    """
    Reponse de comparaison avant/apres reranking.
    """
    query: str
    backend: str
    baseline_total: int
    reranked_total: int
    candidate_pool_size: int
    rerank_top_k: int
    baseline: List[JobResult]
    reranked: List[JobResult]


class SearchModeCompareResponse(BaseModel):
    """
    Reponse de comparaison dense vs hybrid vs hybrid+rerank.
    """
    query: str
    backend: str
    candidate_pool_size: int
    rerank_top_k: int
    dense_total: int
    hybrid_total: int
    hybrid_reranked_total: int
    dense: List[JobResult]
    hybrid: List[JobResult]
    hybrid_reranked: List[JobResult]


class VectorSearchRequest(BaseModel):
    """
    Requête interne de recherche par vecteur (pour recommendation).
    """
    query_vector: List[float] = Field(..., min_length=1, description="Embedding de la requête/CV")
    location: Optional[str] = Field(None, description="Filtrer par ville")
    contract_type: Optional[str] = Field(None, description="CDI, CDD, Stage, etc.")
    skills: Optional[List[str]] = Field(None, description="Competences requises")
    limit: int = Field(20, ge=1, le=500, description="Nombre de candidats")


class SearchEvalRequest(SearchRequest):
    """
    Requête d'évaluation retrieval/reranking sur des jugements de pertinence.
    """
    relevant_ids: Optional[List[str]] = Field(
        None,
        description="IDs pertinents (relevance binaire=1)",
    )
    graded_relevance: Optional[Dict[str, float]] = Field(
        None,
        description="Jugements gradués {doc_id: grade}",
    )
    k_values: List[int] = Field(
        default_factory=lambda: [5, 10],
        description="Valeurs de k pour nDCG/precision/recall",
    )


class RankingMetrics(BaseModel):
    mrr: float
    precision: Dict[str, float]
    recall: Dict[str, float]
    ndcg: Dict[str, float]


class SearchEvalResponse(BaseModel):
    query: str
    backend: str
    judged_count: int
    candidate_pool_size: int
    rerank_top_k: Optional[int] = None
    baseline: RankingMetrics
    reranked: Optional[RankingMetrics] = None
    baseline_ids: List[str]
    reranked_ids: Optional[List[str]] = None


class SearchEvalBatchCase(BaseModel):
    """
    Un cas de test d'évaluation (query + jugements).
    """
    query: str = Field(..., min_length=2)
    location: Optional[str] = None
    contract_type: Optional[str] = None
    skills: Optional[List[str]] = None
    relevant_ids: Optional[List[str]] = None
    graded_relevance: Optional[Dict[str, float]] = None


class SearchEvalBatchRequest(BaseModel):
    """
    Évaluation batch sur plusieurs requêtes pour soutenance/benchmark.
    """
    cases: List[SearchEvalBatchCase] = Field(..., min_length=1)
    limit: int = Field(10, ge=1, le=100)
    candidate_pool_size: Optional[int] = Field(None, ge=1, le=500)
    rerank_top_k: Optional[int] = Field(None, ge=1, le=500)
    k_values: List[int] = Field(default_factory=lambda: [5, 10])


class SearchEvalBatchSummary(BaseModel):
    cases_total: int
    cases_evaluated: int
    cases_skipped: int
    mean_baseline_ndcg: Dict[str, float]
    mean_reranked_ndcg: Dict[str, float]
    mean_baseline_mrr: float
    mean_reranked_mrr: float
    ndcg_gain_abs: Dict[str, float]
    ndcg_gain_pct: Dict[str, float]
    mrr_gain_abs: float
    mrr_gain_pct: float


class SearchEvalBatchCaseResult(BaseModel):
    query: str
    judged_count: int
    baseline: RankingMetrics
    reranked: RankingMetrics
    baseline_top_ids: List[str]
    reranked_top_ids: List[str]


class SearchEvalBatchResponse(BaseModel):
    backend: str
    candidate_pool_size: int
    rerank_top_k: int
    k_values: List[int]
    summary: SearchEvalBatchSummary
    cases: List[SearchEvalBatchCaseResult]
    rerank_policy: Optional[Dict[str, Any]] = None


class RerankPolicyManualRequest(BaseModel):
    enabled: bool


class RerankPolicySettingsRequest(BaseModel):
    target_ndcg_k: Optional[int] = Field(None, ge=1, le=100)
    min_cases_for_decision: Optional[int] = Field(None, ge=1, le=1000)
    enable_ndcg_gain_abs: Optional[float] = None
    enable_mrr_gain_abs: Optional[float] = None
    disable_ndcg_gain_abs: Optional[float] = None
    disable_mrr_gain_abs: Optional[float] = None
    enable_windows: Optional[int] = Field(None, ge=1, le=50)
    disable_windows: Optional[int] = Field(None, ge=1, le=50)


class RerankPolicyStateResponse(BaseModel):
    mode: str
    enabled_default: bool
    target_ndcg_k: int
    min_cases_for_decision: int
    thresholds: Dict[str, float]
    windows: Dict[str, int]
    last_decision_reason: str
    updated_at: str
    history_size: int
    history: List[Dict[str, Any]]
    decision_changed: Optional[bool] = None
    decision_reason: Optional[str] = None


class HealthResponse(BaseModel):
    """
    Statut de sante de l'API.
    """
    status: str
    elasticsearch: bool
    qdrant: bool = False
    search_backend: str = "qdrant"
    index_exists: bool
    doc_count: int
    reranker_available: bool = False
    reranker_loaded: bool = False
    reranker_enabled_default: bool = False
    reranker_model: Optional[str] = None
