from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from api.cv_text.cv_document_classifier import assess_cv_document_text


def main() -> int:
    dataset_path = ROOT / "tests" / "data" / "cv_document_classifier_cases.json"
    cases = json.loads(dataset_path.read_text(encoding="utf-8"))

    confusion: Counter[tuple[str, str]] = Counter()
    failures: list[str] = []

    for case in cases:
        assessment = assess_cv_document_text(case["text"])
        expected = case["expected_document_kind"]
        predicted = assessment.document_kind
        confusion[(expected, predicted)] += 1

        min_conf = case.get("min_confidence")
        max_conf = case.get("max_confidence")
        confidence_ok = True
        if min_conf is not None and assessment.cv_confidence < float(min_conf):
            confidence_ok = False
        if max_conf is not None and assessment.cv_confidence > float(max_conf):
            confidence_ok = False

        if expected != predicted or not confidence_ok:
            failures.append(
                f"- {case['name']}: expected={expected}, predicted={predicted}, "
                f"confidence={assessment.cv_confidence}"
            )

    total = len(cases)
    correct = sum(
        count
        for (expected, predicted), count in confusion.items()
        if expected == predicted
    )
    accuracy = (correct / total) if total else 0.0

    print(f"Dataset: {dataset_path}")
    print(f"Cases: {total}")
    print(f"Accuracy: {accuracy:.1%}")
    print("Confusion matrix:")
    labels = ("cv", "non_cv", "ambiguous")
    for expected in labels:
        row = []
        for predicted in labels:
            row.append(f"{confusion[(expected, predicted)]:>3}")
        print(f"  {expected:>9} -> {' '.join(row)}")

    if failures:
        print("\nFailures:")
        for failure in failures:
            print(failure)
        return 1

    print("\nAll dataset cases passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
