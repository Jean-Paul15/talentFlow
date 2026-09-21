# Script CLI pour indexer les offres

import argparse

from loguru import logger

from services.job_indexer_qdrant import QdrantJobIndexer
from services.qdrant_index_manager import QdrantIndexManager
from core.mongo_reader import MongoReader


def main():
    """
    Point d'entree CLI pour l'indexation.
    """
    parser = argparse.ArgumentParser(description="Indexeur TalentFlow")
    parser.add_argument(
        "--reindex",
        action="store_true",
        help="Reindexer toutes les offres (supprime l'index existant)"
    )
    parser.add_argument(
        "--create-index",
        action="store_true",
        help="Creer uniquement l'index sans indexer"
    )
    parser.add_argument(
        "--status",
        action="store_true",
        help="Afficher le statut de l'index"
    )
    
    args = parser.parse_args()
    logger.info("Backend d'indexation: qdrant")
    if args.status:
        manager = QdrantIndexManager()
        mongo = MongoReader()
        print(f"Collection existe: {manager.collection_exists()}")
        print(f"Documents: {manager.get_doc_count()}")
        print(f"Collection: {manager.collection_name}")
        print(f"Delta pending (Qdrant): {mongo.count_jobs_delta('qdrant')}")
        return

    if args.create_index:
        manager = QdrantIndexManager()
        manager.create_collection(force=args.reindex)
        return

    indexer = QdrantJobIndexer()
    stats = indexer.index_all(reindex=args.reindex)
    logger.info(f"Resultat (Qdrant): {stats}")


if __name__ == "__main__":
    main()
