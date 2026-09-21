# Registre centralise de tous les sites d'emploi
# Source unique de verite pour : spiders, deep_crawler, APIs, Airflow, Streamlit
# Ajouter un site = ajouter une entree dans registry_data_*.py
# Les fonctions d'acces sont dans registry_access.py

from typing import Any
from urllib.parse import urlparse

# Re-exporter les constantes pour compatibilite ascendante
from .registry_constants import (
    PRIORITY_HIGH, PRIORITY_MEDIUM, PRIORITY_LOW, PRIORITY_NIGHTLY,
    CRON_MAP, PRIORITY_LABELS, FREQUENCY_LABELS, SCHEDULE_HOURS,
)

# Importer les donnees par region geographique
from .registry_data_togo import SITES_TOGO
from .registry_data_ouest import SITES_AFRIQUE_OUEST
from .registry_data_ouest2 import SITES_AFRIQUE_OUEST_2
from .registry_data_central import SITES_AFRIQUE_CENTRALE_MAGHREB
from .registry_data_anglophone import SITES_AFRIQUE_ANGLOPHONE
from .registry_data_panafricain import SITES_PANAFRICAIN
from .registry_data_api import SITES_API


# -------------------------------------------------------------------
# Assemblage du registre complet depuis les modules regionaux
# -------------------------------------------------------------------

SITES_REGISTRY: dict[str, dict[str, Any]] = {}
SITES_REGISTRY.update(SITES_TOGO)
SITES_REGISTRY.update(SITES_AFRIQUE_OUEST)
SITES_REGISTRY.update(SITES_AFRIQUE_OUEST_2)
SITES_REGISTRY.update(SITES_AFRIQUE_CENTRALE_MAGHREB)
SITES_REGISTRY.update(SITES_AFRIQUE_ANGLOPHONE)
SITES_REGISTRY.update(SITES_PANAFRICAIN)
SITES_REGISTRY.update(SITES_API)


def _build_whitelist() -> list[str]:
    """Extrait les domaines de tous les sites du registre."""
    domains = set()
    for info in SITES_REGISTRY.values():
        parsed = urlparse(info["url"])
        domain = parsed.netloc.replace("www.", "")
        domains.add(domain)
    return sorted(domains)


# Whitelist construite automatiquement depuis les URLs du registre
EXTERNAL_DOMAINS_WHITELIST = _build_whitelist()


# -------------------------------------------------------------------
# Re-exporter les fonctions d'acces pour compatibilite
# Import retarde pour eviter les imports circulaires
# -------------------------------------------------------------------

from .registry_access import (  # noqa: E402
    get_all_sites,
    get_active_sites,
    get_sites_by_priority,
    get_spider_sites,
    get_deep_crawler_sites,
    get_api_sites,
    get_deep_crawler_urls,
    get_schedule_info,
    get_sites_for_spider,
    get_airflow_dag_config,
)
