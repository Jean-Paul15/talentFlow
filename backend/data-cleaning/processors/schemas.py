# Schema Pydantic pour sortie LLM structuree
# Garantit le format de reponse

from typing import List

from pydantic import BaseModel, Field


class SkillExtractionOutput(BaseModel):
    """
    Schema de sortie pour l'extraction de competences.
    LangChain force le LLM a respecter cette structure.
    """
    
    hard_skills: List[str] = Field(
        default_factory=list,
        description="Competences techniques: langages, frameworks, outils"
    )
    
    soft_skills: List[str] = Field(
        default_factory=list,
        description="Competences comportementales"
    )
    
    experience_years: int = Field(
        default=0,
        description="Annees d'experience requises",
        ge=0,
        le=30
    )
    
    education_level: str = Field(
        default="Non precise",
        description="Niveau d'etudes: Bac, Bac+2, Bac+3, Bac+5, Doctorat"
    )
