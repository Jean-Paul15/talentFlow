# Registre des sites d'emploi - Section AFRIQUE CENTRALE et MAGHREB
# Congo, RDC, Gabon, Tchad, Centrafrique, Tunisie, Maroc, Algerie

from .registry_constants import (
    PRIORITY_MEDIUM, PRIORITY_LOW, PRIORITY_NIGHTLY,
)


SITES_AFRIQUE_CENTRALE_MAGHREB = {
    # ================================================================
    # CONGO / RDC
    # ================================================================
    "emploi_cd": {
        "label": "Emploi.cd",
        "url": "https://www.emploi.cd/recherche-jobs-rdc",
        "description": "Plateforme AfricaTalents RDC",
        "pays": "RDC",
        "spider": None,
        "priority": PRIORITY_MEDIUM,
        "category": "portail_emploi",
        "active": True,
        "source": "scraping",
    },
    "novojob_cd": {
        "label": "NovoJob RDC",
        "url": "https://www.novojob.com/rdc/offres-emploi",
        "description": "Offres RDC via NovoJob",
        "pays": "RDC",
        "spider": None,
        "priority": PRIORITY_LOW,
        "category": "portail_emploi",
        "active": True,
        "source": "scraping",
    },
    "emploi_cg": {
        "label": "Emploi Congo-Brazzaville",
        "url": "https://www.emploi.cg/recherche-jobs-congo",
        "description": "Plateforme AfricaTalents Congo",
        "pays": "Congo",
        "spider": None,
        "priority": PRIORITY_LOW,
        "category": "portail_emploi",
        "active": True,
        "source": "scraping",
    },
    # ================================================================
    # GABON
    # ================================================================
    "emploi_ga": {
        "label": "Emploi.ga",
        "url": "https://www.emploi.ga/recherche-jobs-gabon",
        "description": "Plateforme AfricaTalents Gabon",
        "pays": "Gabon",
        "spider": None,
        "priority": PRIORITY_LOW,
        "category": "portail_emploi",
        "active": True,
        "source": "scraping",
    },
    "goafricaonline_ga": {
        "label": "GoAfricaOnline (Gabon)",
        "url": "https://www.goafricaonline.com/ga/emploi",
        "description": "Reseau economique - offres Gabon",
        "pays": "Gabon",
        "spider": None,
        "priority": PRIORITY_NIGHTLY,
        "category": "portail_emploi",
        "active": True,
        "source": "scraping",
    },
    # ================================================================
    # TCHAD
    # ================================================================
    "emploi_td": {
        "label": "Emploi Tchad",
        "url": "https://www.emploi.td/recherche-jobs-tchad",
        "description": "Plateforme AfricaTalents Tchad",
        "pays": "Tchad",
        "spider": None,
        "priority": PRIORITY_NIGHTLY,
        "category": "portail_emploi",
        "active": True,
        "source": "scraping",
    },
    # ================================================================
    # MADAGASCAR
    # ================================================================
    "emploi_mg": {
        "label": "Emploi.mg",
        "url": "https://www.emploi.mg/recherche-jobs-madagascar",
        "description": "Plateforme AfricaTalents Madagascar",
        "pays": "Madagascar",
        "spider": None,
        "priority": PRIORITY_LOW,
        "category": "portail_emploi",
        "active": True,
        "source": "scraping",
    },
    "moov_mg": {
        "label": "Moov Madagascar",
        "url": "https://www.moov.mg/emploi",
        "description": "Portail annonces et emploi Madagascar",
        "pays": "Madagascar",
        "spider": None,
        "priority": PRIORITY_NIGHTLY,
        "category": "portail_emploi",
        "active": True,
        "source": "scraping",
    },
    # ================================================================
    # TUNISIE
    # ================================================================
    "emploi_tn": {
        "label": "Emploi.tn",
        "url": "https://www.emploi.tn/offre-emploi-tunisie",
        "description": "Premier portail emploi Tunisie",
        "pays": "Tunisie",
        "spider": None,
        "priority": PRIORITY_MEDIUM,
        "category": "portail_emploi",
        "active": True,
        "source": "scraping",
    },
    "tanitjobs": {
        "label": "TanitJobs",
        "url": "https://www.tanitjobs.com/jobs/",
        "description": "Portail emploi tunisien",
        "pays": "Tunisie",
        "spider": None,
        "priority": PRIORITY_LOW,
        "category": "portail_emploi",
        "active": True,
        "source": "scraping",
    },
    # ================================================================
    # MAROC
    # ================================================================
    "emploi_ma": {
        "label": "Emploi.ma",
        "url": "https://www.emploi.ma/recherche-jobs-maroc",
        "description": "Plateforme AfricaTalents Maroc",
        "pays": "Maroc",
        "spider": None,
        "priority": PRIORITY_MEDIUM,
        "category": "portail_emploi",
        "active": True,
        "source": "scraping",
    },
    "rekrute_ma": {
        "label": "ReKrute.com",
        "url": "https://www.rekrute.com/offres-emploi.html",
        "description": "Leader portail emploi Maroc",
        "pays": "Maroc",
        "spider": None,
        "priority": PRIORITY_MEDIUM,
        "category": "portail_emploi",
        "active": True,
        "source": "scraping",
    },
    "marocannonces_emploi": {
        "label": "MarocAnnonces Emploi",
        "url": "https://www.marocannonces.com/categorie/emploi/",
        "description": "Section emploi du portail MarocAnnonces",
        "pays": "Maroc",
        "spider": None,
        "priority": PRIORITY_LOW,
        "category": "portail_emploi",
        "active": True,
        "source": "scraping",
    },
    # ================================================================
    # ALGERIE
    # ================================================================
    "emploitic_dz": {
        "label": "Emploitic",
        "url": "https://www.emploitic.com/offres-emploi",
        "description": "Leader portail emploi Algerie",
        "pays": "Algerie",
        "spider": None,
        "priority": PRIORITY_MEDIUM,
        "category": "portail_emploi",
        "active": True,
        "source": "scraping",
    },
    "emploi_dz": {
        "label": "Emploi Algerie",
        "url": "https://www.emploi.dz/recherche-jobs-algerie",
        "description": "Plateforme AfricaTalents Algerie",
        "pays": "Algerie",
        "spider": None,
        "priority": PRIORITY_LOW,
        "category": "portail_emploi",
        "active": True,
        "source": "scraping",
    },
}
