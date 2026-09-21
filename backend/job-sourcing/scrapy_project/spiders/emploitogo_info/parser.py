"""
Parser pour emploitogo.info (blog WordPress a contenu mixte).
Priorites audit:
- date de publication = meta WordPress (.posted-on/.entry-date), PAS la date dans le titre
- deadline = texte libre ("Date de Soumission", "Date limite", "avant le ...")
- candidature = bloc POSTULER / texte libre (email/URL/telephone/consignes)
"""
from __future__ import annotations

import re
from typing import List, Optional
from urllib.parse import urlparse

from scrapy.http import Response

from . import selectors


def css_first(response: Response, selector: str) -> Optional[str]:
    for sel in selector.split(","):
        result = response.css(sel.strip()).get()
        if result:
            return result.strip()
    return None


def _normalize_space(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    cleaned = re.sub(r"\s+", " ", value).strip()
    return cleaned or None


def _strip_accents_lower(text: str) -> str:
    table = str.maketrans(
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
            "ô": "o",
            "ö": "o",
            "ù": "u",
            "û": "u",
            "ü": "u",
            "’": "'",
        }
    )
    return (text or "").lower().translate(table)


def _content_root(response: Response):
    nodes = response.css(selectors.JOB_CONTENT_CONTAINER)
    return nodes[0] if nodes else None


def _content_text(response: Response) -> str:
    node = _content_root(response)
    if not node:
        return ""
    texts = node.xpath(
        ".//text()[normalize-space() "
        "and not(ancestor::*[contains(@class,'comments-area')]) "
        "and not(ancestor::aside) "
        "and not(ancestor::*[contains(@class,'sidebar')])]"
    ).getall()
    text = _normalize_space(" ".join(t.strip() for t in texts if t and t.strip())) or ""
    # Couper explicitement avant les zones hors contenu qui peuvent être injectées dans entry-content.
    split_markers = [
        "Laisser un commentaire",
        "Leave a Comment",
        "Articles similaires",
        "Lire aussi",
        "Related Posts",
        "Partager",
    ]
    for marker in split_markers:
        parts = re.split(re.escape(marker), text, flags=re.IGNORECASE)
        if parts and len(parts) > 1:
            text = _normalize_space(parts[0]) or text
            break
    return text


def _content_lines(response: Response) -> List[str]:
    node = _content_root(response)
    if not node:
        return []
    lines: List[str] = []
    for child in node.xpath(
        ".//*[self::p or self::li or self::h2 or self::h3 or self::h4 or self::h5 or self::strong]"
        "[not(ancestor::*[contains(@class,'comments-area')]) and not(ancestor::aside)]"
    ):
        txt = _normalize_space(" ".join(child.xpath(".//text()").getall()))
        if txt and len(txt) >= 2:
            lines.append(txt)
    # stop before comment-related blocks if leaked
    cleaned: List[str] = []
    for line in lines:
        low = _strip_accents_lower(line)
        if any(k in low for k in ("laisser un commentaire", "related posts", "articles similaires", "author bio")):
            break
        cleaned.append(line)
    return cleaned


def _extract_wp_posted_date(response: Response) -> tuple[Optional[str], Optional[str], str]:
    """
    Returns (posted_value_for_item, posted_raw, source_label)
    - prefer time datetime (ISO)
    - fallback to visible meta text
    """
    dt_attr = css_first(response, selectors.JOB_DATE_ATTR)
    txt = css_first(response, selectors.JOB_DATE_TEXT)

    if dt_attr:
        dt_attr = _normalize_space(dt_attr)
        # WordPress may return full ISO timestamp; keep raw + normalized YYYY-MM-DD in posted_date.
        m = re.search(r"\d{4}-\d{2}-\d{2}", dt_attr or "")
        if m:
            return m.group(0), (txt or dt_attr), "wordpress_meta_time"
        return dt_attr, (txt or dt_attr), "wordpress_meta_time"

    if txt:
        txt = _normalize_space(txt)
        return txt, txt, "wordpress_meta_text"

    generic = _normalize_space(css_first(response, selectors.JOB_DATE))
    if generic:
        return generic, generic, "generic_meta"

    return None, None, "missing"


def _extract_field(text: str, patterns: List[str]) -> Optional[str]:
    if not text:
        return None
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return _normalize_space(match.group(1))
    return None


def _extract_all_emails(text: str) -> List[str]:
    emails = re.findall(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", text or "")
    unique: List[str] = []
    seen = set()
    for e in emails:
        low = e.lower()
        if low in seen:
            continue
        seen.add(low)
        unique.append(low)
    return unique


def _extract_phones(text: str) -> List[str]:
    patterns = [
        r"(?:\+|00)?\s*228[\s.-]?\d{2}[\s.-]?\d{2}[\s.-]?\d{2}[\s.-]?\d{2}",
        r"\b\d{2}[\s.-]\d{2}[\s.-]\d{2}[\s.-]\d{2}\b",
    ]
    out: List[str] = []
    seen = set()
    for pat in patterns:
        for m in re.findall(pat, text or "", re.IGNORECASE):
            val = _normalize_space(m)
            key = re.sub(r"\D", "", val or "")
            if not val or len(key) < 8 or key in seen:
                continue
            seen.add(key)
            out.append(val)
    return out


def _extract_mailtos(response: Response) -> List[str]:
    emails: List[str] = []
    for raw in response.css(selectors.JOB_APPLY_MAILTOS).getall():
        if not raw:
            continue
        val = raw.split(":", 1)[1].split("?", 1)[0].strip() if raw.lower().startswith("mailto:") else raw.strip()
        val = val.lower()
        if val and val not in emails:
            emails.append(val)
    return emails


def _extract_apply_section_text(lines: List[str]) -> str:
    """
    Capture a partir de "POSTULER" / "Comment postuler" jusqu'a la fin du contenu.
    """
    start_idx = None
    for i, line in enumerate(lines):
        low = _strip_accents_lower(line)
        if "postuler" in low or "comment postuler" in low:
            start_idx = i
            break
    if start_idx is None:
        return ""
    selected = []
    for line in lines[start_idx:]:
        low = _strip_accents_lower(line)
        if any(stop in low for stop in ("laisser un commentaire", "articles similaires", "related posts")):
            break
        selected.append(line)
    return _normalize_space(" ".join(selected)) or ""


def _extract_apply_urls(response: Response) -> List[str]:
    urls: List[str] = []
    for href in response.css(selectors.JOB_ARTICLE_LINKS).getall():
        full = response.urljoin(href)
        low = full.lower()
        if not low.startswith("http"):
            continue
        # Exclure les liens internes de navigation WordPress et réseaux sociaux.
        if "emploitogo.info" in urlparse(full).netloc.lower():
            continue
        if any(k in low for k in ("facebook.com", "linkedin.com", "twitter.com", "whatsapp", "pinterest")):
            continue
        if full not in urls:
            urls.append(full)
    return urls


def _extract_deadline(title: str, full_text: str, apply_text: str) -> tuple[Optional[str], str]:
    """
    Retourne (deadline_raw, source)
    Priorite:
    - bloc POSTULER / "Date de Soumission" dans le corps
    - texte global avec contextes
    - fallback date dans le titre (souvent deadline sur ce site)
    """
    contexts = [apply_text, full_text]
    patterns = [
        r"[Dd]ate de soumission\s*[:\-]?\s*([^\n\.;]{4,80})",
        r"[Dd]eadline\s*[:\-]?\s*([^\n\.;]{4,80})",
        r"[Dd]ate limite(?: de candidature)?\s*[:\-]?\s*([^\n\.;]{4,80})",
        r"avant le\s*([^\n\.;]{4,80})",
        r"au plus tard le\s*([^\n\.;]{4,80})",
    ]
    for idx, text in enumerate(contexts):
        if not text:
            continue
        for pat in patterns:
            m = re.search(pat, text, re.IGNORECASE)
            if m:
                return (_normalize_space(m.group(1)), "apply_section" if idx == 0 else "content_text")

    # Fallback: date in title is often the deadline (audit says critical ambiguity).
    if title:
        m = re.search(r"(\d{1,2}[/-]\d{1,2}[/-]\d{4})", title)
        if m:
            return (m.group(1), "title_deadline_fallback")
    return (None, "missing")


def _extract_company(title: str, full_text: str) -> Optional[str]:
    patterns = [
        r"^(?:le\s+groupe|la\s+soci[eé]t[eé]|la\s+compagnie|l['’]entreprise)\s+(.+?)\s+recrute",
        r"\b([A-Z][A-Z0-9&\-\.\s]{2,})\s+recrute\b",
        r"[Tt]itre du poste\s*:\s*([^\n]+)",  # fallback poor but sometimes useful
        r"[Ee]ntreprise\s*:\s*([^\n]+)",
    ]
    for src in (title or "", full_text or ""):
        for pat in patterns:
            m = re.search(pat, src, re.IGNORECASE)
            if m:
                value = _normalize_space(m.group(1))
                if not value:
                    continue
                if len(value) > 120:
                    continue
                return value
    return None


def _extract_location(full_text: str) -> Optional[str]:
    return _extract_field(
        full_text,
        [
            r"[Ll]ieu du travail\s*[:\-]\s*([^\n\.;]+)",
            r"[Ll]ieu\s*[:\-]\s*([^\n\.;]+)",
            r"[Rr][ée]gion\s*[:\-]\s*([^\n\.;]+)",
            r"[Vv]ille\s*[:\-]\s*([^\n\.;]+)",
        ],
    )


def _extract_contract(full_text: str) -> Optional[str]:
    return _extract_field(
        full_text,
        [
            r"[Tt]ype (?:de )?contrat\s*[:\-]\s*([^\n\.;]+)",
            r"(CDD|CDI|Stage|Freelance|Int[ée]rim|Consultance)",
        ],
    )


def _extract_education(full_text: str) -> Optional[str]:
    return _extract_field(
        full_text,
        [
            r"[Nn]iveau requis\s*[:\-]\s*([^\n\.;]+)",
            r"[Nn]iveau d['’]?[ée]tudes\s*[:\-]\s*([^\n\.;]+)",
            r"[Dd]ipl[oô]me\s*[:\-]\s*([^\n\.;]+)",
        ],
    )


def _extract_experience(full_text: str) -> Optional[str]:
    return _extract_field(
        full_text,
        [
            r"[Aa]nn[ée]es? d['’]exp[ée]rience\s*[:\-]\s*([^\n\.;]+)",
            r"[Ee]xp[ée]rience\s*[:\-]\s*([^\n\.;]+)",
        ],
    )


def _is_likely_job_post(title: str, full_text: str, apply_text: str, emails: List[str], deadline: Optional[str]) -> tuple[bool, list[str]]:
    reasons: list[str] = []
    low_title = _strip_accents_lower(title or "")
    low_full = _strip_accents_lower(full_text or "")
    low_apply = _strip_accents_lower(apply_text or "")

    if "informations sur l'emploi" in low_full:
        reasons.append("job_info_block")
    if "postuler" in low_full or "comment postuler" in low_full or "postuler" in low_apply:
        reasons.append("apply_section")
    if emails:
        reasons.append("email_detected")
    if deadline:
        reasons.append("deadline_detected")
    if any(k in low_title for k in ("recrute", "recrutement", "offre", "poste", "stage")):
        reasons.append("jobish_title")

    # plus strict pour limiter les articles blog non-offre
    is_job = len(reasons) >= 3 and ("apply_section" in reasons or "email_detected" in reasons)
    return is_job, reasons


def parse_job_data(response: Response) -> dict:
    """
    Parse article EmploiTogo.info avec séparation publication/deadline et bloc candidature.
    """
    title = _normalize_space(css_first(response, selectors.JOB_TITLE)) or ""
    full_text = _content_text(response)
    lines = _content_lines(response)
    posted_value, posted_raw, posted_source = _extract_wp_posted_date(response)

    apply_section_text = _extract_apply_section_text(lines)
    emails = _extract_mailtos(response)
    emails_from_apply = _extract_all_emails(apply_section_text)
    emails_from_full = _extract_all_emails(full_text)
    # priorité: bloc POSTULER > mailto > reste du contenu
    ordered_emails: List[str] = []
    for group in (emails_from_apply, emails, emails_from_full):
        for e in group:
            if e not in ordered_emails:
                ordered_emails.append(e)

    phones = _extract_phones(apply_section_text or full_text)
    apply_urls = _extract_apply_urls(response)

    deadline, deadline_source = _extract_deadline(title, full_text, apply_section_text)
    company = _extract_company(title, full_text)
    location = _extract_location(full_text)
    contract_type = _extract_contract(full_text)
    education = _extract_education(full_text)
    experience = _extract_experience(full_text)

    primary_email = ordered_emails[0] if ordered_emails else None
    primary_phone = phones[0] if phones else None
    primary_apply_url = apply_urls[0] if apply_urls else None

    apply_instructions = None
    if apply_section_text:
        apply_instructions = apply_section_text[:500]
    elif full_text:
        m = re.search(r"(?:postuler|comment postuler)[^\n]{0,500}", full_text, re.IGNORECASE)
        if m:
            apply_instructions = _normalize_space(m.group(0))

    apply_method = None
    if primary_email:
        apply_method = "email"
    elif primary_apply_url:
        apply_method = "external_url"
    elif primary_phone:
        apply_method = "phone"
    elif apply_instructions:
        apply_method = "text_instruction"

    is_job_post, job_reasons = _is_likely_job_post(
        title=title,
        full_text=full_text,
        apply_text=apply_section_text,
        emails=ordered_emails,
        deadline=deadline,
    )

    extra_data = {
        "source_template": "wordpress_post_blog",
        "posted_date_source": posted_source,
        "deadline_source": deadline_source,
        "all_emails": ordered_emails or None,
        "all_phones": phones or None,
        "external_apply_links": apply_urls or None,
        "has_job_info_block": "informations sur l'emploi" in _strip_accents_lower(full_text),
        "has_apply_section": bool(apply_section_text),
        "is_job_post": is_job_post,
        "job_detection_reasons": job_reasons or None,
    }

    return {
        "title": title,
        "company": company or "Non precise",
        "location": location or "Togo",
        "description": full_text or "",
        "contract_type": contract_type,
        "posted_date": posted_value,          # publication (meta WP)
        "posted_date_raw": posted_raw,        # meta visible/raw
        "category": _normalize_space(css_first(response, selectors.JOB_CATEGORY)),
        "salary": _extract_field(full_text, [r"[Ss]alaire\s*[:\-]\s*([^\n\.;]+)", r"[Rr][ée]mun[ée]ration\s*[:\-]\s*([^\n\.;]+)"]),
        "availability": _extract_field(full_text, [r"[Dd]isponibilit[ée]\s*[:\-]\s*([^\n\.;]+)"]),
        "deadline": deadline,
        "contact_email": primary_email,
        "contact_phone": primary_phone,
        "apply_url": primary_apply_url,
        "apply_method": apply_method,
        "apply_instructions": apply_instructions,
        "education": education,
        "experience": experience,
        "recruiter_name": None,
        "is_job_post": is_job_post,
        "extra_data": {k: v for k, v in extra_data.items() if v is not None},
    }
