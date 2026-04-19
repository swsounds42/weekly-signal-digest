"""
Slack delivery — ships a block-formatted message to an incoming webhook.

Pass the webhook URL via env var SLACK_WEBHOOK_URL or directly to the
constructor. The Identity's `slack_channel` is used as a hint only; the
webhook itself is channel-bound when you create it.
"""

from __future__ import annotations

import json
import os
import urllib.request
from typing import Optional

from signal_digest.core import Digest


class SlackDelivery:
    name = "slack"

    def __init__(self, webhook_url: Optional[str] = None):
        self.webhook_url = webhook_url or os.environ.get("SLACK_WEBHOOK_URL")
        if not self.webhook_url:
            raise ValueError(
                "Slack webhook URL not set. Pass one in or set SLACK_WEBHOOK_URL."
            )

    def deliver(self, digest: Digest, rendered: str) -> None:
        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"Weekly digest — {digest.identity.name}",
                },
            },
        ]
        for section in digest.sections:
            if not section.items:
                continue
            block_lines = [f"*{section.source_label}*  _({len(section.items)} new)_", ""]
            for item in section.items:
                line = f"• <{item.url}|{item.title}>"
                if item.summary:
                    line += f"\n   _{item.summary}_"
                block_lines.append(line)
            blocks.append({"type": "section", "text": {"type": "mrkdwn", "text": "\n".join(block_lines)}})
            blocks.append({"type": "divider"})

        payload = {
            "text": f"Weekly digest for {digest.identity.name}",
            "blocks": blocks,
        }
        req = urllib.request.Request(
            self.webhook_url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            resp.read()
