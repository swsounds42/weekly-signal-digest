"""
GitHub events source — uses the public Releases API for each repo an
identity follows.

Unauthenticated requests are rate-limited at 60/hour per IP, which is
plenty for a Monday-morning run across ~30 repos. Pass a GITHUB_TOKEN
env var to raise that to 5,000/hour.
"""

from __future__ import annotations

import json
import os
import urllib.request
from datetime import datetime
from typing import Iterable

from signal_digest.core import Identity, Signal


class GitHubEventsSource:
    name = "github_events"
    label = "GitHub Events"

    def __init__(self, *, token: str | None = None):
        self.token = token or os.environ.get("GITHUB_TOKEN")

    def fetch(self, identity: Identity, since: datetime) -> Iterable[Signal]:
        for repo in identity.interests.github_repos:
            try:
                yield from self._releases(repo, since)
            except Exception as e:  # noqa: BLE001
                print(f"[github] skipping {repo}: {e}")

    def _releases(self, repo: str, since: datetime) -> Iterable[Signal]:
        url = f"https://api.github.com/repos/{repo}/releases?per_page=10"
        headers = {
            "Accept": "application/vnd.github+json",
            "User-Agent": "weekly-signal-digest/0.1",
        }
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=10) as resp:
            releases = json.loads(resp.read())

        for r in releases:
            published = _parse(r.get("published_at"))
            if published is None or published < since:
                continue
            yield Signal(
                source="github_events",
                source_label="GitHub Events",
                title=f"{repo} released {r.get('name') or r.get('tag_name')}",
                url=r.get("html_url") or f"https://github.com/{repo}",
                published_at=published,
                summary=(r.get("body") or "")[:280],
                engagement=0.0,
                tags=[f"repo:{repo}", "release"],
                extra={"repo": repo, "tag": r.get("tag_name")},
            )


def _parse(s: str | None) -> datetime | None:
    if not s:
        return None
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except Exception:  # noqa: BLE001
        return None
