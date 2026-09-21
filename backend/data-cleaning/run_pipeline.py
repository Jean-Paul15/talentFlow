# Point d'entree pour executer le pipeline
# Peut etre appele directement ou via Airflow

import argparse
from datetime import datetime, timedelta

from loguru import logger

from pipeline import CleaningPipeline


def main():
    """
    Point d'entree principal.
    """
    parser = argparse.ArgumentParser(description="Pipeline de nettoyage TalentFlow")
    parser.add_argument(
        "--since-hours",
        type=int,
        default=24,
        help="Traiter les offres des N dernieres heures"
    )
    parser.add_argument(
        "--site",
        type=str,
        default=None,
        help="Filtrer par site source (ex: emploi_tg)"
    )
    parser.add_argument(
        "--full",
        action="store_true",
        help="Traiter toutes les offres sans filtre de date"
    )
    
    args = parser.parse_args()
    
    # Configuration du logging
    logger.add("logs/pipeline_{time}.log", rotation="10 MB")
    
    # Calcul de la date de debut
    since_date = None
    if not args.full:
        since_date = datetime.utcnow() - timedelta(hours=args.since_hours)
    
    # Execution du pipeline
    pipeline = CleaningPipeline()
    stats = pipeline.run(since_date=since_date, site_prefix=args.site)
    
    # Affichage des resultats
    logger.info("=== RESULTATS ===")
    logger.info(f"Offres traitees: {stats['processed']}")
    logger.info(f"Offres stockees: {stats['stored']}")
    logger.info(f"Offres ignorees: {stats['skipped']}")
    logger.info(f"Erreurs: {stats['errors']}")
    
    return 0 if stats["errors"] == 0 else 1


if __name__ == "__main__":
    exit(main())
