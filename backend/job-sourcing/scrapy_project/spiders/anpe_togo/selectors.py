"""
Selectors CSS pour ANPE Togo (Joomla CMS).
Base sur analyse reelle du site anpetogo.org 2025.
"""

# Page liste des offres - structure table Joomla (categorie standard)
JOB_LIST = "tbody tr[class*='cat-list-row']"
JOB_LINK = "tbody tr[class*='cat-list-row'] td:first-child a::attr(href)"
JOB_TITLE_LIST = "tbody tr[class*='cat-list-row'] td:first-child a::text"
JOB_LIST_AUTHOR = "td:nth-child(2)::text"
JOB_LIST_CLICKS = "td:nth-child(3) .badge::text"

# Selectors alternatifs pour la page d'accueil
HOME_JOB_LIST = ".mod-articles-category-group h3"
HOME_JOB_LINK = "a::attr(href)"

# Page detail offre
JOB_TITLE = "section.article-content p:first-of-type strong::text, section.article-content p:first-of-type em::text, section.article-content p:first-of-type::text"
JOB_CONTENT = "section.article-content"
JOB_DESCRIPTION = (
    "section.article-content p::text, "
    "section.article-content li::text, "
    "section.article-content td::text, "
    "section.article-content h2::text, "
    "section.article-content h3::text, "
    "section.article-content strong::text"
)
JOB_ARTICLE_LINKS = "section.article-content a[href]::attr(href)"
JOB_ARTICLE_MAILTOS = "section.article-content a[href^='mailto:']::attr(href)"
JOB_VIEWS = ".list-view span::text"
JOB_AUTHOR = ".createdby span::text, .create span::text"
JOB_DATE = (
    "time::attr(datetime), "
    ".published time::attr(datetime), "
    ".published::text, "
    ".article-info .published::text, "
    ".create::text"
)

# Pagination Joomla
PAGINATION_NEXT = ".pagination-next a::attr(href)"
PAGINATION_LINKS = "div.pagination a[href*='start=']::attr(href)"
