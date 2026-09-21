from __future__ import annotations

import asyncio
import json
import os
import re
import time
from dataclasses import dataclass
from typing import Any, List, Optional

from google import genai
from google.genai import types
from tenacity import RetryError, retry, retry_if_exception_type, stop_after_attempt, wait_exponential

try:  # pragma: no cover
    from .metrics import llm_call_duration_seconds, llm_calls_total
except Exception:  # pragma: no cover
    llm_call_duration_seconds = None
    llm_calls_total = None


def _collect_api_keys() -> List[str]:
    values: List[str] = []
    for value in (
        os.getenv("GEMINI_API_KEY", ""),
        os.getenv("GEMINI_API_KEY_FALLBACK", ""),
    ):
        normalized = value.strip()
        if normalized and normalized not in values:
            values.append(normalized)

    for value in os.getenv("GEMINI_API_KEYS", "").split(","):
        normalized = value.strip()
        if normalized and normalized not in values:
            values.append(normalized)
    return values


def _collect_models(primary: Optional[str] = None) -> List[str]:
    base = (primary or os.getenv("GEMINI_MODEL", "gemini-2.5-flash")).strip() or "gemini-2.5-flash"
    values: List[str] = [base]
    for value in os.getenv(
        "GEMINI_MODEL_PRIORITY",
        "gemini-2.5-flash,gemini-2.5-flash-lite,gemini-2.0-flash",
    ).split(","):
        normalized = value.strip()
        if normalized and normalized not in values:
            values.append(normalized)
    return values


def redact_key(value: str) -> str:
    normalized = (value or "").strip()
    if len(normalized) <= 8:
        return "***"
    return f"{normalized[:4]}...{normalized[-4:]}"


def sanitize_error_message(value: str) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    text = re.sub(r"(key=)[A-Za-z0-9_-]+", r"\1***", text, flags=re.IGNORECASE)
    text = re.sub(r"(api[_-]?key[=:]\s*)[A-Za-z0-9._-]+", r"\1***", text, flags=re.IGNORECASE)
    text = re.sub(r"(x-goog-api-key[=:]\s*)[A-Za-z0-9._-]+", r"\1***", text, flags=re.IGNORECASE)
    return text


@dataclass
class GeminiGenerationResult:
    text: str
    model: str
    api_key_redacted: str
    latency_ms: float


@dataclass
class GeminiLLM:
    api_keys: List[str]
    models: List[str]
    base_url: str
    temperature: float = 0.2
    max_output_tokens: int = 1024
    timeout_seconds: int = 45
    max_retries: int = 2
    retry_base_seconds: float = 1.0

    @classmethod
    def from_env(cls, model: Optional[str] = None, temperature: Optional[float] = None) -> "GeminiLLM":
        raw_base_url = (os.getenv("GEMINI_BASE_URL", "https://generativelanguage.googleapis.com").strip() or "https://generativelanguage.googleapis.com").rstrip("/")
        raw_base_url = re.sub(r"/v[0-9]+(?:beta)?$", "", raw_base_url)
        return cls(
            api_keys=_collect_api_keys(),
            models=_collect_models(model),
            base_url=raw_base_url,
            temperature=float(temperature if temperature is not None else os.getenv("LLM_TEMPERATURE", "0.2")),
            max_output_tokens=int(os.getenv("LLM_MAX_TOKENS", os.getenv("GEMINI_MAX_OUTPUT_TOKENS", "1024"))),
            timeout_seconds=int(os.getenv("GEMINI_TIMEOUT_SECONDS", "45")),
            max_retries=max(1, int(os.getenv("GEMINI_MAX_RETRIES", "2"))),
            retry_base_seconds=float(os.getenv("GEMINI_RETRY_BASE_SECONDS", "1.0")),
        )

    async def ainvoke(self, prompt: str) -> str:
        result = await self.agenerate(prompt)
        return result.text

    def invoke(self, prompt: str) -> str:
        return self.generate(prompt).text

    async def agenerate(
        self,
        prompt: str,
        *,
        response_mime_type: str | None = None,
        response_json_schema: dict[str, Any] | None = None,
    ) -> GeminiGenerationResult:
        return await asyncio.to_thread(
            self.generate,
            prompt,
            response_mime_type=response_mime_type,
            response_json_schema=response_json_schema,
        )

    def generate(
        self,
        prompt: str,
        *,
        response_mime_type: str | None = None,
        response_json_schema: dict[str, Any] | None = None,
    ) -> GeminiGenerationResult:
        if not self.api_keys:
            _record_gemini_metric(status="error", duration_seconds=0.0)
            raise RuntimeError("Gemini unavailable: no API key configured")

        errors: List[str] = []
        for model in self.models:
            for api_key in self.api_keys:
                try:
                    result = self._generate_for_key_and_model(
                        prompt=prompt,
                        api_key=api_key,
                        model=model,
                        response_mime_type=response_mime_type,
                        response_json_schema=response_json_schema,
                    )
                    _record_gemini_metric(status="success", duration_seconds=result.latency_ms / 1000.0)
                    return result
                except Exception as err:
                    _record_gemini_metric(status="error", duration_seconds=0.0)
                    errors.append(f"{model}@{redact_key(api_key)}: {sanitize_error_message(err)}")

        if errors:
            raise RuntimeError("Gemini unavailable: " + " | ".join(errors))
        raise RuntimeError("Gemini unavailable")

    def _generate_for_key_and_model(
        self,
        *,
        prompt: str,
        api_key: str,
        model: str,
        response_mime_type: str | None = None,
        response_json_schema: dict[str, Any] | None = None,
    ) -> GeminiGenerationResult:
        @retry(
            stop=stop_after_attempt(max(1, self.max_retries + 1)),
            wait=wait_exponential(multiplier=max(self.retry_base_seconds, 0.1), min=max(self.retry_base_seconds, 0.1), max=8),
            retry=retry_if_exception_type(Exception),
            reraise=True,
        )
        def _call() -> GeminiGenerationResult:
            return self._call_once(
                prompt=prompt,
                api_key=api_key,
                model=model,
                response_mime_type=response_mime_type,
                response_json_schema=response_json_schema,
            )

        try:
            return _call()
        except RetryError as err:  # pragma: no cover
            last = err.last_attempt.exception()
            raise last or err

    def _call_once(
        self,
        *,
        prompt: str,
        api_key: str,
        model: str,
        response_mime_type: str | None = None,
        response_json_schema: dict[str, Any] | None = None,
    ) -> GeminiGenerationResult:
        started = time.perf_counter()
        client = genai.Client(
            api_key=api_key,
            http_options=types.HttpOptions(
                baseUrl=self.base_url,
                timeout=self.timeout_seconds * 1000,
            ),
        )
        config: dict[str, Any] = {
            "temperature": self.temperature,
            "max_output_tokens": self.max_output_tokens,
        }
        if response_mime_type:
            config["response_mime_type"] = response_mime_type
        if response_json_schema:
            config["response_schema"] = response_json_schema
        response = client.models.generate_content(
            model=model,
            contents=prompt,
            config=config,
        )
        parsed = getattr(response, "parsed", None)
        if parsed is not None:
            if hasattr(parsed, "model_dump_json"):
                text = parsed.model_dump_json()
            else:
                text = json.dumps(parsed, ensure_ascii=False)
        else:
            text = (response.text or "").strip()
        if not text:
            raise RuntimeError("Gemini returned empty content")
        return GeminiGenerationResult(
            text=text,
            model=model,
            api_key_redacted=redact_key(api_key),
            latency_ms=(time.perf_counter() - started) * 1000.0,
        )


def _record_gemini_metric(*, status: str, duration_seconds: float) -> None:
    if llm_calls_total is not None:
        llm_calls_total.labels(provider="gemini", status=status).inc()
    if llm_call_duration_seconds is not None and duration_seconds > 0:
        llm_call_duration_seconds.labels(provider="gemini").observe(duration_seconds)
