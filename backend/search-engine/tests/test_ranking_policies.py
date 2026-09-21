from pathlib import Path
import sys
import unittest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from services.search_service import _apply_user_facing_quality_policies


class RankingPoliciesTest(unittest.TestCase):
    def test_user_facing_quality_policy_filters_expired_and_downranks_stale(self):
        results = [
            {
                "id": "expired",
                "title": "Backend Python",
                "score": 0.99,
                "quality_score": 0.95,
                "title_confidence": 0.95,
                "is_expired": True,
                "is_stale": False,
                "freshness_days": 1,
            },
            {
                "id": "fresh",
                "title": "Backend Python Lome",
                "score": 0.82,
                "quality_score": 0.9,
                "title_confidence": 0.95,
                "is_expired": False,
                "is_stale": False,
                "freshness_days": 3,
            },
            {
                "id": "stale",
                "title": "Backend Python Remote",
                "score": 0.88,
                "quality_score": 0.9,
                "title_confidence": 0.95,
                "is_expired": False,
                "is_stale": True,
                "freshness_days": 40,
            },
        ]

        out = _apply_user_facing_quality_policies(results)

        self.assertEqual(["fresh", "stale"], [row["id"] for row in out])
        self.assertGreater(out[0]["score"], out[1]["score"])

    def test_user_facing_quality_policy_penalizes_noisy_job_board_content(self):
        results = [
            {
                "id": "noisy",
                "title": "UN DEVELOPPEUR FRONT - END/BACK - END",
                "company": "ENGINS AGRICOLES.... CLIQUER POUR LIRE Platon Chercheurs d'emploi Nos conseils en",
                "summary": "URGENT : OFFRE DE FORMATION CERTIFIANTE EN REPARATION D'ENGINS AGRICOLES",
                "score": 0.87,
                "quality_score": 0.92,
                "title_confidence": 0.96,
                "is_expired": False,
                "is_stale": False,
                "freshness_days": 2,
            },
            {
                "id": "clean",
                "title": "Developpeur Python Backend",
                "company": "TalentFlow Labs",
                "summary": "Python, FastAPI, Docker et PostgreSQL pour une plateforme produit.",
                "score": 0.82,
                "quality_score": 0.9,
                "title_confidence": 0.95,
                "is_expired": False,
                "is_stale": False,
                "freshness_days": 2,
            },
        ]

        out = _apply_user_facing_quality_policies(results)

        self.assertEqual(["clean", "noisy"], [row["id"] for row in out])
        self.assertGreater(out[0]["score"], out[1]["score"])

    def test_user_facing_quality_policy_prioritizes_role_intent_over_freshness(self):
        results = [
            {
                "id": "fresh_generic",
                "title": "Opportunites digitales recentes",
                "company": "Board Aggregator",
                "summary": "Publication recente pour plusieurs profils numeriques et marketing.",
                "score": 0.86,
                "quality_score": 0.92,
                "title_confidence": 0.95,
                "is_expired": False,
                "is_stale": False,
                "freshness_days": 1,
            },
            {
                "id": "slightly_older_exact",
                "title": "Developpeur Python Backend FastAPI",
                "company": "ResaSalle Labs",
                "summary": "Backend API, Python, FastAPI, Docker et PostgreSQL.",
                "score": 0.81,
                "quality_score": 0.91,
                "title_confidence": 0.96,
                "is_expired": False,
                "is_stale": False,
                "freshness_days": 18,
            },
        ]

        out = _apply_user_facing_quality_policies(
            results,
            query="developpeur python backend fastapi",
        )

        self.assertEqual(
            ["slightly_older_exact", "fresh_generic"],
            [row["id"] for row in out],
        )
        self.assertGreater(out[0]["score"], out[1]["score"])


if __name__ == "__main__":
    unittest.main()
