"""Heuristic CV text analyzer for text-only CV flow.

The frontend sends extracted text; this module provides deterministic parsing
without LLM dependency for fast and stable backend behavior.
"""

from __future__ import annotations

import re
import unicodedata
from pathlib import Path
from typing import Iterable, List, Optional


SKILL_PATTERNS: list[tuple[str, tuple[str, ...]]] = [
    ("Python", ("python",)),
    ("SQL", ("sql", "postgresql", "mysql", "sql server")),
    ("Excel", ("excel", "vba")),
    ("Comptabilité", ("comptabilite", "comptabilité", "accounting")),
    ("Sage", ("sage", "sage saari")),
    ("SAP", ("sap", "sap fi", "sap co")),
    ("Power BI", ("power bi", "powerbi")),
    ("Tableau", ("tableau",)),
    ("Pandas", ("pandas",)),
    ("NumPy", ("numpy",)),
    ("scikit-learn", ("scikit-learn", "sklearn")),
    ("TensorFlow", ("tensorflow",)),
    ("PyTorch", ("pytorch", "torch")),
    ("Machine Learning", ("machine learning", "ml", "apprentissage automatique")),
    ("Deep Learning", ("deep learning", "apprentissage profond")),
    ("NLP", ("nlp", "traitement du langage", "natural language processing")),
    ("LLM", ("llm", "large language model", "gpt", "gemini", "claude")),
    ("LangChain", ("langchain",)),
    ("FastAPI", ("fastapi",)),
    ("Django", ("django",)),
    ("Flask", ("flask",)),
    ("JavaScript", ("javascript", "js ")),
    ("TypeScript", ("typescript", "ts ")),
    ("React", ("react",)),
    ("Angular", ("angular",)),
    ("Node.js", ("node.js", "nodejs", "node js")),
    ("Java", ("java", "spring boot", "spring")),
    ("C#", ("c#", ".net", "dotnet", "asp.net")),
    ("PHP", ("php", "laravel", "symfony")),
    ("Docker", ("docker",)),
    ("Kubernetes", ("kubernetes", "k8s")),
    ("Git", ("git", "github", "gitlab")),
    ("Linux", ("linux",)),
    ("Airflow", ("airflow", "apache airflow")),
    ("Spark", ("spark", "pyspark", "apache spark")),
    ("Kafka", ("kafka", "apache kafka")),
    ("MongoDB", ("mongodb", "mongo db")),
    ("PostgreSQL", ("postgresql", "postgres")),
    ("MySQL", ("mysql",)),
    ("NoSQL", ("nosql",)),
    ("ETL", ("etl", "elt")),
    ("dbt", ("dbt",)),
    ("BigQuery", ("bigquery", "big query")),
    ("Snowflake", ("snowflake",)),
    ("AWS", ("aws", "amazon web services")),
    ("Azure", ("azure", "microsoft azure")),
    ("GCP", ("gcp", "google cloud", "google cloud platform")),
    ("REST API", ("rest api", "api rest", "fastapi", "flask api")),
]


EDU_PATTERNS: list[tuple[str, tuple[str, ...], int]] = [
    ("Doctorat", ("doctorat", "phd", "doctorate"), 8),
    ("Master", ("master", "bac+5", "ingénieur", "ingenieur", "msc"), 7),
    ("Licence", ("licence", "bachelor", "bac+3", "bac+4"), 6),
    ("BTS/DUT", ("bts", "dut", "deug", "brevet de technicien"), 5),
    ("Baccalauréat", ("baccalaureat", "baccalauréat", "bac "), 4),
]


def _strip_accents(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", text)
    return "".join(ch for ch in normalized if not unicodedata.combining(ch))


def _normalize_text(text: str) -> str:
    text = text or ""
    text = text.replace("\x00", " ")
    text = unicodedata.normalize("NFKC", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _normalized_for_match(text: str) -> str:
    text = _normalize_text(text).lower()
    text = _strip_accents(text)
    return f" {text} "


def _contains_token(text_norm: str, token: str) -> bool:
    token_norm = _strip_accents(token.lower()).strip()
    if not token_norm:
        return False
    if re.fullmatch(r"[a-z0-9+#.\- ]+", token_norm):
        pattern = r"(?<![a-z0-9])" + re.escape(token_norm) + r"(?![a-z0-9])"
        return re.search(pattern, text_norm) is not None
    return token_norm in text_norm


def extract_skills_from_text(cv_text: str) -> List[str]:
    text_norm = _normalized_for_match(cv_text)
    found: list[str] = []
    for skill, aliases in SKILL_PATTERNS:
        if any(_contains_token(text_norm, alias) for alias in aliases):
            found.append(skill)
    return found


def extract_experience_years(cv_text: str) -> Optional[int]:
    text = _normalize_text(cv_text)
    text_norm = _normalized_for_match(text)

    # Ranges first: "3-5 ans", "3 à 5 ans", "3/5 years"
    range_patterns = [
        r"(\d{1,2})\s*(?:-|a|à|/|to)\s*(\d{1,2})\s*(?:\+?\s*)?(?:ans?|annees?|années?|years?|yrs?)",
    ]
    years: list[int] = []
    for pat in range_patterns:
        for m in re.finditer(pat, _strip_accents(text.lower())):
            a, b = int(m.group(1)), int(m.group(2))
            years.append(max(a, b))

    # Singles: "5 ans d'expérience", "2 years experience", "5+ years"
    single_patterns = [
        r"(\d{1,2})\s*\+?\s*(?:ans?|annees?|années?|years?|yrs?)\b",
        r"experience\s*(?:de)?\s*(\d{1,2})\s*\+?\s*(?:ans?|annees?|années?|years?|yrs?)",
    ]
    text_ascii = _strip_accents(text.lower())
    for pat in single_patterns:
        for m in re.finditer(pat, text_ascii):
            years.append(int(m.group(1)))

    if years:
        return max(0, min(50, max(years)))

    # Heuristic fallback on experience level keywords
    if any(k in text_norm for k in (" senior ", " confirme ", " confirmé ", " lead ", " expert ")):
        return 5
    if any(k in text_norm for k in (" junior ", " debutant ", " débutant ", " internship ", " stage ")):
        return 0
    return None


def extract_education_level(cv_text: str) -> Optional[str]:
    text_norm = _normalized_for_match(cv_text)
    best: tuple[int, str] | None = None

    # Explicit Bac+N precedence
    m = re.search(r"\bbac\s*\+\s*(\d)\b", _strip_accents(cv_text.lower()))
    if m:
        n = int(m.group(1))
        if n >= 8:
            return "Doctorat"
        if n >= 5:
            return "Master"
        if n >= 3:
            return "Licence"
        if n >= 2:
            return "BTS/DUT"
        return "Baccalauréat"

    for label, aliases, rank in EDU_PATTERNS:
        if any(_contains_token(text_norm, alias) for alias in aliases):
            if best is None or rank > best[0]:
                best = (rank, label)

    return best[1] if best else None


def analyze_cv(file_path: str) -> dict:
    """
    Compatibility helper for legacy upload route.
    Minimal implementation: best-effort text read, then heuristic parsing.
    """
    path = Path(file_path)
    text = ""
    try:
        if path.suffix.lower() == ".txt":
            text = path.read_text(encoding="utf-8", errors="ignore")
        else:
            # For pdf/docx routes we keep a graceful fallback instead of crashing.
            raw = path.read_bytes()
            text = raw.decode("utf-8", errors="ignore")
    except Exception:
        text = ""

    text = _normalize_text(text)
    if not text:
        return {
            "skills": [],
            "experience_years": None,
            "education_level": None,
            "raw_text_preview": "",
        }

    return {
        "skills": extract_skills_from_text(text),
        "experience_years": extract_experience_years(text),
        "education_level": extract_education_level(text),
        "raw_text_preview": text[:200],
    }
