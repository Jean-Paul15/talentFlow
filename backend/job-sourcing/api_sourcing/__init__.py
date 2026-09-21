# Module de collecte via APIs gratuites.
# Le dossier `sources/` contient un dossier dedie par source.

from .collector import run_api_collection
from .sources import (
    AdzunaClient,
    ArbeitnowClient,
    GitHubJobsLegacyClient,
    HackerNewsClient,
    JoinDataClient,
    JSearchClient,
    RemotiveClient,
    RemoteOkClient,
)

__all__ = [
    "AdzunaClient",
    "ArbeitnowClient",
    "GitHubJobsLegacyClient",
    "HackerNewsClient",
    "JoinDataClient",
    "JSearchClient",
    "RemotiveClient",
    "RemoteOkClient",
    "run_api_collection",
]
