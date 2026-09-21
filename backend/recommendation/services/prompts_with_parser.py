# Prompts LangChain avec Output Parsers - Force format JSON
from langchain_core.prompts import ChatPromptTemplate
from langchain.output_parsers import JsonOutputParser
from pydantic import BaseModel, Field
from typing import List

# ============================================================================
# 1. SCHÉMAS DE SORTIE (Pydantic) - Définissent la structure JSON attendue
# ============================================================================

class GapAnalysisOutput(BaseModel):
    """Réponse structurée - Analyse des gaps"""
    points_forts: List[str] = Field(..., description="3-5 points forts correspondant à l'offre")
    competences_manquantes: List[str] = Field(..., description="Compétences à acquérir")
    recommendation: str = Field(..., pattern="^(Oui|Non|Avec reserves)$", description="Recommandation")
    conseils: List[str] = Field(..., max_items=3, description="2-3 actions concrètes")
    confiance: float = Field(..., ge=0, le=100, description="Niveau de confiance (%)")


class CVImprovementOutput(BaseModel):
    """Réponse structurée - Amélioration CV"""
    mots_cles_ajouter: List[str] = Field(..., description="Termes à ajouter dans CV")
    reformulations: List[dict] = Field(..., description="Phrases à modifier avec avant/après")
    sections_renforcer: List[str] = Field(..., description="Sections à développer")
    conseils_ats: List[str] = Field(..., description="Conseils format ATS")


class JobExplanationOutput(BaseModel):
    """Réponse structurée - Explication offre"""
    ce_quil_faut_vraiment: str = Field(..., description="Ce que l'entreprise attend réellement")
    profil_ideal: str = Field(..., description="Description du candidat idéal")
    defis_poste: List[str] = Field(..., description="Défis et difficultés")
    opportunites: List[str] = Field(..., description="Ce qu'on peut y apprendre")


# ============================================================================
# 2. PARSERS JSON - Force la structure des réponses LLM
# ============================================================================

gap_parser = JsonOutputParser(pydantic_object=GapAnalysisOutput)
improvement_parser = JsonOutputParser(pydantic_object=CVImprovementOutput)
explanation_parser = JsonOutputParser(pydantic_object=JobExplanationOutput)


# ============================================================================
# 3. PROMPTS AVEC PARSERS - Intègrent les instructions d'output
# ============================================================================

# PROMPT 1: Analyse des gaps (compétences manquantes)
GAP_ANALYSIS_TEMPLATE = """Tu es un conseiller en recrutement expert. Analyse la correspondance entre ce CV et cette offre d'emploi.

## CV du candidat:
{cv_text}

## Offre d'emploi:
Titre: {job_title}
Entreprise: {company}
Description: {job_description}
Competences requises: {required_skills}

## Score de matching: {match_score}%

## Ta tâche:
Fournis une analyse structurée en français avec les champs suivants (STRICT JSON):

{format_instructions}

## Instructions strictes:
- Réponse UNIQUEMENT en JSON valide
- Ne pas ajouter de texte avant/après JSON
- "recommendation" doit être exactement: "Oui", "Non", ou "Avec reserves"
- "confiance" doit être 0-100"""

GAP_ANALYSIS_PROMPT = ChatPromptTemplate.from_template(
    GAP_ANALYSIS_TEMPLATE,
    partial_variables={"format_instructions": gap_parser.get_format_instructions()}
)


# PROMPT 2: Amélioration CV pour ATS
CV_IMPROVEMENT_TEMPLATE = """Tu es un expert en optimisation de CV pour les filtres ATS.

## CV actuel:
{cv_text}

## Offre ciblée:
Titre: {job_title}
Competences demandées: {required_skills}

## Ta tâche:
Propose des améliorations concrètes en français au format JSON strict:

{format_instructions}

## Instructions strictes:
- Réponse UNIQUEMENT en JSON valide
- "reformulations" est une liste de dict avec keys: "avant", "apres", "raison"
- Ne pas falsifier compétences, valoriser l'existant
- Pas de texte avant/après JSON"""

CV_IMPROVEMENT_PROMPT = ChatPromptTemplate.from_template(
    CV_IMPROVEMENT_TEMPLATE,
    partial_variables={"format_instructions": improvement_parser.get_format_instructions()}
)


# PROMPT 3: Explication offre emploi
JOB_EXPLANATION_TEMPLATE = """Tu es un conseiller carrière. Explique cette offre d'emploi de manière claire.

## Offre:
Titre: {job_title}
Entreprise: {company}
Description: {job_description}
Competences: {required_skills}
Experience demandée: {experience_years} ans

## Ta tâche:
Explique en français au format JSON strict:

{format_instructions}

## Instructions strictes:
- Réponse UNIQUEMENT en JSON valide
- "defis_poste" et "opportunites" doivent être des listes (3-5 items chacune)
- Texte synthétique et pragmatique
- Pas de texte avant/après JSON"""

JOB_EXPLANATION_PROMPT = ChatPromptTemplate.from_template(
    JOB_EXPLANATION_TEMPLATE,
    partial_variables={"format_instructions": explanation_parser.get_format_instructions()}
)


# ============================================================================
# 4. CHAINS AVEC PARSERS - Retournent directement des objets Python
# ============================================================================

def create_gap_analysis_chain(llm):
    """Crée une chain gap analysis avec parser
    
    Usage:
        chain = create_gap_analysis_chain(gemini_llm)
        result = chain.invoke({
            "cv_text": "...",
            "job_title": "...",
            ...
        })
        # result est un GapAnalysisOutput (object Python, pas string)
    """
    return GAP_ANALYSIS_PROMPT | llm | gap_parser


def create_cv_improvement_chain(llm):
    """Crée une chain amélioration CV avec parser"""
    return CV_IMPROVEMENT_PROMPT | llm | improvement_parser


def create_job_explanation_chain(llm):
    """Crée une chain explication offre avec parser"""
    return JOB_EXPLANATION_PROMPT | llm | explanation_parser
