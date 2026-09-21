# Fingerprinting de site - Apprentissage structurel automatique
# Analyse les premieres pages d'un site, apprend les patterns CSS,
# puis les reutilise pour toutes les pages suivantes du meme domaine

from typing import Dict, Optional, List
from urllib.parse import urlparse

from scrapy.http import HtmlResponse

from .utils import normalize_text


# Cache global des fingerprints par domaine
_site_cache: Dict[str, "SiteFingerprint"] = {}


class SiteFingerprint:
    """
    Empreinte structurelle d'un site.
    Stocke les selecteurs CSS qui ont fonctionne pour chaque champ.
    """

    def __init__(self, domain: str):
        self.domain = domain
        # Selecteurs appris {champ: [selecteur, nb_succes]}
        self.learned: Dict[str, List[tuple]] = {}
        self.pages_analyzed = 0

    def record_success(self, field: str, selector: str):
        """Enregistre qu'un selecteur a fonctionne pour un champ."""
        if field not in self.learned:
            self.learned[field] = []
        for i, (sel, count) in enumerate(self.learned[field]):
            if sel == selector:
                self.learned[field][i] = (sel, count + 1)
                return
        self.learned[field].append((selector, 1))

    def get_best_selector(self, field: str) -> Optional[str]:
        """Retourne le selecteur le plus fiable pour un champ."""
        entries = self.learned.get(field, [])
        if not entries:
            return None
        # Trier par nombre de succes decroissant
        entries.sort(key=lambda x: x[1], reverse=True)
        return entries[0][0]

    def get_all_selectors(self, field: str) -> List[str]:
        """Retourne tous les selecteurs connus pour un champ, tries par fiabilite."""
        entries = self.learned.get(field, [])
        entries.sort(key=lambda x: x[1], reverse=True)
        return [sel for sel, _ in entries]


def get_fingerprint(domain: str) -> SiteFingerprint:
    """Recupere ou cree le fingerprint d'un domaine."""
    clean = domain.replace("www.", "")
    if clean not in _site_cache:
        _site_cache[clean] = SiteFingerprint(clean)
    return _site_cache[clean]


def learn_from_page(response: HtmlResponse, extracted_data: dict):
    """
    Apprend les patterns structurels a partir d'une extraction reussie.
    Quand on trouve un titre via h1::text, on enregistre ce selecteur
    pour le reutiliser sur les prochaines pages du meme domaine.
    """
    domain = urlparse(response.url).netloc
    fp = get_fingerprint(domain)
    fp.pages_analyzed += 1

    # Pour chaque champ extrait, retrouver quel selecteur a fonctionne
    field_selectors = {
        "title": [
            "h1.entry-title::text", "h1.job-title::text", "h1.page-title::text",
            "h1::text", ".job-title::text", ".post-title::text",
        ],
        "company": [
            ".company-name::text", ".employer-name::text", ".recruteur a::text",
            ".recruteur::text", ".company::text",
        ],
        "location": [
            ".job-location::text", ".location::text", ".region::text",
            ".ville::text",
        ],
    }

    for field, selectors in field_selectors.items():
        value = extracted_data.get(field)
        if not value or value in ("Non precise", ""):
            continue
        for sel in selectors:
            found = response.css(sel).get()
            if found and normalize_text(found) == normalize_text(value):
                fp.record_success(field, sel)
                break


def extract_with_fingerprint(response: HtmlResponse, field: str) -> Optional[str]:
    """
    Tente d'extraire un champ en utilisant les selecteurs appris.
    Retourne None si aucun selecteur appris ne fonctionne.
    """
    domain = urlparse(response.url).netloc
    fp = get_fingerprint(domain)

    for sel in fp.get_all_selectors(field):
        result = response.css(sel).get()
        if result and len(result.strip()) > 1:
            return normalize_text(result)

    return None


def get_cache_stats() -> Dict[str, dict]:
    """Retourne les stats du cache de fingerprints pour monitoring."""
    stats = {}
    for domain, fp in _site_cache.items():
        stats[domain] = {
            "pages_analyzed": fp.pages_analyzed,
            "fields_learned": {
                field: len(entries)
                for field, entries in fp.learned.items()
            },
        }
    return stats
