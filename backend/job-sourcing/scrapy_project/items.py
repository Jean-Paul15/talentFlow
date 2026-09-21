import scrapy


class JobItem(scrapy.Item):
    """
    Item Scrapy pour une offre d'emploi.
    """
    title = scrapy.Field()
    company = scrapy.Field()
    location = scrapy.Field()
    description = scrapy.Field()
    source_url = scrapy.Field()
    source_name = scrapy.Field()
    country = scrapy.Field()
    sector = scrapy.Field()
    contract_type = scrapy.Field()
    salary = scrapy.Field()
    skills = scrapy.Field()
    posted_date = scrapy.Field()
    posted_date_raw = scrapy.Field()
    posted_date_iso = scrapy.Field()
    semantic_fingerprint = scrapy.Field()
    is_probable_job = scrapy.Field()
    scraped_at = scrapy.Field()
    fingerprint = scrapy.Field()
    # Champs enrichis par le SmartParser
    contact_email = scrapy.Field()
    contact_phone = scrapy.Field()
    experience = scrapy.Field()
    education = scrapy.Field()
    deadline = scrapy.Field()
    deadline_raw = scrapy.Field()
    deadline_iso = scrapy.Field()
    is_expired = scrapy.Field()
    days_until_deadline = scrapy.Field()
    # Lien de candidature et recruteur
    apply_url = scrapy.Field()
    apply_email = scrapy.Field()
    apply_phone = scrapy.Field()
    apply_method = scrapy.Field()
    apply_instructions = scrapy.Field()
    recruiter_name = scrapy.Field()
    # Regime horaire (temps complet, partiel, teletravail)
    work_schedule = scrapy.Field()
    # Catch-all : donnees imprevues capturees depuis le DOM
    extra_data = scrapy.Field()
