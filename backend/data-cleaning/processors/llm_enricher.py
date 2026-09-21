from __future__ import annotations

import json
import os
import re
import time
from dataclasses import dataclass
from typing import List, Optional

import httpx
from loguru import logger
from mistralai import Mistral
from tenacity import RetryError, retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from processors.schemas import SkillExtractionOutput


EXTRACTION_PROMPT = """Tu analyses UNE offre d'emploi.
Réponds UNIQUEMENT avec un objet JSON valide, sans markdown, sans texte avant/après.

Schéma JSON strict:
{{
  "hard_skills": ["..."],
  "soft_skills": ["..."],
  "experience_years": 0,
  "education_level": "..."
}}

Règles:
- hard_skills: technologies/outils/méthodes concrètes uniquement.
- soft_skills: compétences comportementales uniquement.
- experience_years: entier >= 0 (0 si absent).
- education_level: texte court ("Non précisé" si absent).
- Ne rien inventer hors du texte.

Titre: {title}
Description: {description}
"""


@dataclass
class LLMEnrichmentResult:
    payload: dict
    provider_used: str
    degraded: bool
    fallback_triggered: bool
    latency_ms: float


@dataclass
class LocalOpenAIEnricher:
    base_url: str
    model: str
    timeout_seconds: int
    temperature: float
    max_tokens: int
    max_retries: int
    retry_base_seconds: float
    num_ctx: int
    top_p: float
    repeat_penalty: float
    api_key: str = ""

    @property
    def enabled(self) -> bool:
        return bool(self.base_url and self.model)

    def extract(self, prompt: str) -> LLMEnrichmentResult:
        @retry(
            stop=stop_after_attempt(max(1, self.max_retries + 1)),
            wait=wait_exponential(
                multiplier=max(self.retry_base_seconds, 0.1),
                min=max(self.retry_base_seconds, 0.1),
                max=8,
            ),
            retry=retry_if_exception_type(Exception),
            reraise=True,
        )
        def _call() -> LLMEnrichmentResult:
            started = time.perf_counter()
            url = f"{self.base_url.rstrip('/')}/chat/completions"
            headers = {"Content-Type": "application/json"}
            if self.api_key:
                headers["Authorization"] = f"Bearer {self.api_key}"
            payload = {
                "model": self.model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": self.temperature,
                "max_tokens": self.max_tokens,
                "stream": False,
                "response_format": {"type": "json_object"},
                "format": "json",
                "options": {
                    "num_ctx": self.num_ctx,
                    "num_predict": self.max_tokens,
                    "top_p": self.top_p,
                    "repeat_penalty": self.repeat_penalty,
                    "temperature": self.temperature,
                },
            }
            with httpx.Client(timeout=self.timeout_seconds) as client:
                response = client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()
            choice = ((data.get("choices") or [None])[0] or {})
            message = choice.get("message") or {}
            content_value = message.get("content")
            if isinstance(content_value, list):
                parts: list[str] = []
                for item in content_value:
                    if isinstance(item, dict):
                        text = item.get("text") or item.get("content")
                        if text:
                            parts.append(str(text))
                    elif item:
                        parts.append(str(item))
                content = "".join(parts).strip()
            else:
                content = str(content_value or "").strip()
            if not content:
                raise RuntimeError("Local LLM returned empty content")
            parsed = _parse_structured_output(content)
            if not parsed:
                raise RuntimeError("Local LLM returned non-parseable JSON")
            return LLMEnrichmentResult(
                payload=parsed,
                provider_used="qwen_local",
                degraded=False,
                fallback_triggered=False,
                latency_ms=(time.perf_counter() - started) * 1000.0,
            )

        try:
            return _call()
        except RetryError as err:  # pragma: no cover
            last = err.last_attempt.exception()
            raise last or err


@dataclass
class MistralEnricher:
    api_key: str
    model: str
    timeout_seconds: int
    temperature: float
    max_tokens: int
    max_retries: int
    retry_base_seconds: float

    @property
    def enabled(self) -> bool:
        return bool(self.api_key)

    def extract(self, prompt: str) -> LLMEnrichmentResult:
        @retry(
            stop=stop_after_attempt(max(1, self.max_retries + 1)),
            wait=wait_exponential(multiplier=max(self.retry_base_seconds, 0.1), min=max(self.retry_base_seconds, 0.1), max=8),
            retry=retry_if_exception_type(Exception),
            reraise=True,
        )
        def _call() -> LLMEnrichmentResult:
            started = time.perf_counter()
            client = Mistral(
                api_key=self.api_key,
                timeout_ms=self.timeout_seconds * 1000,
            )
            response = client.chat.complete(
                model=self.model,
                messages=[
                    {
                        "role": "user",
                        "content": prompt,
                    }
                ],
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                response_format={"type": "json_object"},
            )
            choice = (response.choices or [None])[0]
            message = getattr(choice, "message", None)
            content = getattr(message, "content", None)
            if isinstance(content, list):
                parts: List[str] = []
                for item in content:
                    text_value = getattr(item, "text", None)
                    if text_value is None and isinstance(item, dict):
                        text_value = item.get("text")
                    if text_value:
                        parts.append(str(text_value))
                content = "".join(parts)
            text = str(content or "").strip()
            if not text:
                raise RuntimeError("Mistral returned empty content")
            payload = _parse_structured_output(text)
            if not payload:
                raise RuntimeError("Mistral returned non-parseable JSON")
            return LLMEnrichmentResult(
                payload=payload,
                provider_used="mistral",
                degraded=False,
                fallback_triggered=False,
                latency_ms=(time.perf_counter() - started) * 1000.0,
            )

        try:
            return _call()
        except RetryError as err:  # pragma: no cover
            last = err.last_attempt.exception()
            raise last or err


class LLMEnricher:
    """
    Orchestrateur d'enrichissement LLM pour data-cleaning.
    Ordre officiel:
    1. Qwen local (si provider=qwen)
    2. Mistral cloud (fallback ou provider principal)
    3. retour None -> SkillEnricher bascule en NER/patterns
    """

    def __init__(self, model: str | None = None):
        self.enabled = (
            os.getenv("DATA_CLEANING_LLM_ENABLED", os.getenv("LLM_ENABLED", "false")).strip().lower()
            == "true"
        )
        self.provider = (os.getenv("DATA_CLEANING_LLM_PROVIDER", "mistral").strip().lower() or "mistral")
        self.timeout_seconds = int(os.getenv("MISTRAL_TIMEOUT_SECONDS", os.getenv("LLM_TIMEOUT_SECONDS", "45")))
        self.max_tokens = int(os.getenv("LLM_MAX_TOKENS", "300"))
        self.temperature = float(os.getenv("LLM_TEMPERATURE", "0.1"))
        self.title_max_chars = int(os.getenv("DATA_CLEANING_LLM_TITLE_MAX_CHARS", "220"))
        self.description_max_chars = int(os.getenv("DATA_CLEANING_LLM_DESC_MAX_CHARS", "650"))
        self.max_retries = max(1, int(os.getenv("MISTRAL_MAX_RETRIES", "2")))
        self.retry_base_seconds = float(os.getenv("MISTRAL_RETRY_BASE_SECONDS", "1.0"))
        self.local_fallback_enabled = str(
            os.getenv("DATA_CLEANING_LLM_FALLBACK_MISTRAL_ENABLED", "true")
        ).strip().lower() in {"1", "true", "yes", "on"}
        self.last_error: Optional[str] = None

        self.qwen_local = LocalOpenAIEnricher(
            base_url=(os.getenv("QWEN_LOCAL_BASE_URL", "http://qwen-local:11434/v1").strip()),
            model=(os.getenv("QWEN_LOCAL_MODEL", "qwen2.5:7b-instruct").strip() or "qwen2.5:7b-instruct"),
            timeout_seconds=int(os.getenv("QWEN_LOCAL_TIMEOUT_SECONDS", str(self.timeout_seconds))),
            temperature=self.temperature,
            max_tokens=self.max_tokens,
            max_retries=max(1, int(os.getenv("QWEN_LOCAL_MAX_RETRIES", "1"))),
            retry_base_seconds=float(os.getenv("QWEN_LOCAL_RETRY_BASE_SECONDS", str(self.retry_base_seconds))),
            num_ctx=max(1024, int(os.getenv("QWEN_LOCAL_NUM_CTX", "2048"))),
            top_p=float(os.getenv("QWEN_LOCAL_TOP_P", "0.9")),
            repeat_penalty=float(os.getenv("QWEN_LOCAL_REPEAT_PENALTY", "1.05")),
            api_key=(os.getenv("QWEN_LOCAL_API_KEY", "").strip()),
        )

        self.mistral = MistralEnricher(
            api_key=os.getenv("MISTRAL_API_KEY", "").strip(),
            model=(model or os.getenv("MISTRAL_MODEL", "mistral-small-latest")).strip() or "mistral-small-latest",
            timeout_seconds=self.timeout_seconds,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
            max_retries=self.max_retries,
            retry_base_seconds=self.retry_base_seconds,
        )
        logger.info(
            "LLMEnricher data-cleaning: enabled={} provider={} qwen_local={} mistral={} model={}",
            self.enabled,
            self.provider,
            self.qwen_local.enabled,
            self.mistral.enabled,
            self.mistral.model,
        )

    def extract_skills(self, title: str, description: str) -> Optional[LLMEnrichmentResult]:
        self.last_error = None
        if not self.enabled:
            return None

        prompt = EXTRACTION_PROMPT.format(
            title=(title or "")[: self.title_max_chars],
            description=(description or "")[: self.description_max_chars],
        )
        errors: List[str] = []

        if self.provider == "qwen" and self.qwen_local.enabled:
            try:
                result = self.qwen_local.extract(prompt)
                self._log_provider_success(result)
                return result
            except Exception as err:
                errors.append(f"qwen_local: {err}")
                logger.warning("Data-cleaning Qwen local indisponible: {}", err)

            if self.local_fallback_enabled and self.mistral.enabled:
                try:
                    result = self.mistral.extract(prompt)
                    result.provider_used = "mistral_fallback"
                    result.fallback_triggered = True
                    result.degraded = True
                    self._log_provider_success(result)
                    return result
                except Exception as err:
                    errors.append(f"mistral_fallback: {err}")
                    logger.warning("Data-cleaning Mistral fallback indisponible: {}", err)

        if self.provider == "mistral" and self.mistral.enabled:
            try:
                result = self.mistral.extract(prompt)
                self._log_provider_success(result)
                return result
            except Exception as err:
                errors.append(f"mistral: {err}")
                logger.warning("Data-cleaning Mistral indisponible: {}", err)
                if self.qwen_local.enabled:
                    try:
                        result = self.qwen_local.extract(prompt)
                        result.provider_used = "qwen_local_fallback"
                        result.fallback_triggered = True
                        result.degraded = True
                        self._log_provider_success(result)
                        return result
                    except Exception as qerr:
                        errors.append(f"qwen_local_fallback: {qerr}")
                        logger.warning("Data-cleaning Qwen local fallback indisponible: {}", qerr)

        if errors:
            self.last_error = " | ".join(errors)
            logger.error("Data-cleaning LLM indisponible -> fallback NER/patterns: {}", self.last_error)
        return None

    def _log_provider_success(self, result: LLMEnrichmentResult) -> None:
        logger.info(
            "data_cleaning_llm_provider={} latency_ms={:.1f} fallback_triggered={} llm_degraded={}",
            result.provider_used,
            result.latency_ms,
            result.fallback_triggered,
            result.degraded,
        )


def _parse_structured_output(text: str) -> Optional[dict]:
    if not text:
        return None

    cleaned = text.strip()
    if "```json" in cleaned:
        cleaned = cleaned.split("```json", 1)[1].split("```", 1)[0]
    elif "```" in cleaned:
        cleaned = cleaned.split("```", 1)[1].split("```", 1)[0]
    cleaned = cleaned.strip()

    # Tolerate wrappers around JSON (common with local LLMs) while keeping
    # strict schema validation afterwards.
    first = cleaned.find("{")
    last = cleaned.rfind("}")
    if first >= 0 and last > first:
        cleaned = cleaned[first : last + 1].strip()

    try:
        payload = json.loads(cleaned)
        payload = _normalize_payload(payload)
        result = SkillExtractionOutput.model_validate(payload)
        return {
            "hard_skills": result.hard_skills[:25],
            "soft_skills": result.soft_skills[:15],
            "experience_years": result.experience_years,
            "education_level": result.education_level,
        }
    except Exception as err:
        logger.debug("Reponse LLM non exploitable pour enrichment: {}", err)
        return None


def _normalize_payload(payload: object) -> dict:
    if not isinstance(payload, dict):
        return {
            "hard_skills": [],
            "soft_skills": [],
            "experience_years": 0,
            "education_level": "Non précisé",
        }

    def _as_list(value: object) -> list[str]:
        if isinstance(value, list):
            return [str(x).strip() for x in value if str(x).strip()]
        if isinstance(value, str) and value.strip():
            return [value.strip()]
        return []

    def _as_int(value: object) -> int:
        if isinstance(value, int):
            return max(0, value)
        if isinstance(value, float):
            return max(0, int(value))
        if isinstance(value, str):
            m = re.search(r"\d+", value)
            if m:
                try:
                    return max(0, int(m.group(0)))
                except Exception:
                    return 0
        return 0

    education = str(payload.get("education_level") or "").strip() or "Non précisé"
    return {
        "hard_skills": _as_list(payload.get("hard_skills")),
        "soft_skills": _as_list(payload.get("soft_skills")),
        "experience_years": _as_int(payload.get("experience_years")),
        "education_level": education,
    }
