"""
Spider miabejob.com - Service RH.
"""
from urllib.parse import urlparse

import scrapy
from scrapy_project.items import JobItem
from scrapy_project.smart_parser import smart_parse
from . import selectors
from . import parser


class MiabeJobSpider(scrapy.Spider):
    """
    Spider pour miabejob.com.
    """
    
    name = "miabejob"
    allowed_domains = ["miabejob.com"]
    start_urls = ["https://miabejob.com/offres"]
    
    custom_settings = {
        'DOWNLOAD_DELAY': 2,
    }
    
    def parse(self, response):
        """
        Parse page liste offres.
        """
        job_links = response.css(f'{selectors.JOB_LINK}::attr(href)').getall()
        
        for link in job_links:
            if link:
                yield response.follow(link, callback=self.parse_job)
    
    def parse_job(self, response):
        """
        Parse detail offre.
        """
        job_data = parser.parse_job_data(response, selectors)
        
        if not job_data.get('title'):
            self.logger.warning(f"No title found: {response.url}")
            return

        enriched = smart_parse(response, source_name=self.name) or {}
        
        item = JobItem()
        item['title'] = job_data['title']
        item['company'] = job_data.get('company') or enriched.get('company')
        item['location'] = job_data.get('location') or enriched.get('location')
        item['description'] = job_data.get('description') or enriched.get('description')
        item['contract_type'] = job_data.get('contract_type') or enriched.get('contract_type')
        item['posted_date'] = job_data.get('posted_date') or enriched.get('posted_date')
        item['source_url'] = response.url
        item['source_name'] = self.name
        item['country'] = 'Togo'
        item['sector'] = enriched.get('sector')
        item['salary'] = enriched.get('salary')
        item['skills'] = enriched.get('skills') or []
        item['contact_email'] = enriched.get('contact_email')
        item['contact_phone'] = enriched.get('contact_phone')
        item['experience'] = enriched.get('experience')
        item['education'] = enriched.get('education')
        item['deadline'] = enriched.get('deadline')
        item['apply_url'] = enriched.get('apply_url')
        item['recruiter_name'] = enriched.get('recruiter_name')
        item['extra_data'] = {
            'source_domain': urlparse(response.url).netloc.replace('www.', ''),
            **(enriched.get('extra_data') or {}),
        }
        
        yield item
