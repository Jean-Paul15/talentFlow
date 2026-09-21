from typing import Dict, List

from loguru import logger


class GitHubJobsLegacyClient:
    """
    Legacy endpoint retire.
    https://jobs.github.com/positions.json n'est plus operationnel.
    """

    def search_jobs(self) -> List[Dict]:
        logger.warning(
            "GitHub Jobs legacy: endpoint retire, collecte ignoree"
        )
        return []
