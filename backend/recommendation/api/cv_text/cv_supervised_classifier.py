"""Lightweight supervised CV document classifier (Multinomial Naive Bayes)."""

from __future__ import annotations

import json
import math
import os
import re
from collections import Counter
from functools import lru_cache
from pathlib import Path

from .text_utils import _fold_text

LABELS = ("cv", "non_cv", "ambiguous")
TOKEN_PATTERN = re.compile(r"[a-z0-9][a-z0-9+#._-]{1,}", flags=re.IGNORECASE)
DEFAULT_MODEL_PATH = Path(__file__).resolve().parents[2] / "data" / "cv_supervised_model.json"


def _env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _tokenize(text: str) -> Counter[str]:
    normalized = _fold_text(text)
    tokens = TOKEN_PATTERN.findall(normalized)
    return Counter(tokens)


def _resolve_model_path() -> Path:
    raw = str(os.getenv("CV_DOCUMENT_SUPERVISED_MODEL_PATH", "")).strip()
    return Path(raw) if raw else DEFAULT_MODEL_PATH


@lru_cache(maxsize=4)
def _load_model(path: str, mtime_ns: int) -> dict | None:
    del mtime_ns
    p = Path(path)
    if not p.exists():
        return None
    try:
        payload = json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return None
    if not isinstance(payload, dict):
        return None
    if not isinstance(payload.get("token_counts"), dict):
        return None
    if not isinstance(payload.get("class_counts"), dict):
        return None
    return payload


def _get_model() -> dict | None:
    path = _resolve_model_path()
    if not path.exists():
        return None
    stat = path.stat()
    return _load_model(str(path), stat.st_mtime_ns)


def predict_supervised_cv_kind(text: str) -> tuple[str, float] | None:
    if not _env_bool("CV_DOCUMENT_SUPERVISED_ENABLED", True):
        return None

    model = _get_model()
    if not model:
        return None

    token_counts = _tokenize(text or "")
    if not token_counts:
        return None

    min_tokens = int(str(os.getenv("CV_DOCUMENT_SUPERVISED_MIN_TOKENS", "8")).strip() or "8")
    if sum(token_counts.values()) < min_tokens:
        return None

    alpha = float(str(model.get("alpha", 1.0)).strip() or "1.0")
    labels = [label for label in model.get("labels", LABELS) if label in LABELS] or list(LABELS)
    class_counts = {label: int(model["class_counts"].get(label, 0)) for label in labels}
    priors = {label: float(model.get("priors", {}).get(label, 0.0)) for label in labels}
    token_totals = {label: int(model.get("token_totals", {}).get(label, 0)) for label in labels}
    token_maps = {
        label: {str(k): int(v) for k, v in (model["token_counts"].get(label, {}) or {}).items()}
        for label in labels
    }

    vocab_size = max(int(model.get("vocabulary_size", 0)), 1)
    total_samples = max(sum(class_counts.values()), 1)

    log_scores: dict[str, float] = {}
    for label in labels:
        prior = priors.get(label, 0.0)
        if prior <= 0:
            prior = class_counts[label] / total_samples
        prior = max(prior, 1e-9)
        log_score = math.log(prior)

        denom = token_totals.get(label, 0) + alpha * vocab_size
        denom = max(denom, 1e-9)
        label_tokens = token_maps.get(label, {})

        for token, count in token_counts.items():
            observed = label_tokens.get(token, 0)
            token_prob = (observed + alpha) / denom
            log_score += count * math.log(max(token_prob, 1e-12))
        log_scores[label] = log_score

    if not log_scores:
        return None

    best_label = max(log_scores, key=log_scores.get)
    max_log = log_scores[best_label]
    exp_sum = sum(math.exp(score - max_log) for score in log_scores.values())
    confidence = 1.0 / max(exp_sum, 1e-12)

    min_conf = float(str(os.getenv("CV_DOCUMENT_SUPERVISED_MIN_CONFIDENCE", "0.45")).strip() or "0.45")
    if confidence < min_conf:
        return None

    return best_label, round(min(confidence, 1.0), 3)
