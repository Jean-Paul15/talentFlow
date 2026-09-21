"""
Spider emploi.tg - Plateforme majeure AfricaTalents.
Collecte uniquement le domaine emploi.tg pour garder une attribution source propre.
"""
import scrapy
from urllib.parse import parse_qs, urlparse
from scrapy_project.items import JobItem
from scrapy_project.smart_parser import smart_parse
from . import selectors
from . import parser


class EmploiTgSpider(scrapy.Spider):
    """
    Spider pour emploi.tg.
    """

    name = "emploi_tg"
    allowed_domains = ["emploi.tg", "www.emploi.tg"]
    start_urls = [
        "https://www.emploi.tg/recherche-jobs-togo",
    ]

    _EXPECTED_DOMAIN = "emploi.tg"

    custom_settings = {
        'DOWNLOAD_DELAY': 1.5,
        'CONCURRENT_REQUESTS_PER_DOMAIN': 2,
    }

    def parse(self, response):
        """
        Parse page liste offres.
        """
        page_idx = self._current_page_index(response.url)
        seen_links = set()
        raw_links = response.css(selectors.JOB_LINK).getall()
        for position, link in enumerate(raw_links, start=1):
            if not self._is_job_link(response, link):
                continue
            absolute = response.urljoin(link)
            if absolute in seen_links:
                continue
            seen_links.add(absolute)
            listing_meta = {
                "listing_page_index": page_idx,
                "listing_position": position,
                "listing_order_proxy": (page_idx * 100) + position,
                "listing_url": response.url,
            }
            yield response.follow(absolute, callback=self.parse_job, cb_kwargs={"listing_meta": listing_meta})

        next_pages = set()
        for sel in selectors.PAGINATION_NEXT.split(','):
            next_page = response.css(sel.strip()).get()
            if next_page:
                next_pages.add(next_page)
        next_pages.update(response.css(selectors.PAGINATION_LINKS).getall())

        for page_link in next_pages:
            if self._is_listing_link(response, page_link):
                yield response.follow(page_link, callback=self.parse)

    def parse_job(self, response, listing_meta=None):
        """
        Parse detail offre emploi.tg avec double extraction :
        1. Parser specifique emploi.tg (selecteurs connus)
        2. SmartParser pour enrichissement (entites, labels DOM, JSON-LD)
        Fusionne les 2 sources pour ne RIEN perdre.
        """
        if not self._is_expected_domain(response.url):
            self.logger.warning(f"URL ignoree (hors domaine emploi.tg): {response.url}")
            return

        job_data = parser.parse_job_data(response)

        if not job_data.get('title'):
            self.logger.warning(f"Pas de titre trouve: {response.url}")
            return

        # Enrichissement via SmartParser (entites, JSON-LD, labels inconnus)
        enriched = smart_parse(response, source_name=self.name) or {}
        extra_data = dict(enriched.get('extra_data') or {})
        extra_data.update(job_data.get('extra_data') or {})
        if listing_meta:
            extra_data.update({k: v for k, v in listing_meta.items() if v is not None})
        extra_data.setdefault('source_site', 'emploi.tg')
        extra_data.setdefault('source_domain', urlparse(response.url).netloc.replace('www.', ''))

        item = JobItem()
        item['title'] = job_data['title']
        item['company'] = job_data.get('company') or enriched.get('company') or 'Non precise'
        item['location'] = job_data.get('location') or enriched.get('location') or 'Lome'
        item['description'] = job_data.get('description', '')
        item['sector'] = job_data.get('category')
        item['salary'] = (
            job_data.get('salary') or enriched.get('salary')
        )
        item['posted_date'] = (
            job_data.get('posted_date') or enriched.get('posted_date')
        )
        item['posted_date_raw'] = job_data.get('posted_date_raw')
        item['source_url'] = response.url
        item['source_name'] = self.name
        item['country'] = 'Togo'
        item['contract_type'] = (
            job_data.get('contract_type') or enriched.get('contract_type')
        )
        item['skills'] = job_data.get('skills', []) or enriched.get('skills', [])
        # Champs enrichis par le SmartParser (zero perte)
        item['contact_email'] = job_data.get('contact_email') or enriched.get('contact_email')
        item['contact_phone'] = job_data.get('contact_phone') or enriched.get('contact_phone')
        item['experience'] = job_data.get('experience') or enriched.get('experience')
        item['education'] = job_data.get('education') or enriched.get('education')
        item['deadline'] = job_data.get('deadline') or enriched.get('deadline')
        item['apply_url'] = job_data.get('apply_url') or enriched.get('apply_url')
        item['apply_method'] = job_data.get('apply_method') or enriched.get('apply_method')
        item['apply_instructions'] = job_data.get('apply_instructions') or enriched.get('apply_instructions')
        item['recruiter_name'] = job_data.get('recruiter_name') or enriched.get('recruiter_name')
        item['extra_data'] = extra_data

        yield item

    def _is_expected_domain(self, url: str) -> bool:
        domain = urlparse(url).netloc.lower().replace("www.", "")
        return domain == self._EXPECTED_DOMAIN

    def _is_job_link(self, response, link: str) -> bool:
        if not link:
            return False
        absolute = response.urljoin(link)
        parsed = urlparse(absolute)
        if "/offre-emploi-togo/" not in (parsed.path or ""):
            return False
        return self._is_expected_domain(absolute)

    def _is_listing_link(self, response, link: str) -> bool:
        if not link:
            return False
        absolute = response.urljoin(link)
        parsed = urlparse(absolute)
        if not self._is_expected_domain(absolute):
            return False
        return "/recherche-jobs-togo" in (parsed.path or "")

    def _current_page_index(self, url: str) -> int:
        try:
            parsed = urlparse(url)
            page = parse_qs(parsed.query).get("page", [0])[0]
            return int(page)
        except Exception:
            return 0
