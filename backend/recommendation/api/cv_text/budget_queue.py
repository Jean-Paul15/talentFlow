"""Queue helpers for CV text recommendation LLM calls."""

from __future__ import annotations

import asyncio

try:  # pragma: no cover
    from core.metrics import llm_queue_depth
except Exception:  # pragma: no cover
    llm_queue_depth = None

from .runtime_config import _env_int

__all__ = [
    "_llm_queue_max_size",
    "_llm_queue_wait_seconds",
    "_llm_queue_concurrency",
    "_get_llm_semaphore",
    "_update_llm_queue_metrics",
    "_acquire_llm_queue_slot",
    "_release_llm_queue_slot",
    "_llm_queue_lock",
    "_llm_queue_waiting",
    "_llm_queue_active",
]


def _llm_queue_max_size() -> int:
    return max(1, _env_int("DEEPSEEK_QUEUE_MAX_SIZE", 32))


def _llm_queue_wait_seconds() -> float:
    return max(0.1, _env_int("DEEPSEEK_QUEUE_WAIT_MS", 900) / 1000.0)


def _llm_queue_concurrency() -> int:
    return max(1, _env_int("DEEPSEEK_QUEUE_CONCURRENCY", 4))


def _get_llm_semaphore() -> asyncio.Semaphore:
    global _llm_semaphore
    if _llm_semaphore is None:
        _llm_semaphore = asyncio.Semaphore(_llm_queue_concurrency())
    return _llm_semaphore


def _update_llm_queue_metrics(provider: str) -> None:
    if llm_queue_depth is not None:
        try:
            llm_queue_depth.labels(provider=provider).set(float(max(0, _llm_queue_waiting)))
        except Exception:
            pass


async def _acquire_llm_queue_slot(provider: str) -> tuple[bool, str | None]:
    global _llm_queue_waiting, _llm_queue_active
    async with _llm_queue_lock:
        if _llm_queue_waiting >= _llm_queue_max_size():
            _update_llm_queue_metrics(provider)
            return False, "queue_overflow"
        _llm_queue_waiting += 1
        _update_llm_queue_metrics(provider)
    semaphore = _get_llm_semaphore()
    acquired = False
    try:
        await asyncio.wait_for(semaphore.acquire(), timeout=_llm_queue_wait_seconds())
        acquired = True
    except Exception:
        acquired = False
    finally:
        async with _llm_queue_lock:
            _llm_queue_waiting = max(0, _llm_queue_waiting - 1)
            if acquired:
                _llm_queue_active += 1
            _update_llm_queue_metrics(provider)
    if not acquired:
        return False, "queue_timeout"
    return True, None


async def _release_llm_queue_slot(provider: str) -> None:
    global _llm_queue_active
    async with _llm_queue_lock:
        _llm_queue_active = max(0, _llm_queue_active - 1)
        _update_llm_queue_metrics(provider)
    _get_llm_semaphore().release()


_llm_queue_lock = asyncio.Lock()
_llm_queue_waiting = 0
_llm_queue_active = 0
_llm_semaphore: asyncio.Semaphore | None = None
