"""
AfriPlan Electrical v1.0 - Circuit Label Scanner

Scan layout drawings for circuit labels (L1, L2, P1, P2, etc.)
NO LLM CALLS - pure regex pattern matching.

Circuit labels on layouts indicate which DB circuit powers each fixture.
This allows cross-referencing with SLD circuit counts.

Usage:
    from agent.extractors.circuit_label_scanner import scan_circuit_labels

    labels = scan_circuit_labels(page_text)
    # Returns: {"L1": 5, "L2": 3, "P1": 8, ...}
"""

import re
from typing import List, Dict, Set, Optional, Tuple
from dataclasses import dataclass, field
from collections import Counter

from agent.models import ItemConfidence


@dataclass
class CircuitLabel:
    """A single circuit label found on layout."""
    label: str  # e.g., "L1", "P2"
    circuit_type: str  # "lighting", "power", "dedicated"
    db_ref: str = ""  # e.g., "DB-GF" if prefixed
    count: int = 1
    confidence: ItemConfidence = ItemConfidence.EXTRACTED


@dataclass
class CircuitLabelScanResult:
    """Complete scan result for a layout page."""
    labels: Dict[str, int] = field(default_factory=dict)  # label -> count
    by_type: Dict[str, Dict[str, int]] = field(default_factory=dict)  # type -> {label: count}
    by_db: Dict[str, Dict[str, int]] = field(default_factory=dict)  # db -> {label: count}
    total_lighting_points: int = 0
    total_power_points: int = 0
    total_dedicated_points: int = 0
    db_refs_found: List[str] = field(default_factory=list)
    confidence: float = 0.0


# Circuit label patterns
CIRCUIT_PATTERNS = {
    # Lighting circuits: L1, L2, L3, L-1, L-2, LC1, etc.
    "lighting": [
        r'\b(L[-]?\d{1,2})\b',  # L1, L2, L-1, L-2
        r'\b(LC[-]?\d{1,2})\b',  # LC1, LC-1
        r'\b(LT[-]?\d{1,2})\b',  # LT1 (lighting circuit)
    ],
    # Power circuits: P1, P2, P-1, PC1, etc.
    "power": [
        r'\b(P[-]?\d{1,2})\b',  # P1, P2, P-1
        r'\b(PC[-]?\d{1,2})\b',  # PC1 (power circuit)
        r'\b(PP[-]?\d{1,2})\b',  # PP1 (plug point circuit)
        r'\b(SO[-]?\d{1,2})\b',  # SO1 (socket outlet)
    ],
    # Dedicated circuits: AC1, GY1, ST1, etc.
    "dedicated": [
        r'\b(AC[-]?\d{1,2})\b',  # AC1 (air conditioner)
        r'\b(GY[-]?\d{1,2})\b',  # GY1 (geyser)
        r'\b(ST[-]?\d{1,2})\b',  # ST1 (stove)
        r'\b(HP[-]?\d{1,2})\b',  # HP1 (heat pump)
        r'\b(PP[-]?\d{1,2})\b',  # PP1 (pool pump)
        r'\b(GM[-]?\d{1,2})\b',  # GM1 (gate motor)
        r'\b(ISO[-]?\d{1,2})\b',  # ISO1 (isolator circuit)
        r'\b(DED[-]?\d{1,2})\b',  # DED1 (dedicated)
    ],
}

# DB reference patterns: DB-GF, DB-S1, DB-FF, MSB, etc.
DB_PATTERNS = [
    r'\b(DB[-_]?[A-Z0-9]{1,4})\b',  # DB-GF, DB_S1, DBGF
    r'\b(MSB)\b',  # Main switchboard
    r'\b(MDB)\b',  # Main distribution board
]


def scan_circuit_labels(text: str) -> CircuitLabelScanResult:
    """
    Scan text for circuit labels.

    NO LLM CALLS - pure regex scanning.

    Args:
        text: Page text content

    Returns:
        CircuitLabelScanResult with label counts and breakdown
    """
    result = CircuitLabelScanResult()
    text_upper = text.upper()

    # Extract DB references first
    db_refs = set()
    for pattern in DB_PATTERNS:
        for match in re.finditer(pattern, text_upper):
            db_ref = match.group(1)
            db_refs.add(db_ref)
    result.db_refs_found = sorted(list(db_refs))

    # Initialize by_type structure
    result.by_type = {"lighting": {}, "power": {}, "dedicated": {}}

    # Scan for each circuit type
    for circuit_type, patterns in CIRCUIT_PATTERNS.items():
        for pattern in patterns:
            for match in re.finditer(pattern, text_upper):
                label = _normalize_label(match.group(1))

                # Count this label
                result.labels[label] = result.labels.get(label, 0) + 1
                result.by_type[circuit_type][label] = result.by_type[circuit_type].get(label, 0) + 1

    # Calculate totals
    result.total_lighting_points = sum(result.by_type["lighting"].values())
    result.total_power_points = sum(result.by_type["power"].values())
    result.total_dedicated_points = sum(result.by_type["dedicated"].values())

    # Calculate confidence
    total_labels = sum(result.labels.values())
    if total_labels > 0:
        result.confidence = min(0.95, 0.5 + 0.02 * total_labels)
    else:
        result.confidence = 0.0

    return result


def scan_layout_pages(pages: List) -> Dict[str, CircuitLabelScanResult]:
    """
    Scan multiple layout pages for circuit labels.

    Args:
        pages: List of PageInfo objects

    Returns:
        Dict mapping page number to scan result
    """
    results = {}
    for page in pages:
        text = getattr(page, 'text_content', '') or ''
        page_num = getattr(page, 'page_number', 0)
        results[page_num] = scan_circuit_labels(text)
    return results


def aggregate_layout_counts(
    page_results: Dict[int, CircuitLabelScanResult]
) -> Dict[str, int]:
    """
    Aggregate circuit counts across all layout pages.

    Args:
        page_results: Dict from scan_layout_pages

    Returns:
        Dict mapping circuit label to total count
    """
    aggregated: Dict[str, int] = {}
    for result in page_results.values():
        for label, count in result.labels.items():
            aggregated[label] = aggregated.get(label, 0) + count
    return aggregated


def match_with_sld_counts(
    layout_counts: Dict[str, int],
    sld_counts: Dict[str, Dict[str, int]],  # {db_name: {circuit_id: num_points}}
) -> Dict[str, Dict[str, any]]:
    """
    Match layout circuit counts with SLD schedule counts.

    This is the reconciliation step - comparing what we found on
    layouts vs what the SLD schedule says.

    Args:
        layout_counts: From aggregate_layout_counts
        sld_counts: From extract_circuit_counts

    Returns:
        Dict with match status per circuit
    """
    results = {}

    # Flatten SLD counts
    flat_sld: Dict[str, int] = {}
    for db_name, circuits in sld_counts.items():
        for circuit_id, num_points in circuits.items():
            # Try to match normalized labels
            normalized = _normalize_label(circuit_id)
            flat_sld[normalized] = num_points

    # Compare each layout count with SLD
    all_labels = set(layout_counts.keys()) | set(flat_sld.keys())

    for label in all_labels:
        layout_count = layout_counts.get(label, 0)
        sld_count = flat_sld.get(label, 0)

        if layout_count == sld_count and sld_count > 0:
            status = "match"
            confidence = 1.0
        elif layout_count > 0 and sld_count == 0:
            status = "layout_only"  # Found on layout but not in SLD
            confidence = 0.7
        elif layout_count == 0 and sld_count > 0:
            status = "sld_only"  # In SLD but not found on layout
            confidence = 0.5
        elif abs(layout_count - sld_count) <= 2:
            status = "near_match"  # Within tolerance
            confidence = 0.8
        else:
            status = "mismatch"
            confidence = 0.4

        results[label] = {
            "layout_count": layout_count,
            "sld_count": sld_count,
            "difference": layout_count - sld_count,
            "status": status,
            "confidence": confidence,
        }

    return results


def extract_db_circuit_prefix(text: str) -> Optional[Tuple[str, str]]:
    """
    Extract DB-prefixed circuit labels like "DB-GF/L1" or "DBGF.P2".

    Args:
        text: Text to scan

    Returns:
        Tuple of (db_ref, circuit_label) or None
    """
    # Pattern: DB-GF/L1, DBGF.P2, DB_S1-L3, etc.
    pattern = r'(DB[-_]?[A-Z0-9]{1,4})[/.\-]([LP][-]?\d{1,2})'

    match = re.search(pattern, text.upper())
    if match:
        return (match.group(1), match.group(2))
    return None


def _normalize_label(label: str) -> str:
    """
    Normalize circuit label for comparison.

    Removes hyphens, converts to uppercase.
    L-1 -> L1, p2 -> P2
    """
    normalized = label.upper()
    normalized = normalized.replace("-", "")
    normalized = normalized.replace("_", "")
    return normalized


def get_circuit_type(label: str) -> str:
    """
    Determine circuit type from label.

    Args:
        label: Circuit label (e.g., "L1", "P2", "AC1")

    Returns:
        Circuit type: "lighting", "power", "dedicated", or "unknown"
    """
    label_upper = label.upper()

    # Check against patterns
    for circuit_type, patterns in CIRCUIT_PATTERNS.items():
        for pattern in patterns:
            if re.match(pattern, label_upper):
                return circuit_type

    return "unknown"


def summarize_for_boq(
    layout_counts: Dict[str, int],
    legend_lookup: Optional[Dict[str, Dict]] = None,
) -> List[Dict[str, any]]:
    """
    Summarize circuit counts for BOQ generation.

    Args:
        layout_counts: Aggregated layout counts
        legend_lookup: Optional legend lookup for fixture types

    Returns:
        List of BOQ-ready line items
    """
    items = []

    # Group by circuit type
    by_type = {"lighting": [], "power": [], "dedicated": []}

    for label, count in layout_counts.items():
        circuit_type = get_circuit_type(label)
        if circuit_type in by_type:
            by_type[circuit_type].append({
                "circuit": label,
                "count": count,
            })

    # Create summary items
    if by_type["lighting"]:
        total_lighting = sum(item["count"] for item in by_type["lighting"])
        items.append({
            "category": "Lighting Points",
            "description": f"Light points across {len(by_type['lighting'])} circuits",
            "quantity": total_lighting,
            "circuit_breakdown": by_type["lighting"],
            "confidence": ItemConfidence.EXTRACTED.value,
        })

    if by_type["power"]:
        total_power = sum(item["count"] for item in by_type["power"])
        items.append({
            "category": "Power Points",
            "description": f"Socket outlets across {len(by_type['power'])} circuits",
            "quantity": total_power,
            "circuit_breakdown": by_type["power"],
            "confidence": ItemConfidence.EXTRACTED.value,
        })

    if by_type["dedicated"]:
        items.append({
            "category": "Dedicated Circuits",
            "description": f"{len(by_type['dedicated'])} dedicated circuits",
            "quantity": len(by_type["dedicated"]),
            "circuit_breakdown": by_type["dedicated"],
            "confidence": ItemConfidence.EXTRACTED.value,
        })

    return items
