"""Normalization helpers for job records (Scrapy + API providers).

Goals:
- keep backward compatibility with existing fields
- add normalized date and application metadata
- centralize fingerprint generation and URL canonicalization
"""

from __future__ import annotations

import hashlib
import re
from datetime import date, datetime, timedelta, timezone
from typing import Any, Iterable, Mapping, MutableMapping, Optional
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

from scrapy_project.smart_parser.entities import extract_emails, extract_phones, extract_urls

TRACKING_QUERY_KEYS = {
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

NON_JOB_TITLE_KEYWORDS = (
    "formation",
    "formations",
    "cours",
    "certification",
    "webinar",
    "webinaire",
    "tutoriel",
    "tutorial",
)

NON_JOB_URL_HINTS = (
    "/category/",
    "/tag/",
    "/blog/",
    "/actualites",
    "/news/",
    "/formation",
    "/formations",
    "/cours/",
)

JOB_SIGNAL_KEYWORDS = (
    "recrute",
    "recrutement",
    "offre",
    "emploi",
    "poste",
    "job",
    "stage",
    "internship",
    "cdi",
    "cdd",
    "h/f",
    "analyst",
    "engineer",
    "developer",
    "devops",
    "comptable",
    "accountant",
)

APPLY_KEYWORDS = (
    "postuler",
    "candidater",
    "candidature",
    "apply",
    "envoyer",
    "soumettre",
    "deposer",
    "dossier",
    "cv",
    "lettre de motivation",
)

_MONTHS = {
    # FR
    "janvier": 1,
    "janv": 1,
    "jan": 1,
    "fevrier": 2,
    "fevr": 2,
    "fev": 2,
    "fvrier": 2,
    "mars": 3,
    "avril": 4,
    "avr": 4,
    "mai": 5,
    "juin": 6,
    "juillet": 7,
    "juil": 7,
    "aout": 8,
    "aot": 8,
    "septembre": 9,
    "sept": 9,
    "octobre": 10,
    "oct": 10,
    "novembre": 11,
    "nov": 11,
    "decembre": 12,
    "dec": 12,
    # EN
    "january": 1,
    "february": 2,
    "feb": 2,
    "march": 3,
    "april": 4,
    "apr": 4,
    "june": 6,
    "july": 7,
    "august": 8,
    "aug": 8,
    "september": 9,
    "sep": 9,
    "october": 10,
    "november": 11,
    "december": 12,
}


def normalize_job_record(
    job: MutableMapping[str, Any],
    *,
    source_name: str = "",
    now: Optional[datetime] = None,
) -> MutableMapping[str, Any]:
    """Normalize a job record in-place and return it."""
    now_utc = now or datetime.now(timezone.utc)

    # Basic cleanup
    for key in ("title", "company", "location", "description", "posted_date", "source_url", "apply_url"):
        if key in job and isinstance(job.get(key), str):
            job[key] = _normalize_space(job.get(key))

    if job.get("source_url"):
        job["source_url"] = canonicalize_url(_safe_str(job.get("source_url")))
    if job.get("apply_url"):
        job["apply_url"] = canonicalize_url(_safe_str(job.get("apply_url")))

    # Conservative sanitation for noisy parsers.
    if job.get("title"):
        title = _normalize_space(_safe_str(job.get("title")))
        if len(title) > 260:
            title = title[:260].rsplit(" ", 1)[0]
        job["title"] = title
    company = _normalize_space(_safe_str(job.get("company")))
    if company:
        if len(company) > 140 or company.count(" ") > 18:
            company = ""
        job["company"] = company or None

    # Keep raw posted date and compute normalized ISO date (YYYY-MM-DD).
    posted_raw = _first_non_empty(
        job.get("posted_date_raw"),
        job.get("posted_date"),
        _extract_candidate_date_from_text(job.get("description", "")),
    )
    job["posted_date_raw"] = posted_raw
    posted_iso = normalize_posted_date_to_iso(posted_raw, now=now_utc)
    if posted_iso:
        job["posted_date_iso"] = posted_iso
    else:
        job.setdefault("posted_date_iso", None)

    # Keep original posted_date for backward compatibility if already set.
    if not job.get("posted_date") and posted_raw:
        job["posted_date"] = posted_raw

    # Deadline normalization (kept separate from publication date)
    deadline_raw = _first_non_empty(
        job.get("deadline_raw"),
        job.get("deadline"),
    )
    job["deadline_raw"] = deadline_raw
    deadline_iso = normalize_posted_date_to_iso(deadline_raw, now=now_utc)
    if deadline_iso:
        job["deadline_iso"] = deadline_iso
    else:
        job.setdefault("deadline_iso", None)
    if not job.get("deadline") and deadline_raw:
        job["deadline"] = deadline_raw

    if deadline_iso:
        deadline_date = date.fromisoformat(deadline_iso)
        delta_days = (deadline_date - now_utc.date()).days
        job["days_until_deadline"] = delta_days
        job["is_expired"] = delta_days < 0
    else:
        job.setdefault("days_until_deadline", None)
        job.setdefault("is_expired", None)

    # Application metadata
    _enrich_apply_fields(job)

    semantic_fingerprint = compute_job_semantic_fingerprint(job)
    if semantic_fingerprint:
        job["semantic_fingerprint"] = semantic_fingerprint

    is_probable_job = is_probable_job_record(job)
    job["is_probable_job"] = is_probable_job

    # Normalize skills to list[str]
    skills = job.get("skills")
    if skills is None:
        job["skills"] = []
    elif isinstance(skills, str):
        job["skills"] = [s.strip() for s in re.split(r"[,;/|]", skills) if s.strip()]
    elif isinstance(skills, Iterable) and not isinstance(skills, (bytes, bytearray, dict)):
        normalized_skills = []
        for s in skills:
            if s is None:
                continue
            val = _normalize_space(str(s))
            if val:
                normalized_skills.append(val)
        job["skills"] = normalized_skills
    else:
        job["skills"] = []

    # Ensure extra_data is a dict and persist normalization details.
    extra_data = job.get("extra_data")
    if not isinstance(extra_data, dict):
        extra_data = {}
    if source_name and not extra_data.get("source_site"):
        extra_data["source_site"] = source_name
    if posted_raw:
        extra_data.setdefault("posted_date_raw", posted_raw)
    if job.get("posted_date_iso"):
        extra_data.setdefault("posted_date_iso", job.get("posted_date_iso"))
    if deadline_raw:
        extra_data.setdefault("deadline_raw", deadline_raw)
    if job.get("deadline_iso"):
        extra_data.setdefault("deadline_iso", job.get("deadline_iso"))
    if job.get("is_expired") is not None:
        extra_data.setdefault("is_expired", job.get("is_expired"))
    if job.get("apply_method"):
        extra_data.setdefault("apply_method", job.get("apply_method"))
    extra_data.setdefault("is_probable_job", bool(job.get("is_probable_job", True)))
    if semantic_fingerprint:
        extra_data.setdefault("semantic_fingerprint", semantic_fingerprint)
    job["extra_data"] = extra_data

    return job


def compute_job_fingerprint(job: Mapping[str, Any]) -> str:
    """Stable fingerprint with URL canonicalization and normalized text."""
    source_url = canonicalize_url(_safe_str(job.get("source_url")))
    title = _normalize_space(_safe_str(job.get("title"))).lower()
    company = _normalize_space(_safe_str(job.get("company"))).lower()
    location = _normalize_space(_safe_str(job.get("location"))).lower()
    description = _normalize_space(_safe_str(job.get("description"))).lower()
    description = description[:4000]  # bound hash cost and noise

    content = f"{source_url}|{title}|{company}|{location}|{description}"
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def compute_job_semantic_fingerprint(job: Mapping[str, Any]) -> Optional[str]:
    """
    Fingerprint plus robuste contre duplications inter-URLs (UTM, mirrors).
    Intègre l'identité métier (titre/entreprise/lieu/date) et le domaine source.
    """
    title = _normalize_space(_safe_str(job.get("title"))).lower()
    if len(title) < 6:
        return None
    company = _normalize_space(_safe_str(job.get("company"))).lower()
    location = _normalize_space(_safe_str(job.get("location"))).lower()
    posted = _normalize_space(
        _safe_str(job.get("posted_date_iso") or job.get("posted_date"))
    ).lower()
    deadline = _normalize_space(
        _safe_str(job.get("deadline_iso") or job.get("deadline"))
    ).lower()
    source_url = canonicalize_url(_safe_str(job.get("source_url")))
    apply_url = canonicalize_url(_safe_str(job.get("apply_url")))
    source_domain = _domain(source_url)
    apply_domain = _domain(apply_url)

    # Date helps avoid collapsing recurrent openings with same title/company.
    identity_date = posted or deadline
    if not identity_date and not (company or location):
        return None

    payload = "|".join(
        [
            title,
            company,
            location,
            identity_date,
            source_domain,
            apply_domain,
        ]
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def is_probable_job_record(job: Mapping[str, Any]) -> bool:
    """
    Heuristique conservatrice pour filtrer articles/formations non-offres.
    Ne rejette que les cas fortement suspects.
    """
    title = _normalize_space(_safe_str(job.get("title"))).lower()
    source_url = canonicalize_url(_safe_str(job.get("source_url"))).lower()
    description = _normalize_space(_safe_str(job.get("description"))).lower()
    apply_method = _normalize_space(_safe_str(job.get("apply_method"))).lower()
    posted = _normalize_space(_safe_str(job.get("posted_date") or job.get("posted_date_iso")))
    deadline = _normalize_space(_safe_str(job.get("deadline") or job.get("deadline_iso")))

    blob = f"{title} {description}"
    has_job_signal = any(token in blob for token in JOB_SIGNAL_KEYWORDS)
    has_apply_signal = bool(apply_method and apply_method != "unknown") or bool(job.get("apply_url") or job.get("apply_email"))
    has_time_signal = bool(posted or deadline)

    if any(hint in source_url for hint in NON_JOB_URL_HINTS):
        if not (has_job_signal or has_apply_signal or has_time_signal):
            return False

    if any(token in title for token in NON_JOB_TITLE_KEYWORDS):
        strong_course_title = any(title.startswith(p) for p in ("formation ", "formations ", "cours ", "certification ", "webinar ", "webinaire "))
        if strong_course_title and not (has_job_signal or has_apply_signal):
            return False
        if not (has_job_signal or has_apply_signal) and any(t in title for t in ("cours", "certification", "webinar", "webinaire")):
            return False

    return True


def canonicalize_url(url: str) -> str:
    url = _normalize_space(url)
    if not url:
        return ""
    if url.startswith("mailto:") or url.startswith("tel:"):
        return url
    if url.startswith("www."):
        url = f"https://{url}"
    if not re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*://", url):
        return url

    try:
        parsed = urlparse(url)
    except Exception:
        return url

    scheme = parsed.scheme.lower() or "https"
    netloc = parsed.netloc.lower()
    path = parsed.path or "/"
    if len(path) > 1:
        path = re.sub(r"/{2,}", "/", path).rstrip("/") or "/"

    query_pairs = []
    for k, v in parse_qsl(parsed.query, keep_blank_values=True):
        key_lower = (k or "").lower()
        if key_lower in TRACKING_QUERY_KEYS or key_lower.startswith("utm_"):
            continue
        query_pairs.append((k, v))
    query_pairs.sort(key=lambda pair: (pair[0], pair[1]))
    query = urlencode(query_pairs, doseq=True)

    return urlunparse((scheme, netloc, path, "", query, ""))


def normalize_posted_date_to_iso(
    raw: Optional[str],
    *,
    now: Optional[datetime] = None,
) -> Optional[str]:
    """Normalize a wide range of raw date expressions to YYYY-MM-DD."""
    value = _normalize_space(raw)
    if not value:
        return None
    now_utc = now or datetime.now(timezone.utc)

    # Clean labels and common prefixes while preserving signal.
    lowered = _strip_accents(value.lower())
    lowered = re.sub(
        r"^(publie(?:e)?\s*(?:le)?|posted\s*(?:on)?|mise?\s+a\s+jour\s*:?)\s*[:\-]?\s*",
        "",
        lowered,
    ).strip()

    rel_date = _parse_relative_date(lowered, now_utc)
    if rel_date:
        return rel_date.isoformat()

    # Try ISO / datetime formats first.
    iso_candidate = value.replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(iso_candidate)
        return dt.date().isoformat()
    except Exception:
        pass
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        return value

    for fmt in ("%d/%m/%Y", "%d-%m-%Y", "%d.%m.%Y", "%Y/%m/%d", "%Y.%m.%d"):
        try:
            return datetime.strptime(value, fmt).date().isoformat()
        except ValueError:
            continue

    # dd/mm/yy or dd-mm-yy
    m = re.fullmatch(r"(\d{1,2})[/-](\d{1,2})[/-](\d{2})", value)
    if m:
        day, month, year = int(m.group(1)), int(m.group(2)), int(m.group(3))
        year += 2000 if year < 70 else 1900
        return _safe_date(year, month, day)

    # Month names (FR/EN), optionally year missing.
    month_name_date = _parse_month_name_date(lowered, now_utc.date().year)
    if month_name_date:
        return month_name_date.isoformat()

    # Last resort flexible extraction from cleaned text.
    fallback = _extract_candidate_date_from_text(value)
    if fallback and fallback != value:
        return normalize_posted_date_to_iso(fallback, now=now_utc)
    return None


def _enrich_apply_fields(job: MutableMapping[str, Any]) -> None:
    description = _safe_str(job.get("description"))
    source_url = canonicalize_url(_safe_str(job.get("source_url")))
    apply_url = canonicalize_url(_safe_str(job.get("apply_url")))
    explicit_apply_method = _safe_str(job.get("apply_method")).strip().lower()

    emails = extract_emails(description)
    phones = extract_phones(description)
    urls = [canonicalize_url(u) for u in extract_urls(description)]

    if apply_url.startswith("mailto:"):
        email = apply_url.split("mailto:", 1)[1].split("?", 1)[0].strip()
        if email and email not in emails:
            emails.insert(0, email)
    if apply_url.startswith("tel:"):
        phone = apply_url.split("tel:", 1)[1].strip()
        if phone and phone not in phones:
            phones.insert(0, phone)

    if not apply_url:
        apply_url = _pick_apply_url_from_text(urls, source_url)

    # Reuse contact fields if already extracted and keep aliases in sync.
    apply_email = _first_non_empty(job.get("apply_email"), job.get("contact_email"))
    if not apply_email and emails:
        apply_email = emails[0]

    apply_phone = _first_non_empty(job.get("apply_phone"), job.get("contact_phone"))
    if not apply_phone and phones:
        apply_phone = phones[0]

    apply_instructions = _first_non_empty(
        job.get("apply_instructions"),
        _extract_apply_instruction(description),
    )

    apply_method = classify_apply_method(
        apply_url=apply_url,
        source_url=source_url,
        apply_email=apply_email,
        apply_phone=apply_phone,
        apply_instructions=apply_instructions,
    )
    if explicit_apply_method and explicit_apply_method != "unknown":
        # Les parsers spécifiques (ex: emploi.tg formulaire intégré) peuvent être plus précis
        # que la détection générique basée sur URL/email/téléphone.
        apply_method = explicit_apply_method

    job["apply_url"] = apply_url or None
    job["apply_email"] = apply_email or None
    job["apply_phone"] = apply_phone or None
    job["apply_method"] = apply_method
    job["apply_instructions"] = apply_instructions or None

    # Legacy aliases kept for compatibility.
    if apply_email and not job.get("contact_email"):
        job["contact_email"] = apply_email
    if apply_phone and not job.get("contact_phone"):
        job["contact_phone"] = apply_phone


def classify_apply_method(
    *,
    apply_url: str,
    source_url: str,
    apply_email: Optional[str],
    apply_phone: Optional[str],
    apply_instructions: Optional[str],
) -> str:
    apply_url = apply_url or ""
    source_url = source_url or ""

    if apply_url.startswith("mailto:") or apply_email:
        return "email"
    if apply_url.startswith("tel:") or apply_phone:
        return "phone"
    if apply_url:
        if _looks_like_internal_form(apply_url):
            return "internal_form"
        if source_url:
            source_domain = _domain(source_url)
            apply_domain = _domain(apply_url)
            if apply_domain and source_domain and apply_domain != source_domain:
                return "external_url"
        if _looks_like_apply_link(apply_url):
            return "external_url"
        return "unknown"
    if apply_instructions:
        return "text_instruction"
    return "unknown"


def _looks_like_internal_form(url: str) -> bool:
    u = url.lower()
    return any(token in u for token in ("/apply", "/postuler", "/candid", "apply=", "postuler=", "form"))


def _looks_like_apply_link(url: str) -> bool:
    u = url.lower()
    return any(token in u for token in ("apply", "postuler", "candid", "career", "jobs/", "recrut"))


def _pick_apply_url_from_text(urls: list[str], source_url: str) -> Optional[str]:
    if not urls:
        return None
    source_domain = _domain(source_url)
    scored: list[tuple[int, str]] = []
    for url in urls:
        score = 0
        low = url.lower()
        if _looks_like_apply_link(low):
            score += 5
        if source_domain and _domain(url) and _domain(url) != source_domain:
            score += 2
        if any(x in low for x in ("linkedin.com/jobs", "indeed", "greenhouse", "lever.co", "workday", "smartrecruiters")):
            score += 3
        scored.append((score, url))
    scored.sort(key=lambda x: (-x[0], x[1]))
    best_score, best_url = scored[0]
    return best_url if best_score > 0 else None


def _extract_apply_instruction(text: str) -> Optional[str]:
    if not text:
        return None
    # Prefer line-based extraction when source text preserves line breaks.
    for raw_line in re.split(r"[\r\n]+", text):
        line = _normalize_space(raw_line)
        if not line:
            continue
        low = _strip_accents(line.lower())
        if any(k in low for k in APPLY_KEYWORDS):
            return line[:300]

    # Fallback: sentence scan on flattened text.
    for sentence in re.split(r"(?<=[\.\!\?;:])\s+", text):
        line = _normalize_space(sentence)
        if not line:
            continue
        low = _strip_accents(line.lower())
        if any(k in low for k in APPLY_KEYWORDS):
            return line[:300]
    return None


def _extract_candidate_date_from_text(text: str) -> Optional[str]:
    if not text:
        return None
    # Prefer publication labels before deadline labels.
    patterns = [
        r"(?:publie|publiee|posted)\s*(?:le|on)?\s*[:\-]?\s*([^\n\.;]{4,40})",
        r"(?:date de publication|publication)\s*[:\-]?\s*([^\n\.;]{4,40})",
        r"(?:today|today posted|hier|yesterday|recently posted|\d+\+?\s*(?:days?|jours?)\s*ago)",
        r"(\d{4}-\d{2}-\d{2})",
        r"(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})",
        r"(\d{1,2}\s+[A-Za-z\u00C0-\u017F\.]+\s+\d{2,4})",
    ]
    for pattern in patterns:
        m = re.search(pattern, text, re.IGNORECASE)
        if m:
            return _normalize_space(m.group(1) if m.lastindex else m.group(0))
    return None


def _parse_relative_date(value: str, now: datetime) -> Optional[date]:
    txt = value.strip()
    if not txt:
        return None
    if any(token in txt for token in ("today", "aujourd", "ce jour", "just now", "now", "recently posted", "recent")):
        return now.date()
    if any(token in txt for token in ("yesterday", "hier")):
        return (now - timedelta(days=1)).date()

    patterns = [
        (r"(\d+)\+?\s*(?:day|days|jour|jours)\b", "days"),
        (r"(\d+)\+?\s*(?:hour|hours|heure|heures|hr|hrs)\b", "hours"),
        (r"(\d+)\+?\s*(?:week|weeks|semaine|semaines)\b", "weeks"),
        (r"(\d+)\+?\s*(?:month|months|mois)\b", "months"),
    ]
    for pattern, unit in patterns:
        m = re.search(pattern, txt)
        if not m:
            continue
        qty = int(m.group(1))
        if unit == "days":
            return (now - timedelta(days=qty)).date()
        if unit == "hours":
            return now.date()
        if unit == "weeks":
            return (now - timedelta(days=qty * 7)).date()
        if unit == "months":
            return (now - timedelta(days=qty * 30)).date()
    return None


def _parse_month_name_date(value_ascii_lower: str, default_year: int) -> Optional[date]:
    cleaned = re.sub(r"[,\u00A0]", " ", value_ascii_lower)
    cleaned = re.sub(r"\s+", " ", cleaned).strip(". ")

    # "15 janvier 2026" or "15 janv. 2026"
    m = re.search(r"\b(\d{1,2})\s+([a-z]+)\.?\s+(\d{4}|\d{2})\b", cleaned)
    if m:
        day = int(m.group(1))
        month = _MONTHS.get(m.group(2))
        year = int(m.group(3))
        if year < 100:
            year += 2000 if year < 70 else 1900
        if month:
            return _safe_date_obj(year, month, day)

    # "janvier 15 2026" / "feb 2 2026"
    m = re.search(r"\b([a-z]+)\.?\s+(\d{1,2})(?:st|nd|rd|th)?\s+(\d{4})\b", cleaned)
    if m:
        month = _MONTHS.get(m.group(1))
        day = int(m.group(2))
        year = int(m.group(3))
        if month:
            return _safe_date_obj(year, month, day)

    # "15 janvier" (year omitted)
    m = re.search(r"\b(\d{1,2})\s+([a-z]+)\.?\b", cleaned)
    if m:
        day = int(m.group(1))
        month = _MONTHS.get(m.group(2))
        if month:
            candidate = _safe_date_obj(default_year, month, day)
            # If far in the future, interpret as previous year.
            if candidate and candidate > (date.today() + timedelta(days=7)):
                prev = _safe_date_obj(default_year - 1, month, day)
                return prev or candidate
            return candidate
    return None


def _safe_date(year: int, month: int, day: int) -> Optional[str]:
    dt = _safe_date_obj(year, month, day)
    return dt.isoformat() if dt else None


def _safe_date_obj(year: int, month: int, day: int) -> Optional[date]:
    try:
        return date(year, month, day)
    except ValueError:
        return None


def _domain(url: str) -> str:
    try:
        return urlparse(url).netloc.lower().replace("www.", "")
    except Exception:
        return ""


def _safe_str(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    return str(value)


def _normalize_space(value: str) -> str:
    return re.sub(r"\s+", " ", (value or "")).strip()


def _first_non_empty(*values: Any) -> Optional[str]:
    for value in values:
        if value is None:
            continue
        text = _normalize_space(_safe_str(value))
        if text:
            return text
    return None


def _strip_accents(text: str) -> str:
    # Light-weight accent normalization without external dependencies.
    replacements = str.maketrans(
        {
            "à": "a",
            "â": "a",
            "ä": "a",
            "á": "a",
            "ç": "c",
            "é": "e",
            "è": "e",
            "ê": "e",
            "ë": "e",
            "î": "i",
            "ï": "i",
            "ì": "i",
            "í": "i",
            "ô": "o",
            "ö": "o",
            "ò": "o",
            "ó": "o",
            "ù": "u",
            "û": "u",
            "ü": "u",
            "ú": "u",
            "œ": "oe",
            "’": "'",
        }
    )
    return text.translate(replacements)
