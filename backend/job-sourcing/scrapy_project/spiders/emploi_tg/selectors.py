"""
Selectors CSS pour emploi.tg (AfricaTalents/AfricaWork).
Base sur analyse reelle du site 2025.
"""

# Page liste des offres
JOB_LIST = (
    "main h2 > a[href*='/offre-emploi-togo/']::attr(href), "
    "main a[href*='/offre-emploi-togo/']::attr(href)"
)
JOB_LINK = (
    "main h2 > a[href*='/offre-emploi-togo/']::attr(href), "
    "main a[href*='/offre-emploi-togo/']::attr(href)"
)
JOB_TITLE_LIST = "main h2 > a[href*='/offre-emploi-togo/']::text, h2 a::text"
JOB_LIST_TIMES = "main time::attr(datetime), main time::text"

# Page detail offre
JOB_TITLE = "h1.title-job-offer::text, h1::text"
JOB_COMPANY = (
    "a.card-job-company::text, "
    ".job-advertiser a::text, "
    "a[href*='/recruteur/']::text"
)
JOB_LOCATION = "p.job-region::text, .job-region::text"
JOB_DESCRIPTION = (
    "main article *::text, "
    ".description-offre *::text, "
    ".job-advert-description *::text, "
    ".card-block-content .job-description *::text"
)
JOB_CONTRACT = ".type-contrat::text"
JOB_EXPERIENCE = ".experience::text"
JOB_EDUCATION = ".niveau-etudes::text"
JOB_POSTED_DATE = "time::attr(datetime), .job-date::text, .date-publication::text, .job-info span::text"
JOB_POSTED_DATE_ATTR = "time::attr(datetime)"
JOB_POSTED_DATE_TEXT = "time::text"
JOB_SKILLS = ".competences-cles::text"

# Pagination (multiples selecteurs pour robustesse)
PAGINATION_NEXT = (
    "li.pagination-next a::attr(href), "
    "li.pager-next a::attr(href), "
    "a.next::attr(href), a[rel='next']::attr(href), "
    "a[title='Aller à la page suivante']::attr(href), "
    "ul.pager li.pager-next a::attr(href)"
)

PAGINATION_LINKS = (
    "div.pagination a[href*='?page=']::attr(href), "
    "ul.pagination a[href*='?page=']::attr(href), "
    "ul.pager li a[href*='?page=']::attr(href), "
    "li.pagination-numbers a[href*='?page=']::attr(href), "
    "a[href*='/recherche-jobs-togo?page=']::attr(href), "
    "a[href*='Aller à la page suivante']::attr(href)"
)
