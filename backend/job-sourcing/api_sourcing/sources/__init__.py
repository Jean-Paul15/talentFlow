# Sources API avec dossiers dedies.

from .adzuna.client import AdzunaClient
from .arbeitnow.client import ArbeitnowClient
from .github_jobs_legacy.client import GitHubJobsLegacyClient
from .hackernews.client import HackerNewsClient
from .joindata.client import JoinDataClient
from .jsearch.client import JSearchClient
from .remotive.client import RemotiveClient
from .remoteok.client import RemoteOkClient

__all__ = [
    "AdzunaClient",
    "ArbeitnowClient",
    "GitHubJobsLegacyClient",
    "HackerNewsClient",
    "JoinDataClient",
    "JSearchClient",
    "RemotiveClient",
    "RemoteOkClient",
]
