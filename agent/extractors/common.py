"""
AfriPlan Electrical - Common Extraction Utilities

Shared utilities for deterministic extraction:
- Text normalization
- Regex finders for cables, DBs, circuits
- Unit parsing
- Deduplication helpers

No AI/cloud APIs used.
"""

from __future__ import annotations

import logging
import re
from typing import List, Dict, Set, Optional, Tuple, Any
from dataclasses import dataclass

logger = logging.getLogger(__name__)


# ============================================================================
# TEXT NORMALIZATION
# ============================================================================

def normalize_text(text: str) -> str:
    """
    Normalize text for consistent matching.

    - Convert to lowercase
    - Normalize whitespace
    - Remove special characters (keep alphanumeric, basic punctuation)
    """
    if not text:
        return ""

    # Normalize whitespace
    text = " ".join(text.split())

    # Convert to lowercase for comparison
    text = text.lower()

    return text.strip()


def clean_text_for_display(text: str) -> str:
    """
    Clean text for display (keep case, normalize whitespace).
    """
    if not text:
        return ""

    # Normalize whitespace only
    return " ".join(text.split()).strip()


def remove_special_chars(text: str, keep_pattern: str = r'[\w\s\-\.\/\(\)²]') -> str:
    """
    Remove special characters, keeping alphanumeric and specified chars.
    """
    return re.sub(f'[^{keep_pattern[1:-1]}]', '', text)


# ============================================================================
# CABLE SIZE EXTRACTION
# ============================================================================

# Common cable size patterns in SA electrical drawings
CABLE_SIZE_PATTERNS = [
    r'(\d+(?:\.\d+)?)\s*mm[²2]',           # 2.5mm², 4mm2
    r'(\d+(?:\.\d+)?)\s*sq\.?\s*mm',       # 4 sq mm
    r'(\d+)x(\d+(?:\.\d+)?)\s*mm[²2]',     # 4x2.5mm²
    r'(\d+)[cC]x?(\d+(?:\.\d+)?)\s*mm[²2]', # 4Cx2.5mm², 4C 4mm²
    r'(\d+)\s*[cC]ore[s]?\s*[xX]?\s*(\d+(?:\.\d+)?)\s*mm[²2]',  # 4 cores x 2.5mm²
]

# Cable type patterns
CABLE_TYPE_PATTERNS = [
    r'(PVC\s*SWA\s*PVC)',       # Standard armoured
    r'(SWA)',                   # Steel Wire Armoured
    r'(XLPE)',                  # Cross-linked polyethylene
    r'(PILC)',                  # Paper Insulated Lead Covered
    r'(NYY)',                   # PVC insulated
    r'(NYM)',                   # Sheathed cable
]


@dataclass
class CableSpec:
    """Parsed cable specification."""
    size_mm2: float = 0.0
    cores: int = 0
    cable_type: str = ""
    raw_text: str = ""
    is_3phase: bool = False


def extract_cable_sizes(text: str) -> List[CableSpec]:
    """
    Extract all cable sizes from text.

    Args:
        text: Text to search

    Returns:
        List of CableSpec objects
    """
    results = []
    seen = set()

    text_upper = text.upper()

    for pattern in CABLE_SIZE_PATTERNS:
        for match in re.finditer(pattern, text, re.IGNORECASE):
            raw = match.group(0)
            key = raw.lower()

            if key in seen:
                continue
            seen.add(key)

            spec = CableSpec(raw_text=raw)

            # Parse cores and size
            groups = match.groups()
            if len(groups) >= 2:
                try:
                    spec.cores = int(groups[0])
                    spec.size_mm2 = float(groups[1])
                except (ValueError, IndexError):
                    pass
            elif len(groups) == 1:
                try:
                    spec.size_mm2 = float(groups[0])
                except ValueError:
                    pass

            # Determine if 3-phase (4 core typically)
            spec.is_3phase = spec.cores >= 4

            # Try to find cable type nearby
            for type_pattern in CABLE_TYPE_PATTERNS:
                type_match = re.search(type_pattern, text_upper)
                if type_match:
                    spec.cable_type = type_match.group(1)
                    break

            results.append(spec)

    return results


def format_cable_spec(size_mm2: float, cores: int = 0, cable_type: str = "") -> str:
    """Format a cable specification string."""
    parts = []

    if cores > 0:
        parts.append(f"{cores}C")

    parts.append(f"{size_mm2}mm²")

    if cable_type:
        parts.append(cable_type)

    return " ".join(parts)


# ============================================================================
# DISTRIBUTION BOARD EXTRACTION
# ============================================================================

# DB reference patterns
DB_REF_PATTERNS = [
    r'(DB[-\s]?[A-Z0-9]+)',           # DB-S1, DB-GF, DB S2
    r'(D\.?B\.?\s*[A-Z0-9]+)',        # D.B. S1
    r'(MSB)',                         # Main Switch Board
    r'(MDB)',                         # Main Distribution Board
    r'(Kiosk)',                       # Eskom Kiosk
    r'(Sub[-\s]?Board\s*\d*)',        # Sub-Board 1
]


def extract_db_refs(text: str) -> List[str]:
    """
    Extract distribution board references from text.

    Args:
        text: Text to search

    Returns:
        List of unique DB references
    """
    found = set()

    for pattern in DB_REF_PATTERNS:
        for match in re.finditer(pattern, text, re.IGNORECASE):
            ref = match.group(1).upper().strip()
            # Normalize spacing
            ref = re.sub(r'[\s\.\-]+', '-', ref)
            found.add(ref)

    return sorted(list(found))


def parse_db_name(db_ref: str) -> Tuple[str, str]:
    """
    Parse a DB reference into name and location hint.

    Examples:
        "DB-S1" -> ("DB-S1", "Suite 1")
        "DB-GF" -> ("DB-GF", "Ground Floor")

    Returns:
        Tuple of (db_name, location_hint)
    """
    db_ref = db_ref.upper().strip()

    # Location hints based on common abbreviations
    location_map = {
        "GF": "Ground Floor",
        "FF": "First Floor",
        "1F": "First Floor",
        "2F": "Second Floor",
        "CA": "Common Area",
        "S1": "Suite 1",
        "S2": "Suite 2",
        "S3": "Suite 3",
        "S4": "Suite 4",
        "AB": "Ablution Block",
        "PB": "Pool Block",
        "ECH": "Community Hall",
        "LGH": "Large Guard House",
        "SGH": "Small Guard House",
    }

    location = ""
    for code, loc_name in location_map.items():
        if code in db_ref:
            location = loc_name
            break

    return (db_ref, location)


# ============================================================================
# CIRCUIT EXTRACTION
# ============================================================================

# Circuit ID patterns
CIRCUIT_ID_PATTERNS = [
    r'\b(L\d+)\b',           # Lighting: L1, L2
    r'\b(P\d+)\b',           # Power: P1, P2
    r'\b(AC\d+)\b',          # Air conditioning: AC1
    r'\b(ISO\d+)\b',         # Isolator: ISO1
    r'\b(PP\d+)\b',          # Pool pump: PP1
    r'\b(HP\d+)\b',          # Heat pump: HP1
    r'\b(CP\d+)\b',          # Circulation pump: CP1
    r'\b(D/N\d*)\b',         # Day/Night: D/N, D/N1
    r'\b(RWB\d*)\b',         # Red-White-Blue phase designation
    r'\b(GY\d+)\b',          # Geyser: GY1
    r'\b(ST\d+)\b',          # Stove: ST1
]


def extract_circuit_ids(text: str) -> List[str]:
    """
    Extract circuit IDs from text.

    Args:
        text: Text to search

    Returns:
        List of unique circuit IDs
    """
    found = set()

    for pattern in CIRCUIT_ID_PATTERNS:
        for match in re.finditer(pattern, text, re.IGNORECASE):
            cid = match.group(1).upper().strip()
            found.add(cid)

    return sorted(list(found))


def classify_circuit_type(circuit_id: str) -> str:
    """
    Classify circuit type from circuit ID.

    Args:
        circuit_id: Circuit identifier (L1, P1, AC1, etc.)

    Returns:
        Circuit type string
    """
    circuit_id = circuit_id.upper()

    if circuit_id.startswith('L'):
        return "lighting"
    elif circuit_id.startswith('P'):
        return "power"
    elif circuit_id.startswith('AC'):
        return "aircon"
    elif circuit_id.startswith('ISO'):
        return "isolator"
    elif circuit_id.startswith('PP'):
        return "pool_pump"
    elif circuit_id.startswith('HP'):
        return "heat_pump"
    elif circuit_id.startswith('CP'):
        return "circulation_pump"
    elif circuit_id.startswith('D/N') or circuit_id.startswith('DN'):
        return "day_night"
    elif circuit_id.startswith('GY'):
        return "geyser"
    elif circuit_id.startswith('ST'):
        return "stove"
    elif circuit_id.startswith('SP'):
        return "spare"
    else:
        return "other"


# ============================================================================
# ROOM LABELS
# ============================================================================

# Common room label patterns
ROOM_PATTERNS = [
    r'\b(SUITE\s*\d+)\b',
    r'\b(BEDROOM\s*\d*)\b',
    r'\b(BATHROOM\s*\d*)\b',
    r'\b(KITCHEN\s*\d*)\b',
    r'\b(LOUNGE)\b',
    r'\b(LIVING\s*ROOM)\b',
    r'\b(DINING\s*ROOM)\b',
    r'\b(OFFICE\s*\d*)\b',
    r'\b(RECEPTION)\b',
    r'\b(LOBBY)\b',
    r'\b(CORRIDOR\s*\d*)\b',
    r'\b(PASSAGE)\b',
    r'\b(STORE\s*ROOM?\s*\d*)\b',
    r'\b(GUARD\s*HOUSE)\b',
    r'\b(POOL\s*AREA)\b',
    r'\b(CHANGING\s*ROOM)\b',
    r'\b(ABLUTION\s*\d*)\b',
    r'\b(WC\s*\d*)\b',
    r'\b(TOILET\s*\d*)\b',
    r'\b(ENTRANCE)\b',
    r'\b(FOYER)\b',
]


def extract_room_labels(text: str) -> List[str]:
    """
    Extract room labels from text.

    Args:
        text: Text to search

    Returns:
        List of unique room labels
    """
    found = set()

    for pattern in ROOM_PATTERNS:
        for match in re.finditer(pattern, text, re.IGNORECASE):
            room = match.group(1).strip()
            # Normalize
            room = " ".join(room.split()).title()
            found.add(room)

    return sorted(list(found))


# ============================================================================
# NUMERIC PARSING
# ============================================================================

def parse_wattage(text: str) -> Optional[float]:
    """
    Parse wattage value from text.

    Handles: 500W, 0.5kW, 500 watts, etc.
    """
    # Try kW first
    kw_match = re.search(r'(\d+(?:\.\d+)?)\s*kW', text, re.IGNORECASE)
    if kw_match:
        return float(kw_match.group(1)) * 1000

    # Try W
    w_match = re.search(r'(\d+(?:\.\d+)?)\s*W(?:att)?', text, re.IGNORECASE)
    if w_match:
        return float(w_match.group(1))

    return None


def parse_current(text: str) -> Optional[float]:
    """
    Parse current rating from text.

    Handles: 20A, 20 Amp, 20 amps, etc.
    """
    match = re.search(r'(\d+(?:\.\d+)?)\s*[aA](?:mp)?s?', text)
    if match:
        return float(match.group(1))
    return None


def parse_length(text: str) -> Optional[float]:
    """
    Parse length/distance from text.

    Handles: 50m, 50 meters, 50 metres, etc.
    """
    match = re.search(r'(\d+(?:\.\d+)?)\s*m(?:eter|etre)?s?', text, re.IGNORECASE)
    if match:
        return float(match.group(1))
    return None


def parse_height(text: str) -> Optional[int]:
    """
    Parse mounting height from text.

    Handles: @300mm, 300mm AFF, 300mm above floor, etc.
    """
    match = re.search(r'@?\s*(\d+)\s*mm', text, re.IGNORECASE)
    if match:
        return int(match.group(1))
    return None


# ============================================================================
# DEDUPLICATION
# ============================================================================

def dedupe_strings(items: List[str], case_insensitive: bool = True) -> List[str]:
    """
    Remove duplicates from list while preserving order.
    """
    seen = set()
    result = []

    for item in items:
        key = item.lower() if case_insensitive else item
        if key not in seen:
            seen.add(key)
            result.append(item)

    return result


def merge_similar_strings(items: List[str], threshold: float = 0.8) -> List[str]:
    """
    Merge similar strings (e.g., "Suite 1" and "SUITE 1").
    Keeps the first occurrence.
    """
    result = []

    for item in items:
        is_duplicate = False
        for existing in result:
            if _string_similarity(item, existing) >= threshold:
                is_duplicate = True
                break

        if not is_duplicate:
            result.append(item)

    return result


def _string_similarity(a: str, b: str) -> float:
    """
    Calculate simple string similarity (0-1).
    Uses character overlap ratio.
    """
    a_lower = a.lower()
    b_lower = b.lower()

    if a_lower == b_lower:
        return 1.0

    if not a_lower or not b_lower:
        return 0.0

    # Character set overlap
    set_a = set(a_lower)
    set_b = set(b_lower)
    overlap = len(set_a & set_b)
    total = len(set_a | set_b)

    return overlap / total if total > 0 else 0.0
