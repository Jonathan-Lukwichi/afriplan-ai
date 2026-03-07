"""
AfriPlan Electrical v1.0 - Deterministic Legend Extraction

Extract fixture types and symbols from drawing legends using regex patterns.
NO LLM CALLS - pure Python parsing.

Legends contain the mapping between:
- Symbol/abbreviation (e.g., "DL", "DS", "SW1")
- Fixture type (e.g., "LED Downlight", "Double Socket", "1-Lever Switch")
- Optional: wattage, brand, catalog number

Usage:
    from agent.stages.extract_legend import extract_legend, LegendEntry

    entries = extract_legend(page_text)
    # Returns: [LegendEntry(symbol="DL", fixture_type="LED Downlight", ...)]
"""

import re
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field

from agent.models import PageInfo, StageResult, PipelineStage, ItemConfidence
from agent.utils import Timer


@dataclass
class LegendEntry:
    """A single legend entry mapping symbol to fixture type."""
    symbol: str
    fixture_type: str
    category: str = ""  # lighting, power, switch, other
    wattage_w: int = 0
    brand: str = ""
    catalog_number: str = ""
    quantity_symbol: str = ""  # e.g., "Qty" symbol used in drawings
    confidence: ItemConfidence = ItemConfidence.EXTRACTED


@dataclass
class LegendExtractionResult:
    """Complete legend extraction result."""
    entries: List[LegendEntry] = field(default_factory=list)
    fixture_types: Dict[str, str] = field(default_factory=dict)  # symbol -> type
    has_lighting_legend: bool = False
    has_power_legend: bool = False
    has_switch_legend: bool = False
    page_number: int = 0
    confidence: float = 0.0


# Standard SA electrical fixture patterns
FIXTURE_PATTERNS = {
    # Lighting fixtures
    "lighting": [
        (r'(?P<symbol>DL|D/L)\s*[-:=]\s*(?P<desc>.*?(?:downlight|down\s*light))',
         "Downlight"),
        (r'(?P<symbol>LP|LED)\s*[-:=]\s*(?P<desc>.*?(?:led\s*panel|panel\s*light))',
         "LED Panel"),
        (r'(?P<symbol>BH|BLK)\s*[-:=]\s*(?P<desc>.*?(?:bulkhead))',
         "Bulkhead"),
        (r'(?P<symbol>FL|FLD)\s*[-:=]\s*(?P<desc>.*?(?:flood|floodlight))',
         "Floodlight"),
        (r'(?P<symbol>BT|BAT)\s*[-:=]\s*(?P<desc>.*?(?:batten|led\s*batten))',
         "LED Batten"),
        (r'(?P<symbol>LUM|LM)\s*[-:=]\s*(?P<desc>.*?(?:luminaire))',
         "Luminaire"),
        (r'(?P<symbol>EX|EXIT)\s*[-:=]\s*(?P<desc>.*?(?:exit|emergency\s*exit))',
         "Exit Sign"),
        (r'(?P<symbol>EM|EMRG)\s*[-:=]\s*(?P<desc>.*?(?:emergency))',
         "Emergency Light"),
        (r'(?P<symbol>CL|CEIL)\s*[-:=]\s*(?P<desc>.*?(?:ceiling|ceiling\s*light))',
         "Ceiling Light"),
        (r'(?P<symbol>WL|WALL)\s*[-:=]\s*(?P<desc>.*?(?:wall\s*light|wall\s*mount))',
         "Wall Light"),
    ],
    # Power points (sockets)
    "power": [
        (r'(?P<symbol>DS|DSO)\s*[-:=]\s*(?P<desc>.*?(?:double\s*socket|twin\s*socket))',
         "Double Socket"),
        (r'(?P<symbol>SS|SSO)\s*[-:=]\s*(?P<desc>.*?(?:single\s*socket))',
         "Single Socket"),
        (r'(?P<symbol>FB|FLB)\s*[-:=]\s*(?P<desc>.*?(?:floor\s*box))',
         "Floor Box"),
        (r'(?P<symbol>DP|DATA)\s*[-:=]\s*(?P<desc>.*?(?:data\s*point|cat6?))',
         "Data Point"),
        (r'(?P<symbol>ISO|ISOL)\s*[-:=]\s*(?P<desc>.*?(?:isolator))',
         "Isolator"),
        (r'(?P<symbol>TV)\s*[-:=]\s*(?P<desc>.*?(?:tv\s*point|television))',
         "TV Point"),
        (r'(?P<symbol>WSO|WPS)\s*[-:=]\s*(?P<desc>.*?(?:weatherproof|outdoor\s*socket))',
         "Weatherproof Socket"),
    ],
    # Switches
    "switch": [
        (r'(?P<symbol>SW1|1L|1-L)\s*[-:=]\s*(?P<desc>.*?(?:1[-\s]?lever|single\s*lever))',
         "1-Lever Switch"),
        (r'(?P<symbol>SW2|2L|2-L)\s*[-:=]\s*(?P<desc>.*?(?:2[-\s]?lever|double\s*lever))',
         "2-Lever Switch"),
        (r'(?P<symbol>SW3|3L|3-L)\s*[-:=]\s*(?P<desc>.*?(?:3[-\s]?lever|triple\s*lever))',
         "3-Lever Switch"),
        (r'(?P<symbol>SW4|4L|4-L)\s*[-:=]\s*(?P<desc>.*?(?:4[-\s]?lever|quad\s*lever))',
         "4-Lever Switch"),
        (r'(?P<symbol>DIM|DMR)\s*[-:=]\s*(?P<desc>.*?(?:dimmer))',
         "Dimmer Switch"),
        (r'(?P<symbol>PIR|SEN)\s*[-:=]\s*(?P<desc>.*?(?:pir|motion|sensor))',
         "PIR Sensor"),
        (r'(?P<symbol>DNE|D/N)\s*[-:=]\s*(?P<desc>.*?(?:day[-/]?night))',
         "Day/Night Switch"),
    ],
}

# Generic fixture extraction patterns (fallback)
GENERIC_PATTERNS = [
    # "SYMBOL - Description" format
    r'(?P<symbol>[A-Z]{2,4}\d*)\s*[-:=]\s*(?P<desc>[A-Za-z][A-Za-z\s\d]{3,40})',
    # "Description (SYMBOL)" format
    r'(?P<desc>[A-Za-z][A-Za-z\s\d]{3,40})\s*\((?P<symbol>[A-Z]{2,4}\d*)\)',
    # Tabular format: "SYMBOL | Description | Wattage"
    r'(?P<symbol>[A-Z]{2,4}\d*)\s*\|\s*(?P<desc>[A-Za-z][A-Za-z\s\d]{3,30})',
]


def extract_legend(text: str, page_number: int = 0) -> LegendExtractionResult:
    """
    Extract legend entries from page text.

    NO LLM CALLS - pure regex extraction.

    Args:
        text: Page text content
        page_number: Page number for tracking

    Returns:
        LegendExtractionResult with all extracted entries
    """
    result = LegendExtractionResult(page_number=page_number)
    text_upper = text.upper()

    # Check for legend section markers
    legend_markers = [
        "LEGEND", "SYMBOL LEGEND", "FIXTURE LEGEND",
        "KEY", "SYMBOL KEY", "FIXTURE KEY",
        "ABBREVIATIONS", "SYMBOLS",
    ]
    has_legend_section = any(marker in text_upper for marker in legend_markers)

    if not has_legend_section:
        # Try to extract anyway but with lower confidence
        result.confidence = 0.3
    else:
        result.confidence = 0.8

    entries_found = set()  # Track unique symbols

    # Try specific patterns by category
    for category, patterns in FIXTURE_PATTERNS.items():
        for pattern, default_type in patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                symbol = match.group('symbol').upper().strip()
                desc = match.group('desc').strip() if 'desc' in match.groupdict() else ""

                if symbol in entries_found:
                    continue

                entry = LegendEntry(
                    symbol=symbol,
                    fixture_type=default_type,
                    category=category,
                    confidence=ItemConfidence.EXTRACTED,
                )

                # Extract wattage if present
                watt_match = re.search(r'(\d+)\s*[wW]', desc)
                if watt_match:
                    entry.wattage_w = int(watt_match.group(1))

                result.entries.append(entry)
                result.fixture_types[symbol] = default_type
                entries_found.add(symbol)

                if category == "lighting":
                    result.has_lighting_legend = True
                elif category == "power":
                    result.has_power_legend = True
                elif category == "switch":
                    result.has_switch_legend = True

    # Try generic patterns for anything missed
    for pattern in GENERIC_PATTERNS:
        for match in re.finditer(pattern, text, re.IGNORECASE):
            symbol = match.group('symbol').upper().strip()
            desc = match.group('desc').strip()

            if symbol in entries_found:
                continue

            # Infer category from description
            category = _infer_category(desc)
            fixture_type = _normalize_fixture_type(desc)

            entry = LegendEntry(
                symbol=symbol,
                fixture_type=fixture_type,
                category=category,
                confidence=ItemConfidence.INFERRED,  # Lower confidence for generic match
            )

            result.entries.append(entry)
            result.fixture_types[symbol] = fixture_type
            entries_found.add(symbol)

    # Update confidence based on entries found
    if result.entries:
        result.confidence = min(0.9, 0.5 + 0.05 * len(result.entries))

    return result


def extract_legend_from_pages(pages: List[PageInfo]) -> Dict[str, LegendEntry]:
    """
    Extract and merge legends from multiple pages.

    Args:
        pages: List of PageInfo objects

    Returns:
        Dict mapping symbols to LegendEntry
    """
    merged: Dict[str, LegendEntry] = {}

    for page in pages:
        text = page.text_content or ""
        result = extract_legend(text, page.page_number)

        for entry in result.entries:
            # Keep higher confidence entry if duplicate
            if entry.symbol in merged:
                existing = merged[entry.symbol]
                if entry.confidence.value > existing.confidence.value:
                    merged[entry.symbol] = entry
            else:
                merged[entry.symbol] = entry

    return merged


def _infer_category(desc: str) -> str:
    """Infer category from description text."""
    desc_lower = desc.lower()

    lighting_keywords = [
        "light", "downlight", "panel", "batten", "bulkhead",
        "luminaire", "flood", "led", "lamp", "exit", "emergency"
    ]
    power_keywords = [
        "socket", "outlet", "plug", "data", "floor box",
        "isolator", "tv", "power"
    ]
    switch_keywords = [
        "switch", "lever", "dimmer", "pir", "sensor",
        "day/night", "timer"
    ]

    if any(kw in desc_lower for kw in lighting_keywords):
        return "lighting"
    elif any(kw in desc_lower for kw in power_keywords):
        return "power"
    elif any(kw in desc_lower for kw in switch_keywords):
        return "switch"

    return "other"


def _normalize_fixture_type(desc: str) -> str:
    """Normalize fixture type description."""
    # Remove common filler words
    normalized = desc.strip()
    normalized = re.sub(r'^(the|a|an)\s+', '', normalized, flags=re.IGNORECASE)
    normalized = re.sub(r'\s+', ' ', normalized)

    # Capitalize properly
    return normalized.title()


def build_symbol_lookup(legend_entries: List[LegendEntry]) -> Dict[str, Dict[str, Any]]:
    """
    Build lookup table for quick symbol resolution.

    Args:
        legend_entries: List of extracted legend entries

    Returns:
        Dict: {symbol: {type, category, wattage, ...}}
    """
    lookup = {}
    for entry in legend_entries:
        lookup[entry.symbol] = {
            "fixture_type": entry.fixture_type,
            "category": entry.category,
            "wattage_w": entry.wattage_w,
            "brand": entry.brand,
            "confidence": entry.confidence.value,
        }
    return lookup


def extract_legend_with_stage_result(
    pages: List[PageInfo],
) -> tuple[Dict[str, LegendEntry], StageResult]:
    """
    Extract legend with StageResult for pipeline integration.

    Args:
        pages: List of pages to search for legends

    Returns:
        Tuple of (legend_dict, StageResult)
    """
    with Timer("extract_legend") as timer:
        legend = extract_legend_from_pages(pages)

        stage_result = StageResult(
            stage=PipelineStage.DISCOVER,
            success=len(legend) > 0,
            confidence=0.8 if legend else 0.0,
            data={
                "total_entries": len(legend),
                "symbols": list(legend.keys()),
                "categories": list(set(e.category for e in legend.values())),
            },
            model_used=None,  # No LLM!
            tokens_used=0,
            cost_zar=0.0,
            processing_time_ms=timer.elapsed_ms,
            errors=[],
            warnings=[],
        )

        return legend, stage_result
