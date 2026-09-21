"""
Calcul du score d'engagement basé sur le temps de lecture.
"""

def calculate_engagement_score(read_seconds: int) -> float:
    """Calcule un score d'engagement basé sur le temps de lecture."""
    if read_seconds < 5:
        return 0.0
    if read_seconds < 15:
        return 0.3
    if read_seconds < 30:
        return 0.6
    return 1.0
