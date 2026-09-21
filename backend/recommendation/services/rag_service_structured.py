# Service RAG structure - version legacy neutralisee pour politique Gemini-only
import logging

from .prompts_with_parser import (
    GapAnalysisOutput,
    CVImprovementOutput,
    JobExplanationOutput,
)

logger = logging.getLogger(__name__)


class RAGServiceStructured:
    """Service legacy maintenu pour compatibilite sans runtime LLM local."""

    def __init__(self, *args, **kwargs):
        logger.warning("RAGServiceStructured utilise le mode degrade deterministe")

    async def analyze_gaps(self, *args, **kwargs) -> GapAnalysisOutput:
        return GapAnalysisOutput(
            points_forts=["Analyse detaillee non disponible sur ce chemin legacy"],
            competences_manquantes=[],
            recommendation="Avec reserves",
            conseils=["Utiliser l'API CV texte Gemini-only"],
            confiance=0.0,
        )

    async def improve_cv(self, *args, **kwargs) -> CVImprovementOutput:
        return CVImprovementOutput(
            mots_cles_ajouter=[],
            reformulations=[],
            sections_renforcer=["Utiliser l'API CV texte Gemini-only"],
            conseils_ats=[],
        )

    async def explain_job(self, *args, **kwargs) -> JobExplanationOutput:
        return JobExplanationOutput(
            ce_quil_faut_vraiment="Ce chemin legacy est neutralise.",
            profil_ideal="Utiliser l'API CV texte Gemini-only.",
            defis_poste=[],
            opportunites=[],
        )
