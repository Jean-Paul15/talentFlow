from __future__ import annotations

from api.schemas import RankingMetrics


def update_metric_accumulators(
    baseline_rank: RankingMetrics,
    reranked_rank: RankingMetrics,
    ndcg_baseline_acc: dict[str, float],
    ndcg_rerank_acc: dict[str, float],
) -> tuple[float, float]:
    for k, v in baseline_rank.ndcg.items():
        ndcg_baseline_acc[k] = ndcg_baseline_acc.get(k, 0.0) + float(v)
    for k, v in reranked_rank.ndcg.items():
        ndcg_rerank_acc[k] = ndcg_rerank_acc.get(k, 0.0) + float(v)
    return float(baseline_rank.mrr), float(reranked_rank.mrr)


def mean_metrics(
    evaluated: int,
    ndcg_baseline_acc: dict[str, float],
    ndcg_rerank_acc: dict[str, float],
    mrr_baseline_acc: float,
    mrr_rerank_acc: float,
) -> dict[str, object]:
    mean_baseline_ndcg = {k: v / evaluated for k, v in ndcg_baseline_acc.items()}
    mean_reranked_ndcg = {k: v / evaluated for k, v in ndcg_rerank_acc.items()}
    ndcg_gain_abs = {
        k: float(mean_reranked_ndcg.get(k, 0.0) - mean_baseline_ndcg.get(k, 0.0))
        for k in sorted(set(mean_baseline_ndcg) | set(mean_reranked_ndcg))
    }
    ndcg_gain_pct = {
        k: (ndcg_gain_abs[k] / mean_baseline_ndcg[k]) * 100.0 if mean_baseline_ndcg.get(k, 0.0) > 0 else 0.0
        for k in ndcg_gain_abs
    }
    mean_baseline_mrr = mrr_baseline_acc / evaluated
    mean_reranked_mrr = mrr_rerank_acc / evaluated
    mrr_gain_abs = float(mean_reranked_mrr - mean_baseline_mrr)
    mrr_gain_pct = float((mrr_gain_abs / mean_baseline_mrr) * 100.0) if mean_baseline_mrr > 0 else 0.0

    return {
        'mean_baseline_ndcg': mean_baseline_ndcg,
        'mean_reranked_ndcg': mean_reranked_ndcg,
        'mean_baseline_mrr': float(mean_baseline_mrr),
        'mean_reranked_mrr': float(mean_reranked_mrr),
        'ndcg_gain_abs': ndcg_gain_abs,
        'ndcg_gain_pct': ndcg_gain_pct,
        'mrr_gain_abs': mrr_gain_abs,
        'mrr_gain_pct': mrr_gain_pct,
    }
