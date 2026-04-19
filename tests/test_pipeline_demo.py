"""
End-to-end pipeline test using bundled fixtures.

Proves the full Identity → fixture source → filter → rank → render →
stdout delivery loop works.
"""

from datetime import datetime, timedelta, timezone
from pathlib import Path

from signal_digest.core import Identity, Interests, run
from signal_digest.delivery.stdout import StdoutDelivery, render_text
from signal_digest.cli import FixtureSource


FIXTURES = Path(__file__).parent.parent / "fixtures"


class _CaptureDelivery:
    """Stand-in StdoutDelivery that captures instead of printing."""

    def __init__(self):
        self.captured = ""

    def deliver(self, digest, rendered):  # noqa: ARG002
        self.captured = rendered


def test_jane_pipeline_filters_and_ranks():
    # Jane cares about attribution + developer tooling + platform stuff.
    # She explicitly excludes crypto.
    jane = Identity(
        name="Jane",
        interests=Interests(
            terms=["attribution", "revops", "developer", "platform", "pipeline forecasting",
                   "product review"],
            github_repos=["anthropic/claude-code", "vercel/next.js"],
            rss_feeds=["https://lennysnewsletter.com/feed"],
            exclude_terms=["crypto"],
        ),
    )
    source = FixtureSource(name="demo", label="Demo", path=FIXTURES / "signals.jsonl")
    capture = _CaptureDelivery()

    digest = run(
        identity=jane,
        sources=[source],
        delivery=capture,
        renderer=render_text,
        since=datetime.now(timezone.utc) - timedelta(days=30),
    )

    # Crypto item gets excluded even though we have no term blocking it directly.
    titles = [item.title for section in digest.sections for item in section.items]
    assert not any("Bitcoin" in t for t in titles), "crypto exclude should have vetoed"

    # Attribution HN story should be present.
    assert any("Attribution" in t for t in titles)

    # Output should be non-empty.
    assert "Jane" in capture.captured
    assert digest.total_items > 0
