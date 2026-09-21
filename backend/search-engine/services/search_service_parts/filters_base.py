"""Environment helpers and shared filter constants."""

from __future__ import annotations

import os


def _env(name: str, default: str) -> str:
    return str(os.getenv(name, default)).strip()


def _env_float(name: str, default: float) -> float:
    try:
        return float(_env(name, str(default)))
    except Exception:
        return float(default)


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
    "tutoriel",
    "tutorial",
    "vacance de poste",
    "vacances de poste",
    "vacance des postes",
    "vacances des postes",
)

_COURSE_LIKE_TITLE_PATTERNS = (
    "formation ",
    "formations ",
    "cours ",
    "certification ",
    "webinar ",
    "webinaire ",
)

_JOB_SIGNAL_KEYWORDS = (
    "recrute",
    "recrutement",
    "offre",
    "emploi",
    "poste",
    "job",
    "stage",
    "internship",
    "h/f",
    "cdi",
    "cdd",
    "consultant",
    "developer",
    "engineer",
    "analyst",
    "manager",
)

_NON_JOB_URL_HINTS = (
    "/blog/",
    "/category/",
    "/tag/",
    "/actualites",
    "/news/",
    "/formation",
    "/formations",
    "/cours/",
)

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


__all__ = ["_env", "_env_float"]
