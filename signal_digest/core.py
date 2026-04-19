"""
Core types + the pipeline run() orchestrator.

Signal is the common shape every source produces. Identity is a person's
interests config. Section is a group of signals by source (for rendering).
Digest is the full per-identity output ready for delivery.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Callable, Iterable, Optional, Protocol


# ─────────────────────────────────────────────────────────────
# Domain types
# ─────────────────────────────────────────────────────────────


@dataclass
class Signal:
    """A single item from some source. Small on purpose."""

    source: str               # e.g. "hacker_news", "github_events", "rss:lennys"
    source_label: str         # human-readable, e.g. "Hacker News"
    title: str
    url: str
    published_at: datetime
    summary: str = ""
    tags: list[str] = field(default_factory=list)
    # Engagement — HN points, GitHub star delta, RSS comment count, etc.
    # Used by the ranker. Optional.
    engagement: float = 0.0
    # Free-form — sources can stash their own fields here.
    extra: dict = field(default_factory=dict)


@dataclass
class Identity:
    """
    A single person's (or team's) interest config. Loaded from YAML,
    usually one file per person or one file with a top-level list.
    """

    name: str
    interests: "Interests"
    slack_channel: Optional[str] = None
    slack_user_id: Optional[str] = None
    max_items_per_section: int = 5


@dataclass
class Interests:
    """
    What an Identity cares about. Used by the filter to match Signals.

    - `terms`           — substrings to match in title/summary (case-insensitive)
    - `tags`            — exact-match against Signal.tags
    - `github_repos`    — owner/name strings; sources can use these to scope
    - `rss_feeds`       — list of feed URLs; sources consume these directly
    - `sources`         — names of source adapters to include (empty = all)
    - `exclude_terms`   — substrings that veto a signal even if it matched
    """

    terms: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    github_repos: list[str] = field(default_factory=list)
    rss_feeds: list[str] = field(default_factory=list)
    sources: list[str] = field(default_factory=list)
    exclude_terms: list[str] = field(default_factory=list)


@dataclass
class Section:
    """A group of ranked signals from one source. Rendered as one block."""

    source_label: str
    items: list[Signal]


@dataclass
class Digest:
    identity: Identity
    sections: list[Section]
    generated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def total_items(self) -> int:
        return sum(len(s.items) for s in self.sections)


# ─────────────────────────────────────────────────────────────
# Source + Delivery contracts (Protocols)
# ─────────────────────────────────────────────────────────────


class Source(Protocol):
    """A source adapter yields Signals for the week."""

    name: str       # machine name, e.g. "hacker_news"
    label: str      # human label, e.g. "Hacker News"

    def fetch(self, identity: Identity, since: datetime) -> Iterable[Signal]:
        """Return all raw signals relevant to this identity since `since`."""


class Delivery(Protocol):
    """A delivery adapter takes a rendered digest and ships it."""

    def deliver(self, digest: Digest, rendered: str) -> None: ...


Renderer = Callable[[Digest], str]


# ─────────────────────────────────────────────────────────────
# Pipeline
# ─────────────────────────────────────────────────────────────


def run(
    *,
    identity: Identity,
    sources: list[Source],
    delivery: Delivery,
    renderer: Renderer,
    since: datetime,
) -> Digest:
    """
    End-to-end pipeline for a single identity:
      1. Fetch from every source
      2. Filter + rank
      3. Render
      4. Deliver
    """
    from signal_digest.filter import filter_for
    from signal_digest.rank import rank

    # 1. Fetch
    all_signals: list[Signal] = []
    for source in sources:
        if identity.interests.sources and source.name not in identity.interests.sources:
            continue
        all_signals.extend(list(source.fetch(identity, since)))

    # 2. Filter → group by source → rank → truncate
    matched = filter_for(all_signals, identity)
    by_source: dict[str, list[Signal]] = {}
    for s in matched:
        by_source.setdefault(s.source_label, []).append(s)

    sections: list[Section] = []
    for label, items in by_source.items():
        ranked = rank(items)
        sections.append(Section(source_label=label, items=ranked[: identity.max_items_per_section]))

    digest = Digest(identity=identity, sections=sections)

    # 3 + 4. Render + deliver
    rendered = renderer(digest)
    delivery.deliver(digest, rendered)

    return digest
