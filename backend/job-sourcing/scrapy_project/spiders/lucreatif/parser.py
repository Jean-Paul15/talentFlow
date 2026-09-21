"""
Parser for lucreatif.com job pages.

Extraction strategy:
1) HTML detail blocks
2) JSON-LD JobPosting block
3) WordPress REST payload fallback (wp-json/wp/v2/job_listing/<id>)
"""

import json
import re
from html import unescape
from typing import Any, Optional
from urllib.parse import urlparse

from scrapy.http import Response

from . import selectors


EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
PHONE_RE = re.compile(r"(?:\+?\d[\d\s().\-]{7,}\d)")
HTML_TAG_RE = re.compile(r"<[^>]+>")
HREF_RE = re.compile(r'href="([^"]+)"', re.IGNORECASE)

LOCATION_PATTERNS = [
    re.compile(r"Lieu(?: de travail)?\s*[:\-]\s*([^\n\r|.;]+)", re.IGNORECASE),
    re.compile(r"Localisation\s*[:\-]\s*([^\n\r|.;]+)", re.IGNORECASE),
    re.compile(r"Localisation du poste\s*[:\-]\s*([^\n\r|.;]+)", re.IGNORECASE),
]

CONTRACT_PATTERNS = [
    re.compile(r"Type d(?:'|\u2019)emploi\s*[:\-]\s*([^\n\r|.;]+)", re.IGNORECASE),
    re.compile(r"Type de contrat\s*[:\-]\s*([^\n\r|.;]+)", re.IGNORECASE),
    re.compile(
        r"(Contrat\s+(?:[a-zA-Z\u00c0-\u017f'\-\s]{2,60}))",
        re.IGNORECASE,
    ),
]

DEADLINE_PATTERNS = [
    re.compile(r"Date\s*Limite\s*[:\-]?\s*([^\n\r|.;]{4,60})", re.IGNORECASE),
    re.compile(r"Application\s+ends?\s*[:\-]\s*([^\n\r|.;]{4,60})", re.IGNORECASE),
]

SALARY_PATTERNS = [
    re.compile(
        r"(?:salaire|r(?:e|é)mun(?:e|é)ration(?:\s+salariale)?(?:\s+annuelle)?)"
        r"\s*[:\-]?\s*([^\n\r]{4,160})",
        re.IGNORECASE,
    ),
    re.compile(r"(\d[\d\s\u202f.,]*(?:FCFA|XOF|CFA|€|\$)[^\n\r]{0,60})", re.IGNORECASE),
]

EXPERIENCE_PATTERNS = [
    re.compile(r"(\d+\s*(?:ans?|ann(?:e|é)es?)\s+d(?:'|\u2019)exp(?:e|é)rience)", re.IGNORECASE),
    re.compile(r"exp(?:e|é)rience\s*[:\-]\s*([^\n\r|.;]{2,80})", re.IGNORECASE),
    re.compile(r"exp(?:e|é)rience\s*(?:requise)?\s*[:\-]\s*([^\n\r|.;]{2,80})", re.IGNORECASE),
]

EDUCATION_PATTERNS = [
    re.compile(r"(BAC\s*\+?\s*\d+[^\n\r|.;]{0,50})", re.IGNORECASE),
    re.compile(r"(Licence[^\n\r|.;]{0,50}|Master[^\n\r|.;]{0,50})", re.IGNORECASE),
    re.compile(r"(niveau\s*(?:d(?:'|\u2019))?(?:e|é)tudes?\s*[:\-]\s*[^\n\r|.;]{2,80})", re.IGNORECASE),
    re.compile(r"(dipl(?:o|ô)me\s*[:\-]\s*[^\n\r|.;]{2,80})", re.IGNORECASE),
]

RECRUITER_PATTERNS = [
    re.compile(r"A propos de l(?:'|\u2019)?organisation\s*[:\-]\s*([^\n\r]{3,120})", re.IGNORECASE),
    re.compile(r"(?:entreprise|soci(?:e|é)t(?:e|é)|organisation)\s*[:\-]\s*([^\n\r]{3,120})", re.IGNORECASE),
    re.compile(r"([A-Z][A-Za-z0-9&'’\-. ]{2,80})\s+recrute", re.IGNORECASE),
]

START_DATE_PATTERNS = [
    re.compile(r"Prise de fonction\s*[:\-]\s*([^\n\r|.;]{2,80})", re.IGNORECASE),
    re.compile(r"Disponibilit(?:e|é)\s*[:\-]\s*([^\n\r|.;]{2,80})", re.IGNORECASE),
]

SECTION_STOPS_TECH = (
    "qualit",
    "formation",
    "votre profil",
    "candidature",
    "merci",
    "profil recherch",
)

SECTION_STOPS_QUALITIES = (
    "formation",
    "votre profil",
    "candidature",
    "merci",
    "profil recherch",
)


def css_first(response: Response, selector: str) -> Optional[str]:
    """Return first non-empty match across one or many selectors."""
    for sel in selector.split(","):
        value = response.css(sel.strip()).get()
        if value and value.strip():
            return value.strip()
    return None


def css_all_text(response: Response, selector: str) -> str:
    """Collect and normalize all text across one or many selectors."""
    texts = []
    for sel in selector.split(","):
        texts.extend(response.css(sel.strip()).getall())
    return _collapse_spaces(" ".join(t.strip() for t in texts if t and t.strip()))


def selector_first(node: Any, selector: str) -> Optional[str]:
    """Return first non-empty value from a Scrapy Selector/Response context."""
    for sel in selector.split(","):
        value = node.css(sel.strip()).get()
        if value and value.strip():
            return value.strip()
    return None


def parse_listing_card(article: Any, response: Response) -> Optional[dict]:
    """
    Parse one <article> card from /job-list/ pages.
    Returns title + posted text + detail url (/job/<slug>/).
    """
    link = selector_first(article, selectors.LISTING_LINK)
    if not link:
        return None

    absolute_url = response.urljoin(link.strip())
    if "/job/" not in absolute_url:
        return None

    title = selector_first(article, selectors.LISTING_TITLE)
    posted_text = selector_first(article, selectors.LISTING_POSTED_TEXT)

    return {
        "url": absolute_url,
        "title": _collapse_spaces(unescape(title or "")) or None,
        "posted_date": _collapse_spaces(unescape(posted_text or "")) or None,
    }


def extract_pagination_links(response: Response) -> list[str]:
    """
    Collect all pagination links dynamically.
    Avoid assumptions on page count.
    """
    page_links = []
    for raw in response.css(selectors.PAGINATION_LINKS).getall():
        if not raw:
            continue
        absolute = response.urljoin(raw.strip())
        if "/page/" not in absolute:
            continue
        page_links.append(absolute)
    return sorted(set(page_links))


def parse_job_data(response: Response, listing_data: Optional[dict] = None) -> dict:
    """
    Parse lucreatif job detail page.
    Returns partial structured payload before optional wp-json enrichment.
    """
    json_ld = _extract_json_ld_job_posting(response)
    jsonld_posted = _safe_get_jsonld(json_ld, "datePosted")
    jsonld_valid_through = _safe_get_jsonld(json_ld, "validThrough")
    title = css_first(response, selectors.JOB_TITLE)
    if not title and listing_data:
        title = listing_data.get("title")
    if not title and json_ld:
        title = _collapse_spaces(unescape(str(json_ld.get("title", ""))))

    raw_description_text = css_all_text(response, selectors.JOB_DESCRIPTION)
    detail_text = css_all_text(response, selectors.JOB_DETAIL_TEXT)
    detail_lines = _extract_text_lines(response, selectors.JOB_DETAIL_TEXT)

    jsonld_description = _extract_jsonld_description(json_ld)
    description = jsonld_description or raw_description_text
    description_source = "json_ld" if jsonld_description else "html_visible"
    if not description or len(description) < 40:
        description = raw_description_text or jsonld_description or ""
        description_source = "html_visible" if raw_description_text else description_source

    visible_apply_section = _extract_apply_section_text(detail_lines, detail_text)
    description, apply_section_from_desc = _split_candidature_from_description(description)
    apply_section_text = _collapse_spaces(" ".join(x for x in [visible_apply_section, apply_section_from_desc] if x))

    posted_date = (
        jsonld_posted
        or css_first(response, selectors.JOB_POSTED_TEXT)
        or (listing_data or {}).get("posted_date")
    )
    posted_date_raw = (
        css_first(response, selectors.JOB_POSTED_TEXT)
        or (listing_data or {}).get("posted_date")
        or jsonld_posted
    )
    deadline = (
        jsonld_valid_through
        or css_first(response, selectors.JOB_DEADLINE)
    )
    apply_url = _extract_apply_link(response)
    contact_email = _extract_first_email(apply_section_text) or _extract_first_email(detail_text)
    contact_phone = _extract_first_phone(detail_text)

    company = _extract_company(json_ld) or "Lucreatif"
    location = _extract_field(detail_text, LOCATION_PATTERNS) or "Togo"
    contract_type = _extract_field(detail_text, CONTRACT_PATTERNS)
    deadline = deadline or _extract_field(detail_text, DEADLINE_PATTERNS)
    salary = _sanitize_salary(_extract_field(detail_text, SALARY_PATTERNS))
    experience = _extract_field(detail_text, EXPERIENCE_PATTERNS)
    education = _extract_field(detail_text, EDUCATION_PATTERNS)
    recruiter_name = _extract_field(detail_text, RECRUITER_PATTERNS)
    start_date = _extract_field(detail_text, START_DATE_PATTERNS)
    tech_skills = _extract_section_items(
        detail_lines,
        starts=("compétences techniques", "competences techniques"),
        stops=SECTION_STOPS_TECH,
    )
    personal_qualities = _extract_section_items(
        detail_lines,
        starts=("qualités personnelles", "qualites personnelles"),
        stops=SECTION_STOPS_QUALITIES,
    )
    wp_post_id = _extract_wp_post_id(response)
    internal_apply_form = _has_internal_apply_form(response)
    apply_instructions = _extract_apply_instructions(apply_section_text)
    apply_method = None
    if contact_email:
        apply_method = "email"
    elif apply_url:
        apply_method = "external_url" if not apply_url.startswith("#") else "internal_form"
    elif internal_apply_form:
        apply_method = "internal_form"
    elif apply_instructions:
        apply_method = "text_instruction"

    return {
        "title": _collapse_spaces(title) if title else None,
        "company": company,
        "location": location,
        "description": description[:8000] if description else "",
        "posted_date": posted_date,
        "posted_date_raw": posted_date_raw,
        "deadline": deadline,
        "contract_type": contract_type,
        "apply_url": apply_url,
        "apply_method": apply_method,
        "apply_instructions": apply_instructions,
        "contact_email": contact_email,
        "contact_phone": contact_phone,
        "salary": salary,
        "experience": experience,
        "education": education,
        "recruiter_name": recruiter_name,
        "work_schedule": start_date,
        "skills": tech_skills,
        "profile_qualities": personal_qualities,
        "wp_post_id": wp_post_id,
        "json_ld": json_ld or {},
        "extra_data": {
            "posted_date_source": "json_ld_datePosted" if jsonld_posted else "posted_text",
            "deadline_source": "json_ld_validThrough" if jsonld_valid_through else "visible_text",
            "description_source": description_source,
            "has_internal_apply_form": internal_apply_form,
        },
    }


def _extract_text_lines(response: Response, selector: str) -> list[str]:
    lines: list[str] = []
    for sel in selector.split(","):
        raw_values = response.css(sel.strip()).getall()
        for raw in raw_values:
            value = _normalize_line(raw)
            if value:
                lines.append(value)
    return _dedupe_keep_order(lines)


def _lines_from_text(text: str) -> list[str]:
    if not text:
        return []
    return _dedupe_keep_order(
        [_normalize_line(chunk) for chunk in re.split(r"[\r\n]+", text)],
    )


def _normalize_line(value: str) -> str:
    clean = _collapse_spaces(unescape(value or ""))
    clean = clean.replace("•", "").replace("●", "").replace("", "").strip(" -\t")
    return clean


def _dedupe_keep_order(values: list[str]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        if not value:
            continue
        key = value.lower()
        if key in seen:
            continue
        seen.add(key)
        result.append(value)
    return result


def _extract_section_items(
    lines: list[str],
    starts: tuple[str, ...],
    stops: tuple[str, ...],
) -> list[str]:
    if not lines:
        return []

    start_idx = None
    normalized_starts = tuple(start.lower() for start in starts)
    normalized_stops = tuple(stop.lower() for stop in stops)

    for idx, line in enumerate(lines):
        normalized = line.lower()
        if any(start in normalized for start in normalized_starts):
            start_idx = idx
            break

    if start_idx is None:
        return []

    items: list[str] = []
    for line in lines[start_idx + 1:]:
        normalized = line.lower()
        if any(stop in normalized for stop in normalized_stops):
            break
        if len(normalized) < 2:
            continue
        if normalized in {"job description", "candidature"}:
            continue
        if normalized.startswith("application ends"):
            continue
        items.append(line)

    return _dedupe_keep_order(items)


def _merge_unique_values(current: Any, new_values: list[str]) -> list[str]:
    merged: list[str] = []
    if isinstance(current, list):
        merged.extend(str(v).strip() for v in current if str(v).strip())
    merged.extend(str(v).strip() for v in new_values if str(v).strip())
    return _dedupe_keep_order(merged)


def merge_wp_api_data(
    base_data: dict, api_payload: dict, source_url: str,
) -> dict:
    """
    Merge fallback data from wp-json endpoint into base parsed data.
    """
    merged = dict(base_data or {})
    if not api_payload:
        return merged

    title = _clean_html(_safe_get(api_payload, "title", "rendered"))
    if title and not merged.get("title"):
        merged["title"] = title

    content_html = _safe_get(api_payload, "content", "rendered") or ""
    content_text = _clean_html(content_html)
    if content_text and len(merged.get("description", "")) < 80:
        merged["description"] = content_text[:8000]

    if not merged.get("posted_date"):
        merged["posted_date"] = api_payload.get("date")

    metas = api_payload.get("metas", {}) or {}
    if isinstance(metas, dict):
        if not merged.get("deadline"):
            merged["deadline"] = metas.get("_job_application_deadline_date")

        apply_url = metas.get("_job_apply_url")
        if apply_url:
            merged["apply_url"] = apply_url

        map_location = metas.get("_job_map_location") or {}
        if isinstance(map_location, dict):
            address = _collapse_spaces(str(map_location.get("address", "")))
            if address:
                merged["location"] = address

    if not merged.get("contract_type"):
        merged["contract_type"] = _extract_field(content_text, CONTRACT_PATTERNS)
    if not merged.get("salary"):
        merged["salary"] = _sanitize_salary(_extract_field(content_text, SALARY_PATTERNS))
    if not merged.get("experience"):
        merged["experience"] = _extract_field(content_text, EXPERIENCE_PATTERNS)
    if not merged.get("education"):
        merged["education"] = _extract_field(content_text, EDUCATION_PATTERNS)
    if not merged.get("work_schedule"):
        merged["work_schedule"] = _extract_field(content_text, START_DATE_PATTERNS)
    if not merged.get("recruiter_name"):
        merged["recruiter_name"] = _extract_field(content_text, RECRUITER_PATTERNS)

    if not merged.get("location") or merged.get("location") == "Togo":
        extracted_location = _extract_field(content_text, LOCATION_PATTERNS)
        if extracted_location:
            merged["location"] = extracted_location
    if not merged.get("deadline"):
        merged["deadline"] = _extract_field(content_text, DEADLINE_PATTERNS)

    if not merged.get("contact_email"):
        merged["contact_email"] = _extract_first_email(content_text)
    if not merged.get("contact_phone"):
        merged["contact_phone"] = _extract_first_phone(content_text)

    raw_lines = _lines_from_text(content_text)
    tech_skills = _extract_section_items(
        raw_lines,
        starts=("compétences techniques", "competences techniques"),
        stops=SECTION_STOPS_TECH,
    )
    if tech_skills:
        merged["skills"] = _merge_unique_values(merged.get("skills"), tech_skills)

    qualities = _extract_section_items(
        raw_lines,
        starts=("qualités personnelles", "qualites personnelles"),
        stops=SECTION_STOPS_QUALITIES,
    )
    if qualities and not merged.get("profile_qualities"):
        merged["profile_qualities"] = qualities

    if not merged.get("apply_url"):
        links = HREF_RE.findall(content_html)
        merged["apply_url"] = _select_apply_link(links, source_url)

    return merged


def _safe_get(obj: dict, *path: str) -> Any:
    current = obj
    for key in path:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current


def _safe_get_jsonld(json_ld: Optional[dict], key: str) -> Optional[str]:
    if not isinstance(json_ld, dict):
        return None
    value = json_ld.get(key)
    return _collapse_spaces(str(value)) if value else None


def _extract_wp_post_id(response: Response) -> Optional[str]:
    raw = css_first(response, selectors.ARTICLE_ID)
    if not raw:
        return None
    match = re.search(r"post-(\d+)", raw)
    return match.group(1) if match else None


def _extract_company(json_ld: Optional[dict]) -> Optional[str]:
    if not isinstance(json_ld, dict):
        return None
    org = json_ld.get("hiringOrganization")
    if isinstance(org, dict):
        name = _collapse_spaces(str(org.get("name", "")))
        return name or None
    return None


def _extract_jsonld_description(json_ld: Optional[dict]) -> Optional[str]:
    if not isinstance(json_ld, dict):
        return None
    raw = json_ld.get("description")
    if not raw:
        return None
    # Le JSON-LD est la meilleure source de description sur Lucreatif (audit),
    # mais il inclut parfois la section "Candidature" -> on la retire.
    if isinstance(raw, str):
        text = _clean_html(unescape(raw))
    else:
        text = _collapse_spaces(unescape(str(raw)))
    text, _ = _split_candidature_from_description(text)
    return text or None


def _split_candidature_from_description(text: str) -> tuple[str, str]:
    if not text:
        return "", ""
    # Coupe la description au niveau de la section candidature/apply pour le NLP,
    # et retourne aussi la partie candidature pour l'extraction apply/email.
    markers = [
        r"\bCandidature\b",
        r"\bComment postuler\b",
        r"\bApply(?: now)?\b",
        r"\bPostulez\b",
    ]
    for marker in markers:
        m = re.search(marker, text, re.IGNORECASE)
        if m:
            before = _collapse_spaces(text[:m.start()])
            after = _collapse_spaces(text[m.start():])
            return before, after
    return _collapse_spaces(text), ""


def _extract_apply_section_text(detail_lines: list[str], detail_text: str) -> str:
    if detail_lines:
        start = None
        for idx, line in enumerate(detail_lines):
            low = line.lower()
            if "candidature" in low or "apply" in low or "postuler" in low:
                start = idx
                break
        if start is not None:
            selected: list[str] = []
            for line in detail_lines[start:]:
                low = line.lower()
                if any(stop in low for stop in ("related jobs", "offres similaires", "job description")) and selected:
                    break
                selected.append(line)
            return _collapse_spaces(" ".join(selected))
    if detail_text:
        m = re.search(
            r"((?:candidature|apply|postuler).{0,800})$",
            detail_text,
            flags=re.IGNORECASE,
        )
        if m:
            return _collapse_spaces(m.group(1))
    return ""


def _extract_apply_instructions(text: str) -> Optional[str]:
    if not text:
        return None
    for sentence in re.split(r"(?<=[\.\!\?;:])\s+", text):
        candidate = _collapse_spaces(sentence)
        if not candidate:
            continue
        low = candidate.lower()
        if any(k in low for k in ("candidature", "envoyer", "adresse", "objet", "prétention salariale", "pretention salariale")):
            return candidate[:400]
    return _collapse_spaces(text)[:400] if text else None


def _has_internal_apply_form(response: Response) -> bool:
    # WP Job Manager Pro forms: ids/classes often contain "job-apply-internal"
    return bool(
        response.css(
            "form[id*='job-apply-internal'], "
            "form[id*='apply-internal'], "
            "form[class*='job-apply']"
        ).get()
    )


def _extract_first_email(text: str) -> Optional[str]:
    if not text:
        return None
    match = EMAIL_RE.search(text)
    return match.group(0) if match else None


def _extract_first_phone(text: str) -> Optional[str]:
    if not text:
        return None
    for match in PHONE_RE.finditer(text):
        start, end = match.span()
        candidate = _collapse_spaces(match.group(0))
        upper_candidate = candidate.upper()
        context = text[max(0, start - 16):min(len(text), end + 16)].upper()
        if any(token in upper_candidate for token in ("FCFA", "XOF", "CFA", "USD", "EUR", "€", "$")):
            continue
        if any(token in context for token in ("FCFA", "XOF", "CFA", "USD", "EUR", "€", "$")):
            continue
        if re.fullmatch(r"\d{1,3}(?:\s\d{3}){2,}", candidate):
            # Format typique des montants monetaires (ex: 11 015 000)
            continue

        digits = re.sub(r"\D", "", candidate)
        if 8 <= len(digits) <= 14:
            return candidate
    return None


def _extract_field(text: str, patterns: list[re.Pattern]) -> Optional[str]:
    if not text:
        return None
    for pattern in patterns:
        match = pattern.search(text)
        if match:
            value = _collapse_spaces(match.group(1))
            if value:
                return value
    return None


def _sanitize_salary(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    cleaned = _collapse_spaces(value)
    cleaned = re.split(
        r"\b(?:si vous|pour postuler|envoyez|contact|profil recherch(?:e|é))\b",
        cleaned,
        maxsplit=1,
        flags=re.IGNORECASE,
    )[0].strip(" -:;,")
    cleaned = re.split(r"[•●]", cleaned, maxsplit=1)[0].strip(" -:;,")
    cleaned = re.split(r"\b(?:candidat(?:e)?s?)\b", cleaned, maxsplit=1, flags=re.IGNORECASE)[0].strip(" -:;,")

    if len(cleaned) > 120:
        currency_match = re.search(
            r"\d[\d\s\u202f.,]*(?:FCFA|XOF|CFA|€|\$)",
            cleaned,
            re.IGNORECASE,
        )
        if currency_match:
            cleaned = currency_match.group(0)
        else:
            cleaned = cleaned[:120].rstrip()

    return cleaned or None


def _extract_apply_link(response: Response) -> Optional[str]:
    links = response.css(selectors.APPLY_LINKS).getall()
    return _select_apply_link(links, response.url)


def _select_apply_link(links: list[str], source_url: str) -> Optional[str]:
    source_domain = urlparse(source_url).netloc.replace("www.", "")
    for link in links:
        if not link:
            continue
        candidate = link.strip()
        if not candidate or candidate.startswith("#"):
            continue
        if candidate.startswith("mailto:"):
            return candidate
        if candidate.startswith("/"):
            continue

        domain = urlparse(candidate).netloc.replace("www.", "")
        if domain and domain != source_domain:
            return candidate
    return None


def _extract_json_ld_job_posting(response: Response) -> Optional[dict]:
    scripts = response.xpath('//script[@type="application/ld+json"]/text()').getall()
    for raw in scripts:
        cleaned = raw.strip()
        if not cleaned:
            continue
        try:
            data = json.loads(cleaned)
        except json.JSONDecodeError:
            continue

        for node in _walk_json_nodes(data):
            node_type = node.get("@type")
            if isinstance(node_type, list):
                types = {str(x).lower() for x in node_type}
                if "jobposting" in types:
                    return node
            elif isinstance(node_type, str) and node_type.lower() == "jobposting":
                return node
    return None


def _walk_json_nodes(node: Any):
    if isinstance(node, dict):
        yield node
        for value in node.values():
            yield from _walk_json_nodes(value)
    elif isinstance(node, list):
        for item in node:
            yield from _walk_json_nodes(item)


def _clean_html(html_text: str) -> str:
    if not html_text:
        return ""
    no_tags = HTML_TAG_RE.sub(" ", html_text)
    return _collapse_spaces(unescape(no_tags))


def _collapse_spaces(value: str) -> str:
    return re.sub(r"\s+", " ", value or "").strip()
