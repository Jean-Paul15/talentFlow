"""
Génération des labels pour learning-to-rank.
"""
import pandas as pd

LABEL_MAP = {
    'view': 1,
    'click': 2,
    'save': 3,
    'apply': 4,
    'reject': 0,
    'read': 2
}


def generate_labels(interactions_df: pd.DataFrame) -> pd.Series:
    """Génère les labels pour learning-to-rank (0-4)."""
    labels = interactions_df['interaction_type'].map(LABEL_MAP)
    read_time_boost = interactions_df['metadata'].apply(
        lambda x: x.get('engagement_score', 0) if isinstance(x, dict) else 0
    )
    labels = labels + read_time_boost
    return labels.clip(0, 4)
