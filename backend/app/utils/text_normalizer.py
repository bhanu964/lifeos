import re
from typing import Dict, List, Tuple

# Mapping of phonetically misrecognized terms to actual recognized technologies
RECOGNIZED_PRODUCT_MAPPINGS: List[Tuple[re.Pattern, str, str]] = [
    # (Regex pattern, replacement, canonical name)
    (re.compile(r"\bQuadrant\b", re.IGNORECASE), "Qdrant", "Qdrant"),
    (re.compile(r"\bLyzer\b", re.IGNORECASE), "Lyzr", "Lyzr"),
    (re.compile(r"\bLyzzer\b", re.IGNORECASE), "Lyzr", "Lyzr"),
]


def normalize_transcript_text(text: str) -> str:
    """
    Produces a normalized display representation of a voice transcript,
    substituting recognized product names where context is clear.
    
    IMPORTANT: This is strictly for display/presentation and prompt clarity.
    The original raw voice evidence must NEVER be overwritten.
    
    Examples:
        "uses Quadrant for persistent memory" -> "uses Qdrant for persistent memory"
        "On Lyzer for agent orchestration"   -> "On Lyzr for agent orchestration"
    """
    if not text:
        return text

    normalized = text
    for pattern, replacement, _ in RECOGNIZED_PRODUCT_MAPPINGS:
        normalized = pattern.sub(replacement, normalized)

    return normalized


def get_normalized_terms_found(text: str) -> Dict[str, str]:
    """
    Returns a dictionary of original terms found in text that were mapped
    to canonical product names, e.g. {"Quadrant": "Qdrant"}.
    """
    if not text:
        return {}

    found: Dict[str, str] = {}
    for pattern, _, canonical in RECOGNIZED_PRODUCT_MAPPINGS:
        matches = pattern.findall(text)
        for match in matches:
            if match != canonical:
                found[match] = canonical

    return found
