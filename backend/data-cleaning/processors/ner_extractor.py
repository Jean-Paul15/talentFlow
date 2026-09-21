# Extracteur NER avec JobBERT
# Extraction de skills via Token Classification

from typing import List, Set

from loguru import logger

from processors.skill_utils import extract_by_patterns, normalize_skills


class NERExtractor:
    """
    Extracteur de skills utilisant JobBERT NER.
    Fallback sur patterns regex.
    """
    
    def __init__(self, model_name: str, device: str = "cpu"):
        """
        Initialise le pipeline NER.
        """
        self.model_name = model_name
        self.device = device
        self.pipeline = None
        self._load_model()
    
    def _load_model(self) -> None:
        """
        Charge le pipeline NER.
        """
        try:
            from transformers import pipeline
            
            self.pipeline = pipeline(
                "ner",
                model=self.model_name,
                aggregation_strategy="simple",
                device=-1 if self.device == "cpu" else 0
            )
            logger.info(f"NER charge: {self.model_name}")
        except ImportError:
            logger.warning("Transformers non installe")
        except Exception as err:
            logger.error(f"Erreur NER: {err}")
    
    def extract_skills(self, text: str) -> List[str]:
        """
        Extrait les hard skills via NER + patterns.
        """
        skills: Set[str] = set()
        
        if self.pipeline:
            skills.update(self._ner_extract(text))
        
        skills.update(extract_by_patterns(text))
        return list(normalize_skills(skills))[:25]
    
    def _ner_extract(self, text: str) -> List[str]:
        """
        Extraction via NER (labels: B, I, O).
        """
        skills = []
        try:
            # Keep below model max sequence budget to avoid tensor shape errors
            entities = self.pipeline(text[:480])
            current_skill = []
            
            for entity in entities:
                label = entity.get("entity_group", entity.get("entity", ""))
                word = entity["word"].replace("##", "").strip()
                score = entity["score"]
                
                if label in ("B", "B-Skill", "Skill") and score > 0.5:
                    if current_skill:
                        skills.append(" ".join(current_skill))
                    current_skill = [word]
                elif label in ("I", "I-Skill") and score > 0.5:
                    current_skill.append(word)
                else:
                    if current_skill:
                        skills.append(" ".join(current_skill))
                        current_skill = []
            
            if current_skill:
                skills.append(" ".join(current_skill))
                
        except Exception as err:
            logger.debug(f"Erreur NER: {err}")
        
        return [s for s in skills if len(s) > 2]
