"""
Deterministic per-identity filter.

A Signal matches an Identity if ANY of:
  - any interest `term` appears in title or summary (case-insensitive), OR
  - any interest `tag` is present in Signal.tags, OR
  - the Signal is from a source that scoped itself to this identity's
    config (GitHub repos, RSS feeds) — those arrive pre-filtered by
    definition.

And NONE of the `exclude_terms` appear in title or summary.

Pure function. No randomness, no model calls. Given the same inputs,
always the same output — which is what makes "why did you miss X?"
debuggable.
"""

from __future__ import annotations

from typing import Iterable

from signal_digest.core import Identity, Signal


def filter_for(signals: Iterable[Signal], identity: Identity) -> list[Signal]:
    interests = identity.interests
    terms = [t.lower() for t in interests.terms]
    excludes = [t.lower() for t in interests.exclude_terms]
    tags = set(interests.tags)
    repos = set(interests.github_repos)
    feeds = set(interests.rss_feeds)

    out: list[Signal] = []
    for s in signals:
        # Search title + summary + tags — tags carry source-query hints
        # (e.g. "hn:revops") that should count as matches for the raw term.
        haystack = f"{s.title}\n{s.summary}\n{' '.join(s.tags)}".lower()

        # Excludes short-circuit
        if any(x in haystack for x in excludes):
            continue

        term_hit = any(t in haystack for t in terms)
        tag_hit = bool(tags and tags.intersection(s.tags))

        # Pre-scoped sources — if the source already narrowed by repo/feed,
        # trust it and admit.
        repo_scoped = bool(
            repos and any(tag == f"repo:{r}" for r in repos for tag in s.tags)
        )
        feed_scoped = bool(
            feeds and s.extra.get("feed_url") in feeds
        )

        # If identity has no narrowing config at all, pass everything through.
        if not terms and not tags and not repos and not feeds:
            out.append(s)
            continue

        if term_hit or tag_hit or repo_scoped or feed_scoped:
            out.append(s)

    return out
