# Mapping Elasticsearch pour l'index des offres
# Inclut champ dense_vector pour recherche semantique

INDEX_MAPPING = {
    "mappings": {
        "properties": {
            # Identifiants
            "job_id": {"type": "keyword"},
            "source_url": {"type": "keyword"},
            "source_name": {"type": "keyword"},
            
            # Texte recherchable (BM25)
            "title": {
                "type": "text",
                "analyzer": "french",
                "fields": {"keyword": {"type": "keyword"}}
            },
            "company": {
                "type": "text",
                "fields": {"keyword": {"type": "keyword"}}
            },
            "description": {
                "type": "text",
                "analyzer": "french"
            },
            
            # Filtres exacts
            "location": {"type": "keyword"},
            "country": {"type": "keyword"},
            "contract_type": {"type": "keyword"},
            "sector": {"type": "keyword"},
            
            # Competences (filtrable et recherchable)
            "hard_skills": {"type": "keyword"},
            "soft_skills": {"type": "keyword"},
            
            # Numerique
            "experience_years": {"type": "integer"},
            "salary_min": {"type": "integer"},
            "salary_max": {"type": "integer"},
            
            # Dates
            "posted_date": {"type": "date"},
            "indexed_at": {"type": "date"},
            
            # Vecteur semantique (384 dimensions)
            "description_vector": {
                "type": "dense_vector",
                "dims": 384,
                "index": True,
                "similarity": "cosine"
            },
            
            # Metadata enrichissement
            "enriched": {"type": "boolean"},
            "enrichment_method": {"type": "keyword"},
        }
    }
}
