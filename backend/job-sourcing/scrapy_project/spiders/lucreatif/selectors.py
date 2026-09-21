"""
CSS selectors for lucreatif.com.
Structure observed on live site (WordPress + wp-job-board-pro).
"""

# Listing page
LISTING_ARTICLE = "article.job_listing, article.type-job_listing, article"

LISTING_LINK = (
    "h2.entry-title.job-title a::attr(href), "
    "h2.entry-title a::attr(href), "
    'a[href*="/job/"]::attr(href)'
)

LISTING_TITLE = (
    "h2.entry-title.job-title a::text, "
    "h2.entry-title a::text, "
    "h3.entry-title a::text, "
    "h3 a::text, "
    "h2.entry-title::text, "
    "h3::text, "
    "h2::text"
)

LISTING_POSTED_TEXT = ".posted::text, .job-date-author::text"

# Compat alias (utilise historiquement dans le spider)
JOB_LINK = LISTING_LINK

PAGINATION_NEXT = (
    "ul.pagination a.next.page-numbers::attr(href), "
    "a.next.page-numbers::attr(href)"
)

PAGINATION_ALL = (
    "ul.pagination a.page-numbers::attr(href), "
    "a.page-numbers::attr(href)"
)

PAGINATION_LINKS = (
    "ul.pagination a.page-numbers::attr(href), "
    "ul.pagination a.next.page-numbers::attr(href), "
    "a.next.page-numbers::attr(href), "
    "a[href*='/page/']::attr(href)"
)

# Detail page
ARTICLE_ID = "article.job_listing::attr(id)"
JOB_TITLE = "h1.entry-title.job-title::text, h1.entry-title::text"
JOB_POSTED_TEXT = ".posted::text, .job-date-author::text"
JOB_DESCRIPTION = (
    ".job-detail-description .inner *::text, "
    ".job-detail-description p::text, "
    ".job-detail-description li::text"
)
JOB_DETAIL_TEXT = (
    ".job-detail-header *::text, "
    ".job-detail-description .inner *::text, "
    ".job-detail-description li::text"
)
JOB_DEADLINE = ".deadline-time strong::text, .deadline-time::text"
APPLY_LINKS = (
    ".job-detail-buttons a.btn-apply::attr(href), "
    ".job-detail-description a::attr(href)"
)
