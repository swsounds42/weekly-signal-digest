"""
Rank signals within a source.

Score = recency * 0.6 + engagement_normalized * 0.4.

Recency: fresher is better, linearly decayed across the 7-day window.
Engagement: log-scaled then normalized per-source so GitHub stars and HN
points aren't directly compared.

Tune weights in-place for your use case. This is intentionally simple
because the interesting work is in `filter.py`.
"""

from __future__ import annotations

import math
from datetime import datetime, timedelta, timezone

from signal_digest.core import Signal

_WINDOW = timedelta(days=7)


def _recency_score(s: Signal, now: datetime) -> float:
    age = (now - s.published_at).total_seconds()
    window = _WINDOW.total_seconds()
    if age <= 0:
        return 1.0
    if age >= window:
        return 0.0
    return 1.0 - (age / window)


def rank(signals: list[Signal]) -> list[Signal]:
    if not signals:
        return []

    now = datetime.now(timezone.utc)

    # Per-batch engagement normalization — log then min/max to [0,1]
    eng_vals = [max(s.engagement, 0) for s in signals]
    log_eng = [math.log1p(v) for v in eng_vals]
    lo, hi = (min(log_eng), max(log_eng)) if log_eng else (0.0, 0.0)
    span = (hi - lo) or 1.0

    def score(s: Signal) -> float:
        recency = _recency_score(s, now)
        engagement = (math.log1p(max(s.engagement, 0)) - lo) / span
        return 0.6 * recency + 0.4 * engagement

    return sorted(signals, key=score, reverse=True)
