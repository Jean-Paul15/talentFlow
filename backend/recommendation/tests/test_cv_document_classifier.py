from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from api.cv_text.cv_document_classifier import assess_cv_document_text


def _load_cases() -> list[dict]:
    cases_path = Path(__file__).with_name("data") / "cv_document_classifier_cases.json"
    return json.loads(cases_path.read_text(encoding="utf-8"))


class CvDocumentClassifierDatasetTest(unittest.TestCase):
    def test_seed_dataset_matches_expected_labels(self) -> None:
        for case in _load_cases():
            if case.get("ci_enforced", True) is False:
                continue
            with self.subTest(case=case["name"]):
                assessment = assess_cv_document_text(case["text"])
                self.assertEqual(
                    case["expected_document_kind"],
                    assessment.document_kind,
                    msg=case.get("notes", ""),
                )

                min_confidence = case.get("min_confidence")
                if min_confidence is not None:
                    self.assertGreaterEqual(
                        assessment.cv_confidence,
                        float(min_confidence),
                        msg=case["name"],
                    )

                max_confidence = case.get("max_confidence")
                if max_confidence is not None:
                    self.assertLessEqual(
                        assessment.cv_confidence,
                        float(max_confidence),
                        msg=case["name"],
                    )


if __name__ == "__main__":
    unittest.main()
