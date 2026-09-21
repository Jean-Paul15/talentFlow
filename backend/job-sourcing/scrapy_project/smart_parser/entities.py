# Extraction d'entites nommees par regex avancees
# Emails, telephones, montants financiers, dates multi-format
# URLs, langues, references, adresses, nombre de postes
# Fonctionne sur n'importe quel texte sans selecteur CSS

import re
from typing import Optional, List, Dict


def extract_emails(text: str) -> List[str]:
    """Extrait toutes les adresses email du texte."""
    if not text:
        return []
    pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
    return list(set(re.findall(pattern, text)))


def extract_phones(text: str) -> List[str]:
    """
    Extrait les numeros de telephone.
    Formats Afrique : +228 90 XX XX XX, 00228 9X XX XX XX,
    90 XX XX XX, (228) 90-XX-XX-XX
    Formats internationaux : +33 X XX XX XX XX, +1-XXX-XXX-XXXX
    """
    if not text:
        return []
    patterns = [
        r'(?:\+|00)?\s*228\s*[\s.-]?\d{2}\s*[\s.-]?\d{2}\s*[\s.-]?\d{2}\s*[\s.-]?\d{2}',
        r'(?:\+|00)?\s*\d{3}\s*[\s.-]?\d{2}\s*[\s.-]?\d{2}\s*[\s.-]?\d{2}\s*[\s.-]?\d{2}',
        r'\b\d{2}\s*[\s.-]\d{2}\s*[\s.-]\d{2}\s*[\s.-]\d{2}\b',
        r'(?:\+|00)\d{1,3}[\s.-]?\d{1,4}[\s.-]?\d{2,4}[\s.-]?\d{2,4}[\s.-]?\d{0,4}',
        r'\(\d{3}\)\s*\d{3}[\s.-]?\d{4}',
    ]
    results = []
    for pat in patterns:
        matches = re.findall(pat, text)
        results.extend(m.strip() for m in matches if len(m.strip()) >= 8)
    return list(set(results))


def extract_urls(text: str) -> List[str]:
    """Extrait toutes les URLs du texte (http, https, www)."""
    if not text:
        return []
    pattern = r'https?://[^\s<>"\']+|www\.[^\s<>"\']+'
    urls = re.findall(pattern, text)
    # Nettoyer les fins d'URL (ponctuation trailing)
    cleaned = []
    for url in urls:
        url = url.rstrip(".,;:!?)>]}")
        if len(url) > 10:
            cleaned.append(url)
    return list(set(cleaned))


def extract_salary_amount(text: str) -> Optional[str]:
    """
    Extrait un montant financier avec devise.
    Formats : 500 000 FCFA, 200.000 XOF, 1500 EUR, $2000
    """
    if not text:
        return None
    patterns = [
        # FCFA / XOF avec separateurs
        r'(\d[\d\s.]*\d)\s*(?:FCFA|XOF|F\s*CFA)',
        r'(?:FCFA|XOF|F\s*CFA)\s*(\d[\d\s.]*\d)',
        # EUR / USD
        r'(\d[\d\s.]*\d)\s*(?:EUR|euros?|USD|\$)',
        r'(?:EUR|euros?|USD|\$)\s*(\d[\d\s.]*\d)',
        # Fourchette
        r'(\d[\d\s.]*\d\s*[-àa]\s*\d[\d\s.]*\d)\s*(?:FCFA|XOF|EUR)',
        # Generique avec "salaire" proche
        r'[Ss]alaire\s*:?\s*(\d[\d\s.]*\d[^\n]{0,20})',
    ]
    for pat in patterns:
        match = re.search(pat, text, re.IGNORECASE)
        if match:
            return match.group(0).strip()
    return None


def extract_date_flexible(text: str) -> Optional[str]:
    """
    Extrait une date dans de nombreux formats :
    - 15/01/2025, 15-01-2025
    - 15 janvier 2025, 15 janv. 2025
    - 2025-01-15 (ISO)
    - Il y a 3 jours, Publie le 15/01
    """
    if not text:
        return None

    # ISO
    m = re.search(r'\d{4}-\d{2}-\d{2}', text)
    if m:
        return m.group(0)

    # FR : JJ/MM/AAAA ou JJ-MM-AAAA
    m = re.search(r'\d{1,2}[/-]\d{1,2}[/-]\d{2,4}', text)
    if m:
        return m.group(0)

    # Mois en lettres
    mois = (
        r'(?:janvier|f[eé]vrier|mars|avril|mai|juin|juillet|'
        r'ao[uû]t|septembre|octobre|novembre|d[eé]cembre|'
        r'janv|f[eé]v|avr|juil|sept|oct|nov|d[eé]c)'
    )
    m = re.search(rf'\d{{1,2}}\s*{mois}\.?\s*\d{{2,4}}', text, re.IGNORECASE)
    if m:
        return m.group(0)

    # "Publie le ..."
    m = re.search(r'[Pp]ubli[eé]\s*(?:le)?\s*:?\s*(.{8,20})', text)
    if m:
        return m.group(1).strip()

    return None


def extract_experience_years(text: str) -> Optional[str]:
    """Extrait le nombre d'annees d'experience requis."""
    if not text:
        return None
    patterns = [
        r'(\d+)\s*(?:ans?|ann[eé]es?)\s*(?:d.exp[eé]rience)',
        r'[Ee]xp[eé]rience\s*:?\s*(\d+)\s*(?:ans?|ann[eé]es?)',
        r'(\d+)\s*(?:ans?)\s*(?:minimum|min\.?)',
        r'[Mm]inimum\s*(\d+)\s*(?:ans?)',
        r'(\d+)\s*(?:to|[àa])\s*(\d+)\s*(?:ans?|years?)',
        r'(\d+)\+?\s*(?:years?)\s*(?:of)?\s*(?:experience)',
    ]
    for pat in patterns:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            groups = [g for g in m.groups() if g]
            if len(groups) >= 2:
                return f"{groups[0]}-{groups[1]} ans"
            return f"{groups[0]} ans"
    return None


def extract_education_level(text: str) -> Optional[str]:
    """Detecte le niveau d'etudes requis."""
    if not text:
        return None
    patterns = [
        r'(BAC\s*\+\s*\d)',
        r'(Bac\s*\+\s*\d)',
        r'(BTS|DUT|DEUG|Licence|Master|Doctorat|PhD|MBA|Ing[eé]nieur)',
        r'(BEPC|CAP|BEP|DTS|DETS)',
        r'[Nn]iveau\s*(?:d.[eé]tudes?)?\s*:?\s*([^\n,.]+)',
    ]
    for pat in patterns:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            return m.group(1).strip() if m.lastindex else m.group(0).strip()
    return None


def extract_deadline(text: str) -> Optional[str]:
    """Extrait la date limite de candidature."""
    if not text:
        return None
    patterns = [
        r'[Dd]ate\s*limite\s*:?\s*(.{8,25})',
        r'[Dd][eé]lai\s*:?\s*(.{8,25})',
        r'[Aa]vant\s*le\s*(.{8,25})',
        r'[Cc]l[oô]ture\s*:?\s*(.{8,25})',
        r'[Dd]eadline\s*:?\s*(.{8,25})',
        r'[Ee]xpiry\s*:?\s*(.{8,25})',
        r'[Aa]pply\s*before\s*:?\s*(.{8,25})',
    ]
    for pat in patterns:
        m = re.search(pat, text)
        if m:
            raw = m.group(1).strip()
            # Essayer d'extraire une date de ce fragment
            date = extract_date_flexible(raw)
            return date or raw[:30]
    return None


def extract_languages(text: str) -> List[str]:
    """Detecte les langues requises dans l'offre."""
    if not text:
        return []
    lang_patterns = [
        r'(?:[Ff]ran[çc]ais|[Ee]nglish|[Aa]nglais|[Ee]spagnol|'
        r'[Pp]ortugais|[Aa]rabe|[Aa]llemand|[Cc]hinois|[Ii]talien|'
        r'[Ff]rench|[Ss]panish|[Gg]erman|[Pp]ortuguese|[Aa]rabic|'
        r'[Mm]andarin|[Jj]apanese|[Jj]aponais)',
    ]
    results = []
    for pat in lang_patterns:
        found = re.findall(pat, text)
        results.extend(found)
    return list(set(results))


def extract_reference(text: str) -> Optional[str]:
    """Extrait un numero de reference de l'offre."""
    if not text:
        return None
    patterns = [
        r'[Rr][eé]f[eé]rence\s*:?\s*([A-Z0-9][\w-]{2,20})',
        r'[Rr]ef\s*[\.:]\s*([A-Z0-9][\w-]{2,20})',
        r'[Nn]?[oO]?\s*(?:de\s*)?[Rr]ef\s*:?\s*([A-Z0-9][\w-]{2,20})',
        r'[Jj]ob\s*[Ii][Dd]\s*:?\s*([A-Z0-9][\w-]{2,20})',
        r'[Rr]equisition\s*:?\s*([A-Z0-9][\w-]{2,20})',
    ]
    for pat in patterns:
        m = re.search(pat, text)
        if m:
            return m.group(1).strip()
    return None


def extract_nb_positions(text: str) -> Optional[str]:
    """Extrait le nombre de postes ouverts."""
    if not text:
        return None
    patterns = [
        r'(\d+)\s*(?:postes?|places?)\s*(?:[àa]\s*pourvoir|disponibles?|ouverts?)',
        r'(?:recrut\w+|cherch\w+)\s*(\d+)\s*(?:personnes?|candidats?|profils?)',
        r'[Nn]ombre\s*(?:de\s*)?postes?\s*:?\s*(\d+)',
        r'(\d+)\s*(?:positions?|openings?|vacancies?)\s*(?:available)?',
    ]
    for pat in patterns:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            return m.group(1)
    return None


def extract_address(text: str) -> Optional[str]:
    """Extrait une adresse physique du texte."""
    if not text:
        return None
    patterns = [
        r'[Aa]dresse\s*:?\s*([^\n]{10,100})',
        r'[Ss]i[eè]ge\s*:?\s*([^\n]{10,100})',
        r'(?:BP|B\.?P\.?)\s*\d{2,6}[^\n]{0,50}',
        r'\d+[,\s]+(?:rue|avenue|boulevard|av\.|bd\.?)\s+[^\n]{5,80}',
    ]
    for pat in patterns:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            val = m.group(0).strip() if not m.lastindex else m.group(1).strip()
            if len(val) > 8:
                return val[:150]
    return None


def extract_all_entities(text: str) -> Dict:
    """
    Extrait toutes les entites detectables d'un texte.
    Retourne un dict avec les entites trouvees (cles absentes si rien).
    """
    result = {}

    emails = extract_emails(text)
    if emails:
        result["emails"] = emails

    phones = extract_phones(text)
    if phones:
        result["phones"] = phones

    urls = extract_urls(text)
    if urls:
        result["urls"] = urls

    salary = extract_salary_amount(text)
    if salary:
        result["salary"] = salary

    date = extract_date_flexible(text)
    if date:
        result["date"] = date

    experience = extract_experience_years(text)
    if experience:
        result["experience"] = experience

    education = extract_education_level(text)
    if education:
        result["education"] = education

    deadline = extract_deadline(text)
    if deadline:
        result["deadline"] = deadline

    languages = extract_languages(text)
    if languages:
        result["languages"] = languages

    reference = extract_reference(text)
    if reference:
        result["reference"] = reference

    nb_positions = extract_nb_positions(text)
    if nb_positions:
        result["nb_positions"] = nb_positions

    address = extract_address(text)
    if address:
        result["address"] = address

    return result
