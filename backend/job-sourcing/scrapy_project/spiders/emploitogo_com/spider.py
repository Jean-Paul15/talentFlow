"""
Spider emploitogo.com - WordPress JobBoard.
"""
from urllib.parse import parse_qs, urlparse

import scrapy
from scrapy_project.items import JobItem
from . import selectors
from . import parser


class EmploiTogoComSpider(scrapy.Spider):
    """
    Spider pour emploitogo.com.
    """

    name = "emploitogo_com"
    allowed_domains = ["emploitogo.com", "www.emploitogo.com"]
    start_urls = [
        "https://emploitogo.com/job-listings/",
    ]

    _EXPECTED_DOMAIN = "emploitogo.com"

    custom_settings = {
        'DOWNLOAD_DELAY': 2,
        'CONCURRENT_REQUESTS_PER_DOMAIN': 2,
    }

    def parse(self, response):
        """
        Parse page liste offres.
        """
        job_links = set()
        for card in response.css(selectors.JOB_LIST):
            raw_link = card.css("a.workscout-grid-job-link-handler::attr(href)").get()
            job_id = (card.attrib.get("data-job_id") or "").strip()
            for candidate in self._build_candidate_urls(response, raw_link, job_id):
                if self._is_job_link(candidate):
                    job_links.add(candidate)

        for raw_link in response.css(selectors.JOB_LINK).getall():
            for candidate in self._build_candidate_urls(response, raw_link):
                if self._is_job_link(candidate):
                    job_links.add(candidate)

        for link in sorted(job_links):
            yield response.follow(link, callback=self.parse_job)

        next_links = set()
        for sel in selectors.PAGINATION_NEXT.split(","):
            candidate = response.css(sel.strip()).get()
            if candidate:
                next_links.add(candidate)
        next_links.update(response.css(selectors.PAGINATION_LINKS).getall())
        next_links.update(response.css(selectors.LOAD_MORE).getall())

        for link in next_links:
            if self._is_listing_link(response, link):
                yield response.follow(link, callback=self.parse)

    def parse_job(self, response):
        """
        Parse detail offre.
        """
        if not self._is_expected_domain(response.url):
            self.logger.warning(f"URL ignoree (hors domaine emploitogo.com): {response.url}")
            return

        job_data = parser.parse_job_data(response)

        if not job_data.get('title'):
            self.logger.warning(f"No title found: {response.url}")
            return

        item = JobItem()
        item['title'] = job_data['title']
        item['company'] = job_data.get('company', 'Non precise')
        item['location'] = job_data.get('location', 'Togo')
        item['description'] = job_data.get('description', '')
        item['source_url'] = response.url
        item['source_name'] = self.name
        item['country'] = 'Togo'
        item['sector'] = job_data.get('category')
        item['contract_type'] = job_data.get('job_type')
        item['salary'] = None
        item['skills'] = []
        item['posted_date'] = job_data.get('posted_date')
        item['extra_data'] = {
            'source_site': 'emploitogo.com',
            'source_domain': urlparse(response.url).netloc.replace('www.', ''),
        }

        yield item

    def _build_candidate_urls(
        self, response, raw_link: str | None, job_id: str | None = None,
    ) -> list[str]:
        candidates: list[str] = []

        if raw_link:
            absolute = response.urljoin(raw_link)
            candidates.append(absolute)

            parsed = urlparse(absolute)
            query = parse_qs(parsed.query)
            post_ids = query.get("p", [])
            if "post_type=job_listing" in parsed.query and post_ids:
                candidates.append(
                    f"{parsed.scheme}://{parsed.netloc}/job/{post_ids[0]}/"
                )

        if job_id:
            candidates.append(f"https://emploitogo.com/job/{job_id}/")

        seen = set()
        normalized = []
        for candidate in candidates:
            if not candidate:
                continue
            url = candidate.strip()
            if url and url not in seen:
                seen.add(url)
                normalized.append(url)
        return normalized

    def _is_expected_domain(self, url: str) -> bool:
        domain = urlparse(url).netloc.lower().replace("www.", "")
        return domain == self._EXPECTED_DOMAIN

    def _is_job_link(self, url: str) -> bool:
        if not url or not self._is_expected_domain(url):
            return False
        parsed = urlparse(url)
        path = (parsed.path or "").lower()
        query = (parsed.query or "").lower()
        return "/job/" in path or "post_type=job_listing" in query

    def _is_listing_link(self, response, link: str) -> bool:
        if not link:
            return False
        absolute = response.urljoin(link)
        if not self._is_expected_domain(absolute):
            return False
        parsed = urlparse(absolute)
        path = (parsed.path or "").lower()
        if "/job-listings/" in path:
            return True
        query = (parsed.query or "").lower()
        return "page=" in query and "/job/" not in path
