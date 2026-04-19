"""
Rank tests — recency wins over engagement; log-scaled engagement keeps
one outlier from dominating.
"""

from datetime import datetime, timedelta, timezone

from signal_digest.core import Signal
from signal_digest.rank import rank


def _sig(title: str, hours_ago: float, engagement: float) -> Signal:
    return Signal(
        source="x",
        source_label="X",
        title=title,
        url="",
        published_at=datetime.now(timezone.utc) - timedelta(hours=hours_ago),
        engagement=engagement,
    )


def test_recency_dominates_when_engagement_tied():
    sigs = [
        _sig("old", hours_ago=100, engagement=50),
        _sig("new", hours_ago=1, engagement=50),
    ]
    ranked = rank(sigs)
    assert ranked[0].title == "new"


def test_engagement_breaks_recency_tie():
    sigs = [
        _sig("quiet", hours_ago=24, engagement=10),
        _sig("loud", hours_ago=24, engagement=1000),
    ]
    ranked = rank(sigs)
    assert ranked[0].title == "loud"


def test_stable_on_single_signal():
    sigs = [_sig("alone", hours_ago=12, engagement=42)]
    assert rank(sigs) == sigs


def test_empty_input():
    assert rank([]) == []
