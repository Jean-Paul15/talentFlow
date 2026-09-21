"""
Analyse salariale pour RAG.
"""
import logging
from typing import Dict, Any, List

logger = logging.getLogger(__name__)


def analyze_salary_expectations(
    cv_profile: Dict[str, Any],
    matched_jobs: List[Dict[str, Any]],
    currency: str
) -> Dict[str, str]:
    """Analyse les salaires proposés vs attentes."""
    try:
        salaries = []
        for job in matched_jobs:
            salary_min = job.get('salary_min')
            salary_max = job.get('salary_max')
            if salary_min and salary_max:
                salaries.append((salary_min, salary_max))
        if not salaries:
            return {
                "range": "Non communiqué",
                "position": "Les salaires ne sont généralement pas affichés"
            }
        all_mins = [s[0] for s in salaries]
        all_maxs = [s[1] for s in salaries]
        avg_min = sum(all_mins) / len(all_mins)
        avg_max = sum(all_maxs) / len(all_maxs)
        salary_range = f"{int(avg_min/1000)}K-{int(avg_max/1000)}K {currency}"
        expected_salary = cv_profile.get('expected_salary', 0)
        if expected_salary:
            if expected_salary < avg_min:
                position = "Vos attentes sont en dessous du marché - vous pouvez négocier à la hausse"
            elif expected_salary > avg_max:
                position = "Vos attentes sont au-dessus du marché - soyez flexible sur certains critères"
            else:
                position = "Vos attentes sont alignées avec le marché"
        else:
            position = "Fourchette moyenne du marché pour votre profil"
        return {"range": salary_range, "position": position}
    except Exception as e:
        logger.error(f"Erreur analyse salariale: {e}")
        return {"range": "Non disponible", "position": "Analyse non disponible"}
