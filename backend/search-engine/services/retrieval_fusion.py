from __future__ import annotations

import math
import re
from collections import Counter
from typing import Any, Dict, Iterable, List, Tuple


_TOKEN_RE = re.compile(r"[A-Za-z0-9_+#.-]+", re.UNICODE)


def tokenize(text: str) -> List[str]:
    if not text:
        return []
    return [t.lower() for t in _TOKEN_RE.findall(text)]


def build_lexical_text(row: Dict[str, Any]) -> str:
    parts = [
        row.get("title") or "",
        row.get("company") or "",
        row.get("location") or "",
        " ".join(row.get("hard_skills") or []),
        " ".join(row.get("soft_skills") or []),
        row.get("description") or "",
    ]
    return " ".join([str(p).strip() for p in parts if str(p).strip()])


def lexical_score(query: str, row: Dict[str, Any]) -> float:
    """
    BM25-lite local score (fallback lexical ranking when sparse/BM25 is unavailable).
    It is not a true global BM25, but it provides an independent lexical ordering
    over a candidate pool to enable RRF fusion.
    """
    q_tokens = tokenize(query)
    if not q_tokens:
        return 0.0
    d_tokens = tokenize(build_lexical_text(row))
    if not d_tokens:
        return 0.0

    d_counts = Counter(d_tokens)
    d_len = len(d_tokens)
    avg_dl = 120.0  # heuristic average length for job docs
    k1 = 1.2
    b = 0.75

    score = 0.0
    unique_q = Counter(q_tokens)
    for term, qtf in unique_q.items():
        tf = d_counts.get(term, 0)
        if tf <= 0:
            continue
        # pseudo-IDF fallback: rarer terms get a slightly higher boost within query.
        idf = 1.0 + math.log(1.0 + (len(unique_q) / qtf))
        denom = tf + k1 * (1 - b + b * (d_len / avg_dl))
        score += idf * ((tf * (k1 + 1)) / max(denom, 1e-9))
    return float(score)


def rank_by_lexical(query: str, rows: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    scored: List[Dict[str, Any]] = []
    for row in rows:
        item = dict(row)
        item["lexical_score"] = lexical_score(query, item)
        scored.append(item)
    scored.sort(
        key=lambda r: (
            float(r.get("lexical_score") or 0.0),
            float(r.get("score") or 0.0),
        ),
        reverse=True,
    )
    return scored


def rrf_fuse(
    ranked_lists: List[Tuple[str, List[Dict[str, Any]]]],
    *,
    k: int = 60,
    final_limit: int | None = None,
) -> List[Dict[str, Any]]:
    """
    Reciprocal Rank Fusion on lists of result dicts (must expose `id`).
    Keeps original row payload and annotates:
    - `rrf_score`
    - `rrf_sources`
    """
    fused: Dict[str, Dict[str, Any]] = {}

    for source_name, rows in ranked_lists:
        for rank, row in enumerate(rows, start=1):
            row_id = str(row.get("id") or "")
            if not row_id:
                continue
            contrib = 1.0 / float(k + rank)

            current = fused.get(row_id)
            if current is None:
                current = dict(row)
                current["rrf_score"] = 0.0
                current["rrf_sources"] = {}
                # Preserve retrieval score before fusion if not already tracked.
                if "base_score" not in current:
                    current["base_score"] = current.get("score")
                fused[row_id] = current

            current["rrf_score"] = float(current.get("rrf_score") or 0.0) + contrib
            current["rrf_sources"][source_name] = {
                "rank": rank,
                "contrib": contrib,
            }

            # Prefer richer payloads / longer descriptions if duplicate rows differ.
            current_desc = str(current.get("description") or "")
            new_desc = str(row.get("description") or "")
            if len(new_desc) > len(current_desc):
                for key, value in row.items():
                    if value not in (None, "", [], {}):
                        current[key] = value

    fused_rows = list(fused.values())
    fused_rows.sort(
        key=lambda r: (
            float(r.get("rrf_score") or 0.0),
            float(r.get("score") or 0.0),
        ),
        reverse=True,
    )

    for row in fused_rows:
        row["score"] = float(row.get("rrf_score") or row.get("score") or 0.0)

    if final_limit is not None:
        return fused_rows[:final_limit]
    return fused_rows

