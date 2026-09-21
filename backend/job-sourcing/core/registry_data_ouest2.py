# Registre des sites d'emploi - Section AFRIQUE DE L'OUEST suite
# Cameroun, Burkina, Benin, Mali, Niger, Guinee

from .registry_constants import (
    PRIORITY_MEDIUM, PRIORITY_LOW, PRIORITY_NIGHTLY,
)


SITES_AFRIQUE_OUEST_2 = {
    # ================================================================
    # CAMEROUN
    # ================================================================
    "goafricaonline_cm": {
        "label": "GoAfricaOnline (Cameroun)",
        "url": "https://www.goafricaonline.com/cm/emploi",
        "description": "Reseau economique africain - offres Cameroun",
        "pays": "Cameroun",
        "spider": None,
        "priority": PRIORITY_MEDIUM,
        "category": "portail_emploi",
        "active": True,
        "source": "scraping",
    },
    "emploi_cm": {
        "label": "Emploi.cm",
        "url": "https://www.emploi.cm/recherche-jobs-cameroun",
        "description": "Plateforme AfricaTalents Cameroun",
        "pays": "Cameroun",
        "spider": None,
        "priority": PRIORITY_MEDIUM,
        "category": "portail_emploi",
        "active": True,
        "source": "scraping",
    },
    "novojob_cm": {
        "label": "NovoJob Cameroun",
        "url": "https://www.novojob.com/cameroun/offres-emploi",
        "description": "Offres Cameroun via NovoJob",
        "pays": "Cameroun",
        "spider": None,
        "priority": PRIORITY_LOW,
        "category": "portail_emploi",
        "active": True,
        "source": "scraping",
    },
    "kamerpower": {
        "label": "KamerPower",
        "url": "https://kfrfrec.com/emploi/",
        "description": "Offres d'emploi et concours Cameroun",
        "pays": "Cameroun",
        "spider": None,
        "priority": PRIORITY_LOW,
        "category": "portail_emploi",
        "active": True,
        "source": "scraping",
    },
    "camerjob": {
        "label": "CamerJob",
        "url": "https://www.camerjob.com/offres-emploi/",
        "description": "Portail emploi camerounais",
        "pays": "Cameroun",
        "spider": None,
        "priority": PRIORITY_LOW,
        "category": "portail_emploi",
        "active": True,
        "source": "scraping",
    },
    # ================================================================
    # BURKINA FASO
    # ================================================================
    "goafricaonline_bf": {
        "label": "GoAfricaOnline (Burkina Faso)",
        "url": "https://www.goafricaonline.com/bf/emploi",
        "description": "Reseau economique africain - offres Burkina",
        "pays": "Burkina Faso",
        "spider": None,
        "priority": PRIORITY_LOW,
        "category": "portail_emploi",
        "active": True,
        "source": "scraping",
    },
    "emploi_bf": {
        "label": "Emploi.bf",
        "url": "https://www.emploi.bf/recherche-jobs-burkina-faso",
        "description": "Plateforme AfricaTalents Burkina",
        "pays": "Burkina Faso",
        "spider": None,
        "priority": PRIORITY_MEDIUM,
        "category": "portail_emploi",
        "active": True,
        "source": "scraping",
    },
    "novojob_bf": {
        "label": "NovoJob Burkina",
        "url": "https://www.novojob.com/burkina-faso/offres-emploi",
        "description": "Offres Burkina via NovoJob",
        "pays": "Burkina Faso",
        "spider": None,
        "priority": PRIORITY_LOW,
        "category": "portail_emploi",
        "active": True,
        "source": "scraping",
    },
    # ================================================================
    # BENIN
    # ================================================================
    "goafricaonline_bj": {
        "label": "GoAfricaOnline (Benin)",
        "url": "https://www.goafricaonline.com/bj/emploi",
        "description": "Reseau economique africain - offres Benin",
        "pays": "Benin",
        "spider": None,
        "priority": PRIORITY_LOW,
        "category": "portail_emploi",
        "active": True,
        "source": "scraping",
    },
    "emploi_bj": {
        "label": "Emploi.bj",
        "url": "https://www.emploi.bj/recherche-jobs-benin",
        "description": "Plateforme AfricaTalents Benin",
        "pays": "Benin",
        "spider": None,
        "priority": PRIORITY_MEDIUM,
        "category": "portail_emploi",
        "active": True,
        "source": "scraping",
    },
    # ================================================================
    # MALI
    # ================================================================
    "emploi_ml": {
        "label": "Emploi.ml",
        "url": "https://www.emploi.ml/recherche-jobs-mali",
        "description": "Plateforme AfricaTalents Mali",
        "pays": "Mali",
        "spider": None,
        "priority": PRIORITY_MEDIUM,
        "category": "portail_emploi",
        "active": True,
        "source": "scraping",
    },
    "novojob_ml": {
        "label": "NovoJob Mali",
        "url": "https://www.novojob.com/mali/offres-emploi",
        "description": "Offres Mali via NovoJob",
        "pays": "Mali",
        "spider": None,
        "priority": PRIORITY_LOW,
        "category": "portail_emploi",
        "active": True,
        "source": "scraping",
    },
    "maliemploi": {
        "label": "MaliEmploi",
        "url": "https://maliemploi.org/offres-emploi",
        "description": "Portail emploi malien",
        "pays": "Mali",
        "spider": None,
        "priority": PRIORITY_LOW,
        "category": "portail_emploi",
        "active": True,
        "source": "scraping",
    },
    # ================================================================
    # NIGER
    # ================================================================
    "emploi_ne": {
        "label": "Emploi Niger",
        "url": "https://www.emploi.ne/recherche-jobs-niger",
        "description": "Plateforme AfricaTalents Niger",
        "pays": "Niger",
        "spider": None,
        "priority": PRIORITY_LOW,
        "category": "portail_emploi",
        "active": True,
        "source": "scraping",
    },
    "nigeremploi": {
        "label": "NigerEmploi",
        "url": "https://nigeremploi.com/offres-emploi",
        "description": "Portail emploi nigerien",
        "pays": "Niger",
        "spider": None,
        "priority": PRIORITY_NIGHTLY,
        "category": "portail_emploi",
        "active": True,
        "source": "scraping",
    },
    # ================================================================
    # GUINEE
    # ================================================================
    "emploi_gn": {
        "label": "Emploi Guinee",
        "url": "https://www.emploi.gn/recherche-jobs-guinee",
        "description": "Plateforme AfricaTalents Guinee",
        "pays": "Guinee",
        "spider": None,
        "priority": PRIORITY_LOW,
        "category": "portail_emploi",
        "active": True,
        "source": "scraping",
    },
    "guineeemploi": {
        "label": "GuineeEmploi",
        "url": "https://guineeemploi.com/offres-emploi",
        "description": "Portail emploi guineen",
        "pays": "Guinee",
        "spider": None,
        "priority": PRIORITY_NIGHTLY,
        "category": "portail_emploi",
        "active": True,
        "source": "scraping",
    },
}
