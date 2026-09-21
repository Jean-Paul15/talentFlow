# Collecteur central API : orchestre les providers actives du registre
# Publie les resultats dans Kafka avec deduplication Redis.

from datetime import datetime
from typing import Any, Dict, List, Optional

from loguru import logger

from core.kafka_producer import KafkaJobProducer
from core.job_normalizer import compute_job_fingerprint, normalize_job_record
from core.redis_client import RedisFingerprint
from core.sites_registry import get_api_sites

from .sources import (
    AdzunaClient,
    ArbeitnowClient,
    GitHubJobsLegacyClient,
    HackerNewsClient,
    JoinDataClient,
    JSearchClient,
    RemotiveClient,
    RemoteOkClient,
)


DEFAULT_JSEARCH_QUERIES = [
    "emploi",
    "recrutement",
    "stage",
    "developer",
    "data",
]
DEFAULT_ADZUNA_QUERY = "emploi"


def run_api_collection(source_ids: Optional[List[str]] = None) -> int:
    """
    Execute la collecte depuis les APIs actives du registre.
    Si source_ids est fourni, la collecte est limitee a ces sources.

    Returns:
        Nombre total d'offres publiees dans Kafka.
    """
    api_sites = get_api_sites()
    selected_sites = _select_sites(api_sites, source_ids)
    if not selected_sites:
        logger.warning("Collecte API ignoree: aucune source active selectionnee")
        return 0

    redis = RedisFingerprint()
    producer = KafkaJobProducer()
    clients: Dict[str, Any] = {}

    total_collected = 0
    total_duplicates = 0
    total_published = 0

    logger.info(
        f"Demarrage collecte API sur {len(selected_sites)} source(s): "
        f"{', '.join(sorted(selected_sites.keys()))}"
    )

    for site_id, site_info in selected_sites.items():
        provider = _resolve_provider(site_id, site_info)
        client = _get_client(provider, clients)
        if client is None:
            logger.warning(f"Provider API inconnu pour {site_id}: {provider}")
            continue

        try:
            jobs = _collect_jobs_for_site(provider, client, site_id, site_info)
        except Exception as err:
            logger.error(f"Erreur collecte {site_id} ({provider}): {err}")
            continue

        total_collected += len(jobs)

        for job in jobs:
            result = _publish_job(job, site_id, redis, producer)
            if result == "published":
                total_published += 1
            elif result == "duplicate":
                total_duplicates += 1

    producer.flush()
    producer.close()

    logger.info(
        f"Collecte API terminee: "
        f"{total_collected} trouvees, "
        f"{total_published} publiees, "
        f"{total_duplicates} doublons"
    )
    return total_published


def _select_sites(
    api_sites: Dict[str, Dict[str, Any]],
    source_ids: Optional[List[str]],
) -> Dict[str, Dict[str, Any]]:
    if not source_ids:
        return api_sites

    selected = {}
    for source_id in source_ids:
        if source_id in api_sites:
            selected[source_id] = api_sites[source_id]
    return selected


def _resolve_provider(site_id: str, site_info: Dict[str, Any]) -> str:
    provider = str(site_info.get("api_provider", "")).strip().lower()
    if provider:
        return provider

    if site_id.startswith("jsearch"):
        return "jsearch"
    if site_id.startswith("adzuna"):
        return "adzuna"
    if site_id.startswith("remoteok"):
        return "remoteok"
    if site_id.startswith("hackernews"):
        return "hackernews"
    if site_id.startswith("joindata"):
        return "joindata"
    if site_id.startswith("github_jobs"):
        return "github_jobs_legacy"
    if site_id.startswith("remotive"):
        return "remotive"
    if site_id.startswith("arbeitnow"):
        return "arbeitnow"
    return site_id.lower()


def _get_client(provider: str, cache: Dict[str, Any]) -> Optional[Any]:
    if provider in cache:
        return cache[provider]

    if provider == "jsearch":
        cache[provider] = JSearchClient()
    elif provider == "adzuna":
        cache[provider] = AdzunaClient()
    elif provider == "remoteok":
        cache[provider] = RemoteOkClient()
    elif provider == "hackernews":
        cache[provider] = HackerNewsClient()
    elif provider == "joindata":
        cache[provider] = JoinDataClient()
    elif provider == "github_jobs_legacy":
        cache[provider] = GitHubJobsLegacyClient()
    elif provider == "remotive":
        cache[provider] = RemotiveClient()
    elif provider == "arbeitnow":
        cache[provider] = ArbeitnowClient()
    else:
        return None

    return cache[provider]


def _collect_jobs_for_site(
    provider: str,
    client: Any,
    site_id: str,
    site_info: Dict[str, Any],
) -> List[Dict]:
    if provider == "jsearch":
        return _collect_jsearch(client, site_info)
    if provider == "adzuna":
        return _collect_adzuna(client, site_id, site_info)
    if provider == "remoteok":
        return client.fetch_jobs(limit=100)
    if provider == "hackernews":
        return client.fetch_jobs(limit=100)
    if provider == "joindata":
        keyword = site_info.get("query", "python")
        return client.search_jobs(keyword=keyword, limit=30)
    if provider == "github_jobs_legacy":
        return client.search_jobs()
    if provider == "remotive":
        return client.fetch_jobs(limit=100)
    if provider == "arbeitnow":
        return client.fetch_jobs(limit=100)
    return []


def _collect_jsearch(client: JSearchClient, site_info: Dict[str, Any]) -> List[Dict]:
    # JSearch global: pas de filtre pays par defaut.
    location = str(site_info.get("location_filter", "")).strip()
    jobs: List[Dict] = []
    for query in DEFAULT_JSEARCH_QUERIES:
        jobs.extend(
            client.search_jobs(
                query=query,
                location=location,
                num_pages=1,
            )
        )
    return _deduplicate_local(jobs)


def _collect_adzuna(
    client: AdzunaClient, site_id: str, site_info: Dict[str, Any]
) -> List[Dict]:
    country = str(site_info.get("adzuna_country") or _infer_adzuna_country(site_id))
    query = str(site_info.get("query", DEFAULT_ADZUNA_QUERY))
    return client.search_jobs(
        what=query,
        country=country,
        results_per_page=30,
        page=1,
    )


def _infer_adzuna_country(site_id: str) -> str:
    if site_id.endswith("_za"):
        return "za"
    return "fr"


def _deduplicate_local(jobs: List[Dict]) -> List[Dict]:
    seen = set()
    unique = []
    for job in jobs:
        normalize_job_record(job)
        dedup_key = compute_job_fingerprint(job)
        if dedup_key in seen:
            continue
        seen.add(dedup_key)
        unique.append(job)
    return unique


def _publish_job(
    job: Dict,
    site_prefix: str,
    redis: RedisFingerprint,
    producer: KafkaJobProducer,
) -> str:
    """
    Publie une offre dans Kafka apres deduplication Redis.

    Returns:
        "published", "duplicate" ou "error"
    """
    normalize_job_record(job, source_name=site_prefix)

    # Calculer fingerprint
    fingerprint = _compute_fingerprint(job)
    if redis.exists(fingerprint):
        return "duplicate"

    # Enrichir l'item
    job["fingerprint"] = fingerprint
    job["hash"] = fingerprint
    job["scraped_at"] = datetime.now().isoformat()

    # Prefixe logique base sur la source du registre
    job["source_site"] = site_prefix

    # Publier dans Kafka
    success = producer.send_job(site_prefix, job)
    if success:
        redis.add(fingerprint, {"url": job.get("source_url", "")})
        return "published"
    return "error"


def _compute_fingerprint(job: Dict) -> str:
    """Calcule le fingerprint SHA256 d'une offre (meme algorithme que le pipeline)."""
    return compute_job_fingerprint(job)
