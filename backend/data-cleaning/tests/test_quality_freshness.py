from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from processors.quality_freshness import annotate_quality_and_freshness


def test_quality_freshness_marks_expired_and_keeps_quality_signals():
    now = datetime(2026, 3, 6, tzinfo=timezone.utc)
    job = {
        "title": "Assistant Comptable H/F",
        "location": "Lome",
        "country": "Togo",
        "description": "Gestion comptable, rapprochement bancaire, paie, facturation et reporting sur un poste permanent.",
        "deadline_iso": "2026-03-01",
        "apply_email": "recrutement@example.com",
    }

    out = annotate_quality_and_freshness(job, now=now)

    assert out["is_expired"] is True
    assert out["is_stale"] is False
    assert out["stale_reason"] == "expired"
    assert out["quality_score"] > 0.5
    assert out["apply_confidence"] == 1.0


def test_quality_freshness_marks_international_offer_as_stale_when_ttl_exceeded():
    now = datetime(2026, 3, 6, tzinfo=timezone.utc)
    posted = (now - timedelta(days=38)).date().isoformat()
    job = {
        "title": "Remote Data Analyst",
        "source_name": "remotive_api",
        "location": "Remote",
        "country": "International",
        "description": "Python, SQL, dashboards, analytics, experimentation, stakeholder communication." * 4,
        "posted_date_iso": posted,
        "apply_url": "https://example.com/apply",
    }

    out = annotate_quality_and_freshness(job, now=now)

    assert out["freshness_source"] == "posted_date_iso"
    assert out["freshness_days"] == 38
    assert out["freshness_ttl_days"] == 21
    assert out["is_stale"] is True
    assert out["stale_reason"] == "ttl_exceeded:38>21"
