# Detecteurs de liens dans les pages HTML
# Detection intelligente d'offres, pagination, liens de candidature

import re
from typing import List, Optional
from urllib.parse import urlparse

from scrapy.http import HtmlResponse

from .constants import JOB_URL_PATTERNS, NAV_URL_PATTERNS


def detect_job_links(response: HtmlResponse) -> List[str]:
    """
    Detecte les liens vers des offres d'emploi dans une page.
    Systeme de scoring : URL patterns (+3), texte du lien (+2), nav (-10).
    """
    links = []
    seen = set()

    for a_tag in response.css("a[href]"):
        href = a_tag.attrib.get("href", "")
        text = " ".join(a_tag.css("::text").getall()).strip().lower()

        if not href or href.startswith("#") or href.startswith("javascript:"):
            continue

        full_url = response.urljoin(href)
        if full_url in seen:
            continue
        seen.add(full_url)

        score = _score_job_link(full_url, text)
        if score > 0:
            links.append(full_url)

    return links


def detect_pagination_links(response: HtmlResponse) -> List[str]:
    """Detecte les liens de pagination (suivant, pages numerotees)."""
    links = []
    seen = set()

    # Selecteurs classiques de pagination
    pagination_selectors = [
        "a.next::attr(href)", "a.page-numbers.next::attr(href)",
        ".pagination a::attr(href)", ".pager a::attr(href)",
        "a[rel='next']::attr(href)", ".nav-links a::attr(href)",
        "li.pager-next a::attr(href)", ".pagination-next a::attr(href)",
        "a[title*='suivant']::attr(href)", "a[title*='next']::attr(href)",
    ]

    for sel in pagination_selectors:
        for href in response.css(sel).getall():
            full_url = response.urljoin(href)
            if full_url not in seen:
                seen.add(full_url)
                links.append(full_url)

    # Liens numerotes (page/2, ?page=2, ?start=20, etc.)
    for a_tag in response.css("a[href]"):
        href = a_tag.attrib.get("href", "")
        full_url = response.urljoin(href)
        if full_url in seen:
            continue
        if re.search(r'[?&]page=\d|/page/\d|[?&]start=\d', full_url):
            seen.add(full_url)
            links.append(full_url)

    return links


def detect_external_apply_links(response: HtmlResponse) -> List[str]:
    """
    Detecte les liens 'Postuler' vers des sites recruteurs externes.
    Suit en profondeur les liens de candidature cross-domaine.
    """
    links = []
    apply_keywords = [
        "postuler", "candidater", "apply", "soumettre",
        "postuler sur le site", "voir l'offre",
    ]

    current_domain = urlparse(response.url).netloc

    for a_tag in response.css("a[href]"):
        href = a_tag.attrib.get("href", "")
        text = " ".join(a_tag.css("::text").getall()).strip().lower()

        if not href or href.startswith("#"):
            continue

        is_apply = any(kw in text for kw in apply_keywords)
        if not is_apply:
            continue

        full_url = response.urljoin(href)
        link_domain = urlparse(full_url).netloc

        if link_domain != current_domain:
            links.append(full_url)

    return links


def detect_apply_url(response: HtmlResponse) -> Optional[str]:
    """
    Detecte l'URL de candidature principale d'une offre.
    Cherche le lien 'Postuler' le plus pertinent (interne OU externe).
    Retourne l'URL ou None.
    """
    apply_keywords = [
        "postuler", "candidater", "apply", "soumettre",
        "postuler sur le site", "envoyer ma candidature",
        "deposer candidature", "submit application",
        "je postule", "postuler maintenant", "apply now",
    ]
    apply_classes = [
        "apply", "postuler", "btn-apply", "apply-btn",
        "candidater", "submit", "postulate",
    ]

    best_url = None
    best_score = 0

    for a_tag in response.css("a[href]"):
        href = a_tag.attrib.get("href", "")
        if not href or href.startswith("#") or href.startswith("javascript:"):
            continue
        if href.startswith("mailto:"):
            continue

        text = " ".join(a_tag.css("::text").getall()).strip().lower()
        css_class = a_tag.attrib.get("class", "").lower()

        score = 0
        # Score par texte du lien
        for kw in apply_keywords:
            if kw in text:
                score += 5
                break
        # Score par classe CSS
        for cls in apply_classes:
            if cls in css_class:
                score += 3
                break
        # Bonus si bouton
        if "btn" in css_class or "button" in css_class:
            score += 1

        if score > best_score:
            best_score = score
            best_url = response.urljoin(href)

    # Fallback : formulaire de candidature
    if not best_url:
        forms = response.css("form[action]")
        for form in forms:
            action = form.attrib.get("action", "").lower()
            if any(kw in action for kw in ["apply", "postuler", "candidat"]):
                best_url = response.urljoin(form.attrib.get("action", ""))
                break

    return best_url


def detect_recruiter_name(response: HtmlResponse) -> Optional[str]:
    """
    Detecte le nom du recruteur / cabinet qui a poste l'offre.
    Distinct de 'company' (l'entreprise qui embauche).
    """
    # Labels specifiques au recruteur
    recruiter_labels = [
        "recruteur", "publie par", "poste par", "cabinet",
        "agence", "posted by", "recruiter", "contact rh",
    ]

    for el in response.css("div, p, span, li, td"):
        text = " ".join(el.css("::text").getall()).strip()
        if len(text) > 200 or len(text) < 5:
            continue
        low = text.lower()
        for label in recruiter_labels:
            if label in low:
                # Extraire la valeur apres le label
                pattern = re.compile(
                    rf'{re.escape(label)}\s*:?\s*(.+)',
                    re.IGNORECASE,
                )
                match = pattern.search(text)
                if match:
                    val = match.group(1).strip().split("\n")[0]
                    if val and len(val) > 1 and len(val) < 100:
                        return val

    return None


def _score_job_link(url: str, text: str) -> int:
    """Calcule un score de probabilite qu'un lien mene a une offre."""
    score = 0
    url_lower = url.lower()

    # Patterns URL indicateurs (+3)
    for pat in JOB_URL_PATTERNS:
        if re.search(pat, url_lower):
            score += 3
            break

    # Texte du lien indicateur (+2)
    job_text_patterns = [
        r'postuler', r'voir l.offre', r'candidater', r'd[eé]tail',
        r'en savoir plus', r'lire la suite', r'apply',
        r'voir', r'consulter', r'\+\s*plus',
    ]
    for pat in job_text_patterns:
        if re.search(pat, text):
            score += 2
            break

    # Exclure navigation (-10)
    for pat in NAV_URL_PATTERNS:
        if re.search(pat, url_lower):
            score -= 10
            break

    return score
