"""
Weekly Signal Digest — a per-identity Monday-morning briefing pipeline.

Public API:
    from signal_digest import run, Identity, Signal
    from signal_digest.sources import RSSSource, HackerNewsSource, GitHubEventsSource
    from signal_digest.delivery import SlackDelivery, StdoutDelivery
"""

from signal_digest.core import Digest, Identity, Section, Signal, run

__all__ = ["Digest", "Identity", "Section", "Signal", "run"]
__version__ = "0.1.0"
