"""
Parser pour emploitogo.com (WordPress JobBoard).
"""
import json
import re
from typing import Optional
from scrapy.http import Response

from . import selectors


def css_first(response: Response, selector: str) -> Optional[str]:
    """
    Extrait premier resultat d'un ou plusieurs selecteurs.
    """
    for sel in selector.split(','):
        result = response.css(sel.strip()).get()
        if result:
            return result.strip()
    return None


def css_all_text(response: Response, selector: str) -> str:
    """
    Concatene tous les textes trouves.
    """
    texts = []
    for sel in selector.split(','):
        texts.extend(response.css(sel.strip()).getall())
    return ' '.join(t.strip() for t in texts if t and t.strip())


def _normalize_space(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    cleaned = re.sub(r"\s+", " ", value).strip()
    return cleaned or None


def _parse_json_payload(raw: str):
    try:
        return json.loads(raw)
    except Exception:
        return None


def _find_job_posting(payload):
    if isinstance(payload, list):
        for entry in payload:
            found = _find_job_posting(entry)
            if found:
                return found
        return None

    if not isinstance(payload, dict):
        return None

    data_type = payload.get("@type")
    if isinstance(data_type, list):
        if any(str(t).lower() == "jobposting" for t in data_type):
            return payload
    elif isinstance(data_type, str) and data_type.lower() == "jobposting":
        return payload

    if "@graph" in payload:
        found = _find_job_posting(payload.get("@graph"))
        if found:
            return found

    for value in payload.values():
        found = _find_job_posting(value)
        if found:
            return found
    return None


def _extract_jobposting_from_jsonld(response: Response) -> dict:
    for raw in response.css('script[type="application/ld+json"]::text').getall():
        payload = _parse_json_payload(raw)
        if payload is None:
            continue
        posting = _find_job_posting(payload)
        if posting:
            return posting
    return {}


def _extract_jsonld_company(jobposting: dict) -> Optional[str]:
    org = jobposting.get("hiringOrganization")
    if isinstance(org, list):
        org = org[0] if org else None
    if isinstance(org, dict):
        return _normalize_space(org.get("name"))
    if isinstance(org, str):
        return _normalize_space(org)
    return None


def _extract_jsonld_location(jobposting: dict) -> Optional[str]:
    location = jobposting.get("jobLocation")
    if isinstance(location, list):
        location = location[0] if location else None
    if isinstance(location, dict):
        address = location.get("address")
        if isinstance(address, dict):
            locality = _normalize_space(address.get("addressLocality"))
            region = _normalize_space(address.get("addressRegion"))
            country = _normalize_space(address.get("addressCountry"))
            parts = [p for p in [locality, region, country] if p]
            if parts:
                return ", ".join(parts)
    return None


def _extract_fallback_date(full_text: str) -> Optional[str]:
    # Exemples: "Publié le décembre 30, 2025"
    patterns = [
        r"Publié le\s+([^\n\r]+)",
        r"Publish(?:ed)?\s+on\s+([^\n\r]+)",
    ]
    for pattern in patterns:
        match = re.search(pattern, full_text, flags=re.IGNORECASE)
        if match:
            return _normalize_space(match.group(1))
    return None


def parse_job_data(response: Response) -> dict:
    """
    Parse les donnees d'une offre emploitogo.com.
    Fallback sur le contenu HTML complet si selecteurs specifiques echouent.
    """
    jsonld_job = _extract_jobposting_from_jsonld(response)

    title = _normalize_space(css_first(response, selectors.JOB_TITLE))

    # Fallback titre depuis balise title ou og:title
    if not title:
        title = response.css('title::text').get()
        if title:
            title = title.split('|')[0].strip()
    if not title:
        title = _normalize_space(jsonld_job.get("title"))

    description = css_all_text(response, selectors.JOB_DESCRIPTION)
    # Fallback description depuis tout le contenu
    if not description or len(description) < 30:
        all_text = response.css('.entry-content *::text, article *::text').getall()
        description = ' '.join(t.strip() for t in all_text if t.strip())
    if (not description or len(description) < 30) and jsonld_job.get("description"):
        description = str(jsonld_job.get("description"))

    full_text = css_all_text(
        response, ".job-overview *::text, .job_listing-meta *::text"
    )
    job_type = _normalize_space(css_first(response, selectors.JOB_TYPE))
    if not job_type:
        employment = jsonld_job.get("employmentType")
        if isinstance(employment, list):
            job_type = ", ".join([str(e).strip() for e in employment if str(e).strip()])
        elif employment:
            job_type = str(employment).strip()

    return {
        'title': title,
        'company': (
            _normalize_space(css_first(response, selectors.JOB_COMPANY))
            or _extract_jsonld_company(jsonld_job)
        ),
        'location': (
            _normalize_space(css_first(response, selectors.JOB_LOCATION))
            or _extract_jsonld_location(jsonld_job)
        ),
        'description': description[:3000] if description else '',
        'job_type': job_type,
        'category': _normalize_space(css_first(response, selectors.JOB_CATEGORY)),
        'posted_date': (
            _normalize_space(css_first(response, selectors.JOB_POSTED_DATE))
            or _normalize_space(jsonld_job.get("datePosted"))
            or _extract_fallback_date(full_text or "")
        ),
    }
