# Moteur principal du SmartParser
# Orchestre 5 niveaux d'extraction par priorite :
# Niveau 0 (cache) : Fingerprint - selecteurs appris du site
# Niveau 1 (fiable) : JSON-LD / schema.org / microdata
# Niveau 2 (puissant) : Proximite de labels dans le DOM
# Niveau 3 (fallback) : Selecteurs CSS generiques + regex texte
# Niveau 4 (enrichissement) : Entites nommees (email, tel, montants)
# + Catch-all : capture TOUT ce qui n'est pas dans les champs prevus
# Strategie ZERO PERTE ABSOLUE : rien n'est jamais perdu

from typing import Optional, Dict
from urllib.parse import urlparse

from scrapy.http import HtmlResponse

from .fingerprint import extract_with_fingerprint, learn_from_page
from .structured import merge_structured_data
from .proximity import extract_all_labeled_fields, extract_all_unknown_labels
from .entities import extract_all_entities, extract_salary_amount
from .extractors import (
    smart_extract_title,
    smart_extract_company,
    smart_extract_location,
    smart_extract_description,
    smart_extract_contract,
    smart_extract_date,
    smart_extract_skills,
    smart_extract_salary,
    smart_extract_sector,
    smart_extract_work_schedule,
)
from .detectors import detect_apply_url, detect_recruiter_name
from .utils import looks_like_job_page, detect_country, get_body_text


def smart_parse(response: HtmlResponse, source_name: str = "") -> Optional[Dict]:
    """
    Parse intelligent 5 niveaux + catch-all zero perte absolue.

    Niveau 0 : Fingerprint (selecteurs appris de ce site)
    Niveau 1 : Donnees structurees (JSON-LD, microdata, Open Graph, Meta)
    Niveau 2 : Labels dans le DOM ("Entreprise :", "Lieu :", etc.)
    Niveau 3 : Selecteurs CSS generiques + heuristiques regex
    Niveau 4 : Entites nommees (emails, telephones, montants, dates,
               URLs, langues, references, adresses, nb postes)
    Catch-all : Tous les labels:valeur non prevus dans extra_data

    Chaque champ utilise la meilleure source disponible.
    Retourne None si la page ne ressemble pas a une offre.
    """
    # Niveau 0 : Fingerprint (selecteurs appris)
    fp_title = extract_with_fingerprint(response, "title")
    fp_company = extract_with_fingerprint(response, "company")
    fp_location = extract_with_fingerprint(response, "location")

    # Niveau 1 : Donnees structurees (TOUTES les sources)
    structured = merge_structured_data(response)
    jsonld = structured.get("jsonld", {})
    micro = structured.get("microdata", {})
    og = structured.get("opengraph", {})
    meta = structured.get("meta", {})

    # Niveau 2 : Labels DOM
    labeled = extract_all_labeled_fields(response)

    # Titre : fingerprint > JSON-LD > microdata > OG > selecteur CSS
    title = _best(
        fp_title,
        jsonld.get("title"),
        micro.get("title"),
        og.get("title"),
        smart_extract_title(response),
    )
    if not title or len(title) < 3:
        return None

    # Description : JSON-LD > OG > meta > selecteur CSS
    description = _best(
        jsonld.get("description"),
        og.get("description"),
        structured.get("og_description"),
        structured.get("meta_description"),
        smart_extract_description(response),
    )

    # Heuristique de validation
    if not looks_like_job_page(title, description, response.url):
        return None

    full_text = description or ""

    # Niveau 4 : Entites nommees depuis le texte complet du body
    body_text = get_body_text(response, max_elements=800)
    entities = extract_all_entities(body_text)

    # URL de candidature (detecteur + JSON-LD)
    apply_url = (
        detect_apply_url(response)
        or jsonld.get("apply_url_jsonld")
    )

    # Nom du recruteur/cabinet
    recruiter = (
        detect_recruiter_name(response)
        or jsonld.get("contact_name")
    )

    # Fusionner les 5 niveaux : champ par champ
    result = {
        "title": title,
        "company": _best(
            fp_company,
            jsonld.get("company"),
            micro.get("company"),
            labeled.get("company"),
            smart_extract_company(response),
            default="Non precise",
        ),
        "location": _best(
            fp_location,
            jsonld.get("location"),
            micro.get("location"),
            labeled.get("location"),
            smart_extract_location(response),
            entities.get("address"),
            default="Non precise",
        ),
        "description": description,
        "contract_type": _best(
            jsonld.get("contract"),
            micro.get("contract"),
            labeled.get("contract"),
            smart_extract_contract(response, full_text),
        ),
        "sector": _best(
            jsonld.get("sector"),
            micro.get("sector"),
            labeled.get("sector"),
            smart_extract_sector(response, full_text),
        ),
        "salary": _best(
            jsonld.get("salary"),
            micro.get("salary"),
            labeled.get("salary"),
            smart_extract_salary(full_text),
            entities.get("salary"),
        ),
        "posted_date": _best(
            jsonld.get("date"),
            micro.get("date"),
            smart_extract_date(response),
            entities.get("date"),
        ),
        "skills": smart_extract_skills(response, full_text),
        "source_url": response.url,
        "source_name": source_name or urlparse(response.url).netloc,
        "country": detect_country(response, full_text),
        # Lien de candidature
        "apply_url": apply_url,
        # Recruteur/cabinet
        "recruiter_name": recruiter,
    }

    # Enrichissement par entites
    if entities.get("emails"):
        result["contact_email"] = entities["emails"][0]
        if len(entities["emails"]) > 1:
            result["all_emails"] = entities["emails"]
    # Email JSON-LD (plus fiable, ecrase si present)
    if jsonld.get("contact_email"):
        result["contact_email"] = jsonld["contact_email"]

    if entities.get("phones"):
        result["contact_phone"] = entities["phones"][0]
        if len(entities["phones"]) > 1:
            result["all_phones"] = entities["phones"]
    if jsonld.get("contact_phone"):
        result["contact_phone"] = jsonld["contact_phone"]

    # Experience : JSON-LD > labels DOM > entites
    result["experience"] = _best(
        jsonld.get("experience"),
        labeled.get("experience"),
        entities.get("experience"),
    )
    # Education : JSON-LD > labels DOM > entites
    result["education"] = _best(
        jsonld.get("education"),
        labeled.get("education"),
        entities.get("education"),
    )
    # Regime horaire : labels DOM > selecteurs CSS
    result["work_schedule"] = _best(
        labeled.get("work_schedule"),
        smart_extract_work_schedule(response, full_text),
    )
    # Deadline : JSON-LD > entites
    result["deadline"] = _best(
        jsonld.get("deadline"),
        entities.get("deadline"),
    )

    # Catch-all SURPUISSANT : capturer TOUT ce qui n'est pas dans les champs
    extra = {}

    # 1. Labels DOM inconnus (proximite)
    unknown_fields = extract_all_unknown_labels(response)
    if unknown_fields:
        extra.update(unknown_fields)

    # 2. Champs JSON-LD enrichis non mappes en champs principaux
    _merge_jsonld_extras(jsonld, extra)

    # 3. Microdata extras
    micro_extra = micro.get("_extra_microdata", {}) if micro else {}
    if micro_extra:
        for k, v in micro_extra.items():
            extra[f"micro_{k}"] = v

    # 4. Entites supplementaires (URLs, langues, reference, adresse, nb postes)
    _merge_entity_extras(entities, extra)

    # 5. Open Graph / Twitter Cards non utilises
    _merge_og_extras(og, extra)

    # 6. Meta tags inattendus
    _merge_meta_extras(meta, extra)

    # 7. JSON-LD brut complet (pour archivage zero perte)
    raw_jsonld = structured.get("jsonld_raw")
    if raw_jsonld:
        extra["_jsonld_raw"] = raw_jsonld

    if extra:
        result["extra_data"] = extra

    # Apprentissage : enregistrer les selecteurs qui ont marche
    learn_from_page(response, result)

    return result


def _merge_jsonld_extras(jsonld: dict, extra: dict):
    """Injecte dans extra les champs JSON-LD enrichis non mappes."""
    if not jsonld:
        return
    # Champs enrichis du schema.org
    _inject(extra, "benefits", jsonld.get("benefits"))
    _inject(extra, "work_hours", jsonld.get("work_hours"))
    _inject(extra, "responsibilities", jsonld.get("responsibilities"))
    _inject(extra, "total_openings", jsonld.get("total_openings"))
    _inject(extra, "remote_type", jsonld.get("remote_type"))
    _inject(extra, "company_url", jsonld.get("company_url"))
    _inject(extra, "geo_coordinates", jsonld.get("geo_coordinates"))
    _inject(extra, "skills_raw", jsonld.get("skills_raw"))
    # Champs JSON-LD inconnus captures par le catch-all
    jsonld_extra = jsonld.get("_extra_jsonld", {})
    if jsonld_extra:
        for k, v in jsonld_extra.items():
            extra[f"jsonld_{k}"] = v


def _merge_entity_extras(entities: dict, extra: dict):
    """Injecte dans extra les entites non utilisees en champs principaux."""
    _inject(extra, "urls_detectees", entities.get("urls"))
    _inject(extra, "langues_requises", entities.get("languages"))
    _inject(extra, "reference_offre", entities.get("reference"))
    _inject(extra, "adresse_physique", entities.get("address"))
    _inject(extra, "nb_postes", entities.get("nb_positions"))


def _merge_og_extras(og: dict, extra: dict):
    """Injecte dans extra les meta OG/Twitter non utilises."""
    if not og:
        return
    # Champs OG utiles hors titre/description
    _inject(extra, "og_image", og.get("image"))
    _inject(extra, "og_site_name", og.get("site_name"))
    _inject(extra, "og_type", og.get("type"))
    _inject(extra, "og_url", og.get("url"))
    _inject(extra, "og_locale", og.get("locale"))
    # Twitter Cards
    _inject(extra, "tw_card", og.get("tw_card"))
    _inject(extra, "tw_site", og.get("tw_site"))
    _inject(extra, "tw_image", og.get("tw_image"))


def _merge_meta_extras(meta: dict, extra: dict):
    """Injecte les meta tags inattendus dans extra."""
    if not meta:
        return
    # Ignorer les meta standards deja utilisees
    skip = {"description", "keywords", "viewport", "charset", "robots",
            "generator", "theme-color", "format-detection"}
    for k, v in meta.items():
        if k.lower() in skip:
            continue
        if k.startswith("og:") or k.startswith("twitter:"):
            continue
        extra[f"meta_{k}"] = v


def _inject(target: dict, key: str, value):
    """Injecte une valeur dans extra si elle est non vide."""
    if not value:
        return
    if isinstance(value, list):
        val = " | ".join(str(v) for v in value)
        if val:
            target[key] = val
    elif isinstance(value, dict):
        target[key] = value
    else:
        target[key] = str(value)


def _best(*values, default: str = None) -> Optional[str]:
    """Retourne la premiere valeur non vide ou le defaut."""
    for v in values:
        if v and str(v).strip():
            return str(v).strip()
    return default
