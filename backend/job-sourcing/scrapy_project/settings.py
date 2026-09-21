import importlib.util
import os

BOT_NAME = 'talentflow_sourcing'

SPIDER_MODULES = ['scrapy_project.spiders']
NEWSPIDER_MODULE = 'scrapy_project.spiders'

ROBOTSTXT_OBEY = False

# Parallelisme controle - plus agressif
CONCURRENT_REQUESTS = 16
CONCURRENT_REQUESTS_PER_DOMAIN = 4
CONCURRENT_ITEMS = 200

# Politesse et rate limiting
DOWNLOAD_DELAY = 1
RANDOMIZE_DOWNLOAD_DELAY = True
AUTOTHROTTLE_ENABLED = True
AUTOTHROTTLE_START_DELAY = 1
AUTOTHROTTLE_MAX_DELAY = 8
AUTOTHROTTLE_TARGET_CONCURRENCY = 4.0
AUTOTHROTTLE_DEBUG = False

# Timeout et retry
DOWNLOAD_TIMEOUT = 30
RETRY_ENABLED = True
RETRY_TIMES = 3
RETRY_HTTP_CODES = [500, 502, 503, 504, 408, 429]

# Profondeur de crawl - suivre les paginations
DEPTH_LIMIT = 20
DEPTH_STATS_VERBOSE = True

COOKIES_ENABLED = False

# Eviter l'encodage Brotli ("br") non decode par certains environnements.
# Les sites cibles servent aussi gzip/deflate, compatibles nativement Scrapy.
DEFAULT_REQUEST_HEADERS = {
    "Accept": (
        "text/html,application/xhtml+xml,application/xml;q=0.9,"
        "application/json;q=0.8,*/*;q=0.7"
    ),
    "Accept-Language": "fr-FR,fr;q=0.9,en;q=0.8",
    "Accept-Encoding": "gzip, deflate",
}

DOWNLOADER_MIDDLEWARES = {
    'scrapy_project.middlewares.RotateUserAgentMiddleware': 400,
    'scrapy_project.middlewares.SmartRefererMiddleware': 410,
    'scrapy_project.middlewares.SmartDelayMiddleware': 420,
    'scrapy_project.middlewares.RetryOn403Middleware': 430,
}

ITEM_PIPELINES = {
    'scrapy_project.pipelines.DataQualityNormalizationPipeline': 50,
    'scrapy_project.pipelines.FingerprintPipeline': 100,
    'scrapy_project.pipelines.KafkaPipeline': 200,
}

# Logging
LOG_LEVEL = 'INFO'
LOG_FILE = 'logs/scrapy.log'
LOG_FILE_APPEND = True
LOG_DATEFORMAT = '%Y-%m-%d %H:%M:%S'

# Cache HTTP desactive (on veut donnees fraiches)
HTTPCACHE_ENABLED = False

# Extensions pour stats
EXTENSIONS = {
    'scrapy.extensions.telnet.TelnetConsole': None,
    'scrapy.extensions.corestats.CoreStats': 500,
}

# Reactor pour meilleures performances
TWISTED_REACTOR = 'twisted.internet.asyncioreactor.AsyncioSelectorReactor'

# Encodage UTF-8 pour toute la sortie
FEED_EXPORT_ENCODING = 'utf-8'


def _env_flag(name: str, default: str = "false") -> bool:
    return str(os.getenv(name, default)).strip().lower() in {"1", "true", "yes", "on"}


SCRAPY_ENABLE_PLAYWRIGHT = _env_flag("SCRAPY_ENABLE_PLAYWRIGHT", "false")
_PLAYWRIGHT_INSTALLED = importlib.util.find_spec("scrapy_playwright") is not None

if SCRAPY_ENABLE_PLAYWRIGHT and _PLAYWRIGHT_INSTALLED:
    # Gestionnaire HTTP optionnel pour pages nécessitant JS (ex: Wiijob listing SPA).
    DOWNLOAD_HANDLERS = {
        "http": "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler",
        "https": "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler",
    }
    PLAYWRIGHT_BROWSER_TYPE = os.getenv("PLAYWRIGHT_BROWSER_TYPE", "chromium")
    PLAYWRIGHT_DEFAULT_NAVIGATION_TIMEOUT = int(
        os.getenv("PLAYWRIGHT_NAV_TIMEOUT_MS", "30000")
    )
    PLAYWRIGHT_LAUNCH_OPTIONS = {
        "headless": _env_flag("PLAYWRIGHT_HEADLESS", "true"),
    }
    # Limiter pour ne pas saturer la VM.
    PLAYWRIGHT_MAX_CONTEXTS = int(os.getenv("PLAYWRIGHT_MAX_CONTEXTS", "2"))
    PLAYWRIGHT_MAX_PAGES_PER_CONTEXT = int(
        os.getenv("PLAYWRIGHT_MAX_PAGES_PER_CONTEXT", "4")
    )
