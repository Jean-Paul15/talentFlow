"""
Schémas Pydantic pour Enhanced RAG.
"""
from pydantic import BaseModel, Field
from typing import List, Dict, Any
from datetime import datetime


class ProfileAnalysis(BaseModel):
    """Analyse détaillée du profil candidat."""
    strengths: List[str] = Field(description="Points forts du profil")
    weaknesses: List[str] = Field(description="Points faibles à améliorer")
    experience_level: str = Field(description="Junior/Mid/Senior")
    technical_depth: str = Field(description="Profondeur technique: Beginner/Intermediate/Expert")
    soft_skills_assessment: str = Field(description="Évaluation soft skills")


class MarketInsights(BaseModel):
    """Insights marché et tendances."""
    demand_trend: str = Field(description="Forte/Moyenne/Faible demande")
    growth_rate: str = Field(description="Taux de croissance annuel")
    hot_skills: List[str] = Field(description="Compétences les plus demandées")
    emerging_technologies: List[str] = Field(description="Technologies émergentes")
    market_saturation: str = Field(description="Niveau de saturation du marché")


class SalaryBenchmark(BaseModel):
    """Benchmarking salarial."""
    min_salary: float = Field(description="Salaire minimum marché")
    median_salary: float = Field(description="Salaire médian")
    max_salary: float = Field(description="Salaire maximum")
    currency: str = Field(default="EUR")
    percentile_position: int = Field(description="Position percentile du candidat")


class CareerAdvice(BaseModel):
    """Conseils de carrière personnalisés."""
    immediate_actions: List[str] = Field(description="Actions immédiates 0-3 mois")
    short_term_goals: List[str] = Field(description="Objectifs court terme 3-12 mois")
    certifications_recommended: List[str] = Field(description="Certifications recommandées")
    learning_paths: List[str] = Field(description="Parcours d'apprentissage")
    networking_tips: List[str] = Field(description="Conseils networking")


class SearchQualityMetrics(BaseModel):
    """Métriques de qualité de la recherche."""
    total_analyzed: int = Field(description="Total jobs analysés")
    matched_count: int = Field(description="Nombre de matches")
    avg_score: float = Field(description="Score moyen des matches")
    confidence_level: str = Field(description="high/medium/low")
    data_freshness: str = Field(description="Fraîcheur des données")


class EnhancedRecommendationOutput(BaseModel):
    """Output complet enrichi avec tous les insights LLM."""
    recommendations: List[Dict[str, Any]] = Field(description="Offres matchées")
    profile_analysis: ProfileAnalysis
    market_insights: MarketInsights
    salary_benchmark: SalaryBenchmark
    career_advice: CareerAdvice
    search_quality: SearchQualityMetrics
    generated_at: str = Field(default_factory=lambda: datetime.now().isoformat())
