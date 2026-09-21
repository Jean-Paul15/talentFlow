"""
Spider emploitogo.info - Blog WordPress Togo/Afrique.
Collecte les articles d'offres, bourses, stages.
"""
import re
from urllib.parse import parse_qs
from urllib.parse import urlparse

import scrapy
from scrapy_project.items import JobItem
from scrapy_project.smart_parser import smart_parse
from . import selectors
from . import parser


class EmploiTogoInfoSpider(scrapy.Spider):
    """
    Spider pour emploitogo.info.
    """

    name = "emploitogo_info"
    allowed_domains = ["emploitogo.info", "www.emploitogo.info"]
    start_urls = [
        "https://www.emploitogo.info/category/offres-demploi/",
        "https://www.emploitogo.info/category/emploitogo/",
        "https://www.emploitogo.info/category/stage/",
        "https://www.emploitogo.info/category/bourse/",
        "https://www.emploitogo.info/category/appel-doffre/",
        "https://www.emploitogo.info/category/concours/",
    ]

    _EXPECTED_DOMAINS = {"emploitogo.info", "www.emploitogo.info"}

    custom_settings = {
        'DOWNLOAD_DELAY': 2,
        'CONCURRENT_REQUESTS_PER_DOMAIN': 2,
    }

    _JOB_URL_KEYWORDS = (
        "recrute", "recrutement", "offre", "emploi", "poste",
        "candidature", "stage", "concours", "bourse", "appel",
    )

    _SKIP_URL_PARTS = (
        "/category/", "/tag/", "/author/", "/page/", "/wp-",
        "/feed", "/comment", "/xmlrpc", "/privacy-policy",
    )

    _SKIP_SLUGS = {
        "", "emploitogo", "offres-emploi", "a-propos", "contact",
        "curriculum-vitae", "publier-une-offre-demploi",
        "se-connecter", "espace-candidats", "espace-recruteurs",
    }

    def parse(self, response):
        """
        Parse page categorie (liste d'articles).
        """
        seen_links = set()
        page_index = self._extract_wp_page_index(response.url)
        category_hint = self._extract_category_hint(response.url)
        position = 0

        article_nodes = response.css(selectors.ARTICLE_LIST)
        for article in article_nodes:
            raw_link = article.css("h2 a::attr(href), h3 a::attr(href), .entry-title a::attr(href), .post-title a::attr(href)").get()
            if not raw_link:
                continue
            if not self._is_candidate_job_link(response, raw_link):
                continue
            absolute = response.urljoin(raw_link)
            if absolute in seen_links:
                continue
            seen_links.add(absolute)
            position += 1
            listing_title = article.css(selectors.ARTICLE_TITLE).get()
            listing_date = article.css(selectors.ARTICLE_DATE).get()
            listing_excerpt = " ".join(article.css(selectors.ARTICLE_EXCERPT).getall()).strip()
            listing_meta = {
                "listing_page_index": page_index,
                "listing_position": position,
                "listing_order_proxy": (page_index * 100) + position,
                "listing_category_hint": category_hint,
                "listing_title": listing_title.strip() if listing_title else None,
                "listing_posted_date_raw": listing_date.strip() if listing_date else None,
                "listing_excerpt": listing_excerpt[:300] if listing_excerpt else None,
                "listing_url": response.url,
            }
            yield response.follow(absolute, callback=self.parse_job, cb_kwargs={"listing_meta": listing_meta})

        # Fallback large: certains templates n'utilisent pas les balises article/h2 classiques
        for link in set(response.css('a::attr(href)').getall()):
            if not self._is_candidate_job_link(response, link):
                continue
            absolute = response.urljoin(link)
            if absolute in seen_links:
                continue
            seen_links.add(absolute)
            yield response.follow(
                absolute,
                callback=self.parse_job,
                cb_kwargs={
                    "listing_meta": {
                        "listing_page_index": page_index,
                        "listing_category_hint": category_hint,
                        "listing_url": response.url,
                    }
                },
            )

        # Pagination multi-selecteur
        page_links = set()
        for sel in selectors.PAGINATION_NEXT.split(','):
            next_page = response.css(sel.strip()).get()
            if next_page:
                page_links.add(next_page)
        page_links.update(response.css(selectors.PAGINATION_LINKS).getall())

        for pl in page_links:
            if not pl:
                continue
            absolute = response.urljoin(pl)
            if "/page/" not in absolute and "page=" not in absolute:
                continue
            yield response.follow(absolute, callback=self.parse)

    def parse_job(self, response, listing_meta=None):
        """
        Parse un article contenant une ou plusieurs offres.
        """
        if not self._is_expected_domain(response.url):
            self.logger.warning(f"URL ignoree (hors domaine emploitogo.info): {response.url}")
            return

        job_data = parser.parse_job_data(response)

        if not job_data.get('title'):
            self.logger.warning(f"Pas de titre: {response.url}")
            return
        if not job_data.get("is_job_post"):
            # Filtre blog/news non-emploi (source mixte WordPress)
            self.logger.info(f"EmploiTogo.info skip non-job article: {response.url}")
            return
        if len(job_data.get('description', '')) < 80:
            # Evite les pages purement navigation/landing.
            return

        enriched = smart_parse(response, source_name=self.name) or {}
        extra_data = {
            'source_site': 'emploitogo.info',
            'source_domain': urlparse(response.url).netloc.replace('www.', ''),
            'availability': job_data.get('availability'),
            **(enriched.get('extra_data') or {}),
            **(job_data.get('extra_data') or {}),
        }
        if listing_meta:
            extra_data.update({k: v for k, v in listing_meta.items() if v is not None})

        item = JobItem()
        item['title'] = job_data['title']
        item['company'] = job_data.get('company') or enriched.get('company') or 'Non precise'
        item['location'] = job_data.get('location') or enriched.get('location') or 'Togo'
        item['description'] = job_data.get('description') or enriched.get('description') or ''
        item['sector'] = job_data.get('category') or enriched.get('sector')
        item['contract_type'] = job_data.get('contract_type') or enriched.get('contract_type')
        item['salary'] = job_data.get('salary') or enriched.get('salary')
        item['posted_date'] = job_data.get('posted_date') or enriched.get('posted_date')
        item['posted_date_raw'] = job_data.get('posted_date_raw')
        item['source_url'] = response.url
        item['source_name'] = self.name
        item['country'] = 'Togo'
        item['skills'] = enriched.get('skills') or []
        item['contact_email'] = job_data.get('contact_email') or enriched.get('contact_email')
        item['contact_phone'] = job_data.get('contact_phone') or enriched.get('contact_phone')
        item['experience'] = job_data.get('experience') or enriched.get('experience')
        item['education'] = job_data.get('education') or enriched.get('education')
        item['deadline'] = job_data.get('deadline') or enriched.get('deadline')
        item['apply_url'] = job_data.get('apply_url') or enriched.get('apply_url')
        item['apply_instructions'] = job_data.get('apply_instructions') or enriched.get('apply_instructions')
        item['apply_method'] = job_data.get('apply_method') or enriched.get('apply_method')
        item['recruiter_name'] = enriched.get('recruiter_name')
        item['extra_data'] = extra_data

        yield item

    def _is_expected_domain(self, url: str) -> bool:
        domain = urlparse(url).netloc.lower()
        return domain in self._EXPECTED_DOMAINS

    def _is_candidate_job_link(self, response, link: str) -> bool:
        """Filtre les liens internes susceptibles d'etre de vraies annonces."""
        if not link:
            return False
        lowered = link.lower()
        if lowered.startswith('#') or lowered.startswith('javascript:'):
            return False

        absolute = response.urljoin(link)
        parsed = urlparse(absolute)
        if parsed.netloc and "emploitogo.info" not in parsed.netloc:
            return False

        path = (parsed.path or "").lower()
        if any(part in path for part in self._SKIP_URL_PARTS):
            return False

        slug = path.strip('/').split('/')[-1]
        if slug in self._SKIP_SLUGS:
            return False
        if path.count('/') <= 1:
            return False

        if any(keyword in path for keyword in self._JOB_URL_KEYWORDS):
            return True

        # Fallback pour les slugs longs de type actualite/recrutement.
        return slug.count('-') >= 2 and len(slug) >= 12

    def _extract_wp_page_index(self, url: str) -> int:
        parsed = urlparse(url)
        m = None
        if parsed.path:
            m = re.search(r"/page/(\d+)/?$", parsed.path)
        if m:
            # WordPress page/2/ = seconde page => index 1
            return max(int(m.group(1)) - 1, 0)
        q = parse_qs(parsed.query).get("page", [None])[0]
        if q is not None:
            try:
                return int(q)
            except ValueError:
                return 0
        return 0

    def _extract_category_hint(self, url: str) -> str:
        parsed = urlparse(url)
        path = (parsed.path or "").lower()
        for part in ("offres-demploi", "emploitogo", "stage", "bourse", "appel-doffre", "concours"):
            if f"/category/{part}/" in path:
                return part
        return ""
