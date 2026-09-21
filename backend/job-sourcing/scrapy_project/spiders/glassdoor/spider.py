"""
Spider glassdoor.com.
Listing-only crawl to keep traffic low and reduce blocking risk.
"""

import os
from urllib.parse import urlparse

import scrapy

from scrapy_project.items import JobItem

from . import parser


class GlassdoorSpider(scrapy.Spider):
    """
    Scrape Glassdoor search result pages.
    """

    name = "glassdoor"
    allowed_domains = ["glassdoor.com", "www.glassdoor.com"]
    start_urls = [
        os.getenv(
            "GLASSDOOR_START_URL",
            "https://www.glassdoor.com/Job/software-engineer-jobs-SRCH_KO0,17.htm",
        ),
    ]

    custom_settings = {
        "DOWNLOAD_DELAY": float(os.getenv("GLASSDOOR_DOWNLOAD_DELAY", "4")),
        "CONCURRENT_REQUESTS_PER_DOMAIN": 1,
        "AUTOTHROTTLE_TARGET_CONCURRENCY": 1.0,
        "RETRY_TIMES": 2,
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.max_pages = max(1, int(os.getenv("GLASSDOOR_MAX_PAGES", "2")))
        self.page_count = 0
        self.seen_pages: set[str] = set()
        self.emitted_jobs: set[str] = set()

    def parse(self, response):
        page_url = response.url
        if page_url in self.seen_pages:
            return
        self.seen_pages.add(page_url)
        self.page_count += 1

        block_reason = parser.detect_block_reason(response)
        if block_reason:
            self.logger.error(
                f"Glassdoor blocked page detected ({block_reason}): {response.url}",
            )
            return

        jobs = parser.parse_jobs(response)
        self.logger.info(
            f"Glassdoor listing: {response.url} | jobs={len(jobs)} | page={self.page_count}/{self.max_pages}",
        )

        for job in jobs:
            item = self._build_item(job, listing_page=response.url)
            if item:
                yield item

        if self.page_count >= self.max_pages:
            return

        next_page = parser.extract_next_page(response)
        if not next_page:
            return

        next_url = response.urljoin(next_page)
        if next_url in self.seen_pages:
            return
        yield response.follow(next_url, callback=self.parse)

    def _build_item(self, data: dict, listing_page: str) -> JobItem | None:
        title = data.get("title")
        source_url = data.get("source_url")
        if not title or not source_url:
            return None

        domain = urlparse(source_url).netloc.lower().replace("www.", "")
        if domain != "glassdoor.com":
            return None

        unique_key = data.get("job_id") or source_url
        if unique_key in self.emitted_jobs:
            return None
        self.emitted_jobs.add(unique_key)

        item = JobItem()
        item["title"] = title
        item["company"] = data.get("company") or "Glassdoor"
        item["location"] = data.get("location") or "International"
        item["description"] = (data.get("description") or "")[:8000]
        item["sector"] = None
        item["contract_type"] = None
        item["salary"] = data.get("salary")
        item["skills"] = []
        item["posted_date"] = data.get("posted_date")
        item["source_url"] = source_url
        item["source_name"] = self.name
        item["country"] = "International"
        item["apply_url"] = data.get("apply_url") or source_url
        item["extra_data"] = {
            "source_site": "glassdoor.com",
            "source_domain": domain,
            "job_id": data.get("job_id"),
            "listing_page": listing_page,
            "listing_age": data.get("posted_date"),
        }
        return item
