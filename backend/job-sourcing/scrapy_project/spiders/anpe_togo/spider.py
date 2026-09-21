"""
Spider ANPE Togo - Site officiel gouvernemental (Joomla).
"""
import re
from urllib.parse import urlparse

import scrapy
from scrapy_project.items import JobItem
from scrapy_project.smart_parser import smart_parse
from . import selectors
from . import parser


class AnpeTogoSpider(scrapy.Spider):
    """
    Spider pour ANPE Togo.
    """
    
    name = "anpe_togo"
    allowed_domains = ["anpetogo.org"]
    start_urls = [
        # URL canonique (audit 2026): /offres/offres-de-formations ; /no-sidebar = alias a ignorer.
        "https://anpetogo.org/index.php/fr-fr/offres/offres-de-formations?limit=0",
    ]
    
    custom_settings = {
        'DOWNLOAD_DELAY': 2,
        'CONCURRENT_REQUESTS_PER_DOMAIN': 2,
    }

    @staticmethod
    def _looks_generic_title(value: str | None) -> bool:
        cleaned = re.sub(r"\s+", " ", str(value or "")).strip().lower()
        if not cleaned:
            return True
        if cleaned in {
            "t",
            "p4",
            "(f/h).",
            "(f/h)",
            "f/h",
            "h/f",
            "poste :",
            "poste:",
            "poste",
            "intitulé du poste",
            "intitule du poste",
            "activités principales",
            "activites principales",
        }:
            return True
        return bool(re.fullmatch(r"p\d+", cleaned))
    
    def parse(self, response):
        """
        Parse page liste offres (structure table et liens Joomla).
        """
        rows = response.css(selectors.JOB_LIST)
        if not rows:
            self.logger.warning(f"ANPE listing vide ou structure inconnue: {response.url}")

        for row in rows:
            link = row.css("td:first-child a::attr(href)").get()
            if not link:
                continue

            absolute = response.urljoin(link)
            lowered = absolute.lower()
            if "/offres/" not in lowered:
                continue
            if "/no-sidebar" in lowered:
                continue

            title_listing = row.css("td:first-child a::text").get()
            author_listing = " ".join(row.css(selectors.JOB_LIST_AUTHOR).getall()).strip()
            clicks_listing = " ".join(row.css(selectors.JOB_LIST_CLICKS).getall()).strip()
            id_match = re.search(r"/(\d+)-", absolute)
            listing_meta = {
                "listing_title": title_listing.strip() if title_listing else None,
                "listing_author_anpe": author_listing or None,
                "listing_clicks": clicks_listing or None,
                "anpe_joomla_id": int(id_match.group(1)) if id_match else None,
                "listing_url": response.url,
            }

            yield response.follow(
                absolute,
                callback=self.parse_job,
                cb_kwargs={"listing_meta": listing_meta},
            )

        # Pagination (utile si limit=0 n'est pas respecte par le serveur)
        if "limit=0" in response.url:
            return
        next_pages = set(response.css(selectors.PAGINATION_LINKS).getall())
        next_page = response.css(selectors.PAGINATION_NEXT).get()
        if next_page:
            next_pages.add(next_page)
        for pl in next_pages:
            if not pl:
                continue
            absolute = response.urljoin(pl)
            if absolute == response.url:
                continue
            yield response.follow(absolute, callback=self.parse)

    def parse_job(self, response, listing_meta=None):
        """
        Parse detail offre.
        """
        job_data = parser.parse_job_data(response)

        listing_title = (listing_meta or {}).get("listing_title")
        if listing_title and self._looks_generic_title(job_data.get("title")):
            job_data["title"] = listing_title.strip()
        
        if not job_data.get('title'):
            self.logger.warning(f"No title found: {response.url}")
            return

        enriched = smart_parse(response, source_name=self.name) or {}
        extra_data = dict(enriched.get('extra_data') or {})
        extra_data.update(job_data.get('extra_data') or {})
        if listing_meta:
            extra_data.update({k: v for k, v in listing_meta.items() if v is not None})
        extra_data.setdefault('source_site', 'anpetogo.org')
        extra_data.setdefault('source_domain', urlparse(response.url).netloc.replace('www.', ''))

        item = JobItem()
        item['title'] = job_data['title']
        item['company'] = job_data.get('company') or enriched.get('company') or 'ANPE Togo'
        item['location'] = job_data.get('location') or enriched.get('location') or 'Togo'
        item['description'] = job_data.get('description') or enriched.get('description') or ''
        item['sector'] = job_data.get('sector') or enriched.get('sector')
        item['contract_type'] = job_data.get('contract_type') or enriched.get('contract_type')
        posted_date = job_data.get('posted_date')
        if not posted_date:
            enriched_date = enriched.get('posted_date')
            # Eviter de confondre la deadline detectee par smart_parse avec la date de publication.
            if enriched_date and enriched_date != job_data.get('deadline'):
                posted_date = enriched_date
        item['posted_date'] = posted_date
        item['source_url'] = response.url
        item['source_name'] = self.name
        item['country'] = 'Togo'
        item['salary'] = job_data.get('salary') or enriched.get('salary')
        item['skills'] = enriched.get('skills') or []
        item['contact_email'] = job_data.get('contact_email') or enriched.get('contact_email')
        item['contact_phone'] = job_data.get('contact_phone') or enriched.get('contact_phone')
        item['experience'] = enriched.get('experience')
        item['education'] = enriched.get('education')
        item['deadline'] = job_data.get('deadline') or enriched.get('deadline')
        item['apply_url'] = job_data.get('apply_url') or enriched.get('apply_url')
        item['apply_instructions'] = job_data.get('apply_instructions')
        item['recruiter_name'] = job_data.get('recruiter_name') or enriched.get('recruiter_name')
        item['extra_data'] = extra_data
        
        yield item
