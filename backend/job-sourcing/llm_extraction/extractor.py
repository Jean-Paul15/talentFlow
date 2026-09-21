# Extracteur LLM pour enrichissement des offres d'emploi
# Mode officiel: Gemini uniquement avec fallback par seconde cle

from __future__ import annotations

import json
from typing import Dict, List, Optional

import httpx
from loguru import logger

from .config import LLMConfig


class LLMExtractor:
    """
    Extracteur intelligent base sur Gemini.
    Enrichit les offres d'emploi apres l'extraction SmartParser.

    Si Gemini est indisponible, l'extraction retourne None et le pipeline
    reste en mode deterministe sans fallback local.
    """

    def __init__(self, config: LLMConfig = None):
        self.config = config or LLMConfig.from_env()
        self.enabled = self.config.enabled

        if self.enabled:
            logger.info("LLM Extractor actif: gemini/{}", self.config.model)

    def enrich_job(self, job_data: Dict) -> Dict:
        if not self.enabled:
            return job_data

        description = job_data.get("description", "")
        if not description or len(description) < 50:
            return job_data

        if not job_data.get("sector"):
            sector = self.classify_sector(description)
            if sector:
                job_data["sector"] = sector

        if not job_data.get("skills"):
            skills = self.extract_skills(description)
            if skills:
                job_data["skills"] = skills

        missing = self._find_missing_fields(job_data)
        if missing:
            extracted = self.extract_structured(description)
            if extracted:
                for field_name in missing:
                    value = extracted.get(field_name)
                    if value and value != "null":
                        job_data[field_name] = value

        return job_data

    def extract_structured(self, text: str) -> Optional[Dict]:
        prompt = self.config.prompts.get("extract_structured", "")
        response = self._call_llm(system=prompt, user=text[:3000])
        return self._parse_json_response(response)

    def classify_sector(self, text: str) -> Optional[str]:
        prompt = self.config.prompts.get("classify_sector", "")
        response = self._call_llm(system=prompt, user=text[:2000])
        if response:
            sector = response.strip().lower().replace(" ", "_")
            return sector if len(sector) < 50 else None
        return None

    def extract_skills(self, text: str) -> Optional[List[str]]:
        prompt = self.config.prompts.get("extract_skills", "")
        response = self._call_llm(system=prompt, user=text[:3000])
        result = self._parse_json_response(response)
        if isinstance(result, list):
            return result
        return None

    def summarize(self, text: str) -> Optional[str]:
        prompt = self.config.prompts.get("summarize", "")
        return self._call_llm(system=prompt, user=text[:3000])

    def _call_llm(self, system: str, user: str) -> Optional[str]:
        if not self.enabled:
            return None

        errors: List[str] = []
        models = self.config.model_priority or [self.config.model]

        for api_key in self.config.api_keys:
            for model in models:
                try:
                    response = self._call_gemini(
                        api_key=api_key,
                        model=model,
                        system=system,
                        user=user,
                    )
                    if response:
                        return response
                except Exception as err:
                    redacted = _redact_key(api_key)
                    errors.append(f"{model}@{redacted}: {err}")
                    logger.warning(
                        "Echec Gemini extractor model={} key={}: {}",
                        model,
                        redacted,
                        err,
                    )

        if errors:
            logger.error("Aucun appel Gemini extractor n'a abouti: {}", " | ".join(errors))
        return None

    def _call_gemini(
        self,
        *,
        api_key: str,
        model: str,
        system: str,
        user: str,
    ) -> Optional[str]:
        url = f"{self.config.base_url}/models/{model}:generateContent"
        headers = {"Content-Type": "application/json"}
        payload = {
            "system_instruction": {"parts": [{"text": system}]},
            "contents": [{"parts": [{"text": user}]}],
            "generationConfig": {
                "temperature": self.config.temperature,
                "maxOutputTokens": self.config.max_tokens,
            },
        }
        with httpx.Client(timeout=60) as client:
            response = client.post(
                url,
                headers=headers,
                params={"key": api_key},
                json=payload,
            )
            response.raise_for_status()
            data = response.json()

        candidates = data.get("candidates") or []
        if not candidates:
            block_reason = (data.get("promptFeedback") or {}).get("blockReason")
            if block_reason:
                raise RuntimeError(f"Gemini blocked prompt: {block_reason}")
            return None

        finish_reason = str((candidates[0] or {}).get("finishReason") or "").upper()
        if finish_reason not in {"", "STOP", "MAX_TOKENS"}:
            raise RuntimeError(f"Gemini finish reason: {finish_reason}")

        parts = (((candidates[0] or {}).get("content") or {}).get("parts") or [])
        text = "".join(str(part.get("text") or "") for part in parts).strip()
        return text or None

    def _parse_json_response(self, text: Optional[str]) -> Optional[dict]:
        if not text:
            return None
        if "```json" in text:
            text = text.split("```json", 1)[1].split("```", 1)[0]
        elif "```" in text:
            text = text.split("```", 1)[1].split("```", 1)[0]
        text = text.strip()
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            logger.debug("Echec parsing JSON LLM: {}...", text[:100])
            return None

    def _find_missing_fields(self, job: Dict) -> List[str]:
        important = [
            "contract_type",
            "salary",
            "experience",
            "education",
            "sector",
            "deadline",
        ]
        missing = []
        for field_name in important:
            value = job.get(field_name)
            if not value or value == "Non precise":
                missing.append(field_name)
        return missing


def _redact_key(value: str) -> str:
    normalized = (value or "").strip()
    if len(normalized) <= 8:
        return "***"
    return f"{normalized[:4]}...{normalized[-4:]}"
