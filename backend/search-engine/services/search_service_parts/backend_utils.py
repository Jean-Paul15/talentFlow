"""Backend utility helpers."""

from __future__ import annotations

from typing import List


def _truncate_text(text: str, max_length: int) -> str:
    if len(text) <= max_length:
        return text
    return text[:max_length].rsplit(" ", 1)[0] + "..."


def _project_vectors_2d(vectors: List[List[float]]) -> List[List[float]]:
    if not vectors:
        return []
    if len(vectors) == 1:
        return [[0.0, 0.0]]
    try:
        import numpy as np  # type: ignore

        matrix = np.array(vectors, dtype=float)
        if matrix.ndim != 2 or matrix.shape[1] < 2:
            return [[float(idx), 0.0] for idx in range(len(vectors))]
        matrix = matrix - matrix.mean(axis=0, keepdims=True)
        _, _, vt = np.linalg.svd(matrix, full_matrices=False)
        basis = vt[:2].T
        projected = matrix @ basis
        return projected[:, :2].tolist()
    except Exception:
        return [[float(idx), float(vec[0] if vec else 0.0)] for idx, vec in enumerate(vectors)]


__all__ = ["_project_vectors_2d", "_truncate_text"]
