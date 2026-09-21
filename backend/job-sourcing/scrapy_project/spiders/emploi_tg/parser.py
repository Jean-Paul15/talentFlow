"""
Parser pour emploi.tg (AfricaTalents/AfricaWork).
Base sur audit DOM (Drupal): dates <time datetime>, pagination ?page=, formulaire interne.
"""
from __future__ import annotations

import re
from typing import List, Optional

from scrapy.http import Response

from . import selectors


def css_first(response: Response, selector: str) -> Optional[str]:
    """
    Extrait premier resultat d'un ou plusieurs selecteurs (virgule).
    """
    for sel in selector.split(","):
        result = response.css(sel.strip()).get()
        if result:
            return result.strip()
    return None


def css_all_text(response: Response, selector: str) -> str:
    """
    Concatene tous les textes trouves.
    """
    texts = []
    for sel in selector.split(","):
        texts.extend(response.css(sel.strip()).getall())
    return " ".join(t.strip() for t in texts if t and t.strip())


def _normalize_space(value: str) -> str:
    return re.sub(r"\s+", " ", value or "").strip()


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


def _extract_posted_date(response: Response) -> tuple[Optional[str], Optional[str]]:
    """
    Priorite audit emploi.tg:
    1) time[datetime] (ISO)
    2) texte visible du time (DD.MM.YYYY)
    """
    dt_attr = css_first(response, selectors.JOB_POSTED_DATE_ATTR)
    time_text = css_first(response, selectors.JOB_POSTED_DATE_TEXT)

    if dt_attr:
        dt_attr = _normalize_space(dt_attr)
        m = re.search(r"\d{4}-\d{2}-\d{2}", dt_attr)
        if m:
            return m.group(0), time_text

    if time_text:
        clean = _normalize_space(time_text)
        m = re.search(r"(\d{2})\.(\d{2})\.(\d{4})", clean)
        if m:
            day, month, year = m.groups()
            return f"{year}-{month}-{day}", clean
        return None, clean

    return None, None


def _node_text(node) -> str:
    if not node:
        return ""
    texts = node.xpath(".//text()[normalize-space() and not(ancestor::form)]").getall()
    return _normalize_space(" ".join(texts))


def _find_heading_node(response: Response, labels: list[str], tags: tuple[str, ...] = ("h2", "h3")):
    nodes = response.xpath("|".join(f"//{tag}" for tag in tags))
    labels_norm = [_strip_accents_lower(lbl) for lbl in labels]
    for node in nodes:
        txt = _normalize_space(" ".join(node.xpath(".//text()").getall()))
        txt_norm = _strip_accents_lower(txt)
        if any(lbl in txt_norm for lbl in labels_norm):
            return node
    return None


def _extract_section_between_markers(
    response: Response,
    *,
    start_labels: list[str],
    stop_labels: list[str],
) -> str:
    """
    Extrait le texte entre 2 sections (ex: "Détails de l'annonce" -> "Postulez en 1 minute").
    """
    start_node = _find_heading_node(response, start_labels, tags=("h2", "h3"))
    if not start_node:
        return ""

    parts: list[str] = []
    for sibling in start_node.xpath("following-sibling::*"):
        sib_heading_texts = [
            _normalize_space(" ".join(h.xpath(".//text()").getall()))
            for h in sibling.xpath("self::h1|self::h2|self::h3|.//h1|.//h2|.//h3")
        ]
        sib_heading_norm = " ".join(_strip_accents_lower(t) for t in sib_heading_texts if t)
        if any(_strip_accents_lower(stop) in sib_heading_norm for stop in stop_labels):
            break

        if sibling.xpath("self::form|.//form"):
            # Le formulaire "Postulez en 1 minute" marque la fin de la description utile.
            break

        txt = _node_text(sibling)
        if not txt:
            continue
        # Exclure les blocs company/sidebar/partage usuels.
        low = _strip_accents_lower(txt)
        if any(k in low for k in ("postulez en 1 minute", "autres offres", "partager", "facebook", "linkedin", "twitter")):
            break
        parts.append(txt)

    return _normalize_space(" ".join(parts))


def _extract_description(response: Response) -> str:
    desc = _extract_section_between_markers(
        response,
        start_labels=["Détails de l'annonce", "Details de l'annonce"],
        stop_labels=["Postulez en 1 minute", "Postuler", "Resume du poste"],
    )
    if desc and len(desc) >= 120:
        return desc

    # Fallback structurel si les titres changent.
    fallback = css_all_text(response, selectors.JOB_DESCRIPTION)
    if fallback:
        # Supprime le bruit du formulaire s'il est concaténé.
        fallback = re.split(r"Postulez en 1 minute", fallback, flags=re.IGNORECASE)[0]
        return _normalize_space(fallback)
    return ""


def _extract_summary_lis(response: Response) -> List[str]:
    """
    Recupere les <li> du bloc "Resume du poste", avec heuristiques anti-bruit.
    """
    lines: List[str] = []
    summary_heading = _find_heading_node(response, ["Résumé du poste", "Resume du poste"], tags=("h2", "h3"))
    if summary_heading:
        scope = summary_heading.xpath("ancestor::*[self::section or self::div or self::article][1]")
        if scope:
            for li in scope[0].xpath(".//li"):
                txt = _normalize_space(" ".join(li.xpath(".//text()").getall()))
                if txt:
                    lines.append(txt)

    if not lines:
        # Fallback global.
        for li in response.xpath("//main//li"):
            txt = _normalize_space(" ".join(li.xpath(".//text()").getall()))
            if txt:
                lines.append(txt)

    blacklist = {
        "civilite",
        "prenom",
        "nom",
        "email",
        "telephone",
        "cv",
        "message personnalise",
        "postulez",
        "envoyer candidature",
    }
    filtered: List[str] = []
    seen = set()
    for line in lines:
        norm = _strip_accents_lower(line)
        if not line or len(line) < 2:
            continue
        if any(b in norm for b in blacklist):
            continue
        if line in seen:
            continue
        seen.add(line)
        filtered.append(line)
    return filtered


def _extract_labeled_value(lines: List[str], labels: List[str]) -> Optional[str]:
    labels_lower = [_strip_accents_lower(label) for label in labels]
    for line in lines:
        lower = _strip_accents_lower(line)
        if not any(label in lower for label in labels_lower):
            continue
        if ":" in line:
            value = _normalize_space(line.split(":", 1)[1])
            if value:
                return value
        return line
    return None


def _infer_summary_fields(lines: List[str]) -> dict:
    """
    Heuristiques pour les 5 items fixes du resume (etudes, experience, contrat, region, competences).
    """
    data = {
        "education": None,
        "experience": None,
        "contract_type": None,
        "location": None,
        "skills_text": None,
    }

    # 1) labels explicites si presents
    data["education"] = _extract_labeled_value(lines, ["niveau d'études", "niveau d'etudes", "diplome"])
    data["experience"] = _extract_labeled_value(lines, ["niveau d'expérience", "niveau d'experience", "experience"])
    data["contract_type"] = _extract_labeled_value(lines, ["type de contrat", "contrat proposé", "contrat propose"])
    data["location"] = _extract_labeled_value(lines, ["région", "region", "localisation", "ville"])
    data["skills_text"] = _extract_labeled_value(lines, ["compétences clés", "competences cles", "compétences", "competences"])

    # 2) fallback heuristique par contenu
    for line in lines:
        low = _strip_accents_lower(line)
        if not data["contract_type"] and any(k in low for k in ("cdi", "cdd", "stage", "freelance", "interim", "consultant", "temps plein", "temps partiel")):
            data["contract_type"] = line
        if not data["experience"] and any(k in low for k in ("an", "ans", "debutant", "experience")):
            data["experience"] = line
        if not data["education"] and any(k in low for k in ("bac", "licence", "master", "doctorat", "bts", "bt", "niveau")):
            data["education"] = line
        if not data["location"] and any(k in low for k in ("lome", "lomé", "togo", "region", "région", "kara", "sokode", "sokodé")):
            data["location"] = line

    # 3) fallback positionnel (audit: 5 items fixes)
    if lines:
        vals = [l for l in lines if len(l) <= 200]
        if not data["education"] and len(vals) >= 1:
            data["education"] = vals[0]
        if not data["experience"] and len(vals) >= 2:
            data["experience"] = vals[1]
        if not data["contract_type"] and len(vals) >= 3:
            data["contract_type"] = vals[2]
        if not data["location"] and len(vals) >= 4:
            data["location"] = vals[3]
        if not data["skills_text"] and len(vals) >= 5:
            data["skills_text"] = vals[4]

    return data


def _extract_deadline(description: str) -> Optional[str]:
    if not description:
        return None
    patterns = [
        r"(?:date limite|avant le|au plus tard le)\s*[:\-]?\s*([^\n\.;]{4,80})",
        r"(?:deadline)\s*[:\-]?\s*([^\n\.;]{4,80})",
    ]
    for pattern in patterns:
        m = re.search(pattern, description, re.IGNORECASE)
        if m:
            return _normalize_space(m.group(1))
    return None


def _extract_company(response: Response) -> Optional[str]:
    company = css_first(response, selectors.JOB_COMPANY)
    if company:
        return _normalize_space(company)

    # Fallback: bloc "Entreprise"
    enterprise_heading = _find_heading_node(response, ["Entreprise"], tags=("h2", "h3"))
    if enterprise_heading:
        for node in enterprise_heading.xpath("following-sibling::*"):
            txt = _node_text(node)
            if txt and len(txt) > 1:
                low = _strip_accents_lower(txt)
                if "autres offres" in low:
                    continue
                return txt
    return None


def _has_internal_apply_form(response: Response) -> bool:
    form_xpath = (
        "//form[.//input[@type='email' or contains(translate(@name,'EMAIL','email'),'email')]]"
        "[.//input[@type='tel' or contains(translate(@name,'TELPHONE','telphone'),'tel') or contains(translate(@name,'TELEPHONE','telephone'),'telephone')]]"
    )
    return bool(response.xpath(form_xpath).get())


def _has_apply_button(response: Response) -> bool:
    button_xpath = (
        "//button[contains(normalize-space(.), 'Postuler') "
        "or contains(normalize-space(.), 'postuler') "
        "or contains(normalize-space(.), 'POSTULER')]"
    )
    return bool(response.xpath(button_xpath).get())


def parse_skills(skills_text: Optional[str]) -> List[str]:
    """
    Extrait liste des competences.
    """
    if skills_text:
        cleaned = re.sub(r"^(comp[ée]tences?\s*(cl[ée]s?)?\s*:?)+", "", skills_text, flags=re.I).strip()
        return [s.strip() for s in re.split(r"[,/;|-]", cleaned) if s and s.strip()]
    return []


def parse_job_data(response: Response) -> dict:
    """
    Parse les donnees d'une offre emploi.tg.
    """
    summary_lines = _extract_summary_lis(response)
    summary = _infer_summary_fields(summary_lines)
    posted_iso, posted_text = _extract_posted_date(response)
    description = _extract_description(response)
    company = _extract_company(response)
    has_form = _has_internal_apply_form(response)
    has_button = _has_apply_button(response)

    apply_instructions = None
    apply_method = None
    if has_form:
        apply_method = "internal_form"
        apply_instructions = "Candidature via formulaire Emploi.tg (Postulez en 1 minute)"
    elif has_button:
        apply_instructions = "Bouton Postuler detecte sur la page detail Emploi.tg"

    # Champs de debug/qualite pour audit data.
    extra_data = {
        "emploi_tg_has_apply_form": has_form,
        "emploi_tg_has_apply_button": has_button,
        "emploi_tg_summary_lines": summary_lines[:8] if summary_lines else None,
        "date_source": "time_datetime" if posted_iso else ("time_text" if posted_text else "missing"),
    }

    return {
        "title": _normalize_space(css_first(response, selectors.JOB_TITLE) or ""),
        "company": company,
        "location": summary.get("location") or css_first(response, selectors.JOB_LOCATION),
        "description": description,
        "contract_type": summary.get("contract_type") or css_first(response, selectors.JOB_CONTRACT),
        "experience": summary.get("experience") or css_first(response, selectors.JOB_EXPERIENCE),
        "education": summary.get("education") or css_first(response, selectors.JOB_EDUCATION),
        # On renvoie directement un ISO si present; le normalizer le conservera dans posted_date_iso.
        "posted_date": posted_iso or posted_text,
        "posted_date_raw": posted_text or posted_iso,
        "skills": parse_skills(summary.get("skills_text") or css_first(response, selectors.JOB_SKILLS)),
        "category": None,
        "salary": None,
        "deadline": _extract_deadline(description),
        "apply_method": apply_method,
        "apply_instructions": apply_instructions,
        # Formulaire interne => pas de contact direct detecte dans l'audit.
        "apply_url": None,
        "contact_email": None,
        "contact_phone": None,
        "recruiter_name": None,
        "extra_data": {k: v for k, v in extra_data.items() if v is not None},
    }
