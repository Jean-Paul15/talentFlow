# Registre des sites d'emploi - Section AFRIQUE ANGLOPHONE
# Nigeria, Ghana, Kenya, Afrique du Sud, Tanzanie, Ouganda, Ethiopie, Rwanda

from .registry_constants import (
    PRIORITY_MEDIUM, PRIORITY_LOW, PRIORITY_NIGHTLY,
)


SITES_AFRIQUE_ANGLOPHONE = {
    # ================================================================
    # NIGERIA
    # ================================================================
    "jobberman_ng": {
        "label": "Jobberman Nigeria",
        "url": "https://www.jobberman.com/jobs",
        "description": "Leader emploi Nigeria - expansion Afrique Ouest",
        "pays": "Nigeria",
        "spider": None,
        "priority": PRIORITY_MEDIUM,
        "category": "portail_emploi",
        "active": True,
        "source": "scraping",
    },
    "myjobmag_ng": {
        "label": "MyJobMag Nigeria",
        "url": "https://www.myjobmag.com/jobs-in-nigeria",
        "description": "Plateforme emploi leader Nigeria",
        "pays": "Nigeria",
        "spider": None,
        "priority": PRIORITY_MEDIUM,
        "category": "portail_emploi",
        "active": True,
        "source": "scraping",
    },
    "ngcareers": {
        "label": "NGCareers",
        "url": "https://ngcareers.com/jobs",
        "description": "Portail emploi et carriere Nigeria",
        "pays": "Nigeria",
        "spider": None,
        "priority": PRIORITY_LOW,
        "category": "portail_emploi",
        "active": True,
        "source": "scraping",
    },
    "hotnigerianjobs": {
        "label": "HotNigerianJobs",
        "url": "https://hotnigerianjobs.com/",
        "description": "Agregateur offres emploi Nigeria",
        "pays": "Nigeria",
        "spider": None,
        "priority": PRIORITY_LOW,
        "category": "portail_emploi",
        "active": True,
        "source": "scraping",
    },
    # ================================================================
    # GHANA
    # ================================================================
    "jobberman_gh": {
        "label": "Jobberman Ghana",
        "url": "https://www.jobberman.com.gh/jobs",
        "description": "Leader emploi Ghana",
        "pays": "Ghana",
        "spider": None,
        "priority": PRIORITY_MEDIUM,
        "category": "portail_emploi",
        "active": True,
        "source": "scraping",
    },
    "jobsinghana": {
        "label": "Jobs In Ghana",
        "url": "https://jobsinghana.com/jobs",
        "description": "Portail emploi ghaneen",
        "pays": "Ghana",
        "spider": None,
        "priority": PRIORITY_LOW,
        "category": "portail_emploi",
        "active": True,
        "source": "scraping",
    },
    "myjobmag_gh": {
        "label": "MyJobMag Ghana",
        "url": "https://www.myjobmag.com/jobs-in-ghana",
        "description": "Plateforme emploi Ghana",
        "pays": "Ghana",
        "spider": None,
        "priority": PRIORITY_LOW,
        "category": "portail_emploi",
        "active": True,
        "source": "scraping",
    },
    # ================================================================
    # KENYA
    # ================================================================
    "brightermonday_ke": {
        "label": "BrighterMonday Kenya",
        "url": "https://www.brightermonday.co.ke/jobs",
        "description": "Leader emploi Kenya et Afrique de l'Est",
        "pays": "Kenya",
        "spider": None,
        "priority": PRIORITY_MEDIUM,
        "category": "portail_emploi",
        "active": True,
        "source": "scraping",
    },
    "myjobmag_ke": {
        "label": "MyJobMag Kenya",
        "url": "https://www.myjobmag.com/jobs-in-kenya",
        "description": "Plateforme emploi Kenya",
        "pays": "Kenya",
        "spider": None,
        "priority": PRIORITY_LOW,
        "category": "portail_emploi",
        "active": True,
        "source": "scraping",
    },
    "fuzu_ke": {
        "label": "Fuzu Kenya",
        "url": "https://www.fuzu.com/kenya/jobs",
        "description": "Plateforme emploi et formation Kenya",
        "pays": "Kenya",
        "spider": None,
        "priority": PRIORITY_LOW,
        "category": "portail_emploi",
        "active": True,
        "source": "scraping",
    },
    # ================================================================
    # AFRIQUE DU SUD
    # ================================================================
    "careers24_za": {
        "label": "Careers24 South Africa",
        "url": "https://www.careers24.com/jobs/",
        "description": "Leader portail emploi Afrique du Sud",
        "pays": "Afrique du Sud",
        "spider": None,
        "priority": PRIORITY_MEDIUM,
        "category": "portail_emploi",
        "active": True,
        "source": "scraping",
    },
    "pnet_za": {
        "label": "PNet South Africa",
        "url": "https://www.pnet.co.za/jobs/",
        "description": "Portail emploi Afrique du Sud",
        "pays": "Afrique du Sud",
        "spider": None,
        "priority": PRIORITY_LOW,
        "category": "portail_emploi",
        "active": True,
        "source": "scraping",
    },
    # ================================================================
    # TANZANIE
    # ================================================================
    "brightermonday_tz": {
        "label": "BrighterMonday Tanzania",
        "url": "https://www.brightermonday.co.tz/jobs",
        "description": "Leader emploi Tanzanie",
        "pays": "Tanzanie",
        "spider": None,
        "priority": PRIORITY_LOW,
        "category": "portail_emploi",
        "active": True,
        "source": "scraping",
    },
    "myjobmag_tz": {
        "label": "MyJobMag Tanzania",
        "url": "https://www.myjobmag.com/jobs-in-tanzania",
        "description": "Plateforme emploi Tanzanie",
        "pays": "Tanzanie",
        "spider": None,
        "priority": PRIORITY_NIGHTLY,
        "category": "portail_emploi",
        "active": True,
        "source": "scraping",
    },
    # ================================================================
    # OUGANDA
    # ================================================================
    "brightermonday_ug": {
        "label": "BrighterMonday Uganda",
        "url": "https://www.brightermonday.co.ug/jobs",
        "description": "Leader emploi Ouganda",
        "pays": "Ouganda",
        "spider": None,
        "priority": PRIORITY_LOW,
        "category": "portail_emploi",
        "active": True,
        "source": "scraping",
    },
    # ================================================================
    # ETHIOPIE
    # ================================================================
    "ethiopianjobs": {
        "label": "EthiopianJobs",
        "url": "https://www.ethiopianjobs.com/jobs",
        "description": "Portail emploi ethiopien",
        "pays": "Ethiopie",
        "spider": None,
        "priority": PRIORITY_NIGHTLY,
        "category": "portail_emploi",
        "active": True,
        "source": "scraping",
    },
    # ================================================================
    # RWANDA
    # ================================================================
    "brightermonday_rw": {
        "label": "BrighterMonday Rwanda",
        "url": "https://www.brightermonday.co.rw/jobs",
        "description": "Leader emploi Rwanda",
        "pays": "Rwanda",
        "spider": None,
        "priority": PRIORITY_NIGHTLY,
        "category": "portail_emploi",
        "active": True,
        "source": "scraping",
    },
}
