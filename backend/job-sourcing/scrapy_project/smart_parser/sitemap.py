# Decouverte automatique de sitemap.xml et flux RSS/Atom
# Permet d'obtenir TOUTES les URLs d'un site sans crawler
# Extremement puissant : un sitemap contient souvent des milliers d'URLs

import re
from typing import List, Optional
from urllib.parse import urlparse, urljoin

from scrapy.http import HtmlResponse


def discover_sitemap_urls(response: HtmlResponse) -> List[str]:
    """
    Decouvre les URLs de sitemaps depuis la page d'accueil.
    Cherche dans : robots.txt link, <link> HTML, patterns classiques.
    """
    urls = set()
    base = f"{urlparse(response.url).scheme}://{urlparse(response.url).netloc}"

    # Patterns classiques de sitemap
    common_paths = [
        "/sitemap.xml", "/sitemap_index.xml", "/sitemap-index.xml",
        "/wp-sitemap.xml", "/sitemap/sitemap.xml",
        "/post-sitemap.xml", "/page-sitemap.xml",
        "/job-sitemap.xml", "/jobs-sitemap.xml",
        "/sitemap1.xml", "/sitemap_1.xml",
    ]
    for path in common_paths:
        urls.add(base + path)

    # Chercher dans le HTML des liens vers sitemap
    for href in response.css("a[href*='sitemap']::attr(href)").getall():
        urls.add(response.urljoin(href))

    # Chercher dans les meta/link
    for href in response.css("link[href*='sitemap']::attr(href)").getall():
        urls.add(response.urljoin(href))

    return list(urls)


def parse_sitemap_xml(response) -> List[str]:
    """
    Parse un fichier sitemap.xml et extrait les URLs.
    Gere les sitemaps index (qui referent d'autres sitemaps).
    """
    urls = []
    body = response.text if hasattr(response, 'text') else str(response.body)

    # Sitemapindex : liens vers d'autres sitemaps
    for match in re.finditer(r'<sitemap>\s*<loc>(.*?)</loc>', body, re.DOTALL):
        urls.append(match.group(1).strip())

    # URLs directes dans <url><loc>
    for match in re.finditer(r'<url>\s*<loc>(.*?)</loc>', body, re.DOTALL):
        urls.append(match.group(1).strip())

    return urls


def filter_job_urls_from_sitemap(urls: List[str]) -> List[str]:
    """Filtre les URLs qui ressemblent a des offres d'emploi."""
    job_patterns = [
        r'/offre', r'/emploi', r'/job', r'/career',
        r'/recrutement', r'/vacancy', r'/poste', r'/annonce',
        r'/position', r'/hiring', r'post_type=job',
        r'/opportunit', r'/stage', r'/apply',
    ]
    filtered = []
    for url in urls:
        url_lower = url.lower()
        if any(re.search(p, url_lower) for p in job_patterns):
            filtered.append(url)
    return filtered


def discover_rss_feeds(response: HtmlResponse) -> List[str]:
    """
    Decouvre les flux RSS/Atom depuis les balises <link> du HTML.
    Beaucoup de sites WordPress exposent un RSS avec toutes les offres.
    """
    feeds = []

    # Balises link type RSS/Atom
    for link in response.css("link[type*='rss'], link[type*='atom'], link[type*='xml']"):
        href = link.attrib.get("href", "")
        if href:
            feeds.append(response.urljoin(href))

    # Patterns classiques RSS
    base = f"{urlparse(response.url).scheme}://{urlparse(response.url).netloc}"
    common_rss = [
        "/feed", "/feed/", "/rss", "/rss.xml",
        "/feed/rss2", "/atom.xml", "/?feed=rss2",
        "/category/offres-demploi/feed/",
        "/job-listings/feed/",
    ]
    for path in common_rss:
        feeds.append(base + path)

    return feeds


def parse_rss_feed(response) -> List[str]:
    """Extrait les URLs des items d'un flux RSS/Atom."""
    urls = []
    body = response.text if hasattr(response, 'text') else str(response.body)

    # RSS <item><link>
    for match in re.finditer(r'<item>.*?<link>(.*?)</link>', body, re.DOTALL):
        url = match.group(1).strip()
        if url:
            urls.append(url)

    # Atom <entry><link href="">
    for match in re.finditer(r'<entry>.*?<link[^>]*href="([^"]+)"', body, re.DOTALL):
        url = match.group(1).strip()
        if url:
            urls.append(url)

    return urls
