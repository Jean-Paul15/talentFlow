from __future__ import annotations

import re
from typing import Any, Mapping, Optional
from urllib.parse import unquote, urlparse

from processors.normalizers import normalize_contract_type, normalize_country, normalize_location


GENERIC_BAD_TITLES = {
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

GENERIC_TITLE_PATTERNS = (
    re.compile(r"^\(?[fh]/?[hf]\)?\.?$", re.IGNORECASE),
    re.compile(r"^p\d+$", re.IGNORECASE),
    re.compile(r"^poste\s*:?\s*$", re.IGNORECASE),
    re.compile(r"^intitul[eé]\s+du\s+poste\s*:?\s*$", re.IGNORECASE),
    re.compile(r"^activit[eé]s?\s+principales\s*:?\s*$", re.IGNORECASE),
)

ANPE_LOCATION_PATTERNS = (
    r"lieu d['’]affectation\s*[:\-]?\s*(.+?)(?=\s+(?:d[ée]but des fonctions|nature du contrat|unit[ée] organisationnelle|salaire et indemnit[ée]s|formation\s*:|exp[ée]rience\s*[–:-]|autres exigences|comp[ée]tences\s*:|langues\s*:|$))",
    r"(?:poste\s+bas[eé]\s+[aà]|bas[eé]\s+[aà]|lieu\s*[:\-]|localisation\s*[:\-])\s*([^.;\n]{2,80})",
    r"lieu d['’]affectation\s*[:\-]?\s*([^.;\n]{2,80})",
    r"zone d['’]intervention directe\s*([^.;\n]{2,80})",
)

ANPE_CONTRACT_PATTERNS = (
    r"nature du contrat\s*[:\-]?\s*([^.;\n]{2,120})",
    r"type de contrat\s*[:\-]?\s*([^.;\n]{2,120})",
    r"statut\s*[:\-]?\s*([^.;\n]{2,120})",
    r"\b(cdi|cdd|stage|freelance|prestataire|consultant|contrat de prestation|contrat [aà] dur[ée]e d[ée]termin[ée]e|contrat [aà] dur[ée]e ind[ée]termin[ée]e)\b",
)

EMPLOI_TG_LOCATION_HINTS = (
    ("teletravail", "Remote"),
    ("télétravail", "Remote"),
    ("travail a distance", "Remote"),
    ("travail à distance", "Remote"),
    ("distance/", "Remote"),
    ("international", "International"),
    ("lome", "Lome"),
    ("lomé", "Lome"),
    ("djidjole", "Lome"),
    ("djidjolé", "Lome"),
    ("adidogome", "Lome"),
    ("adidogomé", "Lome"),
    ("avenou", "Lome"),
    ("atakpame", "Atakpame"),
    ("atakpamé", "Atakpame"),
    ("kpalime", "Kpalime"),
    ("kpalimé", "Kpalime"),
    ("dapaong", "Dapaong"),
    ("aneho", "Aneho"),
    ("aného", "Aneho"),
    ("tsevie", "Tsevie"),
    ("tsévié", "Tsevie"),
    ("sokode", "Sokode"),
    ("sokodé", "Sokode"),
    ("kara", "Kara"),
    ("yaounde", "Yaounde"),
    ("yaoundé", "Yaounde"),
    ("paris", "Paris"),
    ("libreville", "Libreville"),
    ("france", "France"),
)

EMPLOI_TG_BAD_LOCATION_TOKENS = (
    "etudiant",
    "étudiant",
    "jeune diplome",
    "jeune diplômé",
    "debutant",
    "débutant",
    "experience entre",
    "expérience entre",
    "experience >",
    "expérience >",
    "niveau d'experience",
    "niveau d’expérience",
)


def _clean_space(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def _normalize_key(value: Any) -> str:
    cleaned = _clean_space(value).lower()
    return cleaned.replace("’", "'")


def _is_generic_title(value: Optional[str]) -> bool:
    cleaned = _clean_space(value)
    if not cleaned:
        return True
    normalized = _normalize_key(cleaned)
    if normalized in GENERIC_BAD_TITLES:
        return True
    if len(re.sub(r"[^a-z0-9]+", "", normalized)) < 4:
        return True
    return any(pattern.fullmatch(cleaned) for pattern in GENERIC_TITLE_PATTERNS)


def _looks_like_salary_noise(value: Optional[str]) -> bool:
    cleaned = _normalize_key(value)
    if not cleaned:
        return False
    if len(cleaned) > 48:
        return True
    if cleaned in {"et indemnites", "et indemnités"}:
        return True
    if cleaned.startswith(("/", ",", ";", ":")):
        return True
    if any(token in cleaned for token in ("salaire", "indemnit", "ajustement annuel", "salaire de base")):
        return True
    if any(token in cleaned for token in ("default color", "javascript", "visualiser", "blue color", "red color")):
        return True
    return cleaned in GENERIC_BAD_TITLES


def _looks_like_spam_placeholder(value: Optional[str]) -> bool:
    cleaned = _normalize_key(value)
    if not cleaned:
        return False
    return any(
        token in cleaned
        for token in (
            "robots spammeurs",
            "activer le javascript",
            "javascript pour la visualiser",
            "adresse e-mail est protegee",
            "adresse e mail est protegee",
        )
    )


def _looks_like_bad_location(value: Optional[str]) -> bool:
    cleaned = _normalize_key(value)
    if not cleaned:
        return True
    if len(cleaned) > 90:
        return True
    return any(
        token in cleaned
        for token in (
            "$ us",
            "salaire",
            "indemnit",
            "ajustement annuel",
            "salaire de base",
            "l'ajustement",
            "net lors de la nomination",
        )
    )


def _looks_like_emploi_tg_bad_location(value: Optional[str]) -> bool:
    cleaned = _normalize_key(value)
    if not cleaned:
        return True
    if len(cleaned) > 90:
        return True
    return any(token in cleaned for token in EMPLOI_TG_BAD_LOCATION_TOKENS)


def _prettify_title(value: str) -> str:
    cleaned = _clean_space(value)
    cleaned = re.sub(r"\s*[-–]\s*", " - ", cleaned)
    cleaned = re.sub(r"\b([Ff])\s*/?\s*([Hh])\b", "F/H", cleaned)
    cleaned = re.sub(r"\b([Hh])\s*/?\s*([Ff])\b", "H/F", cleaned)
    cleaned = re.sub(r"\s+\.\s*$", "", cleaned)
    return cleaned[:255]


def _title_from_slug(source_url: str) -> Optional[str]:
    raw = _clean_space(source_url)
    if not raw:
        return None
    try:
        slug = unquote(urlparse(raw).path.rsplit("/", 1)[-1])
    except Exception:
        return None
    slug = re.sub(r"^\d+-", "", slug)
    slug = slug.replace(".html", "")
    slug = re.sub(r"[-_]+", " ", slug)
    slug = re.sub(r"\b0+(\d)\b", r"\1", slug)
    slug = _prettify_title(slug)
    return None if _is_generic_title(slug) else slug


def _extract_company_from_text(text: str) -> Optional[str]:
    cleaned = _clean_space(text)
    if not cleaned:
        return None

    generic_match = re.search(
        r"(?:avis de recrutement\s+)?([A-Z][A-Za-z0-9&'().\- ]{2,80}?)\s*(?:,\s*(?:entreprise|organisation|institution)|\s+recrute\b|\s+recherche\b|\s+informe\b)",
        cleaned,
        re.IGNORECASE,
    )
    if generic_match:
        candidate = _prettify_title(generic_match.group(1))
        if "anpe" in _normalize_key(candidate) or "emploi (anpe)" in _normalize_key(candidate):
            candidate = ""
        if candidate and not _is_generic_title(candidate):
            return candidate

    org_match = re.search(r"\b(AVSF|OMPI|OMM|OMS|ONU|OIM|OMC|OIT|BIT|WIPO|WMO|UNESCO|UNICEF|FAO)\b", cleaned, re.IGNORECASE)
    if org_match:
        return _prettify_title(org_match.group(1).upper())
    return None


def _extract_anpe_title(description: str) -> Optional[str]:
    text = _clean_space(description)
    if not text:
        return None

    patterns = (
        r"(?:profils?\s+aux?\s+postes?\s+suivants?\s*:\s*(?:\([Ff]/?[Hh]\)\.?\s*)?)([^.;:\n]{4,180}?)(?=\s+Activit[eé]s?\s+principales)",
        r"intitul[eé]\s+du\s+poste\s*[:\-]?\s*([^.;\n]{4,180})",
        r"poste\s*:\s*([^.;\n]{4,180})",
        r"([^.]{4,180}?)(?=\s+Activit[eé]s?\s+principales)",
        r"([^.]{4,180}?)(?=\s+(?:POST|Niveau|Lieu d['’]affectation|Nature du contrat))",
    )
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if not match:
            continue
        candidate = match.group(1)
        candidate = re.split(r"(?:Profil du candidat|Profil recherch[ée]|Dossier de candidature)", candidate, maxsplit=1, flags=re.IGNORECASE)[0]
        candidate = _prettify_title(candidate.strip(" .:-"))
        candidate = re.sub(r"^(?:Un|Une|Deux|Trois|Quatre|Cinq)\s+\(\d+\)\s+", "", candidate, flags=re.IGNORECASE)
        candidate = re.sub(r"^(?:Un|Une|Deux|Trois|Quatre|Cinq)\s+", "", candidate, flags=re.IGNORECASE)
        if candidate and not _is_generic_title(candidate):
            return candidate
    return None


def _extract_anpe_location(description: str, current_location: str) -> str:
    text = _clean_space(description)
    for pattern in ANPE_LOCATION_PATTERNS:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            candidate = match.group(1)
            candidate = re.split(
                r"(?:d[ée]but des fonctions|nature du contrat|unit[ée] organisationnelle|salaire et indemnit[ée]s|formation\s*:|exp[ée]rience\s*[–:-]|autres exigences|comp[ée]tences\s*:|langues\s*:)",
                candidate,
                maxsplit=1,
                flags=re.IGNORECASE,
            )[0]
            candidate = candidate.strip(" .:-")
            if candidate and not _looks_like_bad_location(candidate):
                return normalize_location(candidate)
    return normalize_location(current_location or "Togo")


def _extract_anpe_contract(description: str, current_contract: Optional[str]) -> Optional[str]:
    text = _clean_space(description)
    for pattern in ANPE_CONTRACT_PATTERNS:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            candidate = _clean_space(match.group(1))
            if candidate:
                return normalize_contract_type(candidate)
    return normalize_contract_type(current_contract)


def _extract_anpe_publication_date(description: str) -> Optional[str]:
    text = _clean_space(description)
    patterns = (
        r"date de publication(?: de l'avis de vacance de poste)?\s*[:\-]?\s*([^.]{6,80})",
        r"publi[ée]\s+le\s*([^.]{6,80})",
    )
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return _clean_space(match.group(1)).strip(" .;:")
    return None


def _extract_anpe_deadline(description: str, current_deadline: Optional[str]) -> Optional[str]:
    def _sanitize_deadline(candidate: Optional[str]) -> Optional[str]:
        cleaned = _clean_space(candidate)
        if not cleaned or _looks_like_spam_placeholder(cleaned):
            return None
        cleaned = re.split(
            r"(?:il reste\s+\d+\s+jours?|les candidatures sont actuellement accept[ée]es|dossiers num[ée]riques|candidature|en objet|veuillez indiquer)",
            cleaned,
            maxsplit=1,
            flags=re.IGNORECASE,
        )[0].strip(" .;:-")
        explicit_date = re.search(
            r"((?:lundi|mardi|mercredi|jeudi|vendredi|samedi|dimanche)\s+)?\d{1,2}\s+\w+\s*\d{0,4}(?:\s+[àa]\s+\d{1,2}\s*h(?:\s*\d{2})?(?:\s*[A-Z]{2,4})?)?",
            cleaned,
            re.IGNORECASE,
        )
        if explicit_date:
            cleaned = explicit_date.group(0).strip(" .;:-")
        return cleaned or None

    current = _sanitize_deadline(current_deadline)
    if current:
        return current

    text = _clean_space(description)
    patterns = (
        r"date limite de candidature\s*[:\-]?\s*([^.;\n]{6,120})",
        r"date limite de d[ée]p[oô]t(?: de dossiers?)?\s*[:\-]?\s*([^.;\n]{6,120})",
        r"au plus tard le\s+([^.;\n]{6,120})",
        r"plus tard le\s+([^.;\n]{6,120})",
    )
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if not match:
            continue
        candidate = _sanitize_deadline(match.group(1))
        if candidate:
            return candidate
    return None


def _clean_long_company(company: str) -> Optional[str]:
    cleaned = _clean_space(company)
    if not cleaned:
        return None
    if len(cleaned) > 120 or cleaned.count(" ") > 14:
        return None
    return cleaned


def _clean_recruiter_name(value: Optional[str]) -> Optional[str]:
    cleaned = _clean_space(value)
    if not cleaned:
        return None
    lowered = _normalize_key(cleaned)
    if "anpe" in lowered:
        return None
    if len(cleaned) > 80 or any(ch.isdigit() for ch in cleaned):
        return None
    return cleaned


def _extract_emploi_tg_location(*candidates: Any) -> Optional[str]:
    for raw_candidate in candidates:
        candidate = _clean_space(raw_candidate)
        if not candidate:
            continue
        lowered = _normalize_key(candidate)
        for token, normalized in EMPLOI_TG_LOCATION_HINTS:
            if token in lowered:
                return normalize_location(normalized)
    return None


class SourceCleaner:
    """
    Nettoyage source-specifique apres nettoyage texte generique.
    """

    def clean(self, job: dict, raw_job: Optional[Mapping[str, Any]] = None) -> dict:
        source_name = _clean_space((job or {}).get("source_name") or (raw_job or {}).get("source_name"))
        if source_name == "anpe_togo":
            return self._clean_anpe(job, raw_job or {})
        if source_name == "emploi_tg":
            return self._clean_emploi_tg(job, raw_job or {})
        return self._clean_generic(job)

    def _clean_generic(self, job: dict) -> dict:
        if _looks_like_salary_noise(job.get("salary")):
            job["salary"] = None
        if _looks_like_spam_placeholder(job.get("deadline")):
            job["deadline"] = None
        job["location"] = normalize_location(job.get("location"))
        job["contract_type"] = normalize_contract_type(job.get("contract_type"))
        job["recruiter_name"] = _clean_recruiter_name(job.get("recruiter_name"))
        job["country"] = normalize_country(
            job.get("country"),
            location=job.get("location"),
            source_name=job.get("source_name"),
        )
        return job

    def _clean_anpe(self, job: dict, raw_job: Mapping[str, Any]) -> dict:
        description = _clean_space(job.get("description") or raw_job.get("description"))
        extra_data = raw_job.get("extra_data") if isinstance(raw_job.get("extra_data"), dict) else {}
        listing_title = _clean_space(extra_data.get("listing_title")) if isinstance(extra_data, Mapping) else ""

        title_candidates = [
            listing_title,
            job.get("title"),
            _extract_anpe_title(description),
            _title_from_slug(job.get("source_url") or raw_job.get("source_url") or ""),
        ]
        for candidate in title_candidates:
            candidate = _prettify_title(candidate or "")
            if candidate and not _is_generic_title(candidate):
                job["title"] = candidate
                break

        company = _clean_long_company(job.get("company"))
        if not company or company.lower().startswith("via anpe"):
            company = _extract_company_from_text(description) or "Via ANPE Togo"
        job["company"] = company

        job["location"] = _extract_anpe_location(description, str(job.get("location") or raw_job.get("location") or "Togo"))
        job["contract_type"] = _extract_anpe_contract(description, job.get("contract_type") or raw_job.get("contract_type"))
        job["deadline"] = _extract_anpe_deadline(description, job.get("deadline") or raw_job.get("deadline"))
        job["recruiter_name"] = _clean_recruiter_name(job.get("recruiter_name") or raw_job.get("recruiter_name"))

        explicit_publication = _extract_anpe_publication_date(description)
        if explicit_publication:
            job["posted_date"] = explicit_publication
        else:
            date_source = _clean_space(extra_data.get("date_source")) if isinstance(extra_data, Mapping) else ""
            if date_source in {"deadline_only", "missing"}:
                job["posted_date"] = None
            elif _clean_space(job.get("posted_date")) == _clean_space(raw_job.get("deadline")):
                job["posted_date"] = None

        if _looks_like_salary_noise(job.get("salary")):
            job["salary"] = None

        job["country"] = normalize_country(
            None,
            location=job.get("location"),
            source_name=job.get("source_name"),
        )
        return job

    def _clean_emploi_tg(self, job: dict, raw_job: Mapping[str, Any]) -> dict:
        job = self._clean_generic(job)

        title = _prettify_title(job.get("title") or raw_job.get("title") or "")
        if title:
            job["title"] = title

        source_url = job.get("source_url") or raw_job.get("source_url") or raw_job.get("url") or ""
        current_location = job.get("location") or raw_job.get("location") or ""
        inferred_location = _extract_emploi_tg_location(title, source_url)
        normalized_current_location = normalize_location(current_location)

        if inferred_location:
            job["location"] = inferred_location
        elif _looks_like_emploi_tg_bad_location(current_location):
            job["location"] = "Non precise"
        else:
            job["location"] = normalized_current_location

        job["country"] = normalize_country(
            None,
            location=job.get("location"),
            source_name=job.get("source_name"),
        )
        return job
