from __future__ import annotations

import argparse
import json
import math
import random
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SEED_PATH = ROOT / "data" / "cv_supervised_seed_cases.json"
DEFAULT_MODEL_PATH = ROOT / "data" / "cv_supervised_model.json"
DEFAULT_DATASET_PATH = ROOT / "data" / "cv_supervised_dataset.jsonl"
TOKEN_PATTERN = re.compile(r"[a-z0-9][a-z0-9+#._-]{1,}", flags=re.IGNORECASE)
LABELS = ("cv", "non_cv", "ambiguous")


def _fold_text(text: str) -> str:
    return (
        str(text or "")
        .replace("\x00", " ")
        .lower()
        .strip()
        .encode("ascii", errors="ignore")
        .decode("ascii", errors="ignore")
    )


def _tokenize(text: str) -> Counter[str]:
    return Counter(TOKEN_PATTERN.findall(_fold_text(text)))


@dataclass(slots=True)
class Sample:
    label: str
    text: str
    source: str


def load_seed_samples(path: Path) -> list[Sample]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    samples: list[Sample] = []
    for item in payload:
        label = str(item.get("label", "")).strip().lower()
        text = str(item.get("text", "")).strip()
        if label not in LABELS or not text:
            continue
        samples.append(Sample(label=label, text=text, source="seed"))
    return samples


def _synthetic_cv_text(rng: random.Random) -> str:
    names = ["Koffi Mensah", "Afi Dossou", "Noah Addo", "Mariam Traoré", "Lina Boateng"]
    cities = ["Lomé", "Accra", "Abidjan", "Cotonou", "Dakar"]
    roles = [
        "Développeur backend",
        "Data analyst",
        "Chargée RH",
        "Operations coordinator",
        "Project manager",
    ]
    companies = ["TalentFlow", "Horizon Group", "Orange Business", "Eco Services", "Atlas Tech"]
    schools = ["Université de Lomé", "University of Ghana", "ESGIS", "African Leadership Institute"]
    skills = [
        "Python, SQL, Docker, communication",
        "Planning, reporting, stakeholder management",
        "Recruitment, payroll, Excel, communication",
        "React, Flutter, TypeScript, testing",
        "Risk analysis, compliance, reporting",
    ]
    name = rng.choice(names)
    city = rng.choice(cities)
    role = rng.choice(roles)
    company = rng.choice(companies)
    school = rng.choice(schools)
    skill_block = rng.choice(skills)
    y1 = rng.randint(2017, 2021)
    y2 = y1 + rng.randint(2, 4)
    return (
        f"{name}\n{city}\n{name.split()[0].lower()}@example.com\n+228 90 00 00 {rng.randint(10,99)}\n"
        f"linkedin.com/in/{name.lower().replace(' ', '')}\n\n"
        f"Profil\n{role} avec {rng.randint(2, 9)} ans d'expérience.\n\n"
        f"Expérience professionnelle\n{y2} - 2026 {role}, {company}\n"
        f"{y1} - {y2} Assistant, {rng.choice(companies)}\n\n"
        f"Formation\nMaster, {school}\n\n"
        f"Compétences\n{skill_block}"
    )


def _synthetic_non_cv_text(rng: random.Random) -> str:
    docs = [
        "FACTURE {ref}\nClient: {client}\nMontant TTC: {amount} FCFA\nConditions générales applicables.",
        "Politique de confidentialité\nNous utilisons des cookies et des traceurs analytiques.\nVoir nos conditions générales.",
        "Article de blog: {topic}\nCliquez pour lire la suite et abonnez-vous à la newsletter.",
        "Contrat de prestation\nArticle 1 objet\nArticle 2 obligations\nArticle 3 résiliation",
        "Compte-rendu de réunion\nBudget, planning, validation des actions et points de suivi.",
        "Offre d'emploi: {topic}\nMissions, profil recherché, processus de recrutement.",
    ]
    topics = [
        "croissance commerciale 2026",
        "transformation digitale",
        "développeur full stack",
        "responsable logistique",
        "analyste financier",
    ]
    clients = ["Société Horizon", "Nova Trading", "Blue Capital", "Atlas Group"]
    template = rng.choice(docs)
    return template.format(
        ref=f"2026-{rng.randint(1000, 9999)}",
        client=rng.choice(clients),
        amount=rng.randint(100000, 800000),
        topic=rng.choice(topics),
    )


def _synthetic_ambiguous_text(rng: random.Random) -> str:
    names = ["Kossi", "Awa", "Daniel", "Sarah", "Mina", "Armel"]
    roles = ["designer", "operations officer", "backend engineer", "commercial", "analyst"]
    templates = [
        (
            "{name} Mensah\nAccra\n{name_lower}@example.com\n+233 20 000 00{suffix}\n\n"
            "Madame, Monsieur,\nJe vous adresse ma candidature au poste de {role}. "
            "Je reste disponible pour un entretien.\nCordialement."
        ),
        (
            "{name} Addo\nLomé\n{name_lower}@example.com\nlinkedin.com/in/{name_lower}\n\n"
            "{role} | Open to opportunities | 3 years experience in projects and reporting."
        ),
        (
            "Profil\n{role} avec expérience terrain.\nCompétences\nCommunication, Excel, organisation.\n"
            "Disponible immédiatement."
        ),
    ]
    name = rng.choice(names)
    return rng.choice(templates).format(
        name=name,
        name_lower=name.lower(),
        role=rng.choice(roles),
        suffix=rng.randint(10, 99),
    )


def generate_synthetic_samples(total: int, rng: random.Random) -> list[Sample]:
    per_class = max(total // len(LABELS), 1)
    samples: list[Sample] = []
    for _ in range(per_class):
        samples.append(Sample(label="cv", text=_synthetic_cv_text(rng), source="synthetic"))
        samples.append(Sample(label="non_cv", text=_synthetic_non_cv_text(rng), source="synthetic"))
        samples.append(Sample(label="ambiguous", text=_synthetic_ambiguous_text(rng), source="synthetic"))
    return samples


def stratified_split(samples: list[Sample], rng: random.Random, ratio: float = 0.8) -> tuple[list[Sample], list[Sample]]:
    buckets: dict[str, list[Sample]] = defaultdict(list)
    for sample in samples:
        buckets[sample.label].append(sample)

    train: list[Sample] = []
    valid: list[Sample] = []
    for label in LABELS:
        items = buckets.get(label, [])
        rng.shuffle(items)
        cut = max(int(len(items) * ratio), 1)
        train.extend(items[:cut])
        valid.extend(items[cut:])
    rng.shuffle(train)
    rng.shuffle(valid)
    return train, valid


def train_naive_bayes(samples: list[Sample], alpha: float = 1.0) -> dict:
    class_counts = Counter(sample.label for sample in samples)
    token_totals = Counter()
    token_counts: dict[str, Counter[str]] = {label: Counter() for label in LABELS}
    vocabulary: set[str] = set()

    for sample in samples:
        tokens = _tokenize(sample.text)
        token_counts[sample.label].update(tokens)
        token_totals[sample.label] += sum(tokens.values())
        vocabulary.update(tokens.keys())

    total_samples = max(sum(class_counts.values()), 1)
    priors = {label: class_counts[label] / total_samples for label in LABELS}

    return {
        "version": 1,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "alpha": alpha,
        "labels": list(LABELS),
        "class_counts": dict(class_counts),
        "priors": priors,
        "token_totals": {label: int(token_totals[label]) for label in LABELS},
        "vocabulary_size": len(vocabulary),
        "token_counts": {label: dict(token_counts[label]) for label in LABELS},
    }


def predict(model: dict, text: str) -> tuple[str, float]:
    tokens = _tokenize(text)
    if not tokens:
        return "non_cv", 1.0

    alpha = float(model["alpha"])
    labels = model["labels"]
    vocab_size = max(int(model["vocabulary_size"]), 1)
    class_counts = model["class_counts"]
    token_totals = model["token_totals"]
    token_maps = model["token_counts"]
    priors = model["priors"]

    log_scores: dict[str, float] = {}
    total_samples = max(sum(class_counts.values()), 1)
    for label in labels:
        prior = max(float(priors.get(label, class_counts[label] / total_samples)), 1e-9)
        log_score = math.log(prior)
        denom = token_totals[label] + alpha * vocab_size
        for token, count in tokens.items():
            observed = token_maps[label].get(token, 0)
            token_prob = (observed + alpha) / max(denom, 1e-9)
            log_score += count * math.log(max(token_prob, 1e-12))
        log_scores[label] = log_score

    best_label = max(log_scores, key=log_scores.get)
    max_log = log_scores[best_label]
    exp_sum = sum(math.exp(v - max_log) for v in log_scores.values())
    confidence = 1 / max(exp_sum, 1e-12)
    return best_label, round(min(confidence, 1.0), 3)


def evaluate(model: dict, samples: list[Sample]) -> dict:
    confusion = {(expected, predicted): 0 for expected in LABELS for predicted in LABELS}
    correct = 0
    for sample in samples:
        predicted, _confidence = predict(model, sample.text)
        confusion[(sample.label, predicted)] += 1
        if predicted == sample.label:
            correct += 1
    total = max(len(samples), 1)
    return {
        "total": len(samples),
        "correct": correct,
        "accuracy": correct / total,
        "confusion": confusion,
    }


def save_dataset(path: Path, samples: list[Sample]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for idx, sample in enumerate(samples, start=1):
            row = {"id": idx, "label": sample.label, "source": sample.source, "text": sample.text}
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Train supervised CV document classifier")
    parser.add_argument("--seed-path", type=Path, default=DEFAULT_SEED_PATH)
    parser.add_argument("--output-model", type=Path, default=DEFAULT_MODEL_PATH)
    parser.add_argument("--output-dataset", type=Path, default=DEFAULT_DATASET_PATH)
    parser.add_argument("--synthetic-count", type=int, default=600)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--alpha", type=float, default=1.0)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    rng = random.Random(args.seed)

    seed_samples = load_seed_samples(args.seed_path)
    synthetic_samples = generate_synthetic_samples(args.synthetic_count, rng)
    all_samples = seed_samples + synthetic_samples
    rng.shuffle(all_samples)

    train_samples, valid_samples = stratified_split(all_samples, rng=rng, ratio=0.8)
    model = train_naive_bayes(train_samples, alpha=args.alpha)
    metrics = evaluate(model, valid_samples)

    args.output_model.parent.mkdir(parents=True, exist_ok=True)
    args.output_model.write_text(json.dumps(model, ensure_ascii=False), encoding="utf-8")
    save_dataset(args.output_dataset, all_samples)

    print(f"Seed samples: {len(seed_samples)}")
    print(f"Synthetic samples: {len(synthetic_samples)}")
    print(f"Total samples: {len(all_samples)}")
    print(f"Train samples: {len(train_samples)}")
    print(f"Validation samples: {len(valid_samples)}")
    print(f"Validation accuracy: {metrics['accuracy']:.2%}")
    print("Confusion matrix (expected -> predicted):")
    for expected in LABELS:
        row = " ".join(str(metrics["confusion"][(expected, predicted)]).rjust(3) for predicted in LABELS)
        print(f"  {expected:>9} -> {row}")
    print(f"Model written to: {args.output_model}")
    print(f"Dataset written to: {args.output_dataset}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
