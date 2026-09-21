from pathlib import Path
import sys

import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from services.search_service import QdrantSearchBackend, _is_probable_non_job_result


def test_sparse_query_vector_handles_numpy_arrays_without_truthiness_error():
    np = pytest.importorskip("numpy")

    class FakeSparseVector:
        indices = np.array([1, 4, 9])
        values = np.array([0.25, 0.5, 0.75], dtype=float)

    class FakeEncoder:
        def embed(self, texts):
            assert texts == ["python fastapi"]
            return [FakeSparseVector()]

    backend = QdrantSearchBackend.__new__(QdrantSearchBackend)
    backend._get_sparse_encoder = lambda: FakeEncoder()

    sparse = QdrantSearchBackend._build_sparse_query_vector(backend, "python fastapi")

    assert sparse["indices"] == [1, 4, 9]
    assert sparse["values"] == pytest.approx([0.25, 0.5, 0.75])


def test_non_job_filter_rejects_generic_and_vacancy_titles():
    assert _is_probable_non_job_result(
        {
            "title": "T",
            "description": "Description vide",
            "source_url": "https://example.com/offre/t",
        }
    )
    assert _is_probable_non_job_result(
        {
            "title": "VACANCES DE POSTES",
            "description": "Cliquez ici pour voir les offres disponibles",
            "source_url": "https://example.com/blog/vacances-de-postes",
        }
    )
