"""
Module ML pour le ranking intelligent des recommandations.
"""
from .ranker import MLRankingService
from .config import RankingConfig

__all__ = ["MLRankingService", "RankingConfig"]
