"""
ELECTRICAL_BLOCK_PATTERNS — the dictionary that drives DXF block recognition.

This is the **single source of truth** for what makes a DXF block name
"electrical." Edit it to extend coverage. The DXF pipeline's
`coverage_score` directly measures how much of any given drawing this
dictionary recognises.

Keep the keys lowercase and alphanumeric-only. We normalise at lookup
time so the pattern table stays readable.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional, Tuple


class FixtureCategory(str, Enum):
    LIGHTING = "lighting"
    POWER = "power"
    SWITCH = "switch"
    DATA = "data"
    SAFETY = "safety"
    HVAC = "hvac"
    WATER = "water"
    DISTRIBUTION = "distribution"
    OTHER = "other"


@dataclass(frozen=True)
class FixtureSpec:
    """One row in the pattern table."""
    canonical_name: str
    category: FixtureCategory
    default_unit_price_zar: float = 0.0   # for ballpark pricing only


# ╔══════════════════════════════════════════════════════════════════╗
# ║ EXACT BLOCK-NAME MAP (short AutoCAD codes)                       ║
# ║ Most native AutoCAD libraries use 1–6 char block names.          ║
# ╚══════════════════════════════════════════════════════════════════╝

EXACT_BLOCK_MAP: Dict[str, FixtureSpec] = {
    # Lighting
    "dl":       FixtureSpec("LED Downlight", FixtureCategory.LIGHTING, 220.0),
    "d/l":      FixtureSpec("LED Downlight", FixtureCategory.LIGHTING, 220.0),
    "downlight":FixtureSpec("LED Downlight", FixtureCategory.LIGHTING, 220.0),
    "fl":       FixtureSpec("Fluorescent Light", FixtureCategory.LIGHTING, 320.0),
    "fluor":    FixtureSpec("Fluorescent Light", FixtureCategory.LIGHTING, 320.0),
    "flood":    FixtureSpec("Floodlight", FixtureCategory.LIGHTING, 650.0),
    "fld":      FixtureSpec("Floodlight", FixtureCategory.LIGHTING, 650.0),
    "bh":       FixtureSpec("Bulkhead Light", FixtureCategory.LIGHTING, 380.0),
    "vp":       FixtureSpec("Vapour Proof Light", FixtureCategory.LIGHTING, 720.0),
    "wl":       FixtureSpec("Wall Light", FixtureCategory.LIGHTING, 280.0),
    "cl":       FixtureSpec("Ceiling Light", FixtureCategory.LIGHTING, 280.0),
    "pendant":  FixtureSpec("Pendant Light", FixtureCategory.LIGHTING, 350.0),
    "panel":    FixtureSpec("LED Panel", FixtureCategory.LIGHTING, 480.0),
    "batten":   FixtureSpec("LED Batten", FixtureCategory.LIGHTING, 280.0),
    "spot":     FixtureSpec("Spotlight", FixtureCategory.LIGHTING, 220.0),

    # Safety
    "em":       FixtureSpec("Emergency Light", FixtureCategory.SAFETY, 850.0),
    "emergency":FixtureSpec("Emergency Light", FixtureCategory.SAFETY, 850.0),
    "exit":     FixtureSpec("Exit Sign", FixtureCategory.SAFETY, 650.0),
    "smoke":    FixtureSpec("Smoke Detector", FixtureCategory.SAFETY, 480.0),
    "pir":      FixtureSpec("PIR Sensor", FixtureCategory.SAFETY, 380.0),

    # Power outlets
    "ds":       FixtureSpec("Double Socket", FixtureCategory.POWER, 160.0),
    "dso":      FixtureSpec("Double Socket", FixtureCategory.POWER, 160.0),
    "ss":       FixtureSpec("Single Socket", FixtureCategory.POWER, 120.0),
    "sso":      FixtureSpec("Single Socket", FixtureCategory.POWER, 120.0),
    "wp":       FixtureSpec("Weatherproof Socket", FixtureCategory.POWER, 280.0),
    "gpo":      FixtureSpec("General Power Outlet", FixtureCategory.POWER, 160.0),
    "fs":       FixtureSpec("Floor Socket", FixtureCategory.POWER, 1800.0),

    # Switches
    "sw1":      FixtureSpec("1-Lever Switch", FixtureCategory.SWITCH, 80.0),
    "sw2":      FixtureSpec("2-Lever Switch", FixtureCategory.SWITCH, 110.0),
    "sw3":      FixtureSpec("3-Lever Switch", FixtureCategory.SWITCH, 140.0),
    "sw":       FixtureSpec("Switch", FixtureCategory.SWITCH, 80.0),
    "iso":      FixtureSpec("Isolator Switch", FixtureCategory.SWITCH, 220.0),
    "dim":      FixtureSpec("Dimmer Switch", FixtureCategory.SWITCH, 280.0),
    "dn":       FixtureSpec("Day/Night Switch", FixtureCategory.SWITCH, 480.0),
    "d/n":      FixtureSpec("Day/Night Switch", FixtureCategory.SWITCH, 480.0),

    # Data
    "data":     FixtureSpec("Data Socket", FixtureCategory.DATA, 450.0),
    "rj45":     FixtureSpec("Data Socket (RJ45)", FixtureCategory.DATA, 450.0),
    "tel":      FixtureSpec("Telephone Socket", FixtureCategory.DATA, 280.0),
    "tv":       FixtureSpec("Television Socket", FixtureCategory.DATA, 220.0),

    # Distribution
    "db":       FixtureSpec("Distribution Board", FixtureCategory.DISTRIBUTION, 4500.0),

    # HVAC / water
    "ac":       FixtureSpec("Air Conditioning Unit", FixtureCategory.HVAC, 8500.0),
    "aircon":   FixtureSpec("Air Conditioning Unit", FixtureCategory.HVAC, 8500.0),
    "geyser":   FixtureSpec("Geyser", FixtureCategory.WATER, 4500.0),
    "hwc":      FixtureSpec("Hot Water Cylinder", FixtureCategory.WATER, 4500.0),
    "ef":       FixtureSpec("Extractor Fan", FixtureCategory.HVAC, 850.0),
}


# ╔══════════════════════════════════════════════════════════════════╗
# ║ REGEX FALLBACKS (long descriptive ArchiCAD-style block names)    ║
# ║ Tried in order; first match wins.                                ║
# ╚══════════════════════════════════════════════════════════════════╝

REGEX_BLOCK_PATTERNS: List[Tuple[re.Pattern[str], FixtureSpec]] = [
    (re.compile(r"socket\s*outlet.*2\s*gang", re.I),
        FixtureSpec("Double Socket Outlet", FixtureCategory.POWER, 160.0)),
    (re.compile(r"socket\s*outlet.*1\s*gang", re.I),
        FixtureSpec("Single Socket Outlet", FixtureCategory.POWER, 120.0)),
    (re.compile(r"socket\s*outlet", re.I),
        FixtureSpec("Socket Outlet", FixtureCategory.POWER, 160.0)),
    (re.compile(r"switch\s*\d", re.I),
        FixtureSpec("Switch", FixtureCategory.SWITCH, 80.0)),
    (re.compile(r"distribution\s*board", re.I),
        FixtureSpec("Distribution Board", FixtureCategory.DISTRIBUTION, 4500.0)),
    (re.compile(r"air\s*condition", re.I),
        FixtureSpec("Air Conditioning Unit", FixtureCategory.HVAC, 8500.0)),
    (re.compile(r"\b(led|light|lamp|luminaire)\b", re.I),
        FixtureSpec("Light Fitting (generic)", FixtureCategory.LIGHTING, 280.0)),
    (re.compile(r"\bextinguisher\b", re.I),
        FixtureSpec("Fire Extinguisher", FixtureCategory.SAFETY, 950.0)),
]


# ╔══════════════════════════════════════════════════════════════════╗
# ║ BLOCKS TO IGNORE (architectural / furniture / plumbing)          ║
# ╚══════════════════════════════════════════════════════════════════╝

SKIP_BLOCK_PATTERNS: List[re.Pattern[str]] = [
    re.compile(r"^(wall|column|slab|roof|morph|stair|railing)_\d+$", re.I),
    re.compile(r"workstation|basin|cabinet|\bwc\b|door|window", re.I),
    re.compile(r"furniture|swing\s*reel", re.I),
    re.compile(r"^a\$c|^architectural", re.I),
]


def _normalise(name: str) -> str:
    """Lower-case and trim non-alphanumeric prefixes/suffixes."""
    return name.strip().lower()


def is_skip_block_name(name: str) -> bool:
    """
    True if `name` matches an architectural / furniture / plumbing pattern
    that should be ignored entirely (not added to 'unrecognised').
    """
    if not name:
        return False
    norm = _normalise(name)
    return any(p.search(norm) for p in SKIP_BLOCK_PATTERNS)


def classify_block_name(name: str) -> Optional[FixtureSpec]:
    """
    Return a FixtureSpec for `name`, or None if it's not electrical.

    The lookup is two-stage:
      1. Exact match against EXACT_BLOCK_MAP after normalising
      2. Regex search against REGEX_BLOCK_PATTERNS

    Names matching SKIP_BLOCK_PATTERNS return None immediately. Use
    `is_skip_block_name()` separately if you need to distinguish
    'known-non-electrical' from 'unknown'.
    """
    if not name:
        return None

    norm = _normalise(name)

    if is_skip_block_name(name):
        return None

    if norm in EXACT_BLOCK_MAP:
        return EXACT_BLOCK_MAP[norm]

    # Strip trailing digits or suffixes, e.g. "DL_001" -> "dl"
    stripped = re.sub(r"[_\-\s]?\d+$", "", norm).strip()
    if stripped and stripped in EXACT_BLOCK_MAP:
        return EXACT_BLOCK_MAP[stripped]

    # Drop leading prefixes like "ELEC$" / "E-"
    short = re.sub(r"^[a-z]+\$|^e[-_]", "", stripped)
    if short and short in EXACT_BLOCK_MAP:
        return EXACT_BLOCK_MAP[short]

    for regex, spec in REGEX_BLOCK_PATTERNS:
        if regex.search(norm):
            return spec

    return None
