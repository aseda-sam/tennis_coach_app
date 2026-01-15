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


def map_legacy_subtype_to_canonical(
    stroke_type: StrokeType | None, legacy_subtype: str | None
) -> str | None:
    """Map legacy subtype values to canonical subtypes.

    This function handles common legacy free-text subtypes and maps them
    to the appropriate canonical subtype based on stroke_type.

    Args:
        stroke_type: The stroke type (e.g., "ground_stroke", "serve")
        legacy_subtype: Legacy subtype value (e.g., "forehand", "backhand")

    Returns:
        Canonical subtype if mapping exists, None if no mapping possible
    """
    if not legacy_subtype or not stroke_type:
        return None

    # Normalize to lowercase for comparison
    legacy_lower = legacy_subtype.lower().strip()

    # Mapping rules based on stroke type
    if stroke_type == "ground_stroke":
        # Map common legacy values to ground stroke subtypes
        if legacy_lower in ["forehand", "fh"]:
            return "forehand_flat"  # Default to flat for generic forehand
        elif legacy_lower in ["backhand", "bh"]:
            return "backhand_flat"  # Default to flat for generic backhand
        elif legacy_lower in ["topspin", "top"] or legacy_lower in ["slice", "sliced"]:
            # Can't determine forehand vs backhand, return None
            return None
        elif legacy_lower in ["drop", "drop shot", "dropshot"]:
            return "drop_shot"
        elif legacy_lower == "lob":
            return "lob"
    elif stroke_type == "serve":
        if legacy_lower in ["flat", "hard"]:
            return "flat"
        elif legacy_lower in ["topspin", "kick", "topspin kick", "topspin_kick"]:
            return "topspin_kick"
        elif legacy_lower in ["slice", "sliced"]:
            return "slice"
        elif legacy_lower in ["underarm", "under arm", "under-arm"]:
            return "underarm"
    elif stroke_type == "return":
        # "forehand" and "backhand" are already valid for return
        if legacy_lower in ["forehand", "fh"]:
            return "forehand"
        elif legacy_lower in ["backhand", "bh"]:
            return "backhand"
    elif stroke_type == "volley":
        # "forehand", "backhand", "drop" are already valid for volley
        if legacy_lower in ["forehand", "fh"]:
            return "forehand"
        elif legacy_lower in ["backhand", "bh"]:
            return "backhand"
        elif legacy_lower == "drop":
            return "drop"
        elif legacy_lower in ["half", "half volley", "half_volley"]:
            return "half"
    elif stroke_type == "overhead" and legacy_lower in ["smash", "overhead"]:
        return "smash"

    # No mapping found
    return None
