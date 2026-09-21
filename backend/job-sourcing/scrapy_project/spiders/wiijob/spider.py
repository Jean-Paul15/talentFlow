"""
Spider wiijob.com - Cabinet RH Afrique francophone.
Collecte les offres CDI, CDD, stages, freelance.
"""
import os
import re
from urllib.parse import urlparse

import scrapy
from scrapy_project.items import JobItem
from . import selectors
from . import parser

try:
    from scrapy_playwright.page import PageMethod
except Exception:  # pragma: no cover - optional dependency
    PageMethod = None


class WiijobSpider(scrapy.Spider):
    """
    Spider pour wiijob.com.
    """

    name = "wiijob"
    allowed_domains = ["wiijob.com", "www.wiijob.com"]
    start_urls = [
        "https://wiijob.com/offres-emploi/",
    ]

    _EXPECTED_DOMAIN = "wiijob.com"

    custom_settings = {
        'DOWNLOAD_DELAY': 2,
        'CONCURRENT_REQUESTS_PER_DOMAIN': 2,
    }
    _DETAIL_URL_RE = re.compile(r'https?://(?:www\.)?wiijob\.com/offre-emploi/[^"\'\s<>()]+', re.IGNORECASE)
    _DETAIL_URL_REL_RE = re.compile(r'(?<![A-Za-z0-9_-])(/offre-emploi/[^"\'\s<>()]+)', re.IGNORECASE)
    _PAGE_COUNT_HINT_RE = re.compile(r"Afficher\s+\d+\s*-\s*\d+\s+des\s+(\d+)\s+r[eé]sultats", re.IGNORECASE)
    _SITEMAP_URLS = (
        "https://wiijob.com/sitemap.xml",
        "https://wiijob.com/sitemap_index.xml",
        "https://wiijob.com/post-sitemap.xml",
        "https://wiijob.com/page-sitemap.xml",
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._seen_sitemaps = set()
        self._use_playwright_listing = self._env_flag("WIIJOB_USE_PLAYWRIGHT", False)
        self._try_sitemap = self._env_flag("WIIJOB_TRY_SITEMAP", True)

    def start_requests(self):
        """
        Strategie d'automatisation:
        1) tenter sitemap (rapide, sans JS)
        2) fallback listing SPA (HTML + hydration regex)
        3) listing Playwright optionnel si active
        """
        if self._try_sitemap:
            for sitemap_url in self._SITEMAP_URLS:
                yield scrapy.Request(
                    sitemap_url,
                    callback=self.parse_sitemap,
                    errback=self._ignore_error,
                    dont_filter=True,
                )

        for url in self.start_urls:
            if self._use_playwright_listing and PageMethod is not None:
                yield scrapy.Request(
                    url,
                    callback=self.parse,
                    meta={
                        "playwright": True,
                        "playwright_page_methods": [
                            PageMethod("wait_for_timeout", 2000),
                            PageMethod("wait_for_selector", "a[href*='/offre-emploi/']", timeout=10000),
                        ],
                    },
                )
            else:
                yield scrapy.Request(url, callback=self.parse)

    def parse(self, response):
        """
        Parse page liste des offres.
        """
        links = set(response.css(selectors.JOB_LINK).getall())
        links.update(response.css('h2 a[href*="/offre-emploi/"]::attr(href)').getall())
        links.update(response.css('h3 a[href*="/offre-emploi/"]::attr(href)').getall())
        # Fallback SPA/hydration: regex sur HTML brut pour recuperer des URLs détail présentes dans scripts/JSON.
        links.update(self._extract_detail_links_from_html(response))

        count_hint = None
        m = self._PAGE_COUNT_HINT_RE.search(response.text or "")
        if m:
            try:
                count_hint = int(m.group(1))
            except ValueError:
                count_hint = None

        for link in links:
            if self._is_job_link(response, link):
                yield response.follow(
                    link,
                    callback=self.parse_job,
                    cb_kwargs={"listing_meta": {"listing_total_hint": count_hint, "listing_url": response.url}},
                )

        next_links = set()
        for sel in selectors.PAGINATION_NEXT.split(','):
            candidate = response.css(sel.strip()).get()
            if candidate:
                next_links.add(candidate)
        next_links.update(response.css(selectors.PAGINATION_LINKS).getall())

        for page_link in next_links:
            if self._is_listing_link(response, page_link):
                yield response.follow(page_link, callback=self.parse)

        if not next_links:
            self.logger.info(
                "Wiijob: pagination HTML non detectee (probable SPA/client-side). "
                "Le spider utilise les URLs détail visibles/hydratées seulement."
            )

    def parse_sitemap(self, response):
        """
        Parse sitemap.xml / sitemap index et récupère les URLs de détail Wiijob.
        """
        if response.url in self._seen_sitemaps:
            return
        self._seen_sitemaps.add(response.url)

        if response.status >= 400:
            return

        locs = [loc.strip() for loc in response.xpath("//*[local-name()='loc']/text()").getall() if loc.strip()]
        if not locs:
            return

        for loc in locs:
            absolute = response.urljoin(loc)
            if absolute.endswith(".xml"):
                if absolute not in self._seen_sitemaps and self._is_expected_domain(absolute):
                    yield scrapy.Request(
                        absolute,
                        callback=self.parse_sitemap,
                        errback=self._ignore_error,
                        dont_filter=True,
                    )
                continue

            if self._is_job_link(response, absolute):
                yield response.follow(
                    absolute,
                    callback=self.parse_job,
                    cb_kwargs={"listing_meta": {"listing_source": "sitemap", "listing_url": response.url}},
                )

    def parse_job(self, response, listing_meta=None):
        """
        Parse une fiche offre individuelle.
        """
        if not self._is_expected_domain(response.url):
            self.logger.warning(f"URL ignoree (hors domaine wiijob.com): {response.url}")
            return

        job_data = parser.parse_job_data(response)

        if not job_data.get('title'):
            self.logger.warning(f"Pas de titre: {response.url}")
            return

        item = JobItem()
        item['title'] = job_data['title']
        item['company'] = job_data.get('company', 'Wiijob')
        item['location'] = job_data.get('location', 'Afrique')
        item['description'] = job_data.get('description', '')
        item['sector'] = job_data.get('category')
        item['contract_type'] = job_data.get('contract_type')
        item['salary'] = job_data.get('salary')
        item['posted_date'] = job_data.get('posted_date')
        item['posted_date_raw'] = job_data.get('posted_date_raw')
        item['source_url'] = response.url
        item['source_name'] = self.name
        item['country'] = 'Afrique'
        item['skills'] = []
        item['deadline'] = job_data.get('deadline')
        item['experience'] = job_data.get('experience')
        item['work_schedule'] = job_data.get('work_schedule')
        item['contact_email'] = job_data.get('contact_email')
        item['contact_phone'] = job_data.get('contact_phone')
        item['apply_url'] = job_data.get('apply_url')
        item['apply_method'] = job_data.get('apply_method')
        item['apply_instructions'] = job_data.get('apply_instructions')
        item['recruiter_name'] = job_data.get('recruiter_name')
        item['extra_data'] = {
            'source_site': 'wiijob.com',
            'source_domain': urlparse(response.url).netloc.replace('www.', ''),
            'work_mode': job_data.get('work_mode'),
            **(job_data.get('extra_data') or {}),
            **(listing_meta or {}),
        }

        yield item

    def _is_expected_domain(self, url: str) -> bool:
        domain = urlparse(url).netloc.lower().replace("www.", "")
        return domain == self._EXPECTED_DOMAIN

    def _is_job_link(self, response, link: str) -> bool:
        if not link:
            return False
        absolute = response.urljoin(link)
        if not self._is_expected_domain(absolute):
            return False
        return "/offre-emploi/" in (urlparse(absolute).path or "")

    def _is_listing_link(self, response, link: str) -> bool:
        if not link:
            return False
        absolute = response.urljoin(link)
        if not self._is_expected_domain(absolute):
            return False
        parsed = urlparse(absolute)
        return "/offres-emploi/" in (parsed.path or "")

    def _extract_detail_links_from_html(self, response):
        found = set()
        for match in self._DETAIL_URL_RE.findall(response.text or ""):
            found.add(match)
        for match in self._DETAIL_URL_REL_RE.findall(response.text or ""):
            found.add(response.urljoin(match))
        return found

    def _ignore_error(self, failure):
        self.logger.debug(f"Wiijob optional source failed: {failure.request.url}")

    @staticmethod
    def _env_flag(name: str, default: bool) -> bool:
        value = os.getenv(name, "true" if default else "false")
        return str(value).strip().lower() in {"1", "true", "yes", "on"}
