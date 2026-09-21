"""
Extension du RAG Service pour outputs LLM enrichis.
Ré-exporte les modules spécialisés.
"""
from .rag_schemas import (
    ProfileAnalysis,
    MarketInsights,
    SalaryBenchmark,
    CareerAdvice,
    SearchQualityMetrics,
    EnhancedRecommendationOutput
)
from .rag_orchestrator import EnhancedRAGOrchestrator as EnhancedRAGService

__all__ = [
    'ProfileAnalysis',
    'MarketInsights',
    'SalaryBenchmark',
    'CareerAdvice',
    'SearchQualityMetrics',
    'EnhancedRecommendationOutput',
    'EnhancedRAGService'
]
