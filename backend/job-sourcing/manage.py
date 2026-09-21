# Script principal pour gerer les spiders
# Permet d'executer, lister et gerer les spiders de scraping

import argparse
import importlib
import sys
from pathlib import Path

from loguru import logger

# Configuration du logging
logger.remove()
logger.add(
    sys.stdout,
    format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}",
    level="INFO"
)
logger.add(
    "logs/scraping_{time:YYYY-MM-DD}.log",
    rotation="1 day",
    retention="30 days",
    level="DEBUG"
)


def get_available_spiders() -> list:
    """
    Liste tous les spiders disponibles dans le dossier spiders/.
    
    Returns:
        Liste des noms de spiders disponibles
    """
    spiders_path = Path(__file__).parent / "spiders"
    spiders = []

    for item in spiders_path.iterdir():
        if item.is_dir() and not item.name.startswith("__"):
            spider_file = item / "spider.py"
            if spider_file.exists():
                spiders.append(item.name)

    return spiders


def run_spider(spider_name: str) -> None:
    """
    Execute un spider specifique.
    
    Args:
        spider_name: Nom du spider a executer
    """
    try:
        module_path = f"spiders.{spider_name}.spider"
        module = importlib.import_module(module_path)

        if hasattr(module, "Spider"):
            spider = module.Spider()
            logger.info(f"Demarrage du spider: {spider_name}")
            spider.run()

            stats = spider.get_stats()
            logger.info(f"Statistiques: {stats}")
        else:
            logger.error(f"Classe Spider non trouvee dans {module_path}")

    except ModuleNotFoundError as err:
        logger.error(f"Spider non trouve: {spider_name} - {err}")
    except Exception as err:
        logger.error(f"Erreur lors de l'execution de {spider_name}: {err}")


def run_all_spiders() -> None:
    """
    Execute tous les spiders disponibles.
    """
    spiders = get_available_spiders()
    logger.info(f"Execution de {len(spiders)} spider(s)")

    for spider_name in spiders:
        run_spider(spider_name)


def list_spiders() -> None:
    """
    Affiche la liste des spiders disponibles.
    """
    spiders = get_available_spiders()

    if spiders:
        logger.info("Spiders disponibles:")
        for spider in spiders:
            print(f"  - {spider}")
    else:
        logger.warning("Aucun spider disponible")


def main() -> None:
    """
    Point d'entree principal du script.
    """
    parser = argparse.ArgumentParser(
        description="Gestionnaire de spiders TalentFlow"
    )

    subparsers = parser.add_subparsers(dest="command", help="Commandes")

    # Commande: run
    run_parser = subparsers.add_parser("run", help="Executer un spider")
    run_parser.add_argument(
        "spider",
        nargs="?",
        help="Nom du spider (ou 'all' pour tous)"
    )

    # Commande: list
    subparsers.add_parser("list", help="Lister les spiders")

    args = parser.parse_args()

    if args.command == "run":
        if args.spider == "all":
            run_all_spiders()
        elif args.spider:
            run_spider(args.spider)
        else:
            parser.print_help()

    elif args.command == "list":
        list_spiders()

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
