"""
RSS source — one feed per entry in identity.interests.rss_feeds.

Uses only the stdlib (xml.etree, urllib). No feedparser dependency —
it's a nice library but not worth a required dep for a 50-line
implementation of what we need.
"""

from __future__ import annotations

import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from typing import Iterable

from signal_digest.core import Identity, Signal


class RSSSource:
    name = "rss"
    label = "RSS"

    def __init__(self, *, user_agent: str = "weekly-signal-digest/0.1"):
        self.user_agent = user_agent

    def fetch(self, identity: Identity, since: datetime) -> Iterable[Signal]:
        for feed_url in identity.interests.rss_feeds:
            try:
                yield from self._fetch_one(feed_url, since)
            except Exception as e:  # noqa: BLE001
                print(f"[rss] skipping {feed_url}: {e}")

    def _fetch_one(self, url: str, since: datetime) -> Iterable[Signal]:
        req = urllib.request.Request(url, headers={"User-Agent": self.user_agent})
        with urllib.request.urlopen(req, timeout=10) as resp:
            body = resp.read()
        root = ET.fromstring(body)

        # RSS 2.0
        for item in root.iter("item"):
            title = (item.findtext("title") or "").strip()
            link = (item.findtext("link") or "").strip()
            pub = _parse_rss_date(item.findtext("pubDate"))
            if pub is None or pub < since:
                continue
            summary = (item.findtext("description") or "").strip()
            yield Signal(
                source="rss",
                source_label=_feed_label(url, root),
                title=title,
                url=link,
                published_at=pub,
                summary=summary[:280],
                engagement=0.0,
                extra={"feed_url": url},
            )

        # Atom fallback
        atom_ns = "{http://www.w3.org/2005/Atom}"
        for entry in root.iter(f"{atom_ns}entry"):
            title = (entry.findtext(f"{atom_ns}title") or "").strip()
            link_el = entry.find(f"{atom_ns}link")
            link = link_el.get("href") if link_el is not None else ""
            pub = _parse_atom_date(entry.findtext(f"{atom_ns}updated") or entry.findtext(f"{atom_ns}published"))
            if pub is None or pub < since:
                continue
            summary = (entry.findtext(f"{atom_ns}summary") or "").strip()
            yield Signal(
                source="rss",
                source_label=_feed_label(url, root),
                title=title,
                url=link,
                published_at=pub,
                summary=summary[:280],
                extra={"feed_url": url},
            )


def _feed_label(url: str, root: ET.Element) -> str:
    chan_title = root.findtext("channel/title") or root.findtext(
        "{http://www.w3.org/2005/Atom}title"
    )
    if chan_title:
        return f"RSS — {chan_title.strip()}"
    return f"RSS — {url}"


def _parse_rss_date(s: str | None) -> datetime | None:
    if not s:
        return None
    # RFC 822, e.g. "Mon, 14 Apr 2026 14:00:00 +0000"
    try:
        from email.utils import parsedate_to_datetime

        dt = parsedate_to_datetime(s)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except Exception:  # noqa: BLE001
        return None


def _parse_atom_date(s: str | None) -> datetime | None:
    if not s:
        return None
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except Exception:  # noqa: BLE001
        return None
