"""
AfriPlan Electrical - Drawing Number Parser

Parse and extract information from drawing numbers.
SA electrical drawings typically follow patterns like:
- WD-AB-01-SLD (Wedela - Ablution Block - 01 - Single Line Diagram)
- TJM-E-01-LIGHTING (Project code - Electrical - 01 - Lighting)

No AI/cloud APIs used.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import Optional, List, Dict, Tuple
from enum import Enum

logger = logging.getLogger(__name__)


class DrawingDiscipline(str, Enum):
    """Engineering discipline indicated by drawing code."""
    ELECTRICAL = "electrical"
    LIGHTING = "lighting"
    POWER = "power"
    MECHANICAL = "mechanical"
    ARCHITECTURAL = "architectural"
    STRUCTURAL = "structural"
    UNKNOWN = "unknown"


class DrawingType(str, Enum):
    """Type of drawing based on suffix."""
    SLD = "sld"
    LIGHTING = "lighting"
    PLUGS = "plugs"
    OUTSIDE_LIGHTS = "outside_lights"
    REGISTER = "register"
    DETAIL = "detail"
    SCHEDULE = "schedule"
    PLAN = "plan"
    SECTION = "section"
    UNKNOWN = "unknown"


@dataclass
class DrawingNumberInfo:
    """Parsed information from a drawing number."""
    raw: str = ""
    project_code: str = ""
    building_code: str = ""
    sequence_number: int = 0
    discipline: DrawingDiscipline = DrawingDiscipline.UNKNOWN
    drawing_type: DrawingType = DrawingType.UNKNOWN
    revision: str = ""

    # Confidence in parsing
    valid: bool = False
    confidence: float = 0.0

    # Building block name (if detectable)
    building_block: str = ""

    # Page type suggestion
    suggested_page_type: str = ""


# Building code to block name mapping (from Wedela project)
BUILDING_CODE_MAP = {
    "AB": "Ablution Retail Block",
    "ECH": "Existing Community Hall",
    "LGH": "Large Guard House",
    "SGH": "Small Guard House",
    "PB": "Pool Block",
    "OL": "Site Infrastructure",
    "CA": "Common Area",
    "GF": "Ground Floor",
    "S1": "Suite 1",
    "S2": "Suite 2",
    "S3": "Suite 3",
    "S4": "Suite 4",
}

# Drawing type suffix patterns
TYPE_SUFFIXES = {
    "SLD": DrawingType.SLD,
    "LIGHTING": DrawingType.LIGHTING,
    "LT": DrawingType.LIGHTING,
    "PLUGS": DrawingType.PLUGS,
    "PWR": DrawingType.PLUGS,
    "POWER": DrawingType.PLUGS,
    "OL": DrawingType.OUTSIDE_LIGHTS,
    "EXT": DrawingType.OUTSIDE_LIGHTS,
    "EXTERNAL": DrawingType.OUTSIDE_LIGHTS,
    "DET": DrawingType.DETAIL,
    "DETAIL": DrawingType.DETAIL,
    "SCH": DrawingType.SCHEDULE,
    "SCHEDULE": DrawingType.SCHEDULE,
    "REG": DrawingType.REGISTER,
    "REGISTER": DrawingType.REGISTER,
}

# Discipline indicators
DISCIPLINE_CODES = {
    "E": DrawingDiscipline.ELECTRICAL,
    "EL": DrawingDiscipline.ELECTRICAL,
    "ELEC": DrawingDiscipline.ELECTRICAL,
    "L": DrawingDiscipline.LIGHTING,
    "LT": DrawingDiscipline.LIGHTING,
    "P": DrawingDiscipline.POWER,
    "PWR": DrawingDiscipline.POWER,
    "M": DrawingDiscipline.MECHANICAL,
    "MECH": DrawingDiscipline.MECHANICAL,
    "A": DrawingDiscipline.ARCHITECTURAL,
    "ARCH": DrawingDiscipline.ARCHITECTURAL,
    "S": DrawingDiscipline.STRUCTURAL,
    "STR": DrawingDiscipline.STRUCTURAL,
}


def parse_drawing_number(drawing_number: str) -> DrawingNumberInfo:
    """
    Parse a drawing number and extract information.

    Supports various formats:
    - WD-AB-01-SLD (Project-Building-Seq-Type)
    - TJM-E-01-LIGHTING (Project-Discipline-Seq-Type)
    - E-01-LIGHTING (Discipline-Seq-Type)
    - 01-SLD (Seq-Type)

    Args:
        drawing_number: The drawing number string

    Returns:
        DrawingNumberInfo with parsed components
    """
    result = DrawingNumberInfo(raw=drawing_number)

    if not drawing_number or not drawing_number.strip():
        return result

    # Normalize the drawing number
    dn = drawing_number.strip().upper()
    result.raw = dn

    # Split by common separators
    parts = re.split(r'[-_\s]+', dn)
    parts = [p for p in parts if p]  # Remove empty parts

    if not parts:
        return result

    # Try to identify parts
    result.valid = True
    result.confidence = 0.3  # Base confidence

    # Check last part for drawing type
    last_part = parts[-1] if parts else ""
    for suffix, dtype in TYPE_SUFFIXES.items():
        if suffix in last_part or last_part == suffix:
            result.drawing_type = dtype
            result.confidence += 0.2
            break

    # Check for sequence number (2-3 digit number)
    for part in parts:
        if re.match(r'^\d{1,3}$', part):
            try:
                result.sequence_number = int(part)
                result.confidence += 0.1
            except ValueError:
                pass
            break

    # Check for building code
    for part in parts:
        if part in BUILDING_CODE_MAP:
            result.building_code = part
            result.building_block = BUILDING_CODE_MAP[part]
            result.confidence += 0.2
            break

    # Check for discipline code
    for part in parts:
        if part in DISCIPLINE_CODES:
            result.discipline = DISCIPLINE_CODES[part]
            result.confidence += 0.1
            break

    # Project code is typically the first part (2-4 letters)
    first_part = parts[0] if parts else ""
    if re.match(r'^[A-Z]{2,4}$', first_part) and first_part not in DISCIPLINE_CODES:
        result.project_code = first_part
        result.confidence += 0.1

    # Check for revision (REV A, R01, etc.)
    for part in parts:
        if re.match(r'^(REV|R)[A-Z0-9]+$', part, re.IGNORECASE):
            result.revision = part
            break

    # Map drawing type to suggested page type
    type_to_page = {
        DrawingType.SLD: "sld",
        DrawingType.LIGHTING: "layout_lighting",
        DrawingType.PLUGS: "layout_plugs",
        DrawingType.OUTSIDE_LIGHTS: "outside_lights",
        DrawingType.REGISTER: "register",
        DrawingType.SCHEDULE: "schedule",
        DrawingType.DETAIL: "detail",
    }
    result.suggested_page_type = type_to_page.get(result.drawing_type, "unknown")

    # Cap confidence at 1.0
    result.confidence = min(1.0, result.confidence)

    return result


def extract_drawing_numbers(text: str) -> List[str]:
    """
    Extract all drawing numbers from text.

    Args:
        text: Text to search

    Returns:
        List of unique drawing numbers found
    """
    # Patterns for drawing numbers
    patterns = [
        r'([A-Z]{2,4}-[A-Z]{1,4}-\d{1,3}-[A-Z]+)',  # WD-AB-01-SLD
        r'([A-Z]{2,4}-[A-Z]{1,2}-\d{1,3}-[A-Z]+)',  # TJM-E-01-LIGHTING
        r'([A-Z]{2,4}-\d{1,3}-[A-Z]+)',  # TJM-01-SLD
        r'([A-Z]{1,2}-\d{1,3}-[A-Z]+)',  # E-01-LIGHTING
    ]

    found = set()
    for pattern in patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        for match in matches:
            found.add(match.upper())

    return sorted(list(found))


def match_drawing_to_register(
    drawing_number: str,
    register_entries: List[str],
    fuzzy: bool = True,
) -> Tuple[Optional[str], float]:
    """
    Match a drawing number to an entry in the register.

    Args:
        drawing_number: Drawing number to match
        register_entries: List of drawing numbers from register
        fuzzy: Allow fuzzy matching

    Returns:
        Tuple of (matched_entry, confidence) or (None, 0.0)
    """
    dn_upper = drawing_number.strip().upper()

    # Exact match
    for entry in register_entries:
        if entry.strip().upper() == dn_upper:
            return (entry, 1.0)

    if not fuzzy:
        return (None, 0.0)

    # Fuzzy matching - check if one contains the other
    best_match = None
    best_score = 0.0

    for entry in register_entries:
        entry_upper = entry.strip().upper()

        # Check if one is substring of other
        if dn_upper in entry_upper or entry_upper in dn_upper:
            # Score based on length similarity
            score = min(len(dn_upper), len(entry_upper)) / max(len(dn_upper), len(entry_upper))
            if score > best_score:
                best_score = score
                best_match = entry

        # Check if they share significant parts
        dn_parts = set(re.split(r'[-_\s]+', dn_upper))
        entry_parts = set(re.split(r'[-_\s]+', entry_upper))
        common = dn_parts & entry_parts

        if len(common) >= 2:  # At least 2 parts match
            score = len(common) / max(len(dn_parts), len(entry_parts))
            if score > best_score:
                best_score = score
                best_match = entry

    return (best_match, best_score) if best_score >= 0.5 else (None, 0.0)


def group_drawings_by_block(
    drawing_numbers: List[str]
) -> Dict[str, List[str]]:
    """
    Group drawing numbers by building block.

    Args:
        drawing_numbers: List of drawing numbers

    Returns:
        Dict mapping building block name to drawing numbers
    """
    groups: Dict[str, List[str]] = {}

    for dn in drawing_numbers:
        info = parse_drawing_number(dn)
        block = info.building_block or "Unknown"

        if block not in groups:
            groups[block] = []
        groups[block].append(dn)

    return groups


def group_drawings_by_type(
    drawing_numbers: List[str]
) -> Dict[str, List[str]]:
    """
    Group drawing numbers by drawing type.

    Args:
        drawing_numbers: List of drawing numbers

    Returns:
        Dict mapping drawing type to drawing numbers
    """
    groups: Dict[str, List[str]] = {}

    for dn in drawing_numbers:
        info = parse_drawing_number(dn)
        dtype = info.drawing_type.value

        if dtype not in groups:
            groups[dtype] = []
        groups[dtype].append(dn)

    return groups
