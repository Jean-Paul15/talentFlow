"""
Parser for monster.com (listing + detail).

Audit-driven goals:
- robust listing parsing on SPA/React pages where content is still visible in HTML
- parse relative dates ("11 days ago", "30+ days ago", "recently posted")
- follow detail pages for full description and apply buttons
- degrade gracefully under anti-bot pages / partial rendering
"""

from __future__ import annotations

import re
from html import unescape
from typing import Any, Optional
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

from scrapy.http import Response

from . import selectors


BLOCK_KEYWORDS = (
    "captcha-delivery.com",
    "please enable js and disable any ad blocker",
    "please enable javascript",
    "access denied",
    "security check",
    "captcha",
    "unusual traffic",
    "verify you are human",
)

SPACE_RE = re.compile(r"\s+")
MONSTER_ID_RE = re.compile(
    r"/job(?:-openings)?/[^/]+/([a-f0-9-]{8,})",
    re.IGNORECASE,
)
DATE_RELATIVE_RE = re.compile(
    r"\b(?:posted|updated)?\s*(recently posted|today|yesterday|\d+\+?\s*(?:minutes?|hours?|days?|weeks?|months?)\s+ago)\b",
    re.IGNORECASE,
)
DATE_ABS_RE = re.compile(r"\b(\d{1,2}/\d{1,2}/\d{4})\b")
SALARY_RE = re.compile(r"\$\s?\d[\d,]*(?:\s?[–-]\s?\$?\d[\d,]*)?(?:\s+per\s+\w+)?", re.IGNORECASE)
EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
PHONE_RE = re.compile(r"(?:\+?\d[\d\s().\-]{7,}\d)")
CONTRACT_HINT_RE = re.compile(
    r"\b(full[\s-]?time|part[\s-]?time|contract|temporary|internship|intern|permanent|freelance)\b",
    re.IGNORECASE,
)


def detect_block_reason(response: Response) -> Optional[str]:
    if response.status in {401, 403, 429, 503}:
        return f"http_{response.status}"

    text = (response.text or "").lower()
    for keyword in BLOCK_KEYWORDS:
        if keyword in text:
            return keyword
    return None


def parse_jobs(response: Response) -> list[dict[str, Any]]:
    """Parse listing job cards."""
    jobs: list[dict[str, Any]] = []
    seen: set[str] = set()

    for card in response.css(selectors.JOB_CARD):
        title = _normalize(_css_first(card, selectors.JOB_TITLE))
        link = _css_first(card, selectors.JOB_LINK)
        if not link:
            # Fallback: any first anchor that looks like a job detail URL.
            for raw in card.css("a::attr(href)").getall():
                if _looks_like_job_url(raw):
                    link = raw
                    break
        if not title or not link:
            continue

        source_url = response.urljoin(link.strip())
        parsed = urlparse(source_url)
        if "monster.com" not in parsed.netloc:
            continue

        job_id = _extract_job_id(source_url)
        unique_key = job_id or source_url
        if unique_key in seen:
            continue
        seen.add(unique_key)

        card_text = _normalize(_css_join_text(card, "*::text")) or ""
        posted_raw = (
            _normalize(_css_first(card, selectors.JOB_POSTED_DATE))
            or _extract_relative_date(card_text)
            or _extract_absolute_date(card_text)
        )
        salary = _normalize(_css_first(card, selectors.JOB_SALARY)) or _extract_salary(card_text)
        contract_type = _normalize(_css_first(card, selectors.JOB_CONTRACT)) or _extract_contract_hint(card_text)
        apply_label = _extract_apply_label(card)
        apply_link = _css_first(card, selectors.JOB_APPLY_BUTTON_LINK)
        apply_url = response.urljoin(apply_link) if apply_link else source_url

        jobs.append(
            {
                "title": title,
                "company": _normalize(_css_first(card, selectors.JOB_COMPANY)),
                "location": _normalize(_css_first(card, selectors.JOB_LOCATION)),
                "description": _normalize(_css_join_text(card, selectors.JOB_SNIPPET)),
                "posted_date": posted_raw,
                "posted_date_raw": posted_raw,
                "salary": salary,
                "contract_type": contract_type,
                "source_url": source_url,
                "apply_url": apply_url,
                "apply_method": _guess_apply_method_from_label_and_url(apply_label, apply_url, source_url),
                "apply_instructions": (
                    f"Bouton {apply_label} visible sur la carte Monster" if apply_label else None
                ),
                "job_id": job_id,
                "extra_data": {
                    "listing_relative_date": posted_raw,
                    "listing_apply_label": apply_label,
                },
            },
        )

    return jobs


def parse_job_detail(response: Response) -> dict[str, Any]:
    """Parse a Monster detail page/panel HTML."""
    block_reason = detect_block_reason(response)
    if block_reason:
        return {"blocked": True, "block_reason": block_reason}

    full_text = _normalize(_css_join_text(response, selectors.DETAIL_TEXT)) or ""
    title = _normalize(_css_first(response, selectors.DETAIL_TITLE))
    company = _normalize(_css_first(response, selectors.DETAIL_COMPANY))
    location = _normalize(_css_first(response, selectors.DETAIL_LOCATION))

    posted_raw = (
        _normalize(_css_first(response, selectors.DETAIL_DATE_TEXT))
        or _extract_relative_date(full_text)
        or _extract_absolute_date_near_label(full_text, ("posted", "updated"))
        or _extract_absolute_date(full_text)
    )
    deadline = _extract_absolute_date_near_label(full_text, ("expires", "expire le"))

    description = _extract_detail_description(response, full_text)
    salary = _normalize(_css_first(response, selectors.JOB_SALARY)) or _extract_salary(full_text)
    contract_type = _normalize(_css_first(response, selectors.JOB_CONTRACT)) or _extract_contract_hint(full_text)

    apply_url = None
    for raw in response.css(selectors.DETAIL_APPLY_LINK).getall():
        if not raw:
            continue
        candidate = response.urljoin(raw.strip())
        if candidate:
            apply_url = candidate
            break

    apply_label = _extract_apply_label(response, detail_mode=True)
    login_prompt = _has_login_prompt(full_text)
    quick_apply = bool(re.search(r"\bquick\s+apply\b", full_text, re.IGNORECASE))
    contact_email = _extract_first_email(full_text)
    contact_phone = _extract_first_phone(full_text)

    apply_method = None
    apply_instructions = None
    if apply_url and _is_external_url(apply_url, response.url):
        apply_method = "external_url"
    elif apply_url or apply_label:
        apply_method = "internal_form"
        if quick_apply:
            apply_instructions = "Quick Apply Monster detecte"
        elif login_prompt:
            apply_instructions = "Candidature Monster (connexion / resume upload possible)"
        elif apply_label:
            apply_instructions = f"Bouton {apply_label} detecte sur Monster"
    elif login_prompt:
        apply_method = "text_instruction"
        apply_instructions = "Connexion Monster requise pour postuler"

    detail_url = response.url
    job_id = _extract_job_id(detail_url)

    return {
        "blocked": False,
        "source_url": detail_url,
        "title": title,
        "company": company,
        "location": location,
        "description": description,
        "posted_date": posted_raw,
        "posted_date_raw": posted_raw,
        "deadline": deadline,
        "salary": salary,
        "contract_type": contract_type,
        "contact_email": contact_email,
        "contact_phone": contact_phone,
        "apply_url": apply_url or detail_url,
        "apply_method": apply_method,
        "apply_instructions": apply_instructions,
        "job_id": job_id,
        "extra_data": {
            "monster_quick_apply": quick_apply,
            "monster_login_prompt": login_prompt,
            "description_truncated_hint": _looks_truncated_description(description),
        },
    }


def extract_next_page(response: Response) -> Optional[str]:
    """
    Prefer explicit next links, otherwise synthesize `page=N+1` from current URL.
    """
    current_page = _extract_page_number(response.url)
    candidates: list[tuple[int, str]] = []

    for href in response.css(selectors.NEXT_PAGE).getall():
        if not href:
            continue
        full = response.urljoin(href.strip())
        parsed = urlparse(full)
        if "monster.com" not in parsed.netloc:
            continue

        page = _extract_page_number(full)
        if page is None or page <= current_page:
            continue
        candidates.append((page, full))

    if candidates:
        candidates.sort(key=lambda row: row[0])
        return candidates[0][1]

    # Fallback for SPA templates that keep search URLs stable but omit visible next links.
    return build_page_url(response.url, current_page + 1)


def build_page_url(url: str, page_number: int) -> str:
    parsed = urlparse(url)
    query = parse_qs(parsed.query, keep_blank_values=True)
    query["page"] = [str(max(1, int(page_number)))]
    new_query = urlencode(query, doseq=True)
    return urlunparse((parsed.scheme, parsed.netloc, parsed.path, parsed.params, new_query, parsed.fragment))


def _extract_page_number(url: str) -> int:
    query = parse_qs(urlparse(url).query)
    raw = query.get("page", [None])[0]
    if raw is None:
        return 1
    try:
        return max(1, int(raw))
    except (TypeError, ValueError):
        return 1


def _extract_job_id(url: str) -> Optional[str]:
    parsed = urlparse(url)
    match = MONSTER_ID_RE.search(parsed.path or "")
    if match:
        return match.group(1)
    query = parse_qs(parsed.query)
    for key in ("jobid", "jobId", "id"):
        value = query.get(key, [None])[0]
        if value:
            return str(value)
    return None


def _extract_relative_date(text: str) -> Optional[str]:
    if not text:
        return None
    m = DATE_RELATIVE_RE.search(text)
    if not m:
        return None
    return _normalize(m.group(1))


def _extract_absolute_date(text: str) -> Optional[str]:
    if not text:
        return None
    m = DATE_ABS_RE.search(text)
    return m.group(1) if m else None


def _extract_absolute_date_near_label(text: str, labels: tuple[str, ...]) -> Optional[str]:
    if not text:
        return None
    low = text.lower()
    for label in labels:
        idx = low.find(label.lower())
        if idx < 0:
            continue
        window = text[idx: idx + 120]
        m = DATE_ABS_RE.search(window)
        if m:
            return m.group(1)
    return None


def _extract_salary(text: str) -> Optional[str]:
    if not text:
        return None
    m = SALARY_RE.search(text)
    return _normalize(m.group(0)) if m else None


def _extract_contract_hint(text: str) -> Optional[str]:
    if not text:
        return None
    m = CONTRACT_HINT_RE.search(text)
    return _normalize(m.group(1)) if m else None


def _extract_apply_label(node: Any, detail_mode: bool = False) -> Optional[str]:
    selector = selectors.DETAIL_APPLY_BUTTON_TEXT if detail_mode else selectors.JOB_APPLY_BUTTON_TEXT
    texts: list[str] = []
    for sel in selector.split(","):
        texts.extend(node.css(sel.strip()).getall())
    cleaned = [_normalize(t) for t in texts]
    cleaned = [t for t in cleaned if t]
    for text in cleaned:
        if "apply" in text.lower():
            return text
    return cleaned[0] if cleaned else None


def _extract_detail_description(response: Response, full_text: str) -> str:
    """
    Prefer a dedicated description container; otherwise use text slicing around 'Description'.
    """
    text = _normalize(_css_join_text(response, selectors.DETAIL_DESCRIPTION)) or ""
    if not text:
        text = full_text

    if not text:
        return ""

    # Try to start at "Description" heading if present.
    m = re.search(r"\bDescription\b", text, re.IGNORECASE)
    if m:
        text = text[m.end():].strip()

    # Cut obvious CTA/login/apply sections from the description.
    stop_markers = [
        "Want to know if you're fit?",
        "Upload your resume",
        "Have an account? Log in",
        "Quick Apply",
        "Apply now",
        "Save job",
    ]
    for marker in stop_markers:
        parts = re.split(re.escape(marker), text, flags=re.IGNORECASE)
        if len(parts) > 1 and parts[0].strip():
            text = parts[0].strip()
            break

    # If the description still contains repeated UI text, trim some common noise.
    text = re.sub(r"\b(Back to search results|Report this job)\b.*$", "", text, flags=re.IGNORECASE)
    return _normalize(text) or ""


def _has_login_prompt(text: str) -> bool:
    low = (text or "").lower()
    markers = (
        "log in",
        "login",
        "upload your resume",
        "have an account",
        "sign in",
    )
    return any(marker in low for marker in markers)


def _extract_first_email(text: str) -> Optional[str]:
    if not text:
        return None
    m = EMAIL_RE.search(text)
    return m.group(0) if m else None


def _extract_first_phone(text: str) -> Optional[str]:
    if not text:
        return None
    for m in PHONE_RE.finditer(text):
        value = _normalize(m.group(0))
        if value and len(re.sub(r"\D", "", value)) >= 8:
            return value
    return None


def _looks_truncated_description(text: str) -> bool:
    if not text:
        return False
    low = text.lower()
    return ("read more" in low) or low.endswith("...")


def _guess_apply_method_from_label_and_url(
    apply_label: Optional[str],
    apply_url: Optional[str],
    source_url: Optional[str],
) -> Optional[str]:
    label_low = (apply_label or "").lower()
    if apply_url and source_url and _is_external_url(apply_url, source_url):
        return "external_url"
    if "quick apply" in label_low or "apply" in label_low:
        return "internal_form"
    return None


def _is_external_url(candidate: str, source_url: str) -> bool:
    try:
        cand_domain = urlparse(candidate).netloc.lower().replace("www.", "")
        src_domain = urlparse(source_url).netloc.lower().replace("www.", "")
    except Exception:
        return False
    if not cand_domain or not src_domain:
        return False
    return cand_domain != src_domain


def _looks_like_job_url(url: str) -> bool:
    if not url:
        return False
    low = url.lower()
    return "/job/" in low or "/job-opening" in low or "/job-openings/" in low


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
    clean = SPACE_RE.sub(" ", unescape(str(value))).strip()
    return clean or None
