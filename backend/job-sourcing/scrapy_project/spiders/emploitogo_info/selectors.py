"""
Selectors CSS pour emploitogo.info (blog WordPress).
Base sur analyse reelle du site 2025.
Structure : articles de type blog avec offres groupees.
"""

# Page liste des articles (page d'accueil ou categorie)
ARTICLE_LIST = "article.post"
ARTICLE_LINK = (
    "h2.entry-title a::attr(href), "
    "h3.entry-title a::attr(href), "
    ".entry-title a::attr(href), "
    ".post-title a::attr(href), "
    ".jeg_post_title a::attr(href), "
    ".td-module-title a::attr(href), "
    "article h2 a::attr(href), "
    "article h3 a::attr(href)"
)
ARTICLE_TITLE = "h2.entry-title a::text, h3.entry-title a::text, .post-title a::text"
ARTICLE_DATE = "article.post .posted-on time::attr(datetime), article.post .posted-on::text, article.post .entry-date::attr(datetime), article.post .entry-date::text"
ARTICLE_EXCERPT = "article.post .entry-summary *::text, article.post .excerpt *::text"

# Page detail article
JOB_TITLE = "h1.entry-title::text, h2.entry-title::text"
JOB_CONTENT_CONTAINER = "article .entry-content, article .post-content, .entry-content"
JOB_CONTENT = (
    "article .entry-content p::text, "
    "article .entry-content li::text, "
    "article .entry-content h2::text, "
    "article .entry-content h3::text, "
    "article .entry-content h4::text, "
    "article .entry-content h5::text, "
    "article .entry-content strong::text, "
    "article .post-content p::text, "
    "article .post-content li::text"
)
JOB_CONTENT_HTML = "article .entry-content, article .post-content, .entry-content"
JOB_HEADINGS = "article .entry-content h2::text, article .entry-content h3::text, article .entry-content h4::text, article .entry-content h5::text, article .post-content h2::text, article .post-content h3::text"
JOB_APPLY_MAILTOS = "article .entry-content a[href^='mailto:']::attr(href), article .post-content a[href^='mailto:']::attr(href)"
JOB_ARTICLE_LINKS = "article .entry-content a[href]::attr(href), article .post-content a[href]::attr(href)"

# Metadonnees
JOB_DATE = (
    "article .posted-on time::attr(datetime), "
    "article .entry-date::attr(datetime), "
    "time.entry-date::attr(datetime), "
    ".posted-on::text, "
    ".entry-date::text, "
    ".post-date::text, "
    ".entry-meta time::attr(datetime)"
)
JOB_DATE_ATTR = "article .posted-on time::attr(datetime), article .entry-date::attr(datetime), time.entry-date::attr(datetime)"
JOB_DATE_TEXT = "article .posted-on::text, .posted-on time::text, .entry-date::text, .post-date::text"
JOB_AUTHOR = ".author a::text, .entry-meta .author::text"
JOB_TAGS = ".post-tags a::text, .entry-footer .tag-links a::text"
JOB_CATEGORY = ".post-categories a::text, .cat-links a::text"

# Pagination
PAGINATION_NEXT = (
    ".nav-links a.next::attr(href), "
    ".navigation a[rel='next']::attr(href), "
    "a[rel='next']::attr(href), "
    ".nav-previous a::attr(href), "
    ".pagination .next::attr(href)"
)
PAGINATION_LINKS = ".nav-links a::attr(href), .navigation a::attr(href), .pagination a::attr(href)"
