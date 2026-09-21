"""
Insights marché pour RAG.
"""
import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)


def generate_market_insights(
    cv_profile: Dict[str, Any],
    matched_jobs: List[Dict[str, Any]],
    market_data: Optional[Dict[str, Any]],
    llm
) -> str:
    """Génère des insights sur le marché du travail."""
    try:
        job_titles = [job.get('title', '') for job in matched_jobs[:10]]
        locations = [job.get('location', {}).get('city', '') for job in matched_jobs[:10]]
        contract_types = {}
        remote_options = {}
        for job in matched_jobs:
            contract = job.get('contract_type', 'unknown')
            remote = job.get('remote_work', 'none')
            contract_types[contract] = contract_types.get(contract, 0) + 1
            remote_options[remote] = remote_options.get(remote, 0) + 1
        most_common_contract = max(contract_types.items(), key=lambda x: x[1])[0] if contract_types else 'CDI'
        most_common_remote = max(remote_options.items(), key=lambda x: x[1])[0] if remote_options else 'hybrid'
        prompt = f"""Génère un insight concis sur le marché du travail pour ce profil:

PROFIL: {cv_profile.get('job_title', 'Professionnel')} avec {cv_profile.get('total_experience_years', 0)} ans d'expérience

MARCHÉ ACTUEL (basé sur {len(matched_jobs)} offres):
- Postes principaux: {', '.join(set(job_titles[:5]))}
- Localités: {', '.join(set(filter(None, locations[:5])))}
- Type de contrat dominant: {most_common_contract}
- Options remote: {most_common_remote}

Génère UN insight marché (2-3 lignes max) incluant:
- Demande actuelle pour ce profil
- Tendances (remote, types de postes, etc.)
- Recommandation stratégique

Réponse (texte court, pas de JSON):"""
        insights = llm.invoke(prompt).strip()
        return insights[:500]
    except Exception as e:
        logger.error(f"Erreur génération insights: {e}")
        return "Marché actif avec plusieurs opportunités correspondant au profil."
