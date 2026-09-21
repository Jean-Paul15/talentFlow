from __future__ import annotations

import argparse
import json
import os
import random
import tempfile
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
import sys

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from api.cv_text.cv_document_classifier import assess_cv_document_text
from api.cv_text.cv_rl_agent import apply_cv_rl_reward

LABELS = ("cv", "non_cv", "ambiguous")


def _load_samples() -> list[dict[str, str]]:
    samples: list[dict[str, str]] = []

    tests_path = ROOT / "tests" / "data" / "cv_document_classifier_cases.json"
    test_cases = json.loads(tests_path.read_text(encoding="utf-8"))
    for case in test_cases:
        samples.append(
            {
                "id": case["name"],
                "label": case["expected_document_kind"],
                "text": case["text"],
                "source": "tests",
            }
        )

    seed_path = ROOT / "data" / "cv_supervised_seed_cases.json"
    seed_cases = json.loads(seed_path.read_text(encoding="utf-8"))
    for case in seed_cases:
        samples.append(
            {
                "id": case["id"],
                "label": case["label"],
                "text": case["text"],
                "source": "seed",
            }
        )

    dedup: dict[str, dict[str, str]] = {}
    for sample in samples:
        dedup[f"{sample['label']}::{sample['text']}"] = sample
    return list(dedup.values())


def _evaluate(samples: list[dict[str, str]]) -> tuple[float, Counter[tuple[str, str]], list[str]]:
    confusion: Counter[tuple[str, str]] = Counter()
    failures: list[str] = []
    ok = 0
    for sample in samples:
        assessment = assess_cv_document_text(sample["text"])
        expected = sample["label"]
        predicted = assessment.document_kind
        confusion[(expected, predicted)] += 1
        if expected == predicted:
            ok += 1
        else:
            failures.append(
                f"{sample['id']} expected={expected} predicted={predicted} confidence={assessment.cv_confidence}"
            )
    accuracy = ok / max(len(samples), 1)
    return accuracy, confusion, failures


def _print_confusion(confusion: Counter[tuple[str, str]]) -> None:
    print("Confusion matrix (expected -> predicted):")
    for expected in LABELS:
        row = " ".join(str(confusion[(expected, predicted)]).rjust(3) for predicted in LABELS)
        print(f"  {expected:>9} -> {row}")


def _load_rl_state(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def run_rl_simulation(samples: list[dict[str, str]], epochs: int, seed: int) -> tuple[float, Counter[tuple[str, str]], list[str], dict]:
    rng = random.Random(seed)
    with tempfile.TemporaryDirectory(prefix="tf-rl-eval-") as tmp:
        state_path = Path(tmp) / "cv_rl_policy_state.json"
        events_path = Path(tmp) / "cv_rl_policy_events.jsonl"
        os.environ["CV_DOCUMENT_RL_ENABLED"] = "true"
        os.environ["CV_DOCUMENT_RL_POLICY_PATH"] = str(state_path)
        os.environ["CV_DOCUMENT_RL_EVENTS_PATH"] = str(events_path)
        os.environ["CV_DOCUMENT_RL_EPSILON"] = "0.05"

        training_samples = list(samples)
        for _ in range(max(epochs, 1)):
            rng.shuffle(training_samples)
            for sample in training_samples:
                assessment = assess_cv_document_text(sample["text"])
                reward = 1.0 if assessment.document_kind == sample["label"] else 0.0
                if assessment.policy_arm:
                    apply_cv_rl_reward(assessment.policy_arm, reward)

        accuracy, confusion, failures = _evaluate(samples)
        state = _load_rl_state(state_path)
        return accuracy, confusion, failures, state


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate CV classifier and RL policy adaptation")
    parser.add_argument("--sample-size", type=int, default=50)
    parser.add_argument("--epochs", type=int, default=6)
    parser.add_argument("--seed", type=int, default=42)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    all_samples = _load_samples()
    random.Random(args.seed).shuffle(all_samples)
    sample_size = min(max(args.sample_size, 1), len(all_samples))
    samples = all_samples[:sample_size]

    print(f"Loaded samples: {len(all_samples)}")
    print(f"Evaluated sample size: {sample_size}")

    os.environ["CV_DOCUMENT_RL_ENABLED"] = "false"
    baseline_accuracy, baseline_confusion, baseline_failures = _evaluate(samples)
    print("\n=== Baseline (RL off) ===")
    print(f"Accuracy: {baseline_accuracy:.2%}")
    _print_confusion(baseline_confusion)
    if baseline_failures:
        print("Failures:")
        for failure in baseline_failures[:10]:
            print(f"- {failure}")

    rl_accuracy, rl_confusion, rl_failures, rl_state = run_rl_simulation(
        samples=samples,
        epochs=args.epochs,
        seed=args.seed,
    )
    print("\n=== After RL adaptation ===")
    print(f"Accuracy: {rl_accuracy:.2%}")
    _print_confusion(rl_confusion)
    if rl_failures:
        print("Failures:")
        for failure in rl_failures[:10]:
            print(f"- {failure}")

    print("\nRL arm means:")
    for arm, payload in (rl_state.get("arms", {}) or {}).items():
        alpha = float(payload.get("alpha", 1.0))
        beta = float(payload.get("beta", 1.0))
        mean = alpha / max(alpha + beta, 1e-9)
        print(f"- {arm}: mean={mean:.3f}, uses={int(payload.get('uses', 0))}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
