"""
Parser pour wiijob.com.
Audit-driven:
- dates sur sidebar "Publié le" / "Expire le" (format JJ/MM/YYYY)
- description complète dans section description
- candidature via bouton/formulaire interne avec authentification (login gate)
- listing potentiellement incomplet (SPA), donc priorité au détail quand URL connue
"""
from __future__ import annotations

import re
import unicodedata
from typing import Optional

from scrapy.http import Response

from . import selectors


EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
PHONE_RE = re.compile(r"(?:\+|00)?\s*\d[\d\s().\-]{7,}\d")
DATE_FR_RE = re.compile(r"\b(\d{2}/\d{2}/\d{4})\b")


def css_first(response: Response, selector: str) -> Optional[str]:
    for sel in selector.split(","):
        result = response.css(sel.strip()).get()
        if result:
            return result.strip()
    return None


def css_all_text(response: Response, selector: str) -> str:
    texts = []
    for sel in selector.split(","):
        texts.extend(response.css(sel.strip()).getall())
    return " ".join(t.strip() for t in texts if t and t.strip())


def _normalize_space(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    # NFKC réduit certains caractères unicode stylisés (audit Wiijob).
    value = unicodedata.normalize("NFKC", value)
    cleaned = re.sub(r"\s+", " ", value).strip()
    return cleaned or None


def _strip_accents_lower(text: str) -> str:
    table = str.maketrans(
        {
            "à": "a", "â": "a", "ä": "a", "á": "a",
            "ç": "c",
            "é": "e", "è": "e", "ê": "e", "ë": "e",
            "î": "i", "ï": "i",
            "ô": "o", "ö": "o",
            "ù": "u", "û": "u", "ü": "u",
            "’": "'",
        }
    )
    return unicodedata.normalize("NFKC", text or "").lower().translate(table)


def _extract_sidebar_fields(response: Response) -> dict[str, str]:
    """
    Essaie d'extraire les paires clé/valeur de la sidebar:
    "Publié le", "Ville", "Expire le", "Expérience", "Secteur", "Temps", "Mode".
    """
    fields: dict[str, str] = {}

    # Variante ciblée existante (template Wiijob observé historiquement)
    for li in response.css(".widget_apus_job_info ul.list li"):
        key = _normalize_space(li.css(".details .text::text").get())
        value = _normalize_space(" ".join(li.css(".details .value *::text, .details .value::text").getall()))
        if key and value:
            fields[_strip_accents_lower(key)] = value

    if fields:
        return fields

    # Fallback générique: lire les <li> de sidebar et splitter "Label : valeur"
    for li in response.css(selectors.JOB_SIDEBAR_INFO):
        line = _normalize_space(" ".join(li.css("::text").getall()))
        if not line:
            continue
        if ":" in line:
            key, val = line.split(":", 1)
            key_n = _strip_accents_lower(_normalize_space(key) or "")
            val_n = _normalize_space(val)
            if key_n and val_n:
                fields[key_n] = val_n
            continue

        # Fallback heuristique pour blocs sur plusieurs lignes
        tokens = [_normalize_space(t) for t in li.css("::text").getall()]
        tokens = [t for t in tokens if t]
        if len(tokens) >= 2:
            key_n = _strip_accents_lower(tokens[0])
            val_n = " ".join(tokens[1:]).strip()
            if key_n and val_n:
                fields[key_n] = val_n

    return fields


def _clean_deadline(value: Optional[str]) -> Optional[str]:
    value = _normalize_space(value)
    if not value:
        return None
    if value in {"-", "–", "—"}:
        return None
    # Si texte type "Expire le 15/07/2025"
    m = DATE_FR_RE.search(value)
    if m:
        return m.group(1)
    return value


def _extract_labeled_date(text: str, labels: tuple[str, ...]) -> Optional[str]:
    if not text:
        return None
    low = _strip_accents_lower(text)
    for label in labels:
        label_low = _strip_accents_lower(label)
        idx = low.find(label_low)
        if idx >= 0:
            window = text[idx: idx + 80]
            m = DATE_FR_RE.search(window)
            if m:
                return m.group(1)
    return None


def _extract_sidebar_text(response: Response) -> str:
    return _normalize_space(css_all_text(response, selectors.JOB_SIDEBAR_TEXT)) or ""


def _extract_description(response: Response) -> str:
    # Priorité: bloc description dédié
    text = _normalize_space(css_all_text(response, selectors.JOB_DESCRIPTION)) or ""
    if not text:
        return ""

    # Exclure la partie login gate / CTA de candidature si incluse dans le même conteneur
    stop_markers = [
        "Veuillez vous connecter",
        "Connectez-vous",
        "Postuler",
        "Apply now",
    ]
    for marker in stop_markers:
        parts = re.split(re.escape(marker), text, flags=re.IGNORECASE)
        if len(parts) > 1:
            text = _normalize_space(parts[0]) or text
            break
    return text


def _extract_apply_artifacts(response: Response, detail_text: str) -> tuple[Optional[str], Optional[str], bool]:
    apply_url = None
    login_required = False

    for raw in response.css(selectors.JOB_APPLY_LINK).getall():
        href = (raw or "").strip()
        if not href:
            continue
        # Wiijob peut utiliser href="#..." pour ouvrir modal/form interne
        apply_url = response.urljoin(href)
        break

    button_texts = " ".join(response.css(selectors.JOB_APPLY_BUTTON_TEXT).getall())
    page_text = f"{button_texts} {detail_text}"
    low = _strip_accents_lower(page_text)
    if "veuillez vous connecter" in low or "connecter comme" in low or "connexion" in low:
        login_required = True

    apply_instructions = None
    if login_required:
        apply_instructions = "Candidature via formulaire Wiijob (authentification requise)"
    elif "postuler" in low:
        apply_instructions = "Bouton Postuler detecte sur la page Wiijob"

    return apply_url, apply_instructions, login_required


def _extract_first_email(text: str) -> Optional[str]:
    if not text:
        return None
    match = EMAIL_RE.search(text)
    return match.group(0) if match else None


def _extract_first_phone(text: str) -> Optional[str]:
    if not text:
        return None
    for m in PHONE_RE.finditer(text):
        candidate = _normalize_space(m.group(0))
        if candidate:
            return candidate
    return None


def _extract_listing_like_date(response: Response) -> Optional[str]:
    # Fallback global sur le détail si sidebar ne donne rien.
    raw = _normalize_space(css_first(response, selectors.JOB_DATE))
    if not raw:
        return None
    m = DATE_FR_RE.search(raw)
    return m.group(1) if m else raw


def parse_job_data(response: Response) -> dict:
    """
    Parse les donnees d'une offre Wiijob.
    """
    sidebar = _extract_sidebar_fields(response)
    sidebar_text = _extract_sidebar_text(response)
    detail_text = _normalize_space(css_all_text(response, selectors.JOB_DETAIL_TEXT)) or ""

    title = _normalize_space(css_first(response, selectors.JOB_TITLE))
    company = _normalize_space(css_first(response, selectors.JOB_COMPANY))
    location = _normalize_space(css_first(response, selectors.JOB_LOCATION)) or sidebar.get("ville")
    contract_type = _normalize_space(css_first(response, selectors.JOB_CONTRACT))
    metier = _normalize_space(css_first(response, selectors.JOB_METIER_DETAIL)) or sidebar.get("secteur d'activite") or sidebar.get("secteur d'activité")
    description = _extract_description(response)

    posted_date = (
        sidebar.get("publie le")
        or sidebar.get("publié le")
        or _extract_labeled_date(sidebar_text, ("Publié le", "Publie le"))
        or _extract_listing_like_date(response)
    )
    deadline = (
        _clean_deadline(sidebar.get("expire le") or sidebar.get("expiré le"))
        or _clean_deadline(_extract_labeled_date(sidebar_text, ("Expire le", "Expiré le")))
    )

    salary = sidebar.get("salaire")
    experience = sidebar.get("experience") or sidebar.get("expérience")
    sector = sidebar.get("secteur d'activite") or sidebar.get("secteur d'activité") or metier
    work_schedule = sidebar.get("temps") or sidebar.get("temps de travail")
    work_mode = sidebar.get("mode") or sidebar.get("mode de travail")

    apply_url, apply_instructions, login_required = _extract_apply_artifacts(response, detail_text)
    contact_email = _extract_first_email(detail_text)
    contact_phone = _extract_first_phone(detail_text)

    apply_method = None
    if contact_email:
        apply_method = "email"
    elif apply_url:
        # Bouton Wiijob = candidature plateforme (souvent gated)
        apply_method = "internal_form"
    elif apply_instructions:
        apply_method = "text_instruction"

    return {
        "title": title,
        "company": company if company else "Wiijob",
        "location": location if location else "Afrique",
        "description": description or "",
        "contract_type": contract_type,
        "category": sector,
        "posted_date": posted_date,
        "posted_date_raw": posted_date,
        "salary": salary,
        "deadline": deadline,
        "experience": experience,
        "work_schedule": work_schedule,
        "work_mode": work_mode,
        "contact_email": contact_email,
        "contact_phone": contact_phone,
        "apply_url": apply_url,
        "apply_method": apply_method,
        "apply_instructions": apply_instructions,
        "recruiter_name": None,
        "extra_data": {
            "source_template": "wiijob_spa_detail",
            "apply_login_required": login_required,
            "sidebar_fields": sidebar or None,
            "deadline_missing_explicit_dash": (
                (sidebar.get("expire le") in {"-", "–", "—"})
                or (sidebar.get("expiré le") in {"-", "–", "—"})
            ),
        },
    }

