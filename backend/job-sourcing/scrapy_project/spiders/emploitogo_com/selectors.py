"""
Selectors CSS pour emploitogo.com (WordPress JobBoard).
Base sur analyse reelle du site 2025.
"""

# Page liste des offres
JOB_LIST = "ul.job_listings li.job-listing, ul.job_listings li.job_listing"
JOB_LINK = (
    "ul.job_listings li.job-listing a.workscout-grid-job-link-handler::attr(href), "
    "ul.job_listings li.job_listing a.workscout-grid-job-link-handler::attr(href), "
    "ul.job_listings li.job-listing a[href*='/job/']::attr(href), "
    "ul.job_listings li.job-listing a[href*='post_type=job_listing']::attr(href)"
)
JOB_TITLE_LIST = "h3.job-listing-title::text"
JOB_COMPANY_LIST = "h4.job-listing-company::text, .job-listing-footer-company::text"
JOB_LOCATION_LIST = ".job-listing-footer-location::text"

# Page detail offre
JOB_TITLE = "#titlebar h1::text, h1.entry-title::text, h1::text"
JOB_COMPANY = ".job-listing-company::text, .company .value a::text, .company .value::text"
JOB_LOCATION = ".job-overview li::text, .location .value::text"
JOB_TYPE = ".listing-types-list .job-type::text, .job-type::text"
JOB_DESCRIPTION = ".single_job_listing .job_description *::text, .job_description *::text"
JOB_CATEGORY = ".job-categories a::text, .job-category a::text"
JOB_POSTED_DATE = ".job-overview time::attr(datetime), time::attr(datetime)"

# Pagination
PAGINATION_NEXT = (
    ".job-manager-pagination a.next::attr(href), "
    ".job_listings_pagination a.next::attr(href), "
    "a.next.page-numbers::attr(href)"
)

PAGINATION_LINKS = "a.page-numbers::attr(href)"
LOAD_MORE = "a.load_more_jobs::attr(href)"
