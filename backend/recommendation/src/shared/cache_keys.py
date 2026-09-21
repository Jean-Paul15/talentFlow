"""
Génération de clés de cache.
"""
import hashlib


def generate_cache_key(prefix: str, *args, **kwargs) -> str:
    """Génère une clé de cache unique basée sur les arguments."""
    data = str(args) + str(sorted(kwargs.items()))
    hash_value = hashlib.md5(data.encode()).hexdigest()
    return f"{prefix}{hash_value}"
