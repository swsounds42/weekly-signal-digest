"""
Dev-mode delivery — prints the rendered digest to stdout.
"""

from signal_digest.core import Digest


class StdoutDelivery:
    name = "stdout"

    def deliver(self, digest: Digest, rendered: str) -> None:
        print(rendered)


def render_text(digest: Digest) -> str:
    """Simple text renderer for stdout."""
    lines = [
        f"▸ {digest.identity.name} — digest generated {digest.generated_at.strftime('%b %d, %Y')}",
        "",
    ]
    for section in digest.sections:
        lines.append(f"{section.source_label}  ({len(section.items)} new)")
        for item in section.items:
            lines.append(f"  ✦ {item.title}")
            if item.summary:
                lines.append(f"      {item.summary}")
            lines.append(f"      {item.url}")
        lines.append("")
    lines.append(f"Total: {digest.total_items} items.")
    return "\n".join(lines)
