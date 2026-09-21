"""
CSS selectors for indeed.com listing pages.
"""

JOB_CARD = (
    "div.job_seen_beacon, "
    "li div.job_seen_beacon, "
    "div[data-jk], "
    "div.slider_container"
)

JOB_LINK = (
    "h2.jobTitle a::attr(href), "
    "a.jcs-JobTitle::attr(href), "
    "a[data-jk]::attr(href)"
)

JOB_TITLE = (
    "h2.jobTitle span[title]::attr(title), "
    "h2.jobTitle a span::text, "
    "a.jcs-JobTitle span::text, "
    "h2.jobTitle::text"
)

JOB_COMPANY = (
    "span[data-testid='company-name']::text, "
    "span.companyName::text, "
    "[data-testid='company-name'] *::text"
)

JOB_LOCATION = (
    "div[data-testid='text-location']::text, "
    "div.companyLocation::text, "
    "[data-testid='job-location']::text"
)

JOB_SNIPPET = (
    "div.job-snippet *::text, "
    "div[data-testid='job-snippet'] *::text, "
    "div.job-snippet::text"
)

JOB_SALARY = (
    "span.estimated-salary *::text, "
    "div.salary-snippet-container *::text, "
    "div[data-testid='attribute_snippet_testid'] *::text"
)

JOB_POSTED_DATE = (
    "span.date::text, "
    "span[data-testid='myJobsStateDate']::text, "
    "div.metadataContainer span::text"
)

NEXT_PAGE = (
    "a[data-testid='pagination-page-next']::attr(href), "
    "a[aria-label='Next Page']::attr(href), "
    "link[rel='next']::attr(href)"
)
