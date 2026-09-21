# Preparation des documents pour Elasticsearch

from datetime import datetime
import os
import re
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse
from typing import Any, Iterable, List


_TRACKING_QUERY_KEYS = {
    "utm_source",
    "utm_medium",
    "utm_campaign",
    "utm_term",
    "utm_content",
    "gclid",
    "fbclid",
    "mc_cid",
    "mc_eid",
    "ref",
    "ref_src",
    "source",
    "src",
}

_NON_JOB_TITLE_KEYWORDS = (
    "formation",
    "formations",
    "cours",
    "certification",
    "webinaire",
    "webinar",
    "tutorial",
    "tutoriel",
    "vacance de poste",
    "vacances de poste",
    "vacance des postes",
    "vacances des postes",
)

_NON_JOB_URL_HINTS = ("/category/", "/tag/", "/blog/", "/formations", "/formation", "/cours/")

_GENERIC_BAD_TITLES = {
    "t",
    "p4",
    "(f/h).",
    "(f/h)",
    "f/h",
    "h/f",
    "poste :",
    "poste:",
    "poste",
    "intitule du poste",
    "intitulé du poste",
    "activites principales",
    "activités principales",
}

_JOB_SIGNAL_KEYWORDS = (
    "emploi",
    "offre",
    "recrute",
    "recrutement",
    "poste",
    "job",
    "stage",
    "cdi",
    "cdd",
    "h/f",
    "engineer",
    "developer",
    "analyst",
    "devops",
    "comptable",
)

_NOISE_MARKERS = (
    "lorem ipsum",
    "conditions générales",
    "conditions generales",
    "politique de confidentialité",
    "privacy policy",
    "termes et conditions",
    "table des matières",
    "table des matieres",
    "cours de",
    "programme de cours",
)

_MIN_QUALITY_SCORE = float(os.getenv("SEARCH_INDEX_MIN_QUALITY_SCORE", "0.25"))
_MIN_DESCRIPTION_CHARS = int(os.getenv("SEARCH_INDEX_MIN_DESCRIPTION_CHARS", "120"))
_MIN_DESCRIPTION_CHARS_STRICT_SOURCES = int(
    os.getenv("SEARCH_INDEX_MIN_DESCRIPTION_CHARS_STRICT_SOURCES", "180")
)
_STRICT_DESCRIPTION_SOURCES = {
    "jsearch_api",
    "hackernews_api",
    "remoteok_api",
    "remotive_api",
}


def get_text_for_embedding(job: dict) -> str:
    """
    Combine les champs pertinents pour generer l'embedding.
    """
    parts = [
        job.get("title", ""),
        job.get("description", ""),
        " ".join(job.get("hard_skills", [])),
    ]
    return " ".join(filter(None, parts))


def canonicalize_tracking_url(url: Any) -> str | None:
    raw = str(url or "").strip()
    if not raw:
        return None
    if raw.startswith(("mailto:", "tel:")):
        return raw
    if raw.startswith("www."):
        raw = f"https://{raw}"
    if not re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*://", raw):
        return raw
    try:
        parsed = urlparse(raw)
    except Exception:
        return raw
    scheme = (parsed.scheme or "https").lower()
    netloc = (parsed.netloc or "").lower()
    path = parsed.path or "/"
    if len(path) > 1:
        path = re.sub(r"/{2,}", "/", path).rstrip("/") or "/"
    query_pairs = []
    for k, v in parse_qsl(parsed.query, keep_blank_values=True):
        key_lower = (k or "").lower()
        if key_lower in _TRACKING_QUERY_KEYS or key_lower.startswith("utm_"):
            continue
        query_pairs.append((k, v))
    query_pairs.sort(key=lambda x: (x[0], x[1]))
    query = urlencode(query_pairs, doseq=True)
    return urlunparse((scheme, netloc, path, "", query, ""))


def is_probable_job_document(job: dict) -> bool:
    title = _norm(job.get("title")).lower()
    description = _norm(job.get("description")).lower()
    source_url = _norm(job.get("source_url")).lower()
    source_name = _norm(job.get("source_name")).lower()
    contract = _norm(job.get("contract_type")).lower()
    apply_hint = _norm(job.get("apply_method")).lower() or _norm(job.get("apply_url")).lower()

    blob = f"{title} {description} {contract} {source_name}"
    has_job_signal = any(tok in blob for tok in _JOB_SIGNAL_KEYWORDS)
    has_apply_signal = bool(apply_hint)
    has_date_signal = bool(job.get("posted_date") or job.get("posted_date_iso") or job.get("deadline") or job.get("deadline_iso"))

    if title in _GENERIC_BAD_TITLES or re.fullmatch(r"p\d+", title):
        return False
    if re.search(r"\bvacances?\s+de[s]?\s+poste[s]?\b", title):
        return False
    if "cliquez ici pour voir les offres" in description and not (has_apply_signal and has_date_signal):
        return False

    if any(h in source_url for h in _NON_JOB_URL_HINTS):
        if not (has_job_signal or has_apply_signal or has_date_signal):
            return False
    if any(k in title for k in _NON_JOB_TITLE_KEYWORDS):
        if not (has_job_signal or has_apply_signal):
            return False

    description_len = len(_norm(job.get("description")))
    quality_score = _safe_float(job.get("quality_score"))
    if source_name in _STRICT_DESCRIPTION_SOURCES and description_len < _MIN_DESCRIPTION_CHARS_STRICT_SOURCES:
        return False
    if description_len < _MIN_DESCRIPTION_CHARS and not (has_apply_signal and has_date_signal):
        return False
    if quality_score < _MIN_QUALITY_SCORE and not (has_apply_signal and has_date_signal and has_job_signal):
        return False
    if any(marker in description for marker in _NOISE_MARKERS) and not has_job_signal:
        return False
    return True


def _normalize_embedding(embedding: Iterable[float]) -> List[float]:
    """
    Convertit un vecteur potentiellement numpy en liste de float Python.
    Evite les erreurs de serialisation (notamment avec NumPy 2.x + client ES).
    """
    if embedding is None:
        return []
    if hasattr(embedding, "tolist"):
        try:
            embedding = embedding.tolist()
        except Exception:
            pass
    try:
        return [float(x) for x in embedding]
    except TypeError:
        return []


def _normalize_json_value(value: Any) -> Any:
    """
    Convertit recursivement les types numpy/iterables en types Python natifs.
    Evite les erreurs de serialisation Elasticsearch (numpy 2.x, qdrant payload, etc.).
    """
    if value is None:
        return None
    if isinstance(value, dict):
        return {k: _normalize_json_value(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_normalize_json_value(v) for v in value]
    if hasattr(value, "tolist"):
        try:
            return _normalize_json_value(value.tolist())
        except Exception:
            pass
    if hasattr(value, "item"):
        try:
            return _normalize_json_value(value.item())
        except Exception:
            pass
    if isinstance(value, (str, int, float, bool)):
        return value
    # BSON/Mongo types (ObjectId, etc.) -> string
    mod = getattr(type(value), "__module__", "")
    if mod.startswith("bson"):
        return str(value)
    return value


def _safe_es_date(job: dict) -> str | None:
    """
    Retourne une date compatible ES (YYYY-MM-DD ou ISO datetime), sinon None.
    Evite les erreurs d'indexation quand posted_date contient du texte bruité.
    """
    candidates = [
        job.get("posted_date_iso"),
        job.get("posted_date"),
    ]
    for raw in candidates:
        if raw is None:
            continue
        value = str(raw).strip()
        if not value:
            continue
        if re.match(r"^\d{4}-\d{2}-\d{2}$", value):
            return value
        if re.match(r"^\d{4}-\d{2}-\d{2}T", value):
            return value
    return None


def prepare_es_document(job: dict, embedding: List[float]) -> dict:
    """
    Prepare un document pour l'indexation ES.
    """
    embedding_values = _normalize_embedding(embedding)
    source_url = canonicalize_tracking_url(job.get("source_url"))
    doc = {
        "job_id": str(job.get("_id")) if job.get("_id") is not None else None,
        "title": job.get("title"),
        "company": job.get("company"),
        "location": job.get("location"),
        "country": job.get("country"),
        "description": job.get("description"),
        "contract_type": job.get("contract_type"),
        "sector": job.get("sector"),
        "hard_skills": job.get("hard_skills", []),
        "soft_skills": job.get("soft_skills", []),
        "experience_years": job.get("experience_years"),
        "source_url": source_url,
        "source_name": job.get("source_name"),
        "posted_date": _safe_es_date(job),
        "posted_date_iso": job.get("posted_date_iso"),
        "deadline_iso": job.get("deadline_iso"),
        "is_expired": job.get("is_expired"),
        "is_stale": job.get("is_stale"),
        "stale_reason": job.get("stale_reason"),
        "freshness_days": job.get("freshness_days"),
        "freshness_source": job.get("freshness_source"),
        "freshness_ttl_days": job.get("freshness_ttl_days"),
        "quality_score": job.get("quality_score"),
        "title_confidence": job.get("title_confidence"),
        "location_confidence": job.get("location_confidence"),
        "date_confidence": job.get("date_confidence"),
        "apply_confidence": job.get("apply_confidence"),
        "description_confidence": job.get("description_confidence"),
        "description_vector": embedding_values,
        "indexed_at": datetime.utcnow().isoformat(),
        "enriched": job.get("enriched", False),
        "enrichment_method": job.get("enrichment_method"),
    }
    return _normalize_json_value(doc)


def prepare_qdrant_payload(job: dict) -> dict:
    """
    Prepare un payload Qdrant (sans vecteur).
    Aligné avec l'API search pour garder la compatibilité des résultats.
    """
    source_url = canonicalize_tracking_url(job.get("source_url"))
    payload = {
        "id": str(job.get("_id")) if job.get("_id") is not None else None,
        "job_id": str(job.get("_id")) if job.get("_id") is not None else None,
        "title": job.get("title"),
        "company": job.get("company"),
        "location": job.get("location"),
        "country": job.get("country"),
        "description": job.get("description"),
        "contract_type": job.get("contract_type"),
        "sector": job.get("sector"),
        "hard_skills": job.get("hard_skills", []) or [],
        "required_skills": job.get("required_skills") or job.get("hard_skills", []) or [],
        "soft_skills": job.get("soft_skills", []) or [],
        "experience_years": job.get("experience_years"),
        "required_experience_years": job.get("required_experience_years") or job.get("experience_years"),
        "salary_min": job.get("salary_min"),
        "salary_max": job.get("salary_max"),
        "remote_work": job.get("remote_work"),
        "seniority_level": job.get("seniority_level"),
        "company_reputation": job.get("company_reputation"),
        "application_rate": job.get("application_rate"),
        "source_url": source_url,
        "source_name": job.get("source_name"),
        "posted_date": job.get("posted_date"),
        "posted_date_iso": job.get("posted_date_iso"),
        "deadline_iso": job.get("deadline_iso"),
        "is_expired": job.get("is_expired"),
        "is_stale": job.get("is_stale"),
        "stale_reason": job.get("stale_reason"),
        "freshness_days": job.get("freshness_days"),
        "freshness_source": job.get("freshness_source"),
        "freshness_ttl_days": job.get("freshness_ttl_days"),
        "quality_score": job.get("quality_score"),
        "title_confidence": job.get("title_confidence"),
        "location_confidence": job.get("location_confidence"),
        "date_confidence": job.get("date_confidence"),
        "apply_confidence": job.get("apply_confidence"),
        "description_confidence": job.get("description_confidence"),
        "indexed_at": datetime.utcnow().isoformat(),
        "enriched": job.get("enriched", False),
        "enrichment_method": job.get("enrichment_method"),
    }
    return _normalize_json_value(payload)


def _norm(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def _safe_float(value: Any) -> float:
    try:
        return float(value)
    except Exception:
        return 0.0


def build_canonical_job_identity(job: dict) -> str:
    """
    Identifiant canonique stable pour dedup cross-sources/index.
    Priorite:
    1) semantic_fingerprint (si fourni par normalizer)
    2) source_url canonique (sans tracking params)
    3) fallback textuel (title/company/location/posted_date_iso)
    """
    semantic = _norm(job.get("semantic_fingerprint")).lower()
    if semantic:
        return f"semantic:{semantic}"

    source_url = canonicalize_tracking_url(job.get("source_url"))
    source_url = _norm(source_url).lower()
    if source_url:
        return f"url:{source_url}"

    fallback = "|".join(
        [
            _norm(job.get("title")).lower(),
            _norm(job.get("company")).lower(),
            _norm(job.get("location")).lower(),
            _norm(job.get("posted_date_iso") or job.get("posted_date")).lower(),
        ]
    )
    return f"fallback:{fallback}"
