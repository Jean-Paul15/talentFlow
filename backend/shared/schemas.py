# Unified Schemas - UNIQUE Job definition across backend
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime

class JobSchema(BaseModel):
    """Job UNIQUE definition - used everywhere"""
    
    id: str = Field(..., description="Unique job ID")
    title: str = Field(..., min_length=3, max_length=200)
    company: str = Field(..., min_length=2, max_length=200)
    location: str = Field(..., min_length=2)
    
    description: str = Field(..., min_length=50)
    requirements: List[str]
    
    salary_min: Optional[int] = None
    salary_max: Optional[int] = None
    salary_currency: str = Field(default="XOF")
    
    job_type: str = Field(default="CDI")  # CDI, CDD, Stage, Freelance
    level: str = Field(default="mid")  # junior, mid, senior, expert
    
    skills: List[str] = Field(default_factory=list)
    
    posted_at: datetime
    url: str
    source: str  # anpe-togo, emploi.tg, etc
    
    class Config:
        json_schema_extra = {
            "example": {
                "id": "job_001",
                "title": "Senior Python Developer",
                "company": "TechCorp",
                "location": "Lome, Togo"
            }
        }

class CVSchema(BaseModel):
    """CV UNIQUE definition"""
    
    user_id: str
    full_text: str = Field(..., min_length=50, max_length=50000)
    
    summary: Optional[str] = None
    skills: List[str] = Field(default_factory=list)
    experience_level: str = Field(default="mid")
    
    posted_at: datetime

class EmbeddingSchema(BaseModel):
    """Embedding result UNIQUE"""
    
    text: str
    embedding: List[float] = Field(..., min_items=384, max_items=384)
    model: str = "paraphrase-multilingual-MiniLM-L12-v2"
    timestamp: datetime

# Re-export
__all__ = ["JobSchema", "CVSchema", "EmbeddingSchema"]
