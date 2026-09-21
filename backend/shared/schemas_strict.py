"""
Schémas Pydantic stricts pour validation d'entrée.
Tous les champs sont validés avec contraintes strictes.
"""

from pydantic import BaseModel, Field, validator, EmailStr
from typing import Optional, List
from datetime import datetime
import re


class MatchRequest(BaseModel):
    """Requête d'analyse CV vs Offre - Validation stricte."""
    
    cv_id: str = Field(
        ...,
        min_length=10,
        max_length=100,
        description="ID du CV (format: cv_{user_id}_{version})"
    )
    job_id: str = Field(
        ...,
        min_length=10,
        max_length=100,
        description="ID de l'offre (format: job_{source}_{id})"
    )
    
    @validator("cv_id")
    def validate_cv_id_format(cls, v):
        """Valide le format cv_{user}_*"""
        if not v.startswith("cv_"):
            raise ValueError("cv_id doit commencer par 'cv_'")
        if not re.match(r"^cv_[a-zA-Z0-9_-]+$", v):
            raise ValueError("cv_id contient des caractères invalides")
        return v
    
    @validator("job_id")
    def validate_job_id_format(cls, v):
        """Valide le format job_{source}_*"""
        if not v.startswith("job_"):
            raise ValueError("job_id doit commencer par 'job_'")
        if not re.match(r"^job_[a-zA-Z0-9_-]+$", v):
            raise ValueError("job_id contient des caractères invalides")
        return v


class CVImprovementRequest(BaseModel):
    """Requête d'amélioration CV - Validation stricte."""
    
    cv_id: str = Field(..., min_length=10, max_length=100)
    job_id: str = Field(..., min_length=10, max_length=100)
    language: str = Field(default="fr", regex="^(fr|en)$")
    
    @validator("cv_id", "job_id")
    def validate_id_format(cls, v, field):
        """Valide les IDs."""
        prefix = "cv_" if field.name == "cv_id" else "job_"
        if not v.startswith(prefix):
            raise ValueError(f"{field.name} doit commencer par '{prefix}'")
        return v


class ScoreDetail(BaseModel):
    """Détails des scores de matching - Toujours entre 0-100."""
    
    total: float = Field(..., ge=0, le=100, description="Score total (0-100)")
    semantic: float = Field(..., ge=0, le=100, description="Similarité sémantique")
    skills: float = Field(..., ge=0, le=100, description="Correspondance compétences")
    experience: float = Field(..., ge=0, le=100, description="Correspondance expérience")
    label: str = Field(..., regex="^(excellent|good|average|poor)$")


class MatchResponse(BaseModel):
    """Réponse d'analyse de matching - Complète."""
    
    scores: ScoreDetail
    analysis: str = Field(..., min_length=50, max_length=5000)
    job: dict  # TODO: Créer JobDetail schema
    suggestions: List[str] = Field(default_factory=list, max_items=10)


class CVImprovementResponse(BaseModel):
    """Réponse suggestions d'amélioration CV."""
    
    suggestions: List[str] = Field(..., min_items=1, max_items=20)


class ScrapeRequest(BaseModel):
    """Requête de scraping - Validation sites."""
    
    sites: List[str] = Field(
        ...,
        min_items=1,
        max_items=10,
        description="Liste des sites à scraper"
    )
    full: bool = Field(default=False, description="Scraping complet ou incrémental")
    max_pages: int = Field(default=10, ge=1, le=100, description="Max pages par site")
    
    @validator("sites")
    def validate_sites(cls, v):
        """Valide que les sites sont dans la liste blanche."""
        ALLOWED_SITES = [
            "indeed", "linkedin", "monster", "glassdoor",
            "anpe_togo", "emploi_tg", "jobintogo"
        ]
        for site in v:
            if site not in ALLOWED_SITES:
                raise ValueError(f"Site non autorisé: {site}. Autorisés: {ALLOWED_SITES}")
        return v


class CleanRequest(BaseModel):
    """Requête de nettoyage - Validation job_ids."""
    
    job_ids: Optional[List[str]] = Field(default=None, max_items=1000)
    since_hours: int = Field(default=24, ge=1, le=168, description="Nettoyer depuis X heures")
    full: bool = Field(default=False, description="Nettoyage complet ou incrémental")
    
    @validator("job_ids")
    def validate_job_ids(cls, v):
        """Valide les job_ids."""
        if v is None:
            return v
        for job_id in v:
            if not job_id.startswith("job_"):
                raise ValueError(f"job_id invalide: {job_id}")
            if not re.match(r"^job_[a-zA-Z0-9_-]+$", job_id):
                raise ValueError(f"job_id contient caractères invalides: {job_id}")
        return v


class SearchRequest(BaseModel):
    """Requête de recherche - Validation query."""
    
    query: str = Field(..., min_length=2, max_length=500, description="Requête de recherche")
    filters: Optional[dict] = Field(default_factory=dict)
    limit: int = Field(default=10, ge=1, le=100, description="Nombre de résultats")
    offset: int = Field(default=0, ge=0, le=10000, description="Offset pagination")
    
    @validator("query")
    def validate_query(cls, v):
        """Nettoie et valide la requête."""
        # Supprime caractères spéciaux dangereux
        v = re.sub(r'[<>\'";{}()\[\]]', '', v)
        return v.strip()


class HealthResponse(BaseModel):
    """Réponse health check standard."""
    
    status: str = Field(..., regex="^(healthy|degraded|unhealthy)$")
    service: str = Field(..., min_length=1, max_length=50)
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    dependencies: Optional[dict] = Field(default_factory=dict)


class ErrorResponse(BaseModel):
    """Réponse d'erreur standard."""
    
    error: str = Field(..., min_length=1, max_length=200)
    message: str = Field(..., min_length=1, max_length=1000)
    status_code: int = Field(..., ge=400, le=599)
    timestamp: datetime = Field(default_factory=datetime.utcnow)
