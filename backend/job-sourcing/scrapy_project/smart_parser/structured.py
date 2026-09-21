# Extraction de donnees structurees embeddees dans le HTML
# JSON-LD (schema.org), microdata, Open Graph, meta tags, Twitter Cards
# Source la plus fiable car les sites eux-memes declarent leurs donnees
# Strategie ZERO PERTE : capture TOUS les champs, pas seulement les prevus

import json
import re
from typing import Optional, Dict, List

from scrapy.http import HtmlResponse

from .utils import normalize_text


# Cles JSON-LD principales deja mappees (ignorees dans le catch-all)
_JSONLD_MAIN_KEYS = {
    "title", "name", "jobtitle", "description", "dateposted",
    "publishdate", "employmenttype", "basesalary", "estimatedsalary",
    "industry", "occupationalcategory", "hiringorganization",
    "employer", "company", "joblocation", "location", "skills",
    "qualifications", "@type", "@context", "@id", "@graph",
    "validthrough", "directapply", "url", "sameas",
    "jobbenefits", "benefits", "workhours", "specialcommitments",
    "experiencerequirements", "educationrequirements",
    "responsibilities", "totaljobobenings", "joblocationtype",
    "applicantlocationrequirements", "applicationcontact",
}


def extract_jsonld(response: HtmlResponse) -> Optional[Dict]:
    """
    Extrait les donnees JSON-LD schema.org d'une page.
    Capture TOUS les champs, y compris les inattendus.
    """
    scripts = response.css('script[type="application/ld+json"]::text').getall()

    for raw in scripts:
        try:
            data = json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            continue

        if isinstance(data, list):
            for item in data:
                result = _parse_jobposting(item)
                if result:
                    return result
        elif isinstance(data, dict):
            result = _parse_jobposting(data)
            if result:
                return result
            for item in data.get("@graph", []):
                result = _parse_jobposting(item)
                if result:
                    return result

    return None


def extract_all_jsonld_raw(response: HtmlResponse) -> List[Dict]:
    """
    Capture BRUTE de tous les blocs JSON-LD de la page.
    Aucun filtrage -- stocke tout pour ne rien perdre.
    """
    results = []
    scripts = response.css('script[type="application/ld+json"]::text').getall()
    for raw in scripts:
        try:
            data = json.loads(raw)
            if isinstance(data, list):
                results.extend(data)
            elif isinstance(data, dict):
                results.append(data)
        except (json.JSONDecodeError, TypeError):
            continue
    return results


def extract_opengraph(response: HtmlResponse) -> Dict[str, str]:
    """Extrait TOUTES les metadonnees Open Graph + Twitter Cards."""
    og = {}
    for meta in response.css("meta[property^='og:']"):
        prop = meta.attrib.get("property", "").replace("og:", "")
        content = meta.attrib.get("content", "")
        if prop and content:
            og[prop] = normalize_text(content)
    # Twitter cards
    for meta in response.css("meta[name^='twitter:']"):
        prop = meta.attrib.get("name", "").replace("twitter:", "tw_")
        content = meta.attrib.get("content", "")
        if prop and content:
            og[prop] = normalize_text(content)
    return og


def extract_meta_tags(response: HtmlResponse) -> Dict[str, str]:
    """Extrait TOUTES les meta tags utiles (pas seulement description/keywords)."""
    meta = {}
    for tag in response.css("meta[name]"):
        name = tag.attrib.get("name", "").lower()
        content = tag.attrib.get("content", "")
        if name and content and len(content) < 1000:
            meta[name] = normalize_text(content)
    # Meta property (non-OG)
    for tag in response.css("meta[property]"):
        prop = tag.attrib.get("property", "").lower()
        content = tag.attrib.get("content", "")
        if prop and content and not prop.startswith("og:") and len(content) < 1000:
            meta[prop] = normalize_text(content)
    return meta


def extract_microdata(response: HtmlResponse) -> Optional[Dict]:
    """
    Extrait les microdata HTML5 (itemtype/itemprop).
    Capture TOUS les itemprop, pas seulement les prevus.
    """
    job_scope = response.css('[itemtype*="JobPosting"]')
    if not job_scope:
        job_scope = response.css('[itemtype*="jobposting"]')
    if not job_scope:
        return None

    scope = job_scope[0]
    result = {}

    prop_map = {
        "title": ["title", "name", "jobTitle"],
        "company": ["hiringOrganization", "employer", "company"],
        "location": ["jobLocation", "location", "addressLocality"],
        "description": ["description"],
        "date": ["datePosted", "publishDate"],
        "salary": ["baseSalary", "salary", "estimatedSalary"],
        "contract": ["employmentType", "contractType"],
        "skills": ["skills", "qualifications"],
        "sector": ["industry", "occupationalCategory"],
    }

    mapped_props = set()
    for field, props in prop_map.items():
        for prop in props:
            mapped_props.add(prop)
            el = scope.css(f'[itemprop="{prop}"]')
            if el:
                val = el.attrib.get("content", "") or el.css("::text").get("")
                if val.strip():
                    result[field] = normalize_text(val)
                    break

    # Capturer TOUS les itemprop non mappes (zero perte)
    extra_micro = {}
    for el in scope.css("[itemprop]"):
        prop_name = el.attrib.get("itemprop", "")
        if not prop_name or prop_name in mapped_props:
            continue
        val = el.attrib.get("content", "") or el.css("::text").get("")
        if val and val.strip() and len(val.strip()) < 500:
            extra_micro[prop_name] = normalize_text(val)

    if extra_micro:
        result["_extra_microdata"] = extra_micro

    return result if (result.get("title") or extra_micro) else None


def merge_structured_data(response: HtmlResponse) -> Dict:
    """
    Fusionne TOUTES les sources de donnees structurees.
    Priorite : JSON-LD > Microdata > OpenGraph > Meta.
    Strategie ZERO PERTE : toutes les donnees capturees sont transmises.
    """
    merged = {}

    # 1. Meta tags (priorite basse mais tout capturer)
    meta = extract_meta_tags(response)
    if meta:
        merged["meta"] = meta
        if meta.get("description"):
            merged["meta_description"] = meta["description"]
        if meta.get("keywords"):
            merged["meta_keywords"] = meta["keywords"]

    # 2. Open Graph + Twitter Cards
    og = extract_opengraph(response)
    if og:
        merged["opengraph"] = og
        if og.get("title"):
            merged["og_title"] = og["title"]
        if og.get("description"):
            merged["og_description"] = og["description"]

    # 3. Microdata
    micro = extract_microdata(response)
    if micro:
        merged["microdata"] = micro

    # 4. JSON-LD (priorite max)
    jsonld = extract_jsonld(response)
    if jsonld:
        merged["jsonld"] = jsonld

    # 5. JSON-LD brut complet (pour ne RIEN perdre)
    raw_jsonld = extract_all_jsonld_raw(response)
    if raw_jsonld:
        merged["jsonld_raw"] = raw_jsonld

    return merged


def _parse_jobposting(data: dict) -> Optional[Dict]:
    """
    Convertit un objet JSON-LD JobPosting en dict normalise.
    Capture TOUS les champs, y compris les inattendus.
    """
    schema_type = data.get("@type", "")
    if isinstance(schema_type, list):
        schema_type = " ".join(schema_type)
    if "jobposting" not in schema_type.lower() and "job" not in schema_type.lower():
        return None

    result = {
        "title": _safe_get(data, "title", "name", "jobTitle"),
        "description": _safe_get(data, "description"),
        "date": _safe_get(data, "datePosted", "publishDate"),
        "contract": _safe_get(data, "employmentType"),
        "salary": _extract_salary_jsonld(data),
        "sector": _safe_get(data, "industry", "occupationalCategory"),
    }

    # Organisation embauchant
    org = data.get("hiringOrganization", {})
    if isinstance(org, dict):
        result["company"] = org.get("name", "")
        org_url = org.get("sameAs") or org.get("url")
        if org_url:
            result["company_url"] = str(org_url)
    elif isinstance(org, str):
        result["company"] = org

    # Localisation detaillee
    loc = data.get("jobLocation", {})
    if isinstance(loc, dict):
        addr = loc.get("address", loc)
        if isinstance(addr, dict):
            parts = [
                addr.get("addressLocality", ""),
                addr.get("addressRegion", ""),
                addr.get("addressCountry", ""),
            ]
            result["location"] = ", ".join(p for p in parts if p)
            geo = loc.get("geo", {})
            if isinstance(geo, dict):
                lat = geo.get("latitude")
                lon = geo.get("longitude")
                if lat and lon:
                    result["geo_coordinates"] = f"{lat},{lon}"
        else:
            result["location"] = str(addr)
    elif isinstance(loc, str):
        result["location"] = loc
    elif isinstance(loc, list):
        locations = []
        for l_item in loc:
            if isinstance(l_item, dict):
                addr = l_item.get("address", l_item)
                if isinstance(addr, dict):
                    parts = [
                        addr.get("addressLocality", ""),
                        addr.get("addressRegion", ""),
                    ]
                    locations.append(", ".join(p for p in parts if p))
                else:
                    locations.append(str(addr))
            else:
                locations.append(str(l_item))
        result["location"] = " | ".join(locations)

    # Skills depuis qualifications
    skills_raw = _safe_get(data, "skills", "qualifications")
    if skills_raw:
        result["skills_raw"] = skills_raw

    # Champs enrichis schema.org souvent ignores
    _enrich_from_jsonld(data, result)

    # Capturer TOUS les champs JSON-LD non mappes (catch-all)
    extra_jsonld = {}
    for key, val in data.items():
        if key.startswith("@"):
            continue
        if key.lower() in _JSONLD_MAIN_KEYS:
            continue
        if val is not None and val != "" and val != []:
            extra_jsonld[key] = _serialize_value(val)

    if extra_jsonld:
        result["_extra_jsonld"] = extra_jsonld

    return {k: v for k, v in result.items() if v} or None


def _enrich_from_jsonld(data: dict, result: dict):
    """
    Extrait les champs schema.org enrichis souvent ignores.
    Chaque champ ajoute de l'information precieuse.
    """
    # Date limite / expiration de l'offre
    valid_through = _safe_get(data, "validThrough")
    if valid_through:
        result["deadline"] = valid_through

    # URL de candidature
    apply_url = _safe_get(data, "url", "sameAs")
    if apply_url and apply_url.startswith("http"):
        result["apply_url_jsonld"] = apply_url

    # Avantages du poste
    benefits = _safe_get(data, "jobBenefits", "benefits")
    if benefits:
        result["benefits"] = benefits

    # Horaires de travail
    work_hours = _safe_get(data, "workHours", "specialCommitments")
    if work_hours:
        result["work_hours"] = work_hours

    # Experience requise
    exp_req = data.get("experienceRequirements", {})
    if isinstance(exp_req, dict):
        months = exp_req.get("monthsOfExperience")
        if months:
            try:
                years = int(months) // 12
                result["experience"] = f"{years} ans" if years else f"{months} mois"
            except (ValueError, TypeError):
                result["experience"] = str(months)
    elif isinstance(exp_req, str) and exp_req.strip():
        result["experience"] = normalize_text(exp_req)

    # Education requise
    edu_req = data.get("educationRequirements", {})
    if isinstance(edu_req, dict):
        level = edu_req.get("credentialCategory", "")
        if level:
            result["education"] = normalize_text(str(level))
    elif isinstance(edu_req, str) and edu_req.strip():
        result["education"] = normalize_text(edu_req)

    # Responsabilites
    resp = _safe_get(data, "responsibilities")
    if resp:
        result["responsibilities"] = resp

    # Nombre de postes
    total = _safe_get(data, "totalJobOpenings")
    if total:
        result["total_openings"] = total

    # Teletravail
    remote = _safe_get(data, "jobLocationType", "applicantLocationRequirements")
    if remote:
        result["remote_type"] = remote

    # Contact pour candidature
    contact = data.get("applicationContact", {})
    if isinstance(contact, dict):
        c_email = contact.get("email", "")
        c_phone = contact.get("telephone", "")
        c_name = contact.get("name", "")
        if c_email:
            result["contact_email"] = c_email
        if c_phone:
            result["contact_phone"] = c_phone
        if c_name:
            result["contact_name"] = c_name


def _safe_get(data: dict, *keys: str) -> str:
    """Recupere la premiere valeur non vide parmi les cles."""
    for key in keys:
        val = data.get(key)
        if val:
            if isinstance(val, dict):
                val = val.get("name", val.get("value", str(val)))
            if isinstance(val, list):
                val = ", ".join(str(v) for v in val)
            return normalize_text(str(val))
    return ""


def _serialize_value(val) -> str:
    """Serialise une valeur JSON-LD en texte lisible."""
    if isinstance(val, str):
        return val.strip()
    if isinstance(val, (int, float, bool)):
        return str(val)
    if isinstance(val, list):
        parts = [_serialize_value(v) for v in val]
        return " | ".join(p for p in parts if p)
    if isinstance(val, dict):
        if "name" in val:
            return str(val["name"])
        try:
            return json.dumps(val, ensure_ascii=False, separators=(",", ":"))
        except (TypeError, ValueError):
            return str(val)
    return str(val)


def _extract_salary_jsonld(data: dict) -> str:
    """Extrait le salaire depuis la structure JSON-LD."""
    salary = data.get("baseSalary", data.get("estimatedSalary"))
    if not salary:
        return ""
    if isinstance(salary, str):
        return salary
    if isinstance(salary, dict):
        currency = salary.get("currency", "")
        unit = salary.get("unitText", "")
        value = salary.get("value", "")
        if isinstance(value, dict):
            min_val = value.get("minValue", "")
            max_val = value.get("maxValue", "")
            base = ""
            if min_val and max_val:
                base = f"{min_val}-{max_val}"
            else:
                base = str(min_val or max_val)
            parts = [p for p in [base, currency, unit] if p]
            return " ".join(parts)
        parts = [p for p in [str(value), currency, unit] if p]
        return " ".join(parts)
    if isinstance(salary, list):
        parts = []
        for s in salary:
            val = _extract_salary_jsonld({"baseSalary": s})
            if val:
                parts.append(val)
        return " | ".join(parts)
    return ""
