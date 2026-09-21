"""
Spider monster.com.
Gracefully stops when anti-bot challenge is detected.
"""

import os
from urllib.parse import urlparse

import scrapy

from scrapy_project.items import JobItem

from . import parser

try:
    from scrapy_playwright.page import PageMethod
except Exception:  # pragma: no cover - optional dependency
    PageMethod = None


class MonsterSpider(scrapy.Spider):
    """
    Scrape Monster listing pages with conservative rate limits.
    """

    name = "monster"
    allowed_domains = ["monster.com", "www.monster.com"]
    start_urls = [
        os.getenv(
            "MONSTER_START_URL",
            "https://www.monster.com/jobs/search/?q=software+engineer",
        ),
    ]

    custom_settings = {
        "DOWNLOAD_DELAY": float(os.getenv("MONSTER_DOWNLOAD_DELAY", "5")),
        "CONCURRENT_REQUESTS_PER_DOMAIN": 1,
        "AUTOTHROTTLE_TARGET_CONCURRENCY": 1.0,
        "RETRY_TIMES": 1,
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.max_pages = max(1, int(os.getenv("MONSTER_MAX_PAGES", "2")))
        self.page_count = 0
        self.seen_pages: set[str] = set()
        self.emitted_jobs: set[str] = set()
        self.scheduled_jobs: set[str] = set()
        self.blocked = False
        self.fetch_details = self._env_flag("MONSTER_FETCH_DETAILS", True)
        self.use_playwright = self._env_flag("MONSTER_USE_PLAYWRIGHT", False)
        self.use_playwright_detail = self._env_flag(
            "MONSTER_DETAIL_USE_PLAYWRIGHT",
            self.use_playwright,
        )

    def start_requests(self):
        for url in self.start_urls:
            if self.use_playwright and PageMethod is not None:
                yield scrapy.Request(
                    url,
                    callback=self.parse,
                    meta={
                        "playwright": True,
                        "playwright_page_methods": [
                            PageMethod("wait_for_timeout", 2000),
                        ],
                    },
                )
            else:
                yield scrapy.Request(url, callback=self.parse)

    def parse(self, response):
        page_url = response.url
        if page_url in self.seen_pages:
            return
        self.seen_pages.add(page_url)
        self.page_count += 1

        block_reason = parser.detect_block_reason(response)
        if block_reason:
            self.blocked = True
            self.logger.error(
                f"Monster blocked page detected ({block_reason}): {response.url}",
            )
            return

        jobs = parser.parse_jobs(response)
        self.logger.info(
            f"Monster listing: {response.url} | jobs={len(jobs)} | page={self.page_count}/{self.max_pages}",
        )

        for job in jobs:
            unique_key = job.get("job_id") or job.get("source_url")
            if not unique_key:
                continue
            if unique_key in self.scheduled_jobs:
                continue
            self.scheduled_jobs.add(unique_key)

            listing_meta = {
                "listing_page": response.url,
                "listing_page_index": self.page_count,
                "relative_time": job.get("posted_date_raw") or job.get("posted_date"),
            }
            if self.fetch_details and job.get("source_url"):
                req_kwargs = {
                    "callback": self.parse_job_detail,
                    "cb_kwargs": {"listing_job": job, "listing_meta": listing_meta},
                }
                if self.use_playwright_detail and PageMethod is not None:
                    req_kwargs["meta"] = {
                        "playwright": True,
                        "playwright_page_methods": [
                            PageMethod("wait_for_timeout", 1500),
                        ],
                    }
                yield response.follow(job["source_url"], **req_kwargs)
            else:
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
        next_kwargs = {"callback": self.parse}
        if self.use_playwright and PageMethod is not None:
            next_kwargs["meta"] = {
                "playwright": True,
                "playwright_page_methods": [
                    PageMethod("wait_for_timeout", 2000),
                ],
            }
        yield response.follow(next_url, **next_kwargs)

    def parse_job_detail(self, response, listing_job: dict, listing_meta: dict | None = None):
        block_reason = parser.detect_block_reason(response)
        if block_reason:
            self.logger.warning(
                f"Monster detail blocked ({block_reason}), fallback listing item: {response.url}",
            )
            fallback_item = self._build_item(
                listing_job,
                listing_page=(listing_meta or {}).get("listing_page", ""),
                extra_meta={
                    **(listing_meta or {}),
                    "detail_fetch_blocked": True,
                    "detail_block_reason": block_reason,
                },
            )
            if fallback_item:
                yield fallback_item
            return

        detail = parser.parse_job_detail(response)
        merged = self._merge_listing_and_detail(listing_job, detail)

        item = self._build_item(
            merged,
            listing_page=(listing_meta or {}).get("listing_page", ""),
            extra_meta={
                **(listing_meta or {}),
                **(detail.get("extra_data") or {}),
                "detail_fetched": True,
            },
        )
        if item:
            yield item

    def _build_item(self, data: dict, listing_page: str, extra_meta: dict | None = None) -> JobItem | None:
        title = data.get("title")
        source_url = data.get("source_url")
        if not title or not source_url:
            return None

        domain = urlparse(source_url).netloc.lower().replace("www.", "")
        if not domain.endswith("monster.com"):
            return None

        unique_key = data.get("job_id") or source_url
        if unique_key in self.emitted_jobs:
            return None
        self.emitted_jobs.add(unique_key)

        item = JobItem()
        item["title"] = title
        item["company"] = data.get("company") or "Monster"
        item["location"] = data.get("location") or "International"
        item["description"] = (data.get("description") or "")[:8000]
        item["sector"] = data.get("sector")
        item["contract_type"] = data.get("contract_type")
        item["salary"] = data.get("salary")
        item["skills"] = []
        item["posted_date"] = data.get("posted_date")
        item["posted_date_raw"] = data.get("posted_date_raw") or data.get("posted_date")
        item["source_url"] = source_url
        item["source_name"] = self.name
        item["country"] = "International"
        item["apply_url"] = data.get("apply_url") or source_url
        item["contact_email"] = data.get("contact_email")
        item["contact_phone"] = data.get("contact_phone")
        item["experience"] = data.get("experience")
        item["education"] = data.get("education")
        item["deadline"] = data.get("deadline")
        item["apply_method"] = data.get("apply_method")
        item["apply_instructions"] = data.get("apply_instructions")
        item["work_schedule"] = data.get("work_schedule")
        item["extra_data"] = {
            "source_site": "monster.com",
            "source_domain": domain,
            "job_id": data.get("job_id"),
            "listing_page": listing_page,
            "listing_relative_date": data.get("posted_date_raw") or data.get("posted_date"),
            **(data.get("extra_data") or {}),
            **(extra_meta or {}),
        }
        return item

    def _merge_listing_and_detail(self, listing_job: dict, detail: dict) -> dict:
        merged = dict(listing_job or {})
        detail = detail or {}
        # Detail values win when present; keep listing as fallback.
        for key, value in detail.items():
            if key == "extra_data":
                continue
            if value not in (None, "", []):
                merged[key] = value
        merged["posted_date_raw"] = (
            detail.get("posted_date_raw")
            or detail.get("posted_date")
            or listing_job.get("posted_date_raw")
            or listing_job.get("posted_date")
        )
        if not merged.get("posted_date"):
            merged["posted_date"] = merged.get("posted_date_raw")
        # Ensure source_url remains the Monster job page, not the external apply URL.
        merged["source_url"] = detail.get("source_url") or listing_job.get("source_url")
        merged_extra = {}
        merged_extra.update(listing_job.get("extra_data") or {})
        merged_extra.update(detail.get("extra_data") or {})
        merged["extra_data"] = merged_extra
        return merged

    @staticmethod
    def _env_flag(name: str, default: bool) -> bool:
        value = os.getenv(name, "true" if default else "false")
        return str(value).strip().lower() in {"1", "true", "yes", "on"}
