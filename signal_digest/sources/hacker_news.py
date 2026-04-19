"""
Hacker News source — uses the HN Algolia search API.

Doesn't fetch everything — searches HN stories from the last 7 days
matching the identity's interest terms. Scoped by term because
otherwise you'd be pulling the entire front page.
"""

from __future__ import annotations

import json
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from typing import Iterable

from signal_digest.core import Identity, Signal

_BASE = "https://hn.algolia.com/api/v1/search_by_date"


class HackerNewsSource:
    name = "hacker_news"
    label = "Hacker News"

    def __init__(self, *, hits_per_term: int = 10, min_points: int = 10):
        self.hits_per_term = hits_per_term
        self.min_points = min_points

    def fetch(self, identity: Identity, since: datetime) -> Iterable[Signal]:
        since_ts = int(since.timestamp())
        for term in identity.interests.terms:
            try:
                yield from self._search(term, since_ts)
            except Exception as e:  # noqa: BLE001
                print(f"[hn] skipping '{term}': {e}")

    def _search(self, term: str, since_ts: int) -> Iterable[Signal]:
        params = {
            "query": term,
            "tags": "story",
            "numericFilters": f"created_at_i>{since_ts},points>{self.min_points - 1}",
            "hitsPerPage": self.hits_per_term,
        }
        url = f"{_BASE}?{urllib.parse.urlencode(params)}"
        req = urllib.request.Request(url, headers={"User-Agent": "weekly-signal-digest/0.1"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            body = json.loads(resp.read())
        for hit in body.get("hits", []):
            created = datetime.fromtimestamp(hit["created_at_i"], tz=timezone.utc)
            story_url = hit.get("url") or f"https://news.ycombinator.com/item?id={hit['objectID']}"
            yield Signal(
                source="hacker_news",
                source_label="Hacker News",
                title=hit.get("title") or "",
                url=story_url,
                published_at=created,
                summary=f"{hit.get('points', 0)} points · {hit.get('num_comments', 0)} comments",
                engagement=float(hit.get("points", 0)),
                tags=[f"hn:{term}"],
                extra={"query_term": term, "object_id": hit.get("objectID")},
            )
