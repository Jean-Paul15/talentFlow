from __future__ import annotations

import asyncio
import json
import os
import time
from dataclasses import dataclass
from typing import Any, Optional

import httpx
from tenacity import RetryError, retry, retry_if_exception_type, stop_after_attempt, wait_exponential

try:  # pragma: no cover
    from .metrics import llm_call_duration_seconds, llm_calls_total
except Exception:  # pragma: no cover
    llm_call_duration_seconds = None
    llm_calls_total = None


def redact_key(value: str) -> str:
    normalized = (value or "").strip()
    if len(normalized) <= 8:
        return "***"
    return f"{normalized[:4]}...{normalized[-4:]}"


@dataclass
class DeepSeekGenerationResult:
    text: str
    model: str
    api_key_redacted: str
    latency_ms: float
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    estimated_input_cost_usd: float = 0.0
    estimated_output_cost_usd: float = 0.0
    estimated_cost_usd: float = 0.0


@dataclass
class DeepSeekLLM:
    api_key: str
    model: str
    base_url: str
    temperature: float = 0.2
    max_output_tokens: int = 1024
    timeout_seconds: int = 45
    max_retries: int = 2
    retry_base_seconds: float = 1.0
    input_cost_per_million_cache_miss: float = 0.28
    output_cost_per_million: float = 0.42

    @classmethod
    def from_env(
        cls,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
    ) -> "DeepSeekLLM":
        api_key = (os.getenv("DEEPSEEK_API_KEY", "") or "").strip()
        base_url = (
            os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com").strip()
            or "https://api.deepseek.com"
        ).rstrip("/")
        resolved_model = (
            (model or "").strip()
            or os.getenv("DEEPSEEK_MODEL", "").strip()
            or "deepseek-chat"
        )
        return cls(
            api_key=api_key,
            model=resolved_model,
            base_url=base_url,
            temperature=float(
                temperature
                if temperature is not None
                else os.getenv("LLM_TEMPERATURE", "0.2")
            ),
            max_output_tokens=int(
                os.getenv(
                    "DEEPSEEK_MAX_OUTPUT_TOKENS",
                    os.getenv("LLM_MAX_TOKENS", "1024"),
                )
            ),
            timeout_seconds=int(os.getenv("DEEPSEEK_TIMEOUT_SECONDS", "45")),
            max_retries=max(1, int(os.getenv("DEEPSEEK_MAX_RETRIES", "2"))),
            retry_base_seconds=float(
                os.getenv("DEEPSEEK_RETRY_BASE_SECONDS", "1.0")
            ),
            input_cost_per_million_cache_miss=float(
                os.getenv("DEEPSEEK_INPUT_COST_PER_MILLION_CACHE_MISS", "0.28")
            ),
            output_cost_per_million=float(
                os.getenv("DEEPSEEK_OUTPUT_COST_PER_MILLION", "0.42")
            ),
        )

    async def agenerate(
        self,
        prompt: str,
        *,
        response_json_schema: dict[str, Any] | None = None,
        messages: list[dict[str, str]] | None = None,
        max_output_tokens: int | None = None,
    ) -> DeepSeekGenerationResult:
        return await asyncio.to_thread(
            self.generate,
            prompt,
            response_json_schema=response_json_schema,
            messages=messages,
            max_output_tokens=max_output_tokens,
        )

    def generate(
        self,
        prompt: str,
        *,
        response_json_schema: dict[str, Any] | None = None,
        messages: list[dict[str, str]] | None = None,
        max_output_tokens: int | None = None,
    ) -> DeepSeekGenerationResult:
        if not self.api_key:
            _record_deepseek_metric(status="error", duration_seconds=0.0)
            raise RuntimeError("DeepSeek unavailable: no API key configured")

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
        def _call() -> DeepSeekGenerationResult:
            return self._call_once(
                prompt=prompt,
                response_json_schema=response_json_schema,
                messages=messages,
                max_output_tokens=max_output_tokens,
            )

        try:
            result = _call()
            _record_deepseek_metric(
                status="success", duration_seconds=result.latency_ms / 1000.0
            )
            return result
        except RetryError as err:  # pragma: no cover
            _record_deepseek_metric(status="error", duration_seconds=0.0)
            last = err.last_attempt.exception()
            raise last or err
        except Exception:
            _record_deepseek_metric(status="error", duration_seconds=0.0)
            raise

    def _call_once(
        self,
        *,
        prompt: str,
        response_json_schema: dict[str, Any] | None = None,
        messages: list[dict[str, str]] | None = None,
        max_output_tokens: int | None = None,
    ) -> DeepSeekGenerationResult:
        started = time.perf_counter()
        request_messages = messages or [
            {"role": "system", "content": "You are a reliable JSON-only career assistant."},
            {"role": "user", "content": prompt},
        ]
        body: dict[str, Any] = {
            "model": self.model,
            "messages": request_messages,
            "temperature": self.temperature,
            "stream": False,
            "max_tokens": int(max_output_tokens or self.max_output_tokens),
        }
        if response_json_schema:
            body["response_format"] = {
                "type": "json_object",
            }

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        with httpx.Client(timeout=self.timeout_seconds) as client:
            response = client.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=body,
            )
            response.raise_for_status()
            payload = response.json()
        choice = ((payload.get("choices") or [None])[0] or {})
        message = choice.get("message") or {}
        text = str(message.get("content") or "").strip()
        if not text:
            raise RuntimeError("DeepSeek returned empty content")
        if response_json_schema:
            json.loads(text)
        usage = payload.get("usage") or {}
        prompt_tokens = int(usage.get("prompt_tokens") or 0)
        completion_tokens = int(usage.get("completion_tokens") or 0)
        total_tokens = int(usage.get("total_tokens") or (prompt_tokens + completion_tokens))
        input_cost = (prompt_tokens / 1_000_000.0) * max(self.input_cost_per_million_cache_miss, 0.0)
        output_cost = (completion_tokens / 1_000_000.0) * max(self.output_cost_per_million, 0.0)
        return DeepSeekGenerationResult(
            text=text,
            model=self.model,
            api_key_redacted=redact_key(self.api_key),
            latency_ms=(time.perf_counter() - started) * 1000.0,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            estimated_input_cost_usd=input_cost,
            estimated_output_cost_usd=output_cost,
            estimated_cost_usd=(input_cost + output_cost),
        )


def _record_deepseek_metric(*, status: str, duration_seconds: float) -> None:
    if llm_calls_total is not None:
        llm_calls_total.labels(provider="deepseek", status=status).inc()
    if llm_call_duration_seconds is not None and duration_seconds > 0:
        llm_call_duration_seconds.labels(provider="deepseek").observe(duration_seconds)
