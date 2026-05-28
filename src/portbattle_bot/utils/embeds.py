"""Helper embed builders for portbattle bot (placeholder).

Add helpers here as needed.
"""

def build_portbattle_embed(*, title: str, fields: list[tuple[str, str, bool]] = None, color: int | None = None):
    # Placeholder factory — cogs currently construct embeds directly.
    return {
        "title": title,
        "fields": fields or [],
        "color": color,
    }
