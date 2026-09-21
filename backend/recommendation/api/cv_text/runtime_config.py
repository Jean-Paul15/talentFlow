"""Shared runtime/env helpers for CV text recommendation modules."""

from __future__ import annotations

import os

__all__ = ["_env_flag", "_env_bool", "_env_int", "_env_float", "_provider_order"]


def _env_flag(name: str, default: bool) -> bool:
    raw = str(os.getenv(name, "true" if default else "false")).strip().lower()
    return raw in {"1", "true", "yes", "on"}


def _env_bool(name: str, default: bool) -> bool:
    return _env_flag(name, default)


def _env_int(name: str, default: int) -> int:
    try:
        return int(str(os.getenv(name, str(default))).strip())
    except Exception:
        return int(default)


def _env_float(name: str, default: float) -> float:
    try:
        return float(str(os.getenv(name, str(default))).strip())
    except Exception:
        return float(default)


def _provider_order() -> list[str]:
    raw = str(os.getenv("LLM_PROVIDER_ORDER", "gemini,deepseek")).strip()
    candidates = [p.strip().lower() for p in raw.split(",") if p.strip()]
    out: list[str] = []
    for provider in candidates:
        if provider in {"gemini", "deepseek"} and provider not in out:
            out.append(provider)
    if not out:
        return ["gemini", "deepseek"]
    return out
