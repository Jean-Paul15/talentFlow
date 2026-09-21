# Fonctions utilitaires partagees


def format_bytes(n: int) -> str:
    """Formate une taille en octets de facon lisible."""
    for unit in ("o", "Ko", "Mo", "Go"):
        if abs(n) < 1024:
            return f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} To"
