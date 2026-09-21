# Étape 4: Schemas de requete/reponse
from pydantic import BaseModel, Field
from typing import List, Optional

class CVAnalysisRequest(BaseModel):
    """Demande analyse CV"""
    cv_text: str = Field(..., min_length=50, max_length=50000)
    user_id: str = Field(..., description="ID utilisateur")
    email: Optional[str] = None

    class Config:
        json_schema_extra = {
            "example": {
                "cv_text": "Senior Python Developer with 5 years experience",
                "user_id": "user_123"
            }
        }

class CVAnalysisResponse(BaseModel):
    """Reponse analyse CV"""
    user_id: str
    summary: str
    skills: List[str]
    experience_level: str
    recommendations: List[str]

class JobMatchRequest(BaseModel):
    """Demande matching offres-CV"""
    cv_text: str = Field(..., min_length=50)
    top_k: int = Field(default=5, ge=1, le=50)
    min_score: float = Field(default=0.7, ge=0.0, le=1.0)

class JobMatchResponse(BaseModel):
    """Reponse matching"""
    job_id: str
    job_title: str
    match_score: float
    reasoning: str

class GapAnalysisRequest(BaseModel):
    """Demande analyse gaps"""
    cv_text: str = Field(..., min_length=50)
    job_title: str = Field(..., min_length=3)

class GapAnalysisResponse(BaseModel):
    """Reponse gaps"""
    job_title: str
    missing_skills: List[str]
    learning_path: List[str]
    estimated_weeks: int

class HealthResponse(BaseModel):
    """Health check"""
    status: str
    service: str
    gemini_ready: bool
    model: str
