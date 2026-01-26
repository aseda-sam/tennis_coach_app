"""Serve subtype definitions for tennis serve analysis (serve MVP focus)."""

# Serve subtypes (only stroke type supported in MVP)
SERVE_SUBTYPES: list[str] = ["flat", "topspin_kick", "slice", "underarm"]

# Human-readable labels for serve subtypes
SERVE_SUBTYPE_LABELS: dict[str, str] = {
    "flat": "Flat",
    "topspin_kick": "Topspin/Kick",
    "slice": "Slice",
    "underarm": "Underarm",
}


def is_valid_serve_subtype(subtype: str | None) -> bool:
    """Check if a serve subtype is valid.

    Args:
        subtype: Serve subtype to validate (e.g., "flat", "slice")

    Returns:
        True if subtype is valid or None (optional field), False otherwise
    """
    if subtype is None:
        return True  # Optional field
    return subtype in SERVE_SUBTYPES
