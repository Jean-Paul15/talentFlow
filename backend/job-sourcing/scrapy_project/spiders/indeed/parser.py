"""
Parser for indeed.com listings.
Strategy:
1) Parse structured payload from window._initialData when available.
2) Fallback to DOM card extraction.
"""

from __future__ import annotations

import json
import re
from html import unescape
from typing import Any, Optional
from urllib.parse import parse_qs, urlparse

from scrapy.http import Response

from . import selectors


BLOCK_KEYWORDS = (
    "captcha",
    "unusual traffic",
    "verify you are human",
    "access denied",
    "enable javascript",
    "temporarily blocked",
)

HTML_TAG_RE = re.compile(r"<[^>]+>")
SPACE_RE = re.compile(r"\s+")
MONEY_RE = re.compile(r"(\$\s?\d[\d,]*(?:\s*-\s*\$?\s?\d[\d,]*)?)")


def detect_block_reason(response: Response) -> Optional[str]:
    """
    Return a short reason if the response looks blocked.
    """
    if response.status in {401, 403, 429, 503}:
        return f"http_{response.status}"

    text = (response.text or "").lower()
    for keyword in BLOCK_KEYWORDS:
        if keyword in text:
            return keyword
    return None


def parse_jobs(response: Response) -> list[dict[str, Any]]:
    """
    Parse jobs from page, structured payload first.
    """
    jobs = _parse_jobs_from_initial_data(response)
    if jobs:
        return jobs
    return _parse_jobs_from_dom(response)


def extract_next_page(response: Response) -> Optional[str]:
    """
    Resolve the next listing page dynamically (no fixed page count).
    """
    direct = _css_first(response, selectors.NEXT_PAGE)
    if direct:
        return direct

    current_start = _extract_start_offset(response.url) or 0
    candidates: list[tuple[int, str]] = []

    hrefs = response.css(
        "link[rel='next']::attr(href), a[href*='start=']::attr(href)",
    ).getall()
    for href in hrefs:
        if not href:
            continue
        full = response.urljoin(href.strip())
        parsed = urlparse(full)
        if "indeed.com" not in parsed.netloc:
            continue
        if "/jobs" not in parsed.path:
            continue

        start = _extract_start_offset(full)
        if start is None:
            continue
        if start <= current_start:
            continue
        candidates.append((start, full))

    if not candidates:
        return None
    candidates.sort(key=lambda row: row[0])
    return candidates[0][1]


def _parse_jobs_from_initial_data(response: Response) -> list[dict[str, Any]]:
    payload = _extract_initial_data_payload(response)
    if not payload:
        return []

    raw_jobs: list[dict[str, Any]] = []
    _collect_candidate_jobs(payload, raw_jobs)

    parsed_jobs: list[dict[str, Any]] = []
    seen_keys: set[str] = set()

    for raw in raw_jobs:
        parsed = _normalize_job(raw, response)
        key = parsed.get("job_key") or parsed.get("source_url") or ""
        if not key or key in seen_keys:
            continue
        if not parsed.get("title") or not parsed.get("source_url"):
            continue
        seen_keys.add(key)
        parsed_jobs.append(parsed)

    return parsed_jobs


def _parse_jobs_from_dom(response: Response) -> list[dict[str, Any]]:
    jobs: list[dict[str, Any]] = []
    seen_keys: set[str] = set()

    for card in response.css(selectors.JOB_CARD):
        title = _normalize(_css_first(card, selectors.JOB_TITLE))
        link = _css_first(card, selectors.JOB_LINK)
        if not title or not link:
            continue

        source_url = response.urljoin(link.strip())
        parsed = urlparse(source_url)
        if "indeed.com" not in parsed.netloc:
            continue

        company = _normalize(_css_first(card, selectors.JOB_COMPANY))
        location = _normalize(_css_first(card, selectors.JOB_LOCATION))
        description = _normalize(_css_join_text(card, selectors.JOB_SNIPPET))
        salary = _normalize(_css_join_text(card, selectors.JOB_SALARY))
        posted_date = _normalize(_css_first(card, selectors.JOB_POSTED_DATE))

        card_data_jk = card.attrib.get("data-jk")
        job_key = card_data_jk or _extract_job_key(source_url)
        unique_key = job_key or source_url
        if unique_key in seen_keys:
            continue
        seen_keys.add(unique_key)

        jobs.append(
            {
                "title": title,
                "company": company,
                "location": location,
                "description": description,
                "salary": salary,
                "posted_date": posted_date,
                "contract_type": None,
                "source_url": source_url,
                "apply_url": source_url,
                "job_key": job_key,
            },
        )

    return jobs


def _extract_initial_data_payload(response: Response) -> Optional[dict[str, Any]]:
    scripts = response.xpath(
        "//script[contains(text(), 'window._initialData=')]/text()",
    ).getall()
    for script_text in scripts:
        data_text = _extract_json_object_after_marker(
            script_text,
            marker="window._initialData=",
        )
        if not data_text:
            continue
        try:
            payload = json.loads(data_text)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            return payload
    return None


def _extract_json_object_after_marker(script_text: str, marker: str) -> Optional[str]:
    index = script_text.find(marker)
    if index < 0:
        return None

    start = script_text.find("{", index)
    if start < 0:
        return None

    depth = 0
    in_string = False
    escaped = False

    for pos in range(start, len(script_text)):
        char = script_text[pos]

        if in_string:
            if escaped:
                escaped = False
                continue
            if char == "\\":
                escaped = True
                continue
            if char == '"':
                in_string = False
            continue

        if char == '"':
            in_string = True
            continue

        if char == "{":
            depth += 1
            continue
        if char == "}":
            depth -= 1
            if depth == 0:
                return script_text[start : pos + 1]

    return None


def _collect_candidate_jobs(node: Any, out: list[dict[str, Any]]) -> None:
    if isinstance(node, dict):
        if _looks_like_job_record(node):
            out.append(node)
        for value in node.values():
            _collect_candidate_jobs(value, out)
        return

    if isinstance(node, list):
        for value in node:
            _collect_candidate_jobs(value, out)


def _looks_like_job_record(node: dict[str, Any]) -> bool:
    has_title = bool(node.get("displayTitle") or node.get("title"))
    has_link = bool(
        node.get("link")
        or node.get("viewJobLink")
        or node.get("clickLoggingUrl")
        or node.get("jobLink"),
    )
    has_company = bool(node.get("company") or node.get("sourceEmployerName"))
    has_key = bool(node.get("jobkey") or node.get("jobKey"))
    return has_title and (has_link or has_key) and has_company


def _normalize_job(raw: dict[str, Any], response: Response) -> dict[str, Any]:
    title = _normalize(_pick_first(raw.get("displayTitle"), raw.get("title")))
    company = _normalize(_pick_first(raw.get("company"), raw.get("sourceEmployerName")))

    location = _normalize(
        _pick_first(
            raw.get("formattedLocation"),
            _pick_nested(raw, "location", "formatted", "long"),
            _pick_nested(raw, "location", "fullAddress"),
            _pick_nested(raw, "location", "city"),
        ),
    )

    link = _pick_first(
        raw.get("viewJobLink"),
        raw.get("link"),
        raw.get("jobLink"),
        raw.get("clickLoggingUrl"),
        _pick_nested(raw, "tracking", "jobClick", "url"),
    )
    source_url = response.urljoin(str(link)) if link else None

    description = _normalize(
        _strip_html(
            _pick_first(
                raw.get("snippet"),
                _pick_nested(raw, "description", "text"),
                _pick_nested(raw, "description", "html"),
            ),
        ),
    )

    posted_date = _normalize(
        _pick_first(
            raw.get("formattedRelativeTime"),
            raw.get("age"),
            raw.get("datePublished"),
        ),
    )
    salary = _extract_salary(raw, description)
    contract_type = _normalize_contract_type(raw.get("jobTypes"))

    job_key = _pick_first(raw.get("jobkey"), raw.get("jobKey"))
    if not job_key and source_url:
        job_key = _extract_job_key(source_url)

    return {
        "title": title,
        "company": company,
        "location": location,
        "description": description,
        "salary": salary,
        "posted_date": posted_date,
        "contract_type": contract_type,
        "source_url": source_url,
        "apply_url": source_url,
        "job_key": _normalize(job_key),
    }


def _extract_salary(raw: dict[str, Any], fallback_text: Optional[str]) -> Optional[str]:
    salary_node = raw.get("salarySnippet")
    if isinstance(salary_node, dict):
        for key in ("salaryText", "salary", "text"):
            value = salary_node.get(key)
            normalized = _normalize(value)
            if normalized:
                return normalized
    elif isinstance(salary_node, str):
        normalized = _normalize(salary_node)
        if normalized:
            return normalized

    if not fallback_text:
        return None
    match = MONEY_RE.search(fallback_text)
    if not match:
        return None
    return _normalize(match.group(1))


def _normalize_contract_type(value: Any) -> Optional[str]:
    if isinstance(value, list):
        parts = [_normalize(str(item)) for item in value if _normalize(str(item))]
        if parts:
            return ", ".join(parts)
    if value:
        return _normalize(str(value))
    return None


def _extract_start_offset(url: str) -> Optional[int]:
    query = parse_qs(urlparse(url).query)
    raw = query.get("start", [None])[0]
    if raw is None:
        return 0
    try:
        return int(raw)
    except (TypeError, ValueError):
        return None


def _extract_job_key(url: str) -> Optional[str]:
    query = parse_qs(urlparse(url).query)
    for key in ("jk", "jobkey"):
        value = query.get(key, [None])[0]
        if value:
            return str(value)
    return None


def _pick_first(*values: Any) -> Optional[str]:
    for value in values:
        if value is None:
            continue
        if isinstance(value, str) and value.strip():
            return value
        if not isinstance(value, str):
            text = str(value).strip()
            if text:
                return text
    return None


def _pick_nested(node: dict[str, Any], *path: str) -> Optional[str]:
    current: Any = node
    for key in path:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    if current is None:
        return None
    return str(current)


def _css_first(node: Any, selector: str) -> Optional[str]:
    for sel in selector.split(","):
        value = node.css(sel.strip()).get()
        if value:
            value = value.strip()
            if value:
                return value
    return None


def _css_join_text(node: Any, selector: str) -> Optional[str]:
    values: list[str] = []
    for sel in selector.split(","):
        values.extend(node.css(sel.strip()).getall())
    if not values:
        return None
    return _normalize(" ".join(values))


def _strip_html(value: Optional[str]) -> Optional[str]:
    if not value:
        return value
    text = HTML_TAG_RE.sub(" ", value)
    return unescape(text)


def _normalize(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    clean = SPACE_RE.sub(" ", str(value)).strip()
    return clean or None
