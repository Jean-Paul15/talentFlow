"""Shared constants for CV text parsing helpers."""

from __future__ import annotations

TOGO_LOCATION_HINTS = {
    "lome": "Lome",
    "lomé": "Lome",
    "kara": "Kara",
    "sokode": "Sokode",
    "sokodé": "Sokode",
    "atakpame": "Atakpame",
    "atakpamé": "Atakpame",
    "dapaong": "Dapaong",
    "kpalime": "Kpalime",
    "kpalimé": "Kpalime",
}

LOW_QUALITY_JOB_TITLES = {
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

INTERNATIONAL_SOURCE_NAMES = {
    "arbeitnow_api",
    "remoteok_api",
    "remotive_api",
    "hackernews_api",
    "monster",
    "glassdoor",
    "indeed",
}

LOCAL_SOURCE_NAMES = {
    "anpe_togo",
    "emploi_tg",
    "lucreatif",
    "wiijob",
}

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
