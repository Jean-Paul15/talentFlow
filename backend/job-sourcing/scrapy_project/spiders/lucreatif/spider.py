"""
Spider lucreatif.com.
Dedicated scraper for LUCREATIF job board pages.
"""

import json
import re
from urllib.parse import parse_qs, urlparse

import scrapy
from scrapy_project.items import JobItem

from . import parser
from . import selectors


class LucreatifSpider(scrapy.Spider):
    """Scrape lucreatif.com listings and job details."""

    name = "lucreatif"
    allowed_domains = ["lucreatif.com", "www.lucreatif.com"]
    start_urls = [
        "https://lucreatif.com/?feed=job_listing_feed",
        "https://lucreatif.com/job-list/",
        "https://lucreatif.com/",
    ]

    custom_settings = {
        "DOWNLOAD_DELAY": 2,
        "CONCURRENT_REQUESTS_PER_DOMAIN": 2,
    }
    _PAGE_NUMBER_RE = re.compile(r"/job-list/page/(\d+)/?$", re.IGNORECASE)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.seen_listing_pages: set[str] = set()
        self.seen_job_urls: set[str] = set()

    def parse(self, response):
        """Parse job listing pages and follow detail links."""
        if "feed=job_listing_feed" in response.url:
            yield from self.parse_rss_feed(response)
            return

        page_url = response.url
        if page_url in self.seen_listing_pages:
            return
        self.seen_listing_pages.add(page_url)

        cards = response.css(selectors.LISTING_ARTICLE)
        self.logger.info(
            f"Lucreatif listing: {response.url} | cards={len(cards)}",
        )

        page_index = self._page_index_from_url(response.url)
        for idx, article in enumerate(cards, start=1):
            listing_data = parser.parse_listing_card(article, response)
            if not listing_data:
                continue

            detail_url = listing_data.get("url")
            if not detail_url or detail_url in self.seen_job_urls:
                continue

            listing_data["listing_page_index"] = page_index
            listing_data["listing_position"] = idx
            listing_data["listing_order_proxy"] = (page_index * 100) + idx
            listing_data["listing_url"] = response.url
            self.seen_job_urls.add(detail_url)
            yield response.follow(
                detail_url,
                callback=self.parse_job,
                meta={"listing_data": listing_data},
            )

        for page_link in parser.extract_pagination_links(response):
            if page_link in self.seen_listing_pages:
                continue
            yield response.follow(page_link, callback=self.parse)

        # Fallback dynamique: tente la page suivante meme si la pagination HTML
        # n'est pas exposee (aucune borne fixe sur le nombre de pages).
        next_guess = self._guess_next_page_url(response.url, cards_count=len(cards))
        if next_guess and next_guess not in self.seen_listing_pages:
            yield response.follow(next_guess, callback=self.parse)

    def parse_rss_feed(self, response):
        """Parse native WP Job Manager RSS feed and schedule detail pages."""
        items = response.xpath("//item")
        self.logger.info(f"Lucreatif RSS: {response.url} | items={len(items)}")
        for idx, node in enumerate(items, start=1):
            link = (node.xpath("./link/text()").get() or "").strip()
            title = (node.xpath("./title/text()").get() or "").strip()
            pub_date = (node.xpath("./pubDate/text()").get() or "").strip()
            if not link or "/job/" not in link:
                continue
            if link in self.seen_job_urls:
                continue
            self.seen_job_urls.add(link)
            listing_data = {
                "url": link,
                "title": title or None,
                "posted_date": pub_date or None,
                "listing_source": "rss_feed",
                "listing_page_index": 0,
                "listing_position": idx,
                "listing_order_proxy": idx,
                "listing_url": response.url,
            }
            yield response.follow(
                link,
                callback=self.parse_job,
                meta={"listing_data": listing_data},
            )

    def parse_job(self, response):
        """Parse job detail page, then enrich with wp-json fallback."""
        listing_data = response.meta.get("listing_data", {}) or {}
        base_data = parser.parse_job_data(response, listing_data=listing_data)
        if not base_data.get("title"):
            self.logger.warning(f"Lucreatif: no title found {response.url}")
            return

        post_id = base_data.pop("wp_post_id", None)
        if not post_id:
            yield self._build_item(base_data, response.url, listing_data)
            return

        api_url = f"https://lucreatif.com/wp-json/wp/v2/job_listing/{post_id}"
        yield scrapy.Request(
            api_url,
            callback=self.parse_job_api,
            errback=self.parse_job_api_error,
            meta={
                "base_data": base_data,
                "source_url": response.url,
                "listing_data": listing_data,
            },
            dont_filter=True,
        )

    def parse_job_api(self, response):
        """Merge data from wp-json payload and emit final item."""
        base_data = response.meta.get("base_data", {})
        source_url = response.meta.get("source_url", response.url)
        listing_data = response.meta.get("listing_data", {}) or {}

        payload = {}
        try:
            payload = json.loads(response.text)
        except json.JSONDecodeError:
            self.logger.debug(f"Lucreatif wp-json invalid JSON: {response.url}")

        merged = parser.merge_wp_api_data(base_data, payload, source_url)
        yield self._build_item(merged, source_url, listing_data)

    def parse_job_api_error(self, failure):
        """Fallback to base data if wp-json endpoint fails."""
        request = failure.request
        base_data = request.meta.get("base_data", {})
        source_url = request.meta.get("source_url", request.url)
        listing_data = request.meta.get("listing_data", {}) or {}
        self.logger.warning(f"Lucreatif wp-json failed: {source_url}")
        yield self._build_item(base_data, source_url, listing_data)

    def _build_item(
        self, data: dict, source_url: str, listing_data: dict | None = None,
    ) -> JobItem:
        """Create JobItem from parsed dictionary."""
        item = JobItem()
        item["title"] = data.get("title")
        item["company"] = data.get("company", "Lucreatif")
        item["location"] = data.get("location", "Togo")
        item["description"] = data.get("description", "")
        item["sector"] = data.get("sector")
        item["contract_type"] = data.get("contract_type")
        item["salary"] = data.get("salary")
        item["skills"] = data.get("skills", [])
        item["posted_date"] = data.get("posted_date") or (listing_data or {}).get("posted_date")
        item["posted_date_raw"] = data.get("posted_date_raw")
        item["source_url"] = source_url
        item["source_name"] = self.name
        item["country"] = "Togo"

        item["contact_email"] = data.get("contact_email")
        item["contact_phone"] = data.get("contact_phone")
        item["experience"] = data.get("experience")
        item["education"] = data.get("education")
        item["deadline"] = data.get("deadline")
        item["apply_url"] = data.get("apply_url")
        item["apply_method"] = data.get("apply_method")
        item["apply_instructions"] = data.get("apply_instructions")
        item["recruiter_name"] = data.get("recruiter_name") or data.get("company")
        item["work_schedule"] = data.get("work_schedule")
        item["extra_data"] = {
            "has_json_ld": bool(data.get("json_ld")),
            "source_site": "lucreatif.com",
            "listing_title": (listing_data or {}).get("title"),
            "listing_posted_date": (listing_data or {}).get("posted_date"),
            "listing_source": (listing_data or {}).get("listing_source"),
            "listing_page_index": (listing_data or {}).get("listing_page_index"),
            "listing_position": (listing_data or {}).get("listing_position"),
            "listing_order_proxy": (listing_data or {}).get("listing_order_proxy"),
            "profile_qualities": data.get("profile_qualities", []),
            **(data.get("extra_data") or {}),
        }

        return item

    def _guess_next_page_url(self, current_url: str, cards_count: int) -> str | None:
        if cards_count <= 0:
            return None

        match = self._PAGE_NUMBER_RE.search(current_url)
        if match:
            next_page = int(match.group(1)) + 1
            return f"https://lucreatif.com/job-list/page/{next_page}/"

        root_match = re.search(r"https://lucreatif\.com/page/(\d+)/?$", current_url, re.IGNORECASE)
        if root_match:
            next_page = int(root_match.group(1)) + 1
            return f"https://lucreatif.com/page/{next_page}/"

        if current_url.rstrip("/") == "https://lucreatif.com/job-list":
            return "https://lucreatif.com/job-list/page/2/"
        if current_url.rstrip("/") == "https://lucreatif.com":
            return "https://lucreatif.com/page/2/"
        return None

    def _page_index_from_url(self, url: str) -> int:
        parsed = urlparse(url)
        q = parse_qs(parsed.query or "")
        if "feed" in q:
            return 0
        m = self._PAGE_NUMBER_RE.search(url)
        if m:
            return max(int(m.group(1)) - 1, 0)
        root_match = re.search(r"/page/(\d+)/?$", parsed.path or "", re.IGNORECASE)
        if root_match:
            return max(int(root_match.group(1)) - 1, 0)
        return 0
