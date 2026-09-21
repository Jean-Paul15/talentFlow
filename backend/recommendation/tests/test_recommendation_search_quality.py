from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from api.cv_text.models import CVAnalysisResult, RecommendedJobPreview
from api.cv_text.parsing_geo_ranking import _rerank_jobs_for_candidate_context
from api.cv_text.recommendation_calibration import (
    _build_precision_query_from_profile,
    _should_retry_with_precision_query,
)


class RecommendationSearchQualityTest(unittest.TestCase):
    def test_precision_query_prioritizes_role_hints_and_skills(self) -> None:
        query = _build_precision_query_from_profile(
            cv_text="Senior data engineer Python Spark Kafka Airflow",
            skills=["Python", "Spark", "Kafka", "Airflow", "Docker"],
            experience_years=5,
        )
        self.assertIn("ingenieur data", query)
        self.assertIn("Python", query)
        self.assertIn("Spark", query)
        self.assertIn("5 ans", query)

    def test_precision_retry_triggers_on_noisy_and_misaligned_results(self) -> None:
        jobs = [
            RecommendedJobPreview(
                id="noisy-1",
                title="UN DEVELOPPEUR FRONT - END/BACK - END",
                company="ENGINS AGRICOLES... CLIQUEZ POUR LIRE Platon Chercheurs d'emploi",
                location="Lome",
                country="Togo",
                score=0.63,
                summary="URGENT : OFFRE DE FORMATION CERTIFIANTE",
            ),
            RecommendedJobPreview(
                id="noisy-2",
                title="Assistant de direction",
                company="Exemple",
                location="Lome",
                country="Togo",
                score=0.61,
                summary="Gestion agenda et bureautique.",
            ),
        ]

        self.assertTrue(
            _should_retry_with_precision_query(
                jobs=jobs,
                role_match_jobs=0,
                overlap_jobs=0,
            )
        )

    def test_rerank_prefers_clean_aligned_job_over_noisy_board_item(self) -> None:
        cv_analysis = CVAnalysisResult(
            skills=["Python", "FastAPI", "Docker"],
            experience_years=4,
            education_level="Licence",
        )
        jobs = [
            RecommendedJobPreview(
                id="noisy",
                title="UN DEVELOPPEUR FRONT - END/BACK - END",
                company="ENGINS AGRICOLES.... CLIQUER POUR LIRE Platon Chercheurs d'emploi Nos conseils en",
                location="Lome",
                country="Togo",
                score=0.78,
                summary="URGENT : OFFRE DE FORMATION CERTIFIANTE EN REPARATION D'ENGINS AGRICOLES",
            ),
            RecommendedJobPreview(
                id="clean",
                title="Developpeur Python Backend",
                company="TalentFlow Labs",
                location="Lome",
                country="Togo",
                score=0.72,
                summary="Python, FastAPI, Docker, PostgreSQL et APIs REST.",
            ),
        ]

        with patch.dict(
            "os.environ",
            {"RECOMMENDATION_MIN_MEANINGFUL_SCORE": "0.52"},
            clear=False,
        ):
            reranked = _rerank_jobs_for_candidate_context(
                jobs=jobs,
                cv_analysis=cv_analysis,
                cv_text="Developpeur Python backend avec APIs REST, Docker et FastAPI.",
                explicit_location="Lome",
                top_k=2,
            )

        self.assertEqual(["clean", "noisy"], [job.id for job in reranked])


if __name__ == "__main__":
    unittest.main()
