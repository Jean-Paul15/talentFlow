from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from api.cv_text.models import CVAnalysisResult, RecommendedJobPreview
from api.cv_text.parsing_response_mode import _recommendation_response_mode
from api.cv_text.recommendation_calibration import _should_force_deepseek_first


def _load_cases() -> list[dict]:
    cases_path = Path(__file__).with_name("data") / "recommendation_calibration_cases.json"
    return json.loads(cases_path.read_text(encoding="utf-8"))


class RecommendationCalibrationTest(unittest.TestCase):
    def test_reference_cases_match_expected_policy(self) -> None:
        with patch.dict(
            "os.environ",
            {
                "LLM_DECISION_MIN_JOB_COUNT": "2",
                "LLM_DECISION_MIN_TOP_SCORE": "0.62",
                "RECOMMENDATION_MIN_MEANINGFUL_SCORE": "0.52",
                "RECOMMENDATION_SINGLE_STRONG_MATCH_SCORE": "0.82",
                "RECOMMENDATION_DEEPSEEK_AMBIGUOUS_FIRST_ENABLED": "true",
            },
            clear=False,
        ):
            for case in _load_cases():
                with self.subTest(case=case["name"]):
                    cv_analysis = CVAnalysisResult.model_validate(case["cv_analysis"])
                    jobs = [
                        RecommendedJobPreview.model_validate(job)
                        for job in case["jobs"]
                    ]

                    mode, reason = _recommendation_response_mode(
                        jobs,
                        cv_analysis,
                        case["cv_text"],
                    )
                    self.assertEqual(case["expected_mode"], mode)
                    self.assertEqual(case["expected_reason"], reason)
                    self.assertEqual(
                        case["expect_deepseek_first"],
                        _should_force_deepseek_first(
                            jobs=jobs,
                            expected_mode=mode,
                            decision_reason=reason,
                        ),
                    )


if __name__ == "__main__":
    unittest.main()
