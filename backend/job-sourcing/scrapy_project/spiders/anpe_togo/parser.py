"""
Parser pour ANPE Togo (site Joomla CMS).
"""
import re
from html import unescape
from typing import Optional
from urllib.parse import urlparse
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


def _clean_text(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    cleaned = re.sub(r"\s+", " ", unescape(value)).strip()
    return cleaned or None


def _article_text(response: Response) -> str:
    # Equivalent fonctionnel d'un innerText sur la zone editoriale.
    texts = response.css("section.article-content *::text").getall()
    return _clean_text(" ".join(t.strip() for t in texts if t and t.strip())) or ""


def _article_lines(response: Response) -> list[str]:
    lines: list[str] = []
    for sel in (
        "section.article-content p",
        "section.article-content li",
        "section.article-content h2",
        "section.article-content h3",
        "section.article-content div",
    ):
        for node in response.css(sel):
            txt = _clean_text(" ".join(node.css("::text").getall()))
            if txt and len(txt) >= 3:
                lines.append(txt)
    return lines


def _extract_title_from_content(response: Response, full_text: str) -> Optional[str]:
    # Audit: le h1 de page = categorie ("OFFRES D'EMPLOIS"), pas le vrai titre.
    title = _clean_text(css_first(response, selectors.JOB_TITLE))
    if title and title.upper() != "OFFRES D'EMPLOIS":
        return title

    for line in _article_lines(response):
        upper = line.upper()
        if upper in {"OFFRES D'EMPLOIS", "INFORMATIONS COMPLÉMENTAIRES", "INFORMATIONS COMPLEMENTAIRES"}:
            continue
        # Ignore pure labels.
        if re.fullmatch(r"[A-ZÉÈÀÙÂÊÎÔÛÇ\s:,'’()/-]{1,80}", line) and len(line.split()) <= 3:
            continue
        if len(line) >= 5:
            return line[:255]

    page_title = _clean_text(css_first(response, "title::text"))
    if page_title:
        page_title = re.sub(r"\s*[-|–]\s*ANPE.*$", "", page_title, flags=re.I).strip()
        if page_title and page_title.upper() != "OFFRES D'EMPLOIS":
            return page_title
    if full_text:
        return full_text[:120]
    return None


def _extract_publication_date(text: str) -> Optional[str]:
    if not text:
        return None
    patterns = [
        r"[Dd]ate de publication(?: de l'avis de vacance de poste)?\s*[:\-]?\s*([^\n\.;]{6,60})",
        r"[Pp]ubli[ée]e?\s+le\s*([^\n\.;]{6,60})",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return _clean_text(match.group(1))
    return None


def _extract_deadline(text: str) -> Optional[str]:
    if not text:
        return None
    patterns = [
        r"[Dd]ate limite(?: de [^\n:]+)?\s*[:\-]?\s*([^\n\.;]{4,80})",
        r"[Dd]eadline\s*[:\-]?\s*([^\n\.;]{4,80})",
        r"au plus tard le\s+([^\n\.]{4,100})",
        r"cl[oô]ture[^:\n]*[:\-]?\s*([^\n\.;]{4,80})",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            raw = _clean_text(match.group(1))
            if raw:
                return raw
    return None


def _extract_emails_from_article(response: Response, text: str) -> list[str]:
    emails: list[str] = []
    for raw in response.css(selectors.JOB_ARTICLE_MAILTOS).getall():
        if not raw:
            continue
        if raw.lower().startswith("mailto:"):
            candidate = raw.split(":", 1)[1].split("?", 1)[0].strip()
            if candidate:
                emails.append(candidate)
    regex_emails = re.findall(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", text or "")
    emails.extend(regex_emails)
    unique = []
    seen = set()
    for email in emails:
        e = email.strip().lower()
        if not e or e in seen:
            continue
        seen.add(e)
        unique.append(e)
    return unique


def _extract_phones_from_text(text: str) -> list[str]:
    patterns = [
        r"(?:\+|00)?\s*228[\s.-]?\d{2}[\s.-]?\d{2}[\s.-]?\d{2}[\s.-]?\d{2}",
        r"(?:T[ée]l(?:[ée]phone)?)\s*[:\-]?\s*(\d{2}(?:[\s.-]\d{2}){3})",
    ]
    results: list[str] = []
    for pat in patterns:
        for m in re.findall(pat, text or "", re.IGNORECASE):
            val = m if isinstance(m, str) else "".join(m)
            val = _clean_text(val)
            if val:
                results.append(val)
    unique = []
    seen = set()
    for p in results:
        key = re.sub(r"\D", "", p)
        if len(key) < 8 or key in seen:
            continue
        seen.add(key)
        unique.append(p)
    return unique


def _extract_external_apply_links(response: Response) -> list[str]:
    exclude_domains = {
        "anpetogo.org",
        "www.anpetogo.org",
        "emploitogo.com",
        "www.emploitogo.com",
        "emploitogo.info",
        "www.emploitogo.info",
        "jobrelais.com",
        "www.jobrelais.com",
        "cdiscussion.com",
        "www.cdiscussion.com",
        "whed.net",
        "www.whed.net",
    }
    links: list[str] = []
    for href in response.css(selectors.JOB_ARTICLE_LINKS).getall():
        full = response.urljoin(href)
        if not full.lower().startswith("http"):
            continue
        domain = urlparse(full).netloc.lower()
        if domain in exclude_domains:
            continue
        if full not in links:
            links.append(full)
    return links


def _extract_apply_instructions(lines: list[str]) -> Optional[str]:
    for line in lines:
        low = line.lower()
        if any(token in low for token in ("dossiers", "candidature", "postulez", "soumises en ligne", "envoyant par mail")):
            return line[:300]
    return None


def _extract_company_from_text(text: str) -> Optional[str]:
    patterns = [
        r"(?:l['’]anpe\s+recherche\s+pour\s+une?\s+entreprise[^\.]{0,80})",
        r"(?:l['’]anpe\s+recrute\s+pour\s+([^,\.\n]+))",
        r"(?:la soci[ée]t[ée]\s+([^,\.\n]+)\s+recrute)",
        r"(?:le cabinet\s+([^,\.\n]+)\s+recrute)",
        r"\b(AVSF|OMPI|OMM|OMS|UNESCO|ONU|WIPO|WMO)\b",
    ]
    for pattern in patterns:
        m = re.search(pattern, text, re.IGNORECASE)
        if not m:
            continue
        if m.lastindex:
            return _clean_text(m.group(1))
        return _clean_text(m.group(0))
    return None


def parse_job_data(response: Response) -> dict:
    """
    Parse les donnees d'une offre ANPE Togo.
    Extraction approfondie depuis le contenu HTML.
    """
    full_text = _article_text(response)
    lines = _article_lines(response)
    title = _extract_title_from_content(response, full_text)

    description = full_text or css_all_text(response, selectors.JOB_DESCRIPTION)
    if not description or len(description) < 50:
        html_content = response.css('section.article-content *::text, .item-page *::text').getall()
        description = _clean_text(' '.join(t.strip() for t in html_content if t.strip())) or ''

    # Extraire l'entreprise depuis le contenu (pas depuis la colonne "Auteur" du listing)
    company = _extract_company_from_text(description) or _extract_field(description, [
        r'(?:entreprise|societe|structure)\s*[:\-]\s*([^\n\.]+)',
        r'recrute pour\s+([^\n\.]+)',
    ])
    
    # Extraire le lieu
    location = _extract_field(description, [
        r'[Ll]ieu\s*[:\-]\s*([^\n\.]+)',
        r'[Bb]as[ee] [a\u00e0]\s+([^\n\.]+)',
        r'[Pp]oste\s+[a\u00e0]\s+([^\n\.]+)',
    ])
    
    # Extraire le type de contrat
    contract = _extract_field(description, [
        r'(CDD|CDI|Stage|Consultant|Freelance)',
        r'[Tt]ype\s*(?:de\s*)?contrat\s*[:\-]\s*([^\n\.]+)',
    ])

    publication_date = _extract_publication_date(description)
    deadline = _extract_deadline(description)
    emails = _extract_emails_from_article(response, description)
    phones = _extract_phones_from_text(description)
    external_apply_links = _extract_external_apply_links(response)
    primary_email = emails[0] if emails else None
    primary_phone = phones[0] if phones else None
    apply_url = external_apply_links[0] if external_apply_links else None
    apply_instructions = _extract_apply_instructions(lines)
    source_lower = (response.url or "").lower()
    joomla_id_match = re.search(r"/(\d+)-", source_lower)
    joomla_id = int(joomla_id_match.group(1)) if joomla_id_match else None

    extra_data = {
        "anpe_joomla_id": joomla_id,
        "publication_order_proxy": joomla_id,
        "date_source": "explicit_publication_label" if publication_date else ("deadline_only" if deadline else "missing"),
        "all_emails": emails or None,
        "all_phones": phones or None,
        "external_apply_links": external_apply_links or None,
        "source_template": "joomla_category_article",
    }

    return {
        'title': title,
        'company': company or 'Via ANPE Togo',
        'location': location or 'Togo',
        # Ne pas tronquer: la description complete est critique pour NLP/matching.
        'description': description or '',
        'sector': None,
        'contract_type': contract,
        # Important: sur ANPE, la plupart des dates visibles sont des deadlines, pas des dates de publication.
        'posted_date': publication_date,
        'deadline': deadline,
        'contact_email': primary_email,
        'contact_phone': primary_phone,
        'apply_url': apply_url,
        'apply_instructions': apply_instructions,
        'recruiter_name': None,
        'extra_data': {k: v for k, v in extra_data.items() if v is not None},
    }


def _extract_field(text: str, patterns: list) -> Optional[str]:
    """Recherche un champ dans le texte via des patterns regex."""
    if not text:
        return None
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1).strip()
    return None
