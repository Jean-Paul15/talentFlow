"""
Script de création d'indexes MongoDB pour performance.
Exécuter une fois après déploiement.
"""

from pymongo import MongoClient, ASCENDING, DESCENDING, TEXT
from pymongo.errors import OperationFailure
import os

# Connection
MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://mongodb:27017")
client = MongoClient(MONGODB_URI)
db = client["talentflow"]

print("🔧 Création indexes MongoDB pour TalentFlow...")

# Collection: jobs_silver (offres nettoyées)
jobs_collection = db["jobs_silver"]

# Index 1: source + processed_at (pour DAG queries)
print("  → Index: source + processed_at")
jobs_collection.create_index(
    [("source", ASCENDING), ("processed_at", DESCENDING)],
    name="idx_source_processed",
    background=True,
)

# Index 2: indexed_in_es (pour search-engine queries)
print("  → Index: indexed_in_es")
jobs_collection.create_index(
    [("indexed_in_es", ASCENDING), ("processed_at", DESCENDING)],
    name="idx_indexed_es",
    background=True,
)

# Index 3: dedup_hash (pour deduplication rapide)
print("  → Index: dedup_hash (unique)")
jobs_collection.create_index(
    [("dedup_hash", ASCENDING)],
    name="idx_dedup_hash",
    unique=True,
    background=True,
)

# Index 4: title + location (pour recherche rapide)
print("  → Index: title + location")
jobs_collection.create_index(
    [("title", TEXT), ("location", ASCENDING)],
    name="idx_title_location",
    background=True,
)

# Index 5: hard_skills (pour matching)
print("  → Index: hard_skills")
jobs_collection.create_index(
    [("hard_skills", ASCENDING)],
    name="idx_hard_skills",
    background=True,
)

# Index 6: experience_years + seniority (pour filtering)
print("  → Index: experience_years + seniority")
jobs_collection.create_index(
    [("experience_years", ASCENDING), ("seniority", ASCENDING)],
    name="idx_experience_seniority",
    background=True,
)

print("\n✅ Indexes créés avec succès!")

# Afficher stats
print("\n📊 Stats collection jobs_silver:")
stats = db.command("collstats", "jobs_silver")
print(f"  Documents: {stats['count']}")
print(f"  Taille: {stats['size'] / 1024 / 1024:.2f} MB")
print(f"  Indexes: {stats['nindexes']}")

# Lister tous les indexes
print("\n📑 Indexes actifs:")
for idx in jobs_collection.list_indexes():
    print(f"  - {idx['name']}: {idx['key']}")
