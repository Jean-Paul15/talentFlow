from __future__ import annotations

import math
from typing import Dict, Iterable, List, Sequence


def normalize_relevance(
    *,
    relevant_ids: Sequence[str] | None = None,
    graded_relevance: Dict[str, float] | None = None,
) -> Dict[str, float]:
    rel: Dict[str, float] = {}
    if graded_relevance:
        for doc_id, grade in graded_relevance.items():
            try:
                rel[str(doc_id)] = float(grade)
            except Exception:
                continue
    if relevant_ids:
        for doc_id in relevant_ids:
            rel.setdefault(str(doc_id), 1.0)
    return rel


def _extract_ids(rows: Iterable[dict]) -> List[str]:
    return [str(r.get("id")) for r in rows if r.get("id") is not None]


def _dcg(ids: Sequence[str], rel: Dict[str, float], k: int) -> float:
    score = 0.0
    for i, doc_id in enumerate(ids[:k], start=1):
        gain = rel.get(str(doc_id), 0.0)
        if gain <= 0:
            continue
        score += (2**gain - 1) / math.log2(i + 1)
    return score


def _idcg(rel: Dict[str, float], k: int) -> float:
    ideal_gains = sorted(rel.values(), reverse=True)[:k]
    score = 0.0
    for i, gain in enumerate(ideal_gains, start=1):
        score += (2**gain - 1) / math.log2(i + 1)
    return score


def ndcg_at_k(rows: Sequence[dict], rel: Dict[str, float], k: int) -> float:
    if k <= 0:
        return 0.0
    ids = _extract_ids(rows)
    denom = _idcg(rel, k)
    if denom <= 0:
        return 0.0
    return float(_dcg(ids, rel, k) / denom)


def precision_at_k(rows: Sequence[dict], rel: Dict[str, float], k: int) -> float:
    if k <= 0:
        return 0.0
    ids = _extract_ids(rows)[:k]
    if not ids:
        return 0.0
    hits = sum(1 for doc_id in ids if rel.get(doc_id, 0.0) > 0)
    return float(hits / max(k, 1))


def recall_at_k(rows: Sequence[dict], rel: Dict[str, float], k: int) -> float:
    positives = sum(1 for v in rel.values() if v > 0)
    if positives <= 0:
        return 0.0
    ids = _extract_ids(rows)[:k]
    hits = sum(1 for doc_id in ids if rel.get(doc_id, 0.0) > 0)
    return float(hits / positives)


def mrr(rows: Sequence[dict], rel: Dict[str, float]) -> float:
    for i, doc_id in enumerate(_extract_ids(rows), start=1):
        if rel.get(doc_id, 0.0) > 0:
            return float(1.0 / i)
    return 0.0


def evaluate_ranked_list(
    rows: Sequence[dict],
    rel: Dict[str, float],
    *,
    k_values: Sequence[int],
) -> Dict[str, object]:
    metrics = {
        "mrr": mrr(rows, rel),
        "precision": {},
        "recall": {},
        "ndcg": {},
    }
    for k in sorted({int(k) for k in k_values if int(k) > 0}):
        metrics["precision"][str(k)] = precision_at_k(rows, rel, k)
        metrics["recall"][str(k)] = recall_at_k(rows, rel, k)
        metrics["ndcg"][str(k)] = ndcg_at_k(rows, rel, k)
    return metrics

