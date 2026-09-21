# Extraction par proximite de labels dans le DOM
# Principe : trouver "Entreprise :" dans le HTML, prendre le texte adjacent
# SURPUISSANT : 8 methodes de detection, capture TOUT label:valeur du DOM
# Ne depend d'aucun selecteur CSS specifique

import re
from typing import Optional, List, Tuple, Dict

from scrapy.http import HtmlResponse

from .constants import JOB_KEYWORDS
from .utils import normalize_text


def extract_by_label(response: HtmlResponse, field: str) -> Optional[str]:
    """
    Extrait une valeur en cherchant un label dans le DOM.

    Strategie : pour chaque mot-cle du champ (ex: "entreprise", "societe"),
    chercher dans le HTML un element qui contient ce texte comme label,
    puis extraire le texte adjacent/sibling/enfant.

    Couvre les structures :
    - <dt>Entreprise</dt><dd>SOGO SA</dd>
    - <strong>Entreprise :</strong> SOGO SA
    - <span class="label">Lieu :</span><span class="value">Lome</span>
    - <tr><td>Contrat</td><td>CDI</td></tr>
    - <div>Lieu : Lome, Togo</div>
    - <h3>Entreprise</h3><p>SOGO SA</p>
    - <li><span>Entreprise</span>SOGO SA</li>
    - data-label="Lieu" -> valeur adjacente
    """
    keywords = JOB_KEYWORDS.get(field, [])
    if not keywords:
        return None

    for kw in keywords:
        # Methode 1 : dt/dd
        result = _extract_dt_dd(response, kw)
        if result:
            return result

        # Methode 2 : label:value dans un meme element
        result = _extract_inline_label(response, kw)
        if result:
            return result

        # Methode 3 : table tr>td
        result = _extract_table_row(response, kw)
        if result:
            return result

        # Methode 4 : element strong/b/label suivi d'un sibling
        result = _extract_strong_sibling(response, kw)
        if result:
            return result

        # Methode 5 : heading (h2, h3, h4) suivi de contenu
        result = _extract_heading_content(response, kw)
        if result:
            return result

        # Methode 6 : data-label ou aria-label
        result = _extract_data_label(response, kw)
        if result:
            return result

    return None


def extract_all_labeled_fields(response: HtmlResponse) -> dict:
    """
    Extrait tous les champs possibles par proximite de labels.
    Retourne un dict {field: value} des champs trouves.
    """
    results = {}
    for field in ["company", "location", "contract", "experience",
                  "education", "salary", "sector", "work_schedule"]:
        value = extract_by_label(response, field)
        if value:
            results[field] = value
    return results


# Champs deja geres par les extracteurs principaux (a ignorer dans le catch-all)
_KNOWN_FIELDS = {
    "entreprise", "societe", "recruteur", "employeur", "company",
    "lieu", "localisation", "ville", "location", "adresse",
    "contrat", "type de contrat", "contract", "employment type",
    "experience", "annees", "niveau d'experience",
    "etudes", "diplome", "formation", "education",
    "salaire", "remuneration", "salary", "compensation",
    "competences", "skills", "qualifications",
    "secteur", "domaine", "metier", "industry",
    "description", "missions", "responsabilites",
    "titre", "poste", "intitule", "title",
    "date", "publie", "published", "posted",
    "reference", "ref", "pays", "country", "region",
}

# Elements de navigation / boilerplate a ignorer dans le catch-all
_BOILERPLATE_LABELS = {
    "menu", "accueil", "home", "contact", "connexion", "login",
    "inscription", "register", "footer", "header", "navigation",
    "recherche", "search", "partager", "share", "suivez",
    "copyright", "mentions legales", "politique", "conditions",
    "cookies", "confidentialite", "newsletter", "abonnez",
}


def extract_all_unknown_labels(response: HtmlResponse) -> dict:
    """
    Capture SURPUISSANTE de TOUS les labels:valeur du DOM.

    Strategie "zero perte absolue" avec 8 methodes de detection :
    1. Paires dt/dd (listes de definition)
    2. Lignes de tableau (tr>td/th)
    3. Inline "Label : Valeur" (div, p, span, li, article, section)
    4. Strong/b/label avec valeur adjacente
    5. Heading (h2-h5) suivi de contenu textuel court
    6. Data-label / aria-label avec valeur
    7. Liste ul/ol avec sous-items
    8. Classe CSS contenant "label", "field", "info", "detail"
    """
    unknown: Dict[str, str] = {}

    # 1. Paires dt/dd
    for dt in response.css("dt"):
        label = normalize_text(dt.css("::text").get(""))
        if not label or len(label) < 2:
            continue
        if _is_known_label(label):
            continue
        dd = dt.xpath("following-sibling::dd[1]")
        if dd:
            val = normalize_text(" ".join(dd.css("::text").getall()))
            if val and len(val) > 1 and len(val) < 2000:
                unknown[_norm_label(label)] = val[:1000]

    # 2. Lignes de tableau (th+td et td+td)
    for tr in response.css("tr"):
        cells = tr.css("td, th")
        if len(cells) < 2:
            continue
        label = normalize_text(cells[0].css("::text").get(""))
        if not label or len(label) < 2 or _is_known_label(label):
            continue
        if _is_boilerplate(label):
            continue
        val = normalize_text(" ".join(cells[1].css("::text").getall()))
        if val and len(val) > 1 and len(val) < 2000:
            unknown[_norm_label(label)] = val[:1000]

    # 3. Inline "Label : Valeur" - elements elargis + limite augmentee
    label_pattern = re.compile(r'^([^:]{2,60})\s*:\s*(.{2,800})$')
    for el in response.css(
        "div, p, span, li, article, section, aside, figcaption, address"
    ):
        text = normalize_text(" ".join(el.css("::text").getall()))
        if not text or len(text) > 900 or len(text) < 4:
            continue
        match = label_pattern.match(text)
        if not match:
            continue
        label = match.group(1).strip()
        val = match.group(2).strip()
        if _is_known_label(label) or _is_boilerplate(label):
            continue
        if len(label) > 60 or len(label) < 2:
            continue
        if val and len(val) > 1:
            unknown[_norm_label(label)] = val[:1000]

    # 4. Strong/b/label/em avec valeur adjacente
    for tag in ("strong", "b", "label", "em", "mark"):
        for el in response.css(tag):
            label = normalize_text(el.css("::text").get(""))
            if not label or len(label) < 2 or len(label) > 60:
                continue
            clean = label.rstrip(" :")
            if _is_known_label(clean) or _is_boilerplate(clean):
                continue
            parent = el.xpath("..")
            if not parent:
                continue
            all_text = " ".join(parent.css("::text").getall())
            pat = re.compile(
                rf'{re.escape(clean)}\s*:?\s*(.+)', re.IGNORECASE,
            )
            m = pat.search(all_text)
            if m:
                val = normalize_text(m.group(1).split("\n")[0])
                if val and len(val) > 1 and val.lower() != clean.lower():
                    unknown[_norm_label(clean)] = val[:1000]

    # 5. Heading (h2-h5) suivi de contenu textuel court
    for heading_tag in ("h2", "h3", "h4", "h5"):
        for heading in response.css(heading_tag):
            label = normalize_text(heading.css("::text").get(""))
            if not label or len(label) < 3 or len(label) > 60:
                continue
            if _is_known_label(label) or _is_boilerplate(label):
                continue
            # Prendre le sibling suivant (p, div, span, ul)
            sibling = heading.xpath(
                "following-sibling::*[self::p or self::div or self::span"
                " or self::ul or self::ol][1]"
            )
            if sibling:
                val = normalize_text(" ".join(sibling.css("::text").getall()))
                if val and 2 < len(val) < 1500:
                    unknown[_norm_label(label)] = val[:1000]

    # 6. Attributs data-label / aria-label
    for el in response.css("[data-label], [aria-label]"):
        label = el.attrib.get("data-label") or el.attrib.get("aria-label", "")
        label = normalize_text(label)
        if not label or len(label) < 2 or _is_known_label(label):
            continue
        val = normalize_text(el.css("::text").get(""))
        if val and len(val) > 1 and len(val) < 2000:
            unknown[_norm_label(label)] = val[:1000]

    # 7. Listes ul/ol : si le premier <li> ressemble a un label
    for ul in response.css("ul, ol"):
        items = ul.css("li")
        if not items or len(items) < 2 or len(items) > 30:
            continue
        first = normalize_text(items[0].css("::text").get(""))
        if not first or ":" not in first:
            continue
        for li in items:
            li_text = normalize_text(" ".join(li.css("::text").getall()))
            if not li_text or ":" not in li_text or len(li_text) > 300:
                continue
            parts = li_text.split(":", 1)
            if len(parts) == 2:
                lbl = parts[0].strip()
                val = parts[1].strip()
                if lbl and val and not _is_known_label(lbl):
                    if 2 <= len(lbl) <= 60 and len(val) > 1:
                        unknown[_norm_label(lbl)] = val[:1000]

    # 8. Elements avec classes "label/field/info/detail"
    for el in response.css(
        "[class*='label'], [class*='field'], [class*='info'],"
        " [class*='detail'], [class*='meta']"
    ):
        classes = el.attrib.get("class", "")
        # Eviter les gros conteneurs
        text = normalize_text(" ".join(el.css("::text").getall()))
        if not text or len(text) > 200 or len(text) < 3:
            continue
        if ":" in text:
            parts = text.split(":", 1)
            lbl = parts[0].strip()
            val = parts[1].strip()
            if lbl and val and not _is_known_label(lbl):
                if 2 <= len(lbl) <= 60 and len(val) > 1:
                    unknown[_norm_label(lbl)] = val[:500]

    return unknown


def _is_known_label(label: str) -> bool:
    """Verifie si un label correspond a un champ deja gere."""
    low = label.lower().rstrip(" :")
    return any(known in low or low in known for known in _KNOWN_FIELDS)


def _is_boilerplate(label: str) -> bool:
    """Verifie si un label est du boilerplate de navigation/footer."""
    low = label.lower().rstrip(" :")
    return any(bl in low for bl in _BOILERPLATE_LABELS)


def _norm_label(label: str) -> str:
    """Normalise un label pour en faire une cle de dictionnaire propre."""
    clean = label.strip().rstrip(":").strip()
    # Remplacer espaces et caracteres speciaux par underscore
    clean = re.sub(r'[^a-zA-Z0-9àâäéèêëïîôùûüçÀÂÉÈÊËÏÎÔÙÛÜÇ]', '_', clean)
    clean = re.sub(r'_+', '_', clean).strip('_')
    return clean.lower()[:60]


def _extract_dt_dd(response: HtmlResponse, keyword: str) -> Optional[str]:
    """Cherche dans les paires <dt>label</dt><dd>valeur</dd>."""
    for dt in response.css("dt"):
        dt_text = dt.css("::text").get("")
        if keyword.lower() in dt_text.lower():
            # Le dd suivant
            dd = dt.xpath("following-sibling::dd[1]")
            if dd:
                val = " ".join(dd.css("::text").getall())
                val = normalize_text(val)
                if val and len(val) > 1:
                    return val
    return None


def _extract_inline_label(response: HtmlResponse, keyword: str) -> Optional[str]:
    """
    Cherche 'Label : Valeur' dans un meme element texte.
    Ex: <div>Lieu : Lome</div> ou <p>Contrat : CDI</p>
    """
    # Pattern regex : keyword suivi de : puis valeur
    pattern = re.compile(
        rf'{re.escape(keyword)}\s*:\s*(.+)',
        re.IGNORECASE,
    )

    # Chercher dans les elements de texte courts (pas les longs paragraphes)
    for el in response.css("div, p, span, li, td, th"):
        text = " ".join(el.css("::text").getall()).strip()
        if len(text) > 200:
            continue
        match = pattern.search(text)
        if match:
            val = normalize_text(match.group(1).split("\n")[0])
            if val and len(val) > 1:
                return val

    return None


def _extract_table_row(response: HtmlResponse, keyword: str) -> Optional[str]:
    """Cherche dans les lignes de tableau <tr><td>label</td><td>valeur</td></tr>."""
    for tr in response.css("tr"):
        tds = tr.css("td")
        if len(tds) < 2:
            continue
        label_text = tds[0].css("::text").get("")
        if keyword.lower() in label_text.lower():
            val = " ".join(tds[1].css("::text").getall())
            val = normalize_text(val)
            if val and len(val) > 1:
                return val

    # Aussi th/td
    for tr in response.css("tr"):
        ths = tr.css("th")
        tds = tr.css("td")
        if ths and tds:
            label_text = ths[0].css("::text").get("")
            if keyword.lower() in label_text.lower():
                val = " ".join(tds[0].css("::text").getall())
                val = normalize_text(val)
                if val and len(val) > 1:
                    return val

    return None


def _extract_strong_sibling(response: HtmlResponse, keyword: str) -> Optional[str]:
    """
    Cherche <strong>Label :</strong> Valeur
    ou <b>Label</b><span>Valeur</span>
    """
    for tag in ("strong", "b", "label", "em"):
        for el in response.css(tag):
            text = el.css("::text").get("")
            if keyword.lower() not in text.lower():
                continue

            # Texte apres le tag dans le parent
            parent = el.xpath("..")
            if not parent:
                continue
            all_text = " ".join(parent.css("::text").getall())
            # Retirer le label lui-meme
            pattern = re.compile(
                rf'{re.escape(keyword)}\s*:?\s*(.+)',
                re.IGNORECASE,
            )
            match = pattern.search(all_text)
            if match:
                val = normalize_text(match.group(1).split("\n")[0])
                if val and len(val) > 1 and val.lower() != keyword.lower():
                    return val

    return None


def _extract_heading_content(
    response: HtmlResponse, keyword: str,
) -> Optional[str]:
    """
    Cherche un heading (h2-h5) contenant le mot-cle,
    puis extrait le contenu du sibling suivant.
    Ex: <h3>Entreprise</h3><p>SOGO SA</p>
    """
    for level in ("h2", "h3", "h4", "h5"):
        for heading in response.css(level):
            text = heading.css("::text").get("")
            if keyword.lower() not in text.lower():
                continue
            sibling = heading.xpath(
                "following-sibling::*[self::p or self::div or self::span"
                " or self::ul or self::ol][1]"
            )
            if sibling:
                val = normalize_text(" ".join(sibling.css("::text").getall()))
                if val and len(val) > 1 and len(val) < 500:
                    return val
    return None


def _extract_data_label(
    response: HtmlResponse, keyword: str,
) -> Optional[str]:
    """
    Cherche les elements avec data-label ou aria-label contenant le mot-cle.
    Ex: <span data-label="Lieu">Lome</span>
    """
    for attr in ("data-label", "aria-label"):
        for el in response.css(f"[{attr}]"):
            label_val = el.attrib.get(attr, "")
            if keyword.lower() not in label_val.lower():
                continue
            val = normalize_text(el.css("::text").get(""))
            if val and len(val) > 1:
                return val
    return None
