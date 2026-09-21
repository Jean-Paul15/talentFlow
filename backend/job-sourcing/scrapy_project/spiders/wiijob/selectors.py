"""
Selectors CSS pour wiijob.com.
Base sur analyse reelle du site 2025.
Structure : fiches offres individuelles avec taxonomie metier/contrat/localisation.
"""

# Page liste des offres
JOB_CARD = "article.job-listing, div.job-listing, article"
JOB_LINK = 'a[href*="/offre-emploi/"]::attr(href)'
JOB_TITLE_LIST = "h2 a::text, h3 a::text"
JOB_METIER = 'a[href*="/offres-emploi-metier/"]::text'
JOB_LOCATION_LIST = 'a[href*="/offres-emploi-localisation/"]::text'
JOB_CONTRACT_LIST = 'a[href*="/offres-emploi-contrat/"]::text'
JOB_LIST_DATE = "span::text, .job-date::text, [class*='date']::text"

# Page detail offre
JOB_TITLE = "h1.job-detail-title::text, h1::text, h1.entry-title::text, .job-title::text"
JOB_DESCRIPTION = (
    ".job-detail-description *::text, "
    ".job-description *::text, "
    ".entry-content *::text, "
    "main article *::text"
)
JOB_COMPANY = ".job-detail-company a::text, .company-name::text, .employer-name::text"
JOB_LOCATION = 'div.job-location a::text, a[href*="/offres-emploi-localisation/"]::text, .job-location::text'
JOB_CONTRACT = 'span.type-job::text, a[href*="/offres-emploi-contrat/"]::text, .job-type::text'
JOB_METIER_DETAIL = 'a[href*="/offres-emploi-metier/"]::text'
JOB_DATE = "time::attr(datetime), .post-date::text, .date-posted::text"
JOB_DETAIL_TEXT = "main article *::text, article *::text"
JOB_APPLY_LINK = "a[href*='postuler']::attr(href), a[class*='apply']::attr(href), .btn-apply::attr(href)"
JOB_APPLY_BUTTON_TEXT = "a.btn-apply::text, button::text, a[class*='apply']::text"
JOB_SIDEBAR_INFO = ".widget_apus_job_info ul.list li, aside li, .job-sidebar li, [class*='sidebar'] li"
JOB_SIDEBAR_TEXT = ".widget_apus_job_info *::text, .job-sidebar *::text, aside *::text"

# Pagination
PAGINATION_NEXT = ".pagination a.next::attr(href), a.next.page-numbers::attr(href), li a.next.page-numbers::attr(href)"
PAGINATION_LINKS = ".pagination a.page-numbers::attr(href), a.page-numbers::attr(href)"
