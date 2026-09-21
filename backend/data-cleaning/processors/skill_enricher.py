# Enrichisseur principal - Orchestrateur
# Priorite: Mistral > Qwen local optionnel > NER > Patterns

from typing import Optional
import os

from loguru import logger

from core.config_loader import ConfigLoader
from processors.llm_enricher import LLMEnricher
from processors.ner_extractor import NERExtractor
from processors.metadata_extractor import (
    extract_soft_skills,
    extract_experience,
    extract_education,
)
from processors.skill_utils import extract_by_patterns, normalize_skills


class SkillEnricher:
    """
    Orchestrateur d'enrichissement avec 3 niveaux:
    1. LLM Mistral cloud
    2. Qwen local optionnel
    3. NER local (JobBERT) pour extraction de skills
    4. Patterns regex (fallback garanti)
    
    Config via settings.yml ou variables d'environnement:
    - MISTRAL_API_KEY: active le chemin LLM principal
    """
    
    def __init__(self):
        """
        Initialise les extracteurs.
        """
        config = ConfigLoader().get_config()
        enrichment_config = config.get("enrichment", {})
        
        # Config LLM
        llm_config = enrichment_config.get("llm", {})
        llm_model = llm_config.get("model", "mistral-small-latest")
        llm_enabled = llm_config.get("enabled", False)
        
        # Config NER
        ner_config = enrichment_config.get("ner", {})
        ner_model = ner_config.get("model", "jjzha/jobbert_skill_extraction")
        ner_device = ner_config.get("device", "cpu")
        
        # Initialiser les extracteurs
        self.llm_enricher: Optional[LLMEnricher] = None
        self.ner_extractor: Optional[NERExtractor] = None
        self.skip_ner = os.getenv("DATA_CLEANING_SKIP_NER", "false").strip().lower() in {"1","true","yes","on"}
        
        if llm_enabled:
            self.llm_enricher = LLMEnricher(llm_model)
            if self.llm_enricher.enabled:
                logger.info(f"LLM data-cleaning actif: {llm_model}")
        
        if self.skip_ner:
            logger.warning("DATA_CLEANING_SKIP_NER actif: extraction hard_skills en mode patterns-only")
            self.ner_extractor = None
        else:
            self.ner_extractor = NERExtractor(ner_model, ner_device)
    
    def enrich_job(self, job_data: dict) -> dict:
        """
        Enrichit une offre avec extraction de competences.
        
        Priorite: LLM > NER > Patterns
        """
        description = job_data.get("description", "")
        title = job_data.get("title", "")
        llm_attempted = bool(self.llm_enricher and self.llm_enricher.enabled)

        job_data.setdefault("llm_provider_used", "none")
        job_data.setdefault("llm_degraded", False)
        job_data.setdefault("llm_fallback_triggered", False)
        
        # 1. Essayer le LLM (plus precis)
        if self._try_llm_enrichment(job_data, title, description):
            return job_data
        
        # 2. Fallback sur NER + patterns
        return self._fallback_enrichment(job_data, title, description, llm_attempted=llm_attempted)
    
    def _try_llm_enrichment(
        self,
        job_data: dict,
        title: str,
        description: str
    ) -> bool:
        """
        Tente l'enrichissement via LLM.
        
        Returns:
            True si reussi, False sinon
        """
        if not self.llm_enricher or not self.llm_enricher.enabled:
            return False
        
        result = self.llm_enricher.extract_skills(title, description)
        if result:
            job_data.update(result.payload)
            job_data["enriched"] = True
            job_data["enrichment_method"] = "llm"
            job_data["llm_provider_used"] = result.provider_used
            job_data["llm_degraded"] = result.degraded
            job_data["llm_fallback_triggered"] = result.fallback_triggered
            return True
        
        return False
    
    def _fallback_enrichment(
        self,
        job_data: dict,
        title: str,
        description: str,
        *,
        llm_attempted: bool,
    ) -> dict:
        """
        Enrichissement via NER + patterns + mots-cles.
        """
        text = f"{title} {description}"
        
        if self.ner_extractor:
            job_data["hard_skills"] = self.ner_extractor.extract_skills(text)
        else:
            job_data["hard_skills"] = list(normalize_skills(extract_by_patterns(text)))[:25]
        job_data["soft_skills"] = extract_soft_skills(text)
        job_data["experience_years"] = extract_experience(text)
        job_data["education_level"] = extract_education(text)
        ner_ready = bool(self.ner_extractor and getattr(self.ner_extractor, "pipeline", None))
        job_data["enriched"] = ner_ready
        job_data["enrichment_method"] = "ner" if ner_ready else "patterns"
        job_data["llm_provider_used"] = "none"
        job_data["llm_degraded"] = llm_attempted
        job_data["llm_fallback_triggered"] = llm_attempted
        
        return job_data
