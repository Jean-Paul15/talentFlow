"""Pydantic schemas for CV text recommendation endpoints."""

from __future__ import annotations

from pydantic import BaseModel, Field

__all__ = [
    "CVAnalyzeRequest",
    "TaskResponse",
    "CVAnalysisResult",
    "TaskStatusResponse",
    "CVRecommendTextRequest",
    "RecommendedJobPreview",
    "CVRecommendTextResponse",
    "AssistantRecommendedJob",
    "AssistantOfferRewritePayload",
    "AssistantOfferPlaybookPayload",
    "AssistantStructuredPayload",
    "AtsLitePayload",
    "CvDocumentAssessRequest",
    "CvDocumentAssessResponse",
    "CVImproveForOfferRequest",
    "CVImproveForOfferResponse",
]

class CVAnalyzeRequest(BaseModel):
    """Requête analyse CV texte brut."""
    cv_text: str = Field(..., min_length=10, description="Texte du CV")
    file_name: str = Field(default="cv.pdf", description="Nom du fichier original")

class TaskResponse(BaseModel):
    """Réponse immédiate avec task_id pour polling."""
    task_id: str = Field(..., description="ID de la tâche")
    status: str = Field(default="processing", description="Status initial")
    message: str = Field(..., description="Message pour utilisateur")

class CVAnalysisResult(BaseModel):
    """Résultat final analyse CV."""
    skills: list[str] = Field(default_factory=list)
    experience_years: int | None = None
    education_level: str | None = None
    raw_text_preview: str = Field(default="", description="Premiers 200 caractères")

class TaskStatusResponse(BaseModel):
    """Status d'une tâche de polling."""
    task_id: str
    task_type: str
    status: str
    progress: int = Field(0, ge=0, le=100)
    step: str
    result: CVAnalysisResult | None = None
    error: str | None = None

class CVRecommendTextRequest(BaseModel):
    """CV texte -> recommandations utilisateur (search + synthèse)."""
    cv_text: str = Field(..., min_length=10)
    file_name: str = Field(default="cv.pdf")
    top_k: int = Field(default=5, ge=1, le=20)
    location: str | None = None
    contract_type: str | None = None
    use_llm: bool = True
    llm_model: str | None = None
    rerank: bool | None = None
    candidate_pool_size: int | None = Field(default=None, ge=1, le=200)

class RecommendedJobPreview(BaseModel):
    id: str
    title: str
    company: str | None = None
    location: str | None = None
    country: str | None = None
    contract_type: str | None = None
    source_name: str | None = None
    source_url: str | None = None
    posted_date: str | None = None
    score: float | None = None
    summary: str = ""

class CVRecommendTextResponse(BaseModel):
    cv_analysis: CVAnalysisResult
    query_used: str
    total_results: int
    jobs: list[RecommendedJobPreview]
    assistant_message: str
    llm_used: bool = False
    llm_provider: str | None = None
    llm_model: str | None = None
    llm_error: str | None = None
    llm_status: str = "fallback_used"
    assistant_structured: "AssistantStructuredPayload | None" = None
    ats_lite: "AtsLitePayload | None" = None

class AssistantRecommendedJob(BaseModel):
    job_id: str
    title: str
    why: str
    url: str
    cv_improvement: str


class AssistantOfferRewritePayload(BaseModel):
    target_title: str
    target_summary: str
    experience_bullets: list[str] = Field(default_factory=list)


class AssistantOfferPlaybookPayload(BaseModel):
    job_id: str
    title: str
    url: str
    why_fit: str
    cv_delta: str
    rewrite: AssistantOfferRewritePayload
    evidence: list[str] = Field(default_factory=list)


class AssistantStructuredPayload(BaseModel):
    mode: str
    profile_summary: str
    strengths: list[str] = Field(default_factory=list)
    gaps: list[str] = Field(default_factory=list)
    recommended_jobs: list[AssistantRecommendedJob] = Field(default_factory=list)
    score_explanation: str | None = None
    offer_playbooks: list[AssistantOfferPlaybookPayload] = Field(default_factory=list)
    actions: list[str] = Field(default_factory=list)
    reason_if_no_match: str | None = None

class AtsLitePayload(BaseModel):
    overall_score: int = Field(ge=0, le=100)
    structure_score: int = Field(ge=0, le=100)
    alignment_score: int = Field(ge=0, le=100)
    evidence_score: int = Field(ge=0, le=100)
    readiness_label: str
    summary: str
    matched_keywords: list[str] = Field(default_factory=list)
    missing_keywords: list[str] = Field(default_factory=list)
    suggestions: list[str] = Field(default_factory=list)
    action_plan: list[str] = Field(default_factory=list)

class CVImproveForOfferRequest(BaseModel):
    """Amélioration ciblée du CV pour une offre donnée (mode texte stable)."""
    cv_text: str = Field(..., min_length=10)
    job_title: str = Field(..., min_length=2)
    job_summary: str = Field(default="")
    job_url: str | None = None
    use_llm: bool = True
    llm_model: str | None = None

class CVImproveForOfferResponse(BaseModel):
    cv_analysis: CVAnalysisResult
    job_title: str
    job_url: str | None = None
    missing_skills: list[str] = Field(default_factory=list)
    improvements: list[str] = Field(default_factory=list)
    llm_used: bool = False
    llm_provider: str | None = None
    llm_model: str | None = None
    llm_error: str | None = None


class CvDocumentAssessRequest(BaseModel):
    """Evaluation de type document (CV / non-CV / ambigu)."""

    cv_text: str = Field(..., min_length=10)
    use_llm: bool = True


class CvDocumentAssessResponse(BaseModel):
    document_kind: str
    cv_confidence: float = Field(ge=0, le=1)
    user_message: str
    used_llm: bool = False
