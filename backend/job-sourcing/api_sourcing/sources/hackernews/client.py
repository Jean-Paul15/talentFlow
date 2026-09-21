from datetime import datetime
from typing import Dict, List, Optional

import httpx
from loguru import logger


class HackerNewsClient:
    """
    Client Hacker News officiel.
    Endpoint fiable utilise: /jobstories + /item/{id}.
    """

    BASE_URL = "https://hacker-news.firebaseio.com/v0"

    def fetch_jobs(self, limit: int = 100) -> List[Dict]:
        try:
            with httpx.Client(timeout=20) as client:
                stories_response = client.get(f"{self.BASE_URL}/jobstories.json")
                stories_response.raise_for_status()
                story_ids = stories_response.json()

                if not isinstance(story_ids, list):
                    return []

                jobs: List[Dict] = []
                for story_id in story_ids:
                    story = self._fetch_item(client, story_id)
                    normalized = self._normalize(story_id, story)
                    if normalized:
                        jobs.append(normalized)
                    if len(jobs) >= limit:
                        break

            logger.info(f"HackerNews: {len(jobs)} offres")
            return jobs
        except Exception as err:
            logger.error(f"HackerNews erreur: {err}")
            return []

    def _fetch_item(self, client: httpx.Client, item_id: int) -> Optional[Dict]:
        response = client.get(f"{self.BASE_URL}/item/{item_id}.json")
        response.raise_for_status()
        payload = response.json()
        return payload if isinstance(payload, dict) else None

    def _normalize(self, story_id: int, story: Optional[Dict]) -> Optional[Dict]:
        if not story:
            return None
        if story.get("type") != "job":
            return None

        title = story.get("title")
        if not title:
            return None

        posted_ts = story.get("time")
        if posted_ts:
            posted_date = datetime.utcfromtimestamp(posted_ts).isoformat()
        else:
            posted_date = datetime.utcnow().isoformat()

        source_url = story.get("url") or f"https://news.ycombinator.com/item?id={story_id}"

        return {
            "title": title,
            "company": "Hacker News Community",
            "location": "International",
            "description": story.get("text", "") or "",
            "source_url": source_url,
            "source_name": "hackernews_api",
            "country": "International",
            "sector": "Tech",
            "contract_type": "",
            "salary": "",
            "skills": [],
            "posted_date": posted_date,
            "apply_url": source_url,
            "contact_email": None,
            "contact_phone": None,
            "experience": None,
            "education": None,
            "deadline": None,
            "recruiter_name": "Hacker News",
            "extra_data": {
                "api_source": "hackernews",
                "story_id": story_id,
                "by": story.get("by"),
                "score": story.get("score"),
            },
        }
