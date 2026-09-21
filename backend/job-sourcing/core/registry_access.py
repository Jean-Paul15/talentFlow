# Registre des fonctions d'acces aux sites du registre
# Fonctions d'interrogation par priorite, spider, pays, etc.

import os
from typing import Any

from .registry_constants import (
    PRIORITY_HIGH, PRIORITY_MEDIUM, PRIORITY_LOW, PRIORITY_NIGHTLY,
    CRON_MAP, PRIORITY_LABELS, FREQUENCY_LABELS, SCHEDULE_HOURS,
)
from .orchestration_settings import (
    get_dag_enabled_by_priority,
    get_orchestration_settings,
    get_priority_cron_map,
)

# Mode strict: n'autoriser que les sites avec spider dedie + APIs.
# Cela desactive les sites "deep_crawler" (sans dossier spider propre).
DEDICATED_SPIDERS_ONLY = os.getenv(
    "DEDICATED_SPIDERS_ONLY", "true",
).lower() in {"1", "true", "yes", "on"}


def _get_registry() -> dict[str, dict[str, Any]]:
    """Charge le registre complet depuis les modules de donnees."""
    # Import local pour eviter les imports circulaires
    from .sites_registry import SITES_REGISTRY
    return SITES_REGISTRY


def _with_registry_defaults(site_id: str, info: dict[str, Any]) -> dict[str, Any]:
    item = dict(info)
    source_type = str(item.get("source") or "scraping").strip().lower() or "scraping"
    pays = str(item.get("pays") or "").strip()
    api_provider = str(item.get("api_provider") or "").strip().lower()

    if "freshness_ttl_days" not in item:
        if source_type == "api":
            if api_provider in {"remoteok", "remotive", "hackernews", "arbeitnow", "jsearch"}:
                item["freshness_ttl_days"] = 21
            else:
                item["freshness_ttl_days"] = 30
        elif pays.lower() == "togo":
            item["freshness_ttl_days"] = 45
        else:
            item["freshness_ttl_days"] = 30

    item.setdefault("source_type", source_type)
    item.setdefault("schedule_priority", item.get("priority"))
    item.setdefault("country_bias", pays or "International")
    item.setdefault("supports_deadline", source_type != "api")
    item.setdefault("supports_apply_url", True)
    item.setdefault(
        "extraction_hints",
        {
            "location": "title,url,body",
            "date": "explicit_label_or_posted_date",
            "apply": "apply_url,apply_email,body",
        },
    )
    item.setdefault("registry_site_id", site_id)
    return item


def _is_enabled_site(info: dict[str, Any]) -> bool:
    """
    Verifie si un site est actif selon le mode courant.

    En mode dedie (par defaut):
    - scraping: spider dedie obligatoire
    - api: toujours autorise (si active=True)
    """
    if not info.get("active", True):
        return False

    if not DEDICATED_SPIDERS_ONLY:
        return True

    if info.get("source") == "api":
        return True

    return bool(info.get("spider"))


def get_all_sites() -> dict[str, dict[str, Any]]:
    """Retourne les sites autorises selon le mode courant."""
    return {
        k: _with_registry_defaults(k, v)
        for k, v in _get_registry().items()
        if _is_enabled_site(v)
    }


def get_active_sites() -> dict[str, dict[str, Any]]:
    """Retourne uniquement les sites actifs."""
    return get_all_sites()


def get_sites_by_priority(priority: int) -> dict[str, dict[str, Any]]:
    """Filtre les sites actifs par niveau de priorite."""
    return {
        k: v for k, v in get_all_sites().items()
        if v["priority"] == priority
    }


def get_spider_sites() -> dict[str, dict[str, Any]]:
    """Sites actifs avec un spider dedie (non deep_crawler, non API)."""
    return {
        k: v for k, v in get_all_sites().items()
        if v["spider"] is not None
        and v.get("source", "scraping") == "scraping"
    }


def get_deep_crawler_sites() -> dict[str, dict[str, Any]]:
    """Sites actifs crawles par deep_crawler (sans spider dedie)."""
    if DEDICATED_SPIDERS_ONLY:
        return {}

    return {
        k: v for k, v in get_all_sites().items()
        if v["spider"] is None
    }


def get_api_sites() -> dict[str, dict[str, Any]]:
    """Sites actifs collectes via APIs (JSearch, Adzuna, etc.)."""
    return {
        k: v for k, v in get_all_sites().items()
        if v.get("source") == "api"
    }


def get_deep_crawler_urls() -> list[str]:
    """URLs a passer au deep_crawler (sites actifs sans spider dedie)."""
    return [v["url"] for v in get_deep_crawler_sites().values()]


def get_schedule_info() -> list[dict[str, Any]]:
    """
    Retourne les informations d'orchestration pour chaque site.
    Format compatible Streamlit / API.
    """
    cron_map = get_priority_cron_map()
    schedule = get_orchestration_settings().get("priority_schedule", {})
    result = []
    for site_id, info in get_all_sites().items():
        priority = info["priority"]
        schedule_info = schedule.get(str(priority), {})
        result.append({
            "site_id": site_id,
            "label": info["label"],
            "url": info["url"],
            "pays": info["pays"],
            "category": info["category"],
            "spider": info["spider"] or "deep_crawler",
            "priority": priority,
            "priority_label": PRIORITY_LABELS[priority],
            "frequency": schedule_info.get("frequency", FREQUENCY_LABELS[priority]),
            "cron": cron_map.get(priority, CRON_MAP[priority]),
            "hours": schedule_info.get("hours", SCHEDULE_HOURS[priority]),
        })
    return result


def get_sites_for_spider(spider_name: str) -> list[str]:
    """
    Retourne les URLs a scraper pour un spider donne.
    Pour deep_crawler : tous les sites sans spider dedie.
    Pour un spider dedie : son URL unique.
    """
    if spider_name == "deep_crawler":
        return get_deep_crawler_urls()
    for _site_id, info in get_all_sites().items():
        if info["spider"] == spider_name:
            return [info["url"]]
    return []


def get_airflow_dag_config() -> dict[int, dict[str, Any]]:
    """
    Genere la configuration des DAGs Airflow depuis le registre.
    Retourne un dict par priorite avec les spiders a lancer.
    """
    registry = get_all_sites()
    cron_map = get_priority_cron_map()
    enabled_by_priority = get_dag_enabled_by_priority()
    dag_config = {}
    for priority in [PRIORITY_HIGH, PRIORITY_MEDIUM, PRIORITY_LOW, PRIORITY_NIGHTLY]:
        sites = {
            k: v for k, v in registry.items()
            if v["priority"] == priority
        }
        spiders_set = set()
        deep_crawler_urls = []
        for _site_id, info in sites.items():
            if info["spider"]:
                spiders_set.add(info["spider"])
            else:
                deep_crawler_urls.append(info["url"])

        if deep_crawler_urls:
            spiders_set.add("deep_crawler")

        dag_config[priority] = {
            "cron": cron_map.get(priority, CRON_MAP[priority]),
            "label": PRIORITY_LABELS[priority],
            "spiders": sorted(spiders_set),
            "deep_crawler_urls": deep_crawler_urls,
            "total_sites": len(sites),
            "enabled": enabled_by_priority.get(priority, True),
        }
    return dag_config
