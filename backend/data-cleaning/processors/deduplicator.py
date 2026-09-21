# Deduplicateur d'offres d'emploi
# Hash robuste base sur role + entreprise + localisation (normalisation agressive)

from __future__ import annotations

import hashlib
import re
from typing import List

from loguru import logger

from core.config_loader import ConfigLoader
from processors.text_utils import normalize_text


_COMPANY_LEGAL_SUFFIXES = {
    "sa", "sarl", "sas", "sasu", "sarlu", "ltd", "llc", "inc", "corp", "plc", "gmbh", "bv", "spa"
}
_TITLE_STOPWORDS = {
    "de", "du", "des", "la", "le", "les", "et", "ou", "en", "pour", "avec", "the", "a", "an"
}


def _norm_company(value: str) -> str:
    txt = normalize_text(value or "").lower()
    txt = re.sub(r"[^a-z0-9\s]", " ", txt)
    tokens = [t for t in txt.split() if t and t not in _COMPANY_LEGAL_SUFFIXES]
    return " ".join(tokens[:8])


def _norm_title(value: str) -> str:
    txt = normalize_text(value or "").lower()
    # '-' en fin de classe: evite l'erreur regex "bad character range _-\s"
    txt = re.sub(r"[^a-z0-9+#./_\s-]", " ", txt)
    tokens = [t for t in txt.split() if t and t not in _TITLE_STOPWORDS]
    return " ".join(tokens[:10])


def _norm_location(value: str) -> str:
    txt = normalize_text(value or "").lower()
    txt = re.sub(r"[^a-z0-9\s]", " ", txt)
    return " ".join(txt.split()[:6])


class Deduplicator:
    """
    Calcule des hash uniques pour detecter les doublons exacts et quasi-semantiques.
    """

    def __init__(self):
        config = ConfigLoader().get_config()
        dedup_config = config.get("deduplication", {})
        self.hash_fields: List[str] = dedup_config.get("hash_fields", ["title", "company", "location"])
        logger.info(f"Deduplicator: champs={self.hash_fields}")

    def _raw_hash(self, job_data: dict) -> str:
        parts = []
        for field in self.hash_fields:
            value = job_data.get(field, "")
            parts.append(normalize_text(value))
        combined = "|".join(parts)
        return hashlib.sha256(combined.encode("utf-8")).hexdigest()

    def _semantic_hash(self, job_data: dict) -> str:
        title = _norm_title(str(job_data.get("title") or ""))
        company = _norm_company(str(job_data.get("company") or ""))
        location = _norm_location(str(job_data.get("location") or ""))
        combined = f"{title}|{company}|{location}"
        return hashlib.sha256(combined.encode("utf-8")).hexdigest()

    def compute_hash(self, job_data: dict) -> str:
        # Hash principal = semantique (plus stable cross-sources)
        return self._semantic_hash(job_data)

    def are_similar(self, job1: dict, job2: dict) -> bool:
        return self.compute_hash(job1) == self.compute_hash(job2)

    def add_dedup_hash(self, job_data: dict) -> dict:
        job_data["dedup_hash"] = self.compute_hash(job_data)
        job_data["dedup_hash_raw"] = self._raw_hash(job_data)
        if not job_data.get("semantic_fingerprint"):
            job_data["semantic_fingerprint"] = job_data["dedup_hash"]
        return job_data
