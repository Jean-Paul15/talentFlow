# Extracteurs de champs d'offre d'emploi
# Chaque fonction detecte un champ specifique via heuristiques multiples

import re
from typing import Optional, List

from scrapy.http import HtmlResponse

from .constants import (
    TITLE_SELECTORS, COMPANY_SELECTORS, LOCATION_SELECTORS,
    DESCRIPTION_SELECTORS, CONTRACT_SELECTORS, DATE_SELECTORS,
)
from .utils import normalize_text, extract_all_text, extract_pattern


def smart_extract_title(response: HtmlResponse) -> Optional[str]:
    """Detecte le titre via selecteurs, og:title, puis <title>."""
    # 1. Selecteurs connus
    for sel in TITLE_SELECTORS:
        result = response.css(sel).get()
        if result and len(result.strip()) > 3:
            return normalize_text(result)

    # 2. Meta og:title
    og_title = response.css("meta[property='og:title']::attr(content)").get()
    if og_title:
        return normalize_text(og_title.split("|")[0].split("-")[0])

    # 3. Balise <title>
    title = response.css("title::text").get()
    if title:
        return normalize_text(title.split("|")[0].split("-")[0])

    return None


def smart_extract_company(response: HtmlResponse) -> Optional[str]:
    """Detecte l'entreprise via selecteurs CSS puis meta."""
    for sel in COMPANY_SELECTORS:
        result = response.css(sel).get()
        if result and len(result.strip()) > 1:
            return normalize_text(result)

    # Selecteurs generiques pour sites africains
    for sel in [
        "[class*='company'] ::text", "[class*='entreprise'] ::text",
        "[class*='employer'] ::text", "[class*='recrut'] ::text",
        "[class*='author'] a::text", "[class*='poster'] a::text",
        "[data-company]::attr(data-company)",
        "[itemprop='hiringOrganization'] ::text",
        "[itemprop='name']::text",
    ]:
        result = response.css(sel).get()
        if result and len(result.strip()) > 1 and len(result.strip()) < 100:
            return normalize_text(result)

    # Fallback meta
    for meta_sel in [
        "meta[property='og:site_name']::attr(content)",
        "meta[name='author']::attr(content)",
    ]:
        result = response.css(meta_sel).get()
        if result:
            return normalize_text(result)

    return None


def smart_extract_location(response: HtmlResponse) -> Optional[str]:
    """Detecte la localisation via selecteurs puis patterns texte."""
    for sel in LOCATION_SELECTORS:
        result = response.css(sel).get()
        if result and len(result.strip()) > 1:
            return normalize_text(result)

    # Selecteurs generiques pour sites africains
    for sel in [
        "[class*='location'] ::text", "[class*='lieu'] ::text",
        "[class*='address'] ::text", "[class*='adresse'] ::text",
        "[class*='ville'] ::text", "[class*='city'] ::text",
        "[itemprop='addressLocality']::text",
        "[itemprop='jobLocation'] ::text",
        "address::text",
    ]:
        result = response.css(sel).get()
        if result and len(result.strip()) > 2 and len(result.strip()) < 150:
            return normalize_text(result)

    # Recherche dans le texte via patterns
    full_text = " ".join(response.css("body *::text").getall()[:200])
    return extract_pattern(full_text, [
        r'[Ll]ieu\s*(?:de\s*travail)?\s*:\s*([^\n,]{3,60})',
        r'[Rr][eé]gion\s*(?:de\s*)?:\s*([^\n,]+)',
        r'[Vv]ille\s*:\s*([^\n,]+)',
        r'[Bb]as[eé]\s+[àa]\s+([^\n,\.]+)',
        r'[Aa]dresse\s*(?:du\s*poste)?\s*:\s*([^\n]{5,100})',
        r'[Ll]ocation\s*:\s*([^\n,]+)',
    ])


def smart_extract_description(response: HtmlResponse) -> str:
    """Extrait la description la plus complete possible (max 10000 car.)."""
    # 1. Selecteurs connus
    for sel in DESCRIPTION_SELECTORS:
        text = extract_all_text(response, sel)
        if text and len(text) > 100:
            return text[:10000]

    # 2. Selecteurs generiques pour sites africains
    for sel in [
        "[class*='description']", "[class*='detail']",
        "[class*='annonce']", "[class*='offre']",
        "[class*='job-content']", "[class*='posting']",
        "[itemprop='description']",
    ]:
        text = extract_all_text(response, sel)
        if text and len(text) > 100:
            return text[:10000]

    # 3. Fallback containers generiques
    for container in ["article", "main", ".content", "#content", ".container"]:
        text = extract_all_text(response, container)
        if text and len(text) > 100:
            return text[:10000]

    # 4. Dernier recours : paragraphes du body
    all_texts = response.css("body p::text, body li::text").getall()
    return normalize_text(" ".join(t.strip() for t in all_texts if t.strip()))[:10000]


def smart_extract_contract(response: HtmlResponse, full_text: str = "") -> Optional[str]:
    """Detecte le type de contrat (CDI, CDD, Stage, etc.)."""
    for sel in CONTRACT_SELECTORS:
        result = response.css(sel).get()
        if result:
            return normalize_text(result)

    # Selecteurs generiques pour sites africains
    for sel in [
        "[class*='contract'] ::text", "[class*='contrat'] ::text",
        "[class*='job-type'] ::text", "[class*='employment'] ::text",
        "[itemprop='employmentType']::text",
        "[itemprop='employmentType']::attr(content)",
    ]:
        result = response.css(sel).get()
        if result and len(result.strip()) > 1:
            return normalize_text(result)

    if not full_text:
        full_text = " ".join(response.css("body *::text").getall()[:300])

    return extract_pattern(full_text, [
        r'[Tt]ype\s*(?:de\s*)?contrat\s*:\s*([^\n]+)',
        r'[Tt]ype\s*d.emploi\s*:\s*([^\n]+)',
        r'[Nn]ature\s*(?:du\s*)?(?:contrat|poste)\s*:\s*([^\n]+)',
        r'(CDI|CDD|Stage|Freelance|Int[eé]rim|Consultant|Vacation|Apprentissage)',
    ])


def smart_extract_date(response: HtmlResponse) -> Optional[str]:
    """Detecte la date de publication."""
    for sel in DATE_SELECTORS:
        result = response.css(sel).get()
        if result and len(result.strip()) > 4:
            return normalize_text(result)
    return None


def smart_extract_skills(response: HtmlResponse, full_text: str = "") -> List[str]:
    """Detecte les competences depuis sections dediees ou texte libre."""
    skills_text = None
    for sel in [
        ".competences-cles::text", ".skills::text", ".competences::text",
        "[class*='skill'] ::text", "[class*='competence'] ::text",
        "[class*='qualification'] ::text", "[class*='requirement'] ::text",
        "[class*='profil'] li::text",
    ]:
        texts = response.css(sel).getall()
        if texts:
            skills_text = " | ".join(t.strip() for t in texts if t.strip())
            break

    if skills_text:
        return [s.strip() for s in re.split(r'[-,;|]', skills_text) if s.strip() and len(s.strip()) > 2]

    if not full_text:
        full_text = " ".join(response.css("body *::text").getall()[:500])

    result = extract_pattern(full_text, [
        r'[Cc]omp[eé]tences\s*(?:cl[eé]s|requises?)?\s*:\s*([^\n]+)',
        r'[Ss]kills?\s*:\s*([^\n]+)',
        r'[Qq]ualifications?\s*:\s*([^\n]+)',
        r'[Pp]rofil\s*(?:recherch[eé])?\s*:\s*([^\n]+)',
    ])
    if result:
        return [s.strip() for s in re.split(r'[-,;|]', result) if s.strip() and len(s.strip()) > 2]
    return []


def smart_extract_salary(full_text: str) -> Optional[str]:
    """Detecte le salaire depuis le texte."""
    return extract_pattern(full_text, [
        r'[Ss]alaire\s*:\s*([^\n]+)',
        r'[Rr][eé]mun[eé]ration\s*:\s*([^\n]+)',
        r'(\d[\d\s]*(?:FCFA|XOF|EUR|USD)[^\n]*)',
    ])


def smart_extract_sector(response: HtmlResponse, full_text: str = "") -> Optional[str]:
    """Detecte le secteur d'activite."""
    for sel in [".sector::text", ".category::text", ".job-category a::text",
                "a[href*='metier']::text", "a[href*='sector']::text",
                ".industry::text", ".job-sector::text",
                ".secteur::text", ".domaine::text",
                "[class*='sector'] ::text", "[class*='categor'] ::text",
                "a[href*='categor']::text", "a[href*='industry']::text",
                ".breadcrumb a::text"]:
        result = response.css(sel).get()
        if result:
            clean = normalize_text(result)
            if clean and len(clean) > 2 and len(clean) < 100:
                return clean

    if not full_text:
        full_text = " ".join(response.css("body *::text").getall()[:300])

    return extract_pattern(full_text, [
        r'[Ss]ecteur\s*(?:d.activit[eé])?\s*:\s*([^\n]+)',
        r'[Mm][eé]tier\s*:\s*([^\n]+)',
        r'[Dd]omaine\s*:\s*([^\n]+)',
        r'[Ii]ndustry\s*:\s*([^\n]+)',
        r'[Cc]at[eé]gorie\s*:\s*([^\n]+)',
    ])


def smart_extract_work_schedule(
    response: HtmlResponse, full_text: str = "",
) -> Optional[str]:
    """
    Detecte le regime horaire : temps complet, partiel, teletravail, hybride.
    Distinct du type de contrat (CDI/CDD).
    """
    # Selecteurs CSS
    for sel in [".work-schedule::text", ".work-type::text",
                ".regime::text", ".schedule::text",
                "[class*='schedule'] ::text", "[class*='remote'] ::text"]:
        result = response.css(sel).get()
        if result:
            clean = normalize_text(result)
            if clean and len(clean) > 3:
                return clean

    if not full_text:
        full_text = " ".join(response.css("body *::text").getall()[:300])

    # Patterns texte - chercher les mentions de regime
    schedule_match = extract_pattern(full_text, [
        r'[Rr][eé]gime\s*(?:horaire)?\s*:\s*([^\n]+)',
        r'[Hh]oraire\s*:\s*([^\n]+)',
        r'[Dd]ur[eé]e\s*:\s*([^\n]+)',
    ])
    if schedule_match:
        return schedule_match

    # Detection directe des mots-cles de regime
    schedule_keywords = [
        (r'[Tt]emps\s+complet', "Temps complet"),
        (r'[Tt]emps\s+partiel', "Temps partiel"),
        (r'[Ff]ull[\s-]?time', "Temps complet"),
        (r'[Pp]art[\s-]?time', "Temps partiel"),
        (r'[Ss]ans\s+t[eé]l[eé]travail', "Sans teletravail"),
        (r'[Tt][eé]l[eé]travail\s+(?:complet|total|100)', "Teletravail complet"),
        (r'[Tt][eé]l[eé]travail\s+(?:partiel|hybride)', "Teletravail partiel"),
        (r'[Hh]ybride', "Hybride"),
        (r'[Pp]r[eé]sentiel', "Presentiel"),
        (r'[Rr]emote', "Remote"),
        (r'[Oo]n[\s-]?site', "Presentiel"),
    ]
    found_parts = []
    for pattern, label in schedule_keywords:
        if re.search(pattern, full_text, re.IGNORECASE):
            found_parts.append(label)
    if found_parts:
        return " | ".join(dict.fromkeys(found_parts))
