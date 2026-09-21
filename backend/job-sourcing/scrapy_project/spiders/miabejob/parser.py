"""
Parser pour miabejob.com.
"""
from typing import Optional
from scrapy.http import Response


def extract_text(response: Response, selector: str) -> Optional[str]:
    """
    Extrait texte d'un selecteur CSS.
    """
    text = response.css(f'{selector}::text').get()
    return text.strip() if text else None


def extract_text_list(response: Response, selector: str) -> str:
    """
    Extrait liste de textes et les concatene.
    """
    texts = response.css(f'{selector}::text').getall()
    return ' '.join(t.strip() for t in texts if t.strip())


def parse_job_data(response: Response, selectors) -> dict:
    """
    Parse les donnees d'une offre complete.
    """
    duration = extract_text(response, selectors.JOB_DURATION)
    contract_type = 'CDD' if duration else None
    
    return {
        'title': extract_text(response, selectors.JOB_TITLE),
        'company': extract_text(response, selectors.JOB_COMPANY) or 'N.C.',
        'location': extract_text(response, selectors.JOB_LOCATION) or 'Lome',
        'description': extract_text_list(response, selectors.JOB_DESCRIPTION),
        'duration': duration,
        'contract_type': contract_type,
        'posted_date': extract_text(response, selectors.JOB_POSTED_DATE),
    }
