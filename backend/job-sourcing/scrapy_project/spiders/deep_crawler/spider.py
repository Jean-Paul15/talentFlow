# Spider adaptatif recursif en profondeur
# Capable de crawler n'importe quel site d'emploi sans selecteurs codes en dur
# Suit les liens externes (recruteurs, sites de candidature)
# Detecte automatiquement les offres d'emploi via heuristiques
# Decouvre les sitemaps et flux RSS pour acces direct aux URLs

import os
import scrapy
from urllib.parse import urlparse
from scrapy_project.items import JobItem
from scrapy_project.smart_parser import (
    smart_parse,
    detect_job_links,
    detect_pagination_links,
    detect_external_apply_links,
    normalize_text,
)
from scrapy_project.smart_parser.sitemap import (
    discover_sitemap_urls,
    parse_sitemap_xml,
    filter_job_urls_from_sitemap,
    discover_rss_feeds,
    parse_rss_feed,
)
from core.sites_registry import (
    get_deep_crawler_urls,
    EXTERNAL_DOMAINS_WHITELIST as REGISTRY_WHITELIST,
)


def _build_default_sites():
    """Construit la liste des URLs depuis le registre de sites."""
    return get_deep_crawler_urls()


# Domaines autorises pour le suivi de liens externes (recruteurs)
# Fusionne les domaines du registre + ceux ajoutes manuellement
EXTERNAL_DOMAINS_WHITELIST = list(set(
    REGISTRY_WHITELIST + [
        "majorel.com", "africatalents.com",
        "careers.un.org", "reliefweb.int",
    ]
))

# Meme drapeau que core/registry_access.py
DEDICATED_SPIDERS_ONLY = os.getenv(
    "DEDICATED_SPIDERS_ONLY", "true",
).lower() in {"1", "true", "yes", "on"}


class DeepCrawlerSpider(scrapy.Spider):
    """
    Spider intelligent et adaptatif.

    Parcourt les sites d'emploi en profondeur :
    - Detecte automatiquement les liens d'offres via heuristiques
    - Suit les liens de pagination automatiquement
    - Traverse les domaines externes (liens 'Postuler')
    - Parse le contenu sans selecteurs CSS codes en dur
    - Gere les structures HTML inconnues

    Usage:
        scrapy crawl deep_crawler
        scrapy crawl deep_crawler -a sites="https://example.com/jobs"
        scrapy crawl deep_crawler -a max_depth=5
    """

    name = "deep_crawler"

    custom_settings = {
        "DOWNLOAD_DELAY": 1.5,
        "CONCURRENT_REQUESTS_PER_DOMAIN": 3,
        "DEPTH_LIMIT": 30,
        "DOWNLOAD_TIMEOUT": 20,
        # Pas de restriction de domaine
        "OFFSITE_ENABLED": False,
        # Encodage UTF-8 force
        "FEED_EXPORT_ENCODING": "utf-8",
    }

    def __init__(self, sites=None, max_depth=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if sites:
            self.start_urls = [s.strip() for s in sites.split(",")]
        else:
            self.start_urls = _build_default_sites()

        if max_depth:
            self.custom_settings["DEPTH_LIMIT"] = int(max_depth)

        # Tracking des URLs visitees
        self._visited = set()
        # Domaines dont le sitemap a deja ete explore
        self._sitemapped = set()
        # Domaines externes autorises
        self._allowed_external = set(EXTERNAL_DOMAINS_WHITELIST)

        self.logger.info(
            f"DeepCrawler initialise: {len(self.start_urls)} sites, "
            f"profondeur max {self.custom_settings['DEPTH_LIMIT']}"
        )

    def start_requests(self):
        """
        Point d'entree des requetes initiales.
        En mode dedie, le deep_crawler est explicitement desactive.
        """
        if DEDICATED_SPIDERS_ONLY:
            self.logger.warning(
                "DeepCrawler desactive (mode spiders dedies uniquement)."
            )
            return

        for url in self.start_urls:
            yield scrapy.Request(url, callback=self.parse)

    def parse(self, response):
        """
        Point d'entree : analyse chaque page et decide quoi faire.
        """
        url = response.url
        if url in self._visited:
            return
        self._visited.add(url)

        response = self._ensure_utf8(response)
        self.logger.info(f"Crawl: {url}")

        # 0. Decouvrir sitemap/RSS du domaine (une seule fois par domaine)
        domain = urlparse(url).netloc
        if domain not in self._sitemapped:
            self._sitemapped.add(domain)
            yield from self._discover_feeds(response)

        # 1. Tenter de parser comme offre d'emploi
        job_data = smart_parse(response, source_name=self._get_source_name(url))
        if job_data and job_data.get("title"):
            yield self._build_item(job_data)

            # Suivre les liens 'Postuler' vers des sites externes
            for apply_url in detect_external_apply_links(response):
                if apply_url not in self._visited:
                    self.logger.info(f"Suivi lien candidature externe: {apply_url}")
                    yield scrapy.Request(
                        apply_url,
                        callback=self.parse_external,
                        meta={"source_url": url},
                        dont_filter=True,
                    )

        # 2. Detecter et suivre les liens d'offres
        for job_url in detect_job_links(response):
            if job_url not in self._visited:
                yield scrapy.Request(
                    job_url,
                    callback=self.parse_job_page,
                    dont_filter=True,
                )

        # 3. Suivre la pagination
        for page_url in detect_pagination_links(response):
            if page_url not in self._visited:
                yield scrapy.Request(
                    page_url,
                    callback=self.parse,
                    dont_filter=True,
                )

    def parse_job_page(self, response):
        """Parse une page identifiee comme offre d'emploi."""
        url = response.url
        if url in self._visited:
            return
        self._visited.add(url)

        response = self._ensure_utf8(response)

        job_data = smart_parse(response, source_name=self._get_source_name(url))
        if job_data and job_data.get("title"):
            yield self._build_item(job_data)

            # Suivre les liens 'Postuler' vers des sites externes
            for apply_url in detect_external_apply_links(response):
                if apply_url not in self._visited:
                    domain = urlparse(apply_url).netloc
                    self.logger.info(f"Suivi externe ({domain}): {apply_url}")
                    yield scrapy.Request(
                        apply_url,
                        callback=self.parse_external,
                        meta={"source_url": url},
                        dont_filter=True,
                    )

    def parse_external(self, response):
        """
        Parse une page externe (site recruteur comme tpcareer.com).
        Crawle aussi les offres trouvees sur ce site.
        """
        url = response.url
        if url in self._visited:
            return
        self._visited.add(url)

        response = self._ensure_utf8(response)

        domain = urlparse(url).netloc
        self.logger.info(f"Crawl externe ({domain}): {url}")

        # Parser comme offre
        job_data = smart_parse(response, source_name=domain)
        if job_data and job_data.get("title"):
            yield self._build_item(job_data)

        # Detecter d'autres offres sur ce site externe
        for job_url in detect_job_links(response):
            link_domain = urlparse(job_url).netloc
            # Rester sur le meme domaine externe ou domaines whitelistes
            if (link_domain == domain or link_domain in self._allowed_external):
                if job_url not in self._visited:
                    yield scrapy.Request(
                        job_url,
                        callback=self.parse_external,
                        dont_filter=True,
                    )

        # Pagination du site externe
        for page_url in detect_pagination_links(response):
            link_domain = urlparse(page_url).netloc
            if link_domain == domain and page_url not in self._visited:
                yield scrapy.Request(
                    page_url,
                    callback=self.parse_external,
                    dont_filter=True,
                )

    def _build_item(self, job_data: dict) -> JobItem:
        """Construit un JobItem depuis les donnees parsees."""
        item = JobItem()
        item["title"] = normalize_text(job_data.get("title", ""))
        item["company"] = normalize_text(job_data.get("company", "Non precise"))
        item["location"] = normalize_text(job_data.get("location", "Non precise"))
        item["description"] = normalize_text(job_data.get("description", ""))
        item["source_url"] = job_data.get("source_url", "")
        item["source_name"] = job_data.get("source_name", "deep_crawler")
        item["country"] = job_data.get("country", "Afrique")
        item["sector"] = job_data.get("sector")
        item["contract_type"] = job_data.get("contract_type")
        item["salary"] = job_data.get("salary")
        item["skills"] = job_data.get("skills", [])
        item["posted_date"] = job_data.get("posted_date")
        # Champs enrichis par le SmartParser
        item["contact_email"] = job_data.get("contact_email")
        item["contact_phone"] = job_data.get("contact_phone")
        item["experience"] = job_data.get("experience")
        item["education"] = job_data.get("education")
        item["deadline"] = job_data.get("deadline")
        # Lien de candidature et recruteur
        item["apply_url"] = job_data.get("apply_url")
        item["recruiter_name"] = job_data.get("recruiter_name")
        item["work_schedule"] = job_data.get("work_schedule")
        # Catch-all : donnees imprevues du DOM
        item["extra_data"] = job_data.get("extra_data", {})
        return item

    def _get_source_name(self, url: str) -> str:
        """Extrait un nom de source depuis l'URL."""
        domain = urlparse(url).netloc
        # Retirer www. et .com/.org/.info etc.
        name = domain.replace("www.", "")
        return name

    def _ensure_utf8(self, response):
        """Force l'encodage UTF-8 sur la reponse."""
        if hasattr(response, "encoding") and response.encoding:
            if response.encoding.lower() not in ("utf-8", "utf8"):
                self.logger.debug(
                    f"Encodage detecte: {response.encoding} -> force UTF-8"
                )
        return response

    def _discover_feeds(self, response):
        """Decouvre et suit les sitemaps et flux RSS d'un domaine."""
        # Sitemaps
        for sitemap_url in discover_sitemap_urls(response):
            if sitemap_url not in self._visited:
                self._visited.add(sitemap_url)
                yield scrapy.Request(
                    sitemap_url,
                    callback=self._parse_sitemap,
                    errback=self._feed_error,
                    dont_filter=True,
                    meta={"handle_httpstatus_list": [404, 403, 500]},
                )

        # RSS
        for rss_url in discover_rss_feeds(response):
            if rss_url not in self._visited:
                self._visited.add(rss_url)
                yield scrapy.Request(
                    rss_url,
                    callback=self._parse_rss,
                    errback=self._feed_error,
                    dont_filter=True,
                    meta={"handle_httpstatus_list": [404, 403, 500]},
                )

    def _parse_sitemap(self, response):
        """Parse un sitemap XML et suit les URLs d'offres."""
        if response.status != 200:
            return
        urls = parse_sitemap_xml(response)
        job_urls = filter_job_urls_from_sitemap(urls)
        self.logger.info(
            f"Sitemap {response.url}: {len(urls)} URLs, {len(job_urls)} offres"
        )

        # Sous-sitemaps (sitemap index)
        for url in urls:
            if "sitemap" in url.lower() and url.endswith(".xml"):
                if url not in self._visited:
                    self._visited.add(url)
                    yield scrapy.Request(
                        url,
                        callback=self._parse_sitemap,
                        errback=self._feed_error,
                        dont_filter=True,
                    )

        # URLs d'offres
        for url in job_urls:
            if url not in self._visited:
                yield scrapy.Request(
                    url,
                    callback=self.parse_job_page,
                    dont_filter=True,
                )

    def _parse_rss(self, response):
        """Parse un flux RSS et suit les URLs des articles."""
        if response.status != 200:
            return
        urls = parse_rss_feed(response)
        self.logger.info(f"RSS {response.url}: {len(urls)} articles")
        for url in urls:
            if url not in self._visited:
                yield scrapy.Request(
                    url,
                    callback=self.parse_job_page,
                    dont_filter=True,
                )

    def _feed_error(self, failure):
        """Ignore silencieusement les erreurs de sitemap/RSS."""
        pass
