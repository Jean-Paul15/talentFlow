"""
CSS selectors for monster.com listings.
Selectors are intentionally broad because templates vary by region.
"""

JOB_CARD = (
    "article[data-testid='JobCard'], "
    "section[data-testid='svx-job-card'], "
    "div[data-testid='svx-job-card'], "
    "article.card-content, "
    "section.card-content, "
    "div.card-content, "
    "article.summary, "
    "div.summary, "
    "li[data-testid='JobCard'], "
    "article"
)

JOB_LINK = (
    "a[data-testid='jobTitle']::attr(href), "
    "a[href*='/job/']::attr(href), "
    "h2 a::attr(href), "
    "h3 a::attr(href), "
    "a.card-link::attr(href), "
    "a[href*='/job-openings/']::attr(href), "
    "a[href*='/job-opening/']::attr(href), "
    "a[href*='monster.com/job/']::attr(href)"
)

JOB_TITLE = (
    "a[data-testid='jobTitle']::text, "
    "h2 a::text, "
    "h3 a::text, "
    "h2::text, "
    ".title::text, "
    "[class*='JobTitle']::text"
)

JOB_COMPANY = (
    "[data-testid='company']::text, "
    ".company::text, "
    ".company-name::text, "
    ".name::text, "
    "[class*='company']::text"
)

JOB_LOCATION = (
    "[data-testid='jobCardLocation']::text, "
    "[data-testid='location']::text, "
    ".location::text, "
    "[class*='location']::text"
)

JOB_SNIPPET = (
    "[data-testid='jobCardSnippet'] *::text, "
    ".summary *::text, "
    ".description *::text, "
    "[class*='snippet'] *::text"
)

JOB_POSTED_DATE = (
    "[data-testid='jobPostedDate']::text, "
    ".posted::text, "
    ".posted-date::text, "
    ".job-age::text, "
    "time::text"
)

JOB_SALARY = (
    "[data-testid='jobSalary']::text, "
    ".salary::text, "
    "[class*='salary']::text"
)

JOB_CONTRACT = (
    "[data-testid='employmentType']::text, "
    ".employment-type::text, "
    "[class*='contract']::text, "
    "[class*='type']::text"
)

JOB_APPLY_BUTTON_TEXT = (
    "button[aria-label*='Apply']::text, "
    "button[class*='apply']::text, "
    "button::text"
)

JOB_APPLY_BUTTON_LINK = (
    "a[aria-label*='Apply']::attr(href), "
    "a[class*='apply']::attr(href), "
    "a[href*='apply']::attr(href)"
)

NEXT_PAGE = (
    "link[rel='next']::attr(href), "
    "a[aria-label='Next']::attr(href), "
    "a[data-testid='svx-pagination-next']::attr(href), "
    "a[href*='page=']::attr(href), "
    "nav a[href*='page=']::attr(href)"
)

# Détail (page ou panneau selon template)
DETAIL_TITLE = (
    "h1::text, "
    "[data-testid='jobTitle']::text, "
    "[class*='job-detail-title']::text, "
    "[class*='JobTitle']::text"
)

DETAIL_COMPANY = (
    "a[href*='/company/']::text, "
    "[data-testid='company']::text, "
    ".company-name::text, "
    "[class*='company']::text"
)

DETAIL_LOCATION = (
    "[data-testid='location']::text, "
    ".location::text, "
    "[class*='location']::text"
)

DETAIL_DATE_TEXT = (
    "[data-testid='jobPostedDate']::text, "
    ".posted-date::text, "
    ".job-age::text, "
    "time::text"
)

DETAIL_DESCRIPTION = (
    "[data-testid='job-description'] *::text, "
    "[class*='description'] *::text, "
    "section[aria-label*='Description'] *::text, "
    "main article *::text"
)

DETAIL_TEXT = (
    "main *::text, "
    "article *::text, "
    "[role='main'] *::text"
)

DETAIL_APPLY_LINK = (
    "a[aria-label*='Apply']::attr(href), "
    "a[class*='apply']::attr(href), "
    "a[href*='apply']::attr(href), "
    "a[href*='monster.com/job/']::attr(href)"
)

DETAIL_APPLY_BUTTON_TEXT = (
    "button[aria-label*='Apply']::text, "
    "button[class*='apply']::text, "
    "button::text"
)
