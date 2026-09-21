"""
Types d'interactions utilisateur.
"""
from enum import Enum


class InteractionType(str, Enum):
    """Types d'interactions utilisateur."""
    VIEW = "view"
    CLICK = "click"
    SAVE = "save"
    APPLY = "apply"
    REJECT = "reject"
    READ = "read"
