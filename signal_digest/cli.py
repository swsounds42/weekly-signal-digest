"""
CLI entrypoint — run the pipeline for every identity in a YAML config.

    python -m signal_digest.cli \
        --identities path/to/identities.yaml \
        [--since 7d] \
        [--demo]                        # use cached fixtures instead of live sources
        [--delivery slack|stdout]       # default: stdout

In --demo mode, a bundled JSONL of prefetched signals is used so you
can see the pipeline end-to-end without a network or API tokens.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import yaml

from signal_digest.core import Identity, Interests, run, Signal
from signal_digest.delivery import SlackDelivery, StdoutDelivery
from signal_digest.delivery.stdout import render_text


def parse_since(s: str) -> datetime:
    if s.endswith("d"):
        days = int(s[:-1])
        return datetime.now(timezone.utc) - timedelta(days=days)
    if s.endswith("h"):
        hours = int(s[:-1])
        return datetime.now(timezone.utc) - timedelta(hours=hours)
    return datetime.fromisoformat(s)


def load_identities(path: Path) -> list[Identity]:
    data = yaml.safe_load(path.read_text())
    identities: list[Identity] = []
    for row in data:
        interests = Interests(**(row.get("interests") or {}))
        identities.append(
            Identity(
                name=row["name"],
                interests=interests,
                slack_channel=row.get("slack_channel"),
                slack_user_id=row.get("slack_user_id"),
                max_items_per_section=row.get("max_items_per_section", 5),
            )
        )
    return identities


class FixtureSource:
    """Source adapter that replays signals from a JSONL file. Dev/demo only."""

    def __init__(self, *, name: str, label: str, path: Path):
        self.name = name
        self.label = label
        self.path = path

    def fetch(self, identity, since):  # noqa: ARG002
        for line in self.path.read_text().splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            yield Signal(
                source=row["source"],
                source_label=row["source_label"],
                title=row["title"],
                url=row["url"],
                published_at=datetime.fromisoformat(row["published_at"]),
                summary=row.get("summary", ""),
                tags=row.get("tags", []),
                engagement=row.get("engagement", 0.0),
                extra=row.get("extra", {}),
            )


def main() -> int:
    parser = argparse.ArgumentParser(prog="signal_digest")
    parser.add_argument("--identities", type=Path, required=True)
    parser.add_argument("--since", default="7d")
    parser.add_argument("--demo", action="store_true",
                        help="use bundled fixtures/signals.jsonl instead of live sources")
    parser.add_argument("--delivery", choices=["slack", "stdout"], default="stdout")
    args = parser.parse_args()

    since = parse_since(args.since)
    identities = load_identities(args.identities)

    # Build sources
    if args.demo:
        fixture_path = Path(__file__).resolve().parent.parent / "fixtures" / "signals.jsonl"
        sources = [FixtureSource(name="demo", label="Demo", path=fixture_path)]
    else:
        # Lazy import to skip network deps in --demo
        from signal_digest.sources import GitHubEventsSource, HackerNewsSource, RSSSource

        sources = [HackerNewsSource(), GitHubEventsSource(), RSSSource()]

    delivery = SlackDelivery() if args.delivery == "slack" else StdoutDelivery()

    for identity in identities:
        run(
            identity=identity,
            sources=sources,
            delivery=delivery,
            renderer=render_text,
            since=since,
        )

    return 0


if __name__ == "__main__":
    sys.exit(main())
