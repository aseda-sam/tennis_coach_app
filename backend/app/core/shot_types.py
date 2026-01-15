"""Canonical shot type and subtype definitions for tennis ball contacts."""

from typing import Dict, List, Literal

# Allowed stroke types
StrokeType = Literal[
    "ground_stroke",
    "serve",
    "return",
    "volley",
    "overhead",
]

# Stroke subtypes organized by stroke type
STROKE_SUBTYPES_BY_TYPE: Dict[StrokeType, List[str]] = {
    "ground_stroke": [
        "forehand_flat",
        "forehand_topspin",
        "forehand_slice",
        "backhand_flat",
        "backhand_topspin",
        "backhand_slice",
        "drop_shot",
        "lob",
    ],
    "serve": [
        "flat",
        "topspin_kick",
        "slice",
        "underarm",
    ],
    "return": [
        "forehand",
        "backhand",
    ],
    "volley": [
        "forehand",
        "backhand",
        "drop",
        "half",
    ],
    "overhead": [
        "smash",
    ],
}

# All allowed stroke subtypes (flattened for validation)
ALL_STROKE_SUBTYPES: List[str] = [
    subtype for subtypes in STROKE_SUBTYPES_BY_TYPE.values() for subtype in subtypes
]

# Human-readable labels for display
STROKE_TYPE_LABELS: Dict[StrokeType, str] = {
    "ground_stroke": "Ground Stroke",
    "serve": "Serve",
    "return": "Return",
    "volley": "Volley",
    "overhead": "Overhead",
}

STROKE_SUBTYPE_LABELS: Dict[str, str] = {
    # Groundstrokes
    "forehand_flat": "Forehand Flat",
    "forehand_topspin": "Forehand Topspin",
    "forehand_slice": "Forehand Slice",
    "backhand_flat": "Backhand Flat",
    "backhand_topspin": "Backhand Topspin",
    "backhand_slice": "Backhand Slice",
    "drop_shot": "Drop Shot",
    "lob": "Lob",
    # Serves
    "flat": "Flat",
    "topspin_kick": "Topspin/Kick",
    "slice": "Slice",
    "underarm": "Underarm",
    # Returns
    "forehand": "Forehand",
    "backhand": "Backhand",
    # Volleys
    "drop": "Drop",
    "half": "Half Volley",
    # Overhead
    "smash": "Smash",
}


def get_subtypes_for_type(stroke_type: StrokeType | None) -> List[str]:
    """Get allowed subtypes for a given stroke type."""
    if stroke_type is None:
        return []
    return STROKE_SUBTYPES_BY_TYPE.get(stroke_type, [])


def is_valid_subtype_for_type(
    stroke_type: StrokeType | None, stroke_subtype: str | None
) -> bool:
    """Check if a subtype is valid for a given stroke type."""
    if stroke_subtype is None or stroke_subtype == "":
        return True  # Subtype is optional
    if stroke_type is None:
        return False
    return stroke_subtype in get_subtypes_for_type(stroke_type)
