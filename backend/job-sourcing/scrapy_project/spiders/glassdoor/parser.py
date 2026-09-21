"""
Parser for glassdoor.com listing pages.
"""

from __future__ import annotations

import re
from html import unescape
from typing import Any, Optional
from urllib.parse import parse_qs, urlparse

from scrapy.http import Response

from . import selectors


BLOCK_KEYWORDS = (
    "captcha",
    "verify you are human",
    "access denied",
    "enable javascript",
    "temporarily blocked",
    "security check",
)

SPACE_RE = re.compile(r"\s+")
IP_PAGE_RE = re.compile(r"_IP(\d+)\.htm", re.IGNORECASE)


def detect_block_reason(response: Response) -> Optional[str]:
    if response.status in {401, 403, 429, 503}:
        return f"http_{response.status}"

    text = (response.text or "").lower()
    for keyword in BLOCK_KEYWORDS:
        if keyword in text:
            return keyword
    return None


def parse_jobs(response: Response) -> list[dict[str, Any]]:
    jobs: list[dict[str, Any]] = []
    seen: set[str] = set()

    for card in response.css(selectors.JOB_CARD):
        title = _normalize(_css_first(card, selectors.JOB_TITLE))
        title_link = _css_first(card, selectors.JOB_TITLE_LINK)
        track_link = _css_first(card, selectors.JOB_TRACKING_LINK)

        source_url = _resolve_source_url(response, title_link, track_link)
        if not title or not source_url:
            continue

        parsed = urlparse(source_url)
        if "glassdoor.com" not in parsed.netloc:
            continue

        job_id = card.attrib.get("data-jobid") or _extract_query_value(source_url, "jl")
        unique_key = job_id or source_url
        if unique_key in seen:
            continue
        seen.add(unique_key)

        company = _pick_company_name(card)
        location = _normalize(_css_first(card, selectors.JOB_LOCATION))
        salary = _normalize(_css_join_text(card, selectors.JOB_SALARY))
        description = _normalize(_css_join_text(card, selectors.JOB_SNIPPET))
        listing_age = _normalize(_css_first(card, selectors.JOB_AGE))
        apply_url = response.urljoin(track_link) if track_link else source_url

        jobs.append(
            {
                "title": title,
                "company": company,
                "location": location,
                "salary": salary,
                "description": description,
                "posted_date": listing_age,
                "source_url": source_url,
                "apply_url": apply_url,
                "job_id": job_id,
            },
        )

    return jobs


def extract_next_page(response: Response) -> Optional[str]:
    direct = response.css("link[rel='next']::attr(href)").get()
    if direct:
        return direct.strip()

    current_page = _extract_page_number(response.url)
    candidates: list[tuple[int, str]] = []

    for href in response.css(selectors.NEXT_PAGE).getall():
        if not href:
            continue
        full = response.urljoin(href.strip())
        parsed = urlparse(full)
        if "glassdoor.com" not in parsed.netloc:
            continue

        page = _extract_page_number(full)
        if page is None:
            continue
        if current_page is not None and page <= current_page:
            continue
        candidates.append((page, full))

    if not candidates:
        return None

    candidates.sort(key=lambda row: row[0])
    return candidates[0][1]


def _extract_page_number(url: str) -> Optional[int]:
    query = parse_qs(urlparse(url).query)
    for key in ("page", "p", "pn"):
        raw = query.get(key, [None])[0]
        if raw is None:
            continue
        try:
            return int(raw)
        except (TypeError, ValueError):
            continue

    ip_match = IP_PAGE_RE.search(url)
    if ip_match:
        try:
            return int(ip_match.group(1))
        except (TypeError, ValueError):
            return None

    return 1 if "glassdoor.com/Job/" in url else None


def _resolve_source_url(
    response: Response,
    title_link: Optional[str],
    tracking_link: Optional[str],
) -> Optional[str]:
    if title_link:
        return response.urljoin(title_link.strip())
    if tracking_link:
        return response.urljoin(tracking_link.strip())
    return None


def _pick_company_name(card: Any) -> Optional[str]:
    values = card.css(selectors.JOB_COMPANY).getall()
    for value in values:
        text = _normalize(value)
        if not text:
            continue
        if re.fullmatch(r"[0-9.]+", text):
            continue
        if len(text) < 2:
            continue
        return text
    return None


def _extract_query_value(url: str, key: str) -> Optional[str]:
    query = parse_qs(urlparse(url).query)
    value = query.get(key, [None])[0]
    if value is None:
        return None
    return str(value)


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


def _normalize(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    text = unescape(str(value))
    clean = SPACE_RE.sub(" ", text).strip()
    return clean or None
