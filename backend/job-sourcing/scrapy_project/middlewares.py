# Middlewares Scrapy avances pour anti-detection
# Stealth mode 2026 : headers complets, delais comportementaux, referer

import random
import time
from urllib.parse import urlparse

from scrapy import signals
from scrapy.downloadermiddlewares.useragent import UserAgentMiddleware


class RotateUserAgentMiddleware(UserAgentMiddleware):
    """
    Rotation User-Agent + headers stealth complets.
    Simule un vrai navigateur avec tous les headers modernes.
    Pool de 15+ navigateurs reels (Chrome, Firefox, Safari, Edge).
    """

    user_agents = [
        # Chrome Windows (2025-2026)
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        # Chrome Mac
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
        # Firefox Windows
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.0',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:122.0) Gecko/20100101 Firefox/122.0',
        # Firefox Mac
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:123.0) Gecko/20100101 Firefox/123.0',
        # Safari
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.3 Safari/605.1.15',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15',
        # Edge
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36 Edg/122.0.0.0',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36 Edg/121.0.0.0',
        # Chrome Linux
        'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
        'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
        # Firefox Linux
        'Mozilla/5.0 (X11; Linux x86_64; rv:123.0) Gecko/20100101 Firefox/123.0',
    ]

    _accept_languages = [
        'fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7',
        'fr;q=0.9,en-US;q=0.8,en;q=0.7',
        'fr-FR,fr;q=0.8,en;q=0.6',
        'en-US,en;q=0.9,fr;q=0.8',
    ]

    def process_request(self, request, spider):
        ua = random.choice(self.user_agents)
        request.headers['User-Agent'] = ua
        request.headers['Accept-Language'] = random.choice(self._accept_languages)
        request.headers['Accept'] = (
            'text/html,application/xhtml+xml,application/xml;'
            'q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8'
        )
        request.headers['Accept-Encoding'] = 'gzip, deflate, br'
        # Headers Sec-Fetch (navigateur moderne)
        request.headers['Sec-Fetch-Dest'] = 'document'
        request.headers['Sec-Fetch-Mode'] = 'navigate'
        request.headers['Sec-Fetch-Site'] = 'none'
        request.headers['Sec-Fetch-User'] = '?1'
        request.headers['Sec-Ch-Ua-Mobile'] = '?0'
        request.headers['Sec-Ch-Ua-Platform'] = random.choice(
            ['"Windows"', '"macOS"', '"Linux"']
        )
        # Sec-Ch-Ua coherent avec le User-Agent
        if 'Chrome' in ua and 'Edg' not in ua:
            ver = ua.split('Chrome/')[1].split('.')[0] if 'Chrome/' in ua else '122'
            request.headers['Sec-Ch-Ua'] = (
                f'"Chromium";v="{ver}", "Google Chrome";v="{ver}", "Not-A.Brand";v="99"'
            )
        elif 'Edg' in ua:
            ver = ua.split('Edg/')[1].split('.')[0] if 'Edg/' in ua else '122'
            request.headers['Sec-Ch-Ua'] = (
                f'"Chromium";v="{ver}", "Microsoft Edge";v="{ver}", "Not-A.Brand";v="99"'
            )
        # Upgrade, DNT, Cache
        request.headers['Upgrade-Insecure-Requests'] = '1'
        request.headers['DNT'] = '1'
        request.headers['Cache-Control'] = 'max-age=0'
        request.headers['Connection'] = 'keep-alive'


class SmartRefererMiddleware:
    """
    Injecte un referer realiste base sur le domaine cible.
    Simule la navigation naturelle depuis un moteur de recherche.
    """

    _search_engines = [
        'https://www.google.com/',
        'https://www.google.fr/',
        'https://www.google.com/search?q=emploi+togo',
        'https://www.bing.com/',
        'https://duckduckgo.com/',
    ]

    def process_request(self, request, spider):
        if not request.headers.get('Referer'):
            domain = urlparse(request.url).netloc
            # Premiere visite du domaine : vient d'un moteur de recherche
            if not hasattr(spider, '_domain_visited'):
                spider._domain_visited = set()
            if domain not in spider._domain_visited:
                spider._domain_visited.add(domain)
                request.headers['Referer'] = random.choice(self._search_engines)
            else:
                # Navigation interne : referer = page precedente du meme site
                scheme = urlparse(request.url).scheme
                request.headers['Referer'] = f"{scheme}://{domain}/"


class SmartDelayMiddleware:
    """
    Delais comportementaux intelligents pour simuler un humain.
    Varie les delais selon le type de page et le contexte.
    """

    def process_request(self, request, spider):
        # Delai supplementaire aleatoire (en plus du DOWNLOAD_DELAY)
        # Plus court pour les pages de liste, plus long pour le detail
        url = request.url.lower()
        if any(kw in url for kw in ['page=', 'offset=', '/page/', '?p=']):
            # Pagination : delai court (humain qui clique vite)
            extra_delay = random.uniform(0.2, 0.8)
        elif any(kw in url for kw in ['job', 'offer', 'employ', 'poste']):
            # Detail offre : delai moyen (lecture rapide)
            extra_delay = random.uniform(0.5, 2.0)
        else:
            # Navigation generale
            extra_delay = random.uniform(0.3, 1.5)

        time.sleep(extra_delay)


class RetryOn403Middleware:
    """
    Retry intelligent sur les erreurs 403/429 avec backoff.
    Attend plus longtemps avant chaque retry.
    """

    def process_response(self, request, response, spider):
        if response.status in (403, 429):
            retries = request.meta.get('retry_403', 0)
            if retries < 2:
                wait = (retries + 1) * random.uniform(5, 15)
                spider.logger.warning(
                    f"[{response.status}] {request.url} - "
                    f"retry {retries + 1}/2 dans {wait:.0f}s"
                )
                time.sleep(wait)
                new_request = request.copy()
                new_request.meta['retry_403'] = retries + 1
                new_request.dont_filter = True
                return new_request
            else:
                spider.logger.error(
                    f"[{response.status}] {request.url} - abandonne apres 2 retries"
                )
        return response
