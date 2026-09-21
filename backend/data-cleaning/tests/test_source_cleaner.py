from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from processors.source_cleaner import SourceCleaner


def test_clean_emploi_tg_uses_location_from_title_when_field_is_polluted():
    cleaner = SourceCleaner()

    raw_job = {
        "source_name": "emploi_tg",
        "title": "Stagiaire en Laravel et Vue.js - Lomé",
        "location": "Etudiant, jeune diplômé - Débutant < 2 ans - Expérience entre 2 ans et 5 ans",
        "source_url": "https://www.emploi.tg/offre-emploi-togo/stagiaire-laravel-vuejs-lome-354334",
    }
    cleaned = cleaner.clean(dict(raw_job), raw_job)

    assert cleaned["location"] == "Lome"
    assert cleaned["country"] == "Togo"


def test_clean_emploi_tg_overrides_wrong_togo_location_with_explicit_city():
    cleaner = SourceCleaner()

    raw_job = {
        "source_name": "emploi_tg",
        "title": "Développeur web - Yaoundé",
        "location": "Lome",
        "source_url": "https://www.emploi.tg/offre-emploi-togo/developpeur-web-yaounde-357594",
    }
    cleaned = cleaner.clean(dict(raw_job), raw_job)

    assert cleaned["location"] == "Yaounde"
    assert cleaned["country"] == "Cameroun"


def test_clean_emploi_tg_marks_remote_jobs_as_international():
    cleaner = SourceCleaner()

    raw_job = {
        "source_name": "emploi_tg",
        "title": "IT Business Developer Bilingue - Télétravail",
        "location": "Expérience entre 2 ans et 5 ans - Expérience entre 5 ans et 10 ans",
        "source_url": "https://www.emploi.tg/offre-emploi-togo/it-business-developer-bilingue-teletravail-352346",
    }
    cleaned = cleaner.clean(dict(raw_job), raw_job)

    assert cleaned["location"] == "Remote"
    assert cleaned["country"] == "International"
