"""
Réexport des composants du data collector.
"""
from .interaction_types import InteractionType
from .data_collector_core import UserInteractionCollector

__all__ = ["InteractionType", "UserInteractionCollector"]
