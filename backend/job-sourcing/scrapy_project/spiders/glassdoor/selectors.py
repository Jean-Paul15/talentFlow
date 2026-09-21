"""
CSS selectors for glassdoor.com listings.
"""

JOB_CARD = "li[data-test='jobListing']"

JOB_TITLE = "a[data-test='job-title']::text"
JOB_TITLE_LINK = "a[data-test='job-title']::attr(href)"
JOB_TRACKING_LINK = "a[data-test='job-link']::attr(href)"

JOB_COMPANY = (
    "div[id^='job-employer-'] span::text, "
    "a[id^='job-employer-'] span::text, "
    "[data-test='employer-name']::text"
)

JOB_LOCATION = (
    "[data-test='emp-location']::text, "
    "[data-test='location']::text"
)

JOB_SALARY = "[data-test='detailSalary'] *::text, [data-test='detailSalary']::text"
JOB_SNIPPET = "[data-test='descSnippet'] *::text, [data-test='descSnippet']::text"
JOB_AGE = "[data-test='job-age']::text"

NEXT_PAGE = (
    "link[rel='next']::attr(href), "
    "a[aria-label='Next']::attr(href), "
    "a[data-test='pagination-next']::attr(href), "
    "a[href*='page=']::attr(href), "
    "a[href*='_IP']::attr(href)"
)
