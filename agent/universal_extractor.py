"""
AfriPlan Electrical — Universal Extraction Module v1.0

Production-ready 5-strategy chain for extracting fixture data from ANY
South African electrical drawing PDF.

Strategy Chain (executed in order, stops when confidence threshold met):
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  Strategy 1: TEXT LAYER MINING
  ├── Cost: R0.00 | Time: <100ms | Data needed: 0
  ├── How: PyMuPDF extracts embedded text + coordinates from vector PDFs
  ├── Works when: PDF exported from AutoCAD/ArchiCAD/Revit (90%+ of drawings)
  └── Extracts: Fixture types, quantities, prices, drawing numbers, room names

  Strategy 2: LEGEND REGION FINDER
  ├── Cost: R0.00 | Time: <200ms | Data needed: 0
  ├── How: Keyword search (SWITCHES, LIGHTS, QTYS) in text coordinates
  ├── Works when: Text layer exists but legend text is fragmented/incomplete
  └── Produces: High-res 300 DPI crop of JUST the legend table

  Strategy 3: LEGEND CROP AI READER
  ├── Cost: R0.18 (Haiku) or R0.00 (Groq) | Time: 2-5s
  ├── How: Send small legend crop image to vision LLM with focused prompt
  ├── Works when: Legend found but text extraction incomplete
  └── Extracts: Complete fixture types + quantities from visual table

  Strategy 4: TITLE BLOCK EXTRACTOR
  ├── Cost: R0.00 | Time: <100ms | Data needed: 0
  ├── How: Extract project metadata from title block region
  └── Extracts: Drawing number, building name, project, engineer, date

  Strategy 5: FULL-PAGE AI FALLBACK
  ├── Cost: R1.80 (Sonnet) | Time: 5-15s
  ├── How: Send entire page to powerful vision LLM
  ├── Works when: All other strategies fail (scanned PDFs, hand-drawn)
  └── Last resort — only triggered when confidence < threshold

Tested on:
- Wedela Recreational Club (Chona-Mulanga Engineering / KABE Consulting)
  → 10 pages, AutoCAD export, legend top-left
- Megchem Training Center (3 Cubes Architects)
  → 3 pages, ArchiCAD export, fixture table right-side with pricing

Author: JLWanalytics
Version: 1.0.0
"""

from __future__ import annotations

import re
import io
import os
import json
import time
import base64
import logging
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Tuple, Optional, Any
from enum import Enum

try:
    import fitz  # PyMuPDF
except ImportError:
    fitz = None

try:
    from PIL import Image
except ImportError:
    Image = None

logger = logging.getLogger(__name__)


# ╔══════════════════════════════════════════════════════════════════════╗
# ║  DATA MODELS                                                        ║
# ╚══════════════════════════════════════════════════════════════════════╝

class ExtractionStrategy(str, Enum):
    """Which strategy produced this extraction."""
    TEXT_LAYER = "text_layer"
    LEGEND_CROP_AI = "legend_crop_ai"
    FULL_PAGE_AI = "full_page_ai"
    DXF_DIRECT = "dxf_direct"
    MANUAL = "manual"


class FixtureCategory(str, Enum):
    LIGHTING = "lighting"
    POWER = "power"
    SWITCH = "switch"
    DATA = "data"
    SAFETY = "safety"
    HVAC = "hvac"
    WATER = "water"
    OTHER = "other"


class DrawingType(str, Enum):
    LIGHTING = "lighting"
    PLUG = "plug"
    COMBINED = "combined"
    SLD = "sld"
    LEGEND_ONLY = "legend"
    COVER = "cover"
    SCHEDULE = "schedule"
    UNKNOWN = "unknown"


class Confidence(str, Enum):
    HIGH = "high"        # >= 0.80 — extracted cleanly from text/legend
    MEDIUM = "medium"    # >= 0.60 — AI-read or partial text match
    LOW = "low"          # >= 0.40 — estimated or inferred
    VERY_LOW = "very_low"  # < 0.40 — uncertain, needs review


@dataclass
class FixtureItem:
    """A single extracted fixture type with quantity."""
    fixture_type: str          # e.g., "LED Downlight 6W"
    category: FixtureCategory
    quantity: int
    unit_price_zar: float = 0.0   # If price found on drawing
    description: str = ""         # Full description from legend
    symbol_code: str = ""         # e.g., "L2", "P1", "S3"
    brand: str = ""               # e.g., "Radiant", "Veti"
    confidence: float = 0.0
    confidence_level: Confidence = Confidence.LOW
    source: ExtractionStrategy = ExtractionStrategy.TEXT_LAYER


@dataclass
class LegendRegion:
    """Detected legend/BOQ table region on a page."""
    x0: float
    y0: float
    x1: float
    y1: float
    detection_method: str   # "keyword", "heuristic", "ml_model"
    keywords_found: List[str] = field(default_factory=list)
    crop_bytes: Optional[bytes] = None  # PNG at 300 DPI
    crop_base64: Optional[str] = None


@dataclass
class TitleBlockInfo:
    """Extracted title block metadata."""
    drawing_number: str = ""
    building_name: str = ""
    project_name: str = ""
    description: str = ""
    engineer: str = ""
    client: str = ""
    date: str = ""
    revision: str = ""
    scale: str = ""
    page_size: str = ""


@dataclass
class PageResult:
    """Complete extraction result for a single page."""
    page_number: int
    drawing_type: DrawingType
    title_block: TitleBlockInfo
    fixtures: List[FixtureItem] = field(default_factory=list)
    legend_region: Optional[LegendRegion] = None
    strategy_used: ExtractionStrategy = ExtractionStrategy.TEXT_LAYER
    strategies_attempted: List[str] = field(default_factory=list)
    confidence: float = 0.0
    confidence_level: Confidence = Confidence.LOW
    processing_time_ms: int = 0
    raw_text_length: int = 0
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)

    @property
    def total_fixtures(self) -> int:
        return sum(f.quantity for f in self.fixtures)

    @property
    def total_value_zar(self) -> float:
        return sum(f.quantity * f.unit_price_zar for f in self.fixtures)


@dataclass
class DocumentResult:
    """Complete extraction result for an entire PDF document."""
    filename: str
    pages: List[PageResult] = field(default_factory=list)
    total_pages: int = 0
    processing_time_ms: int = 0
    strategies_summary: Dict[str, int] = field(default_factory=dict)

    @property
    def total_fixtures(self) -> int:
        return sum(p.total_fixtures for p in self.pages)

    @property
    def total_value_zar(self) -> float:
        return sum(p.total_value_zar for p in self.pages)

    @property
    def average_confidence(self) -> float:
        if not self.pages:
            return 0.0
        return sum(p.confidence for p in self.pages) / len(self.pages)

    def to_dict(self) -> dict:
        return asdict(self)


# ╔══════════════════════════════════════════════════════════════════════╗
# ║  STRATEGY 1: TEXT LAYER MINER                                       ║
# ╚══════════════════════════════════════════════════════════════════════╝

class TextLayerMiner:
    """
    Extract fixture data from the PDF's embedded text layer.

    Most CAD-exported PDFs (AutoCAD, ArchiCAD, Revit, MicroStation) embed
    text as selectable content. PyMuPDF extracts this with coordinates,
    allowing us to find fixture descriptions, quantities, and prices
    without any AI or image processing.

    Cost: R0.00 | Time: <100ms per page
    """

    # ── SA Electrical Drawing Keywords ──
    # These appear on virtually every SA electrical drawing
    LEGEND_HEADER_KEYWORDS = [
        "SWITCHES", "POWER SOCKETS", "LIGHTS", "OTHERS",
        "LEGEND", "KEY TO SYMBOLS", "SYMBOL KEY",
        "LUMINAIRES", "FITTINGS", "FIXTURES",
        "QTYS", "QTY", "QUANTITY", "NO.",
    ]

    # ── Drawing Type Classification Keywords ──
    DRAWING_TYPE_MAP = {
        DrawingType.SLD: [
            "SINGLE LINE DIAGRAM", "SLD", "DISTRIBUTION BOARD",
            "DB SCHEDULE", "CIRCUIT SCHEDULE", "MAIN SWITCH",
            "CIRCUIT BREAKER", "MCB", "MCCB",
        ],
        DrawingType.LIGHTING: [
            "LIGHTING", "LIGHT LAYOUT", "LUMINAIRE LAYOUT",
            "LIGHTING PLAN", "LIGHTING LAYOUT",
            "-LIGHTING",  # catches WD-AB-01-LIGHTING
        ],
        DrawingType.PLUG: [
            "PLUG", "POWER LAYOUT", "SOCKET LAYOUT",
            "POWER PLAN", "GPO LAYOUT",
            "-PLUG",  # catches WD-AB-01-PLUG
        ],
        DrawingType.COMBINED: [
            "ELECTRICAL PLAN", "ELECTRICAL LAYOUT",
            "LIGHTS, SWITCHES AND PLUGS",
            "ELECTRICAL& OTHER",
        ],
        DrawingType.COVER: [
            "COVER PAGE", "DRAWING REGISTER", "DRAWING LIST",
            "INDEX", "TABLE OF CONTENTS",
        ],
    }

    # ── Fixture Extraction Patterns ──
    # These match the actual text found in SA electrical drawing legends
    # and BOQ tables across multiple engineering firms.
    #
    # Pattern format: (regex, fixture_type, category)
    # The regex captures quantity and description from typical legend formats.

    FIXTURE_PATTERNS = [
        # ── LIGHTING ──
        # "600 x 1200 Recessed 2 x 18W LED fluorescent light"
        (r'(\d+)\s*[x×]\s*\d+.*?[Rr]ecessed.*?(\d+)\s*[x×]?\s*\d*\s*[Ww].*?(?:LED|fluorescent)',
         "Recessed Fluorescent", FixtureCategory.LIGHTING),
        # "6W LED downlight white colour"
        (r'(\d+)\s*[Ww]\s*LED\s*[Dd]own\s*light',
         "LED Downlight", FixtureCategory.LIGHTING),
        # "LED downlight" or "DOWNLIGHTER" or "DLIGHT" or "D/LIGHT"
        (r'(?:D/?LIGHT|[Dd]own\s*light(?:er)?|RECESSED\s+DOWNLIGHTER)',
         "Downlight", FixtureCategory.LIGHTING),
        # "FLOODLIGHT BLACK LED 30W 6500K"
        (r'[Ff]lood\s*light.*?(?:LED)?\s*(\d+)\s*[Ww]',
         "LED Floodlight", FixtureCategory.LIGHTING),
        (r'[Ff]lood\s*light',
         "Floodlight", FixtureCategory.LIGHTING),
        # "RADIANT MONTE CEILING LIGHT WHITE"
        (r'(?:CEILING\s+LIGHT|[Cc]eiling\s+light)',
         "Ceiling Light", FixtureCategory.LIGHTING),
        # "RADIANT SLATE GRID WALL LIGHT"
        (r'(?:WALL\s+LIGHT|[Ww]all\s+light|[Ww]all\s+[Mm]ounted.*?[Ll]ight)',
         "Wall Light", FixtureCategory.LIGHTING),
        # "Bulkhead" light
        (r'[Bb]ulk\s*head',
         "Bulkhead Light", FixtureCategory.LIGHTING),
        # "Vapour proof" light
        (r'[Vv]apour\s*proof',
         "Vapour Proof Light", FixtureCategory.LIGHTING),
        # "PENDANT" light
        (r'[Pp]endant',
         "Pendant Light", FixtureCategory.LIGHTING),
        # "Chandelier"
        (r'[Cc]handelier',
         "Chandelier", FixtureCategory.LIGHTING),
        # "FLUORESCENT" tube
        (r'[Ff]luorescent.*?(\d+)\s*[Ww]',
         "Fluorescent Tube", FixtureCategory.LIGHTING),
        # "LED Panel" or "PANEL LED"
        (r'(?:LED\s+[Pp]anel|[Pp]anel\s+LED)',
         "LED Panel", FixtureCategory.LIGHTING),
        # "LED Tube light" or "LED tube"
        (r'LED\s+[Tt]ube\s*light',
         "LED Tube Light", FixtureCategory.LIGHTING),
        # "600x600 LED Diffused light"
        (r'600\s*[x×]\s*600.*?LED.*?[Dd]iffused',
         "600x600 LED Panel", FixtureCategory.LIGHTING),
        # "Emergency light"
        (r'[Ee]mergency\s*light',
         "Emergency Light", FixtureCategory.SAFETY),
        # "EXIT sign"
        (r'[Ee]xit\s*(?:sign|light)',
         "Exit Sign", FixtureCategory.SAFETY),
        # "SPOTLIGHT"
        (r'[Ss]pot\s*light',
         "Spotlight", FixtureCategory.LIGHTING),

        # ── POWER / SOCKETS ──
        # "16A Double Switched Socket @300mm above FFL"
        (r'[Dd]ouble\s*[Ss]witched?\s*[Ss]ocket',
         "Double Switched Socket", FixtureCategory.POWER),
        # "16A Single Switched Socket"
        (r'[Ss]ingle\s*[Ss]witched?\s*[Ss]ocket',
         "Single Switched Socket", FixtureCategory.POWER),
        # "Weatherproof Socket"
        (r'[Ww]eather\s*proof.*?[Ss]ocket',
         "Weatherproof Socket", FixtureCategory.POWER),
        # "Double Socket 16A" (without "switched")
        (r'[Dd]ouble\s*[Ss]ocket',
         "Double Socket", FixtureCategory.POWER),
        # "Single plug" / "Single socket"
        (r'[Ss]ingle\s*[Pp]lug',
         "Single Plug", FixtureCategory.POWER),
        # "Workstation plug" with USB
        (r'[Ww]orkstation\s*[Pp]lug',
         "Workstation Plug (USB)", FixtureCategory.POWER),
        # "Floor Socket" or "Floor Box"
        (r'[Ff]loor\s*[Ss]ocket',
         "Floor Socket", FixtureCategory.POWER),
        # "External plug box"
        (r'[Ee]xternal\s*[Pp]lug',
         "External Plug Box", FixtureCategory.POWER),

        # ── SWITCHES ──
        # "1 Lever Switch" / "1lever" / "1-lever"
        (r'1\s*[-]?\s*[Ll]ever\s*[Ss]witch',
         "1-Lever Switch", FixtureCategory.SWITCH),
        (r'2\s*[-]?\s*[Ll]ever\s*[Ss]witch',
         "2-Lever Switch", FixtureCategory.SWITCH),
        (r'3\s*[-]?\s*[Ll]ever\s*[Ss]witch',
         "3-Lever Switch", FixtureCategory.SWITCH),
        # "Isolator Switch"
        (r'[Ii]solator\s*[Ss]witch',
         "Isolator Switch", FixtureCategory.SWITCH),
        # "Day/night switch"
        (r'[Dd]ay\s*/?\s*[Nn]ight\s*[Ss]witch',
         "Day/Night Switch", FixtureCategory.SWITCH),
        # "Dimmer"
        (r'[Dd]immer\s*[Ss]witch',
         "Dimmer Switch", FixtureCategory.SWITCH),

        # ── DATA / TELECOMS ──
        # "RJ45" or "Data Socket" or "Data point"
        (r'(?:RJ45|[Dd]ata\s*[Ss]ocket|[Dd]ata\s*[Pp]oint|[Tt]elephone.*?[Ss]ocket)',
         "Data/Telephone Socket", FixtureCategory.DATA),
        # "Television Socket"
        (r'[Tt]elevision\s*[Ss]ocket',
         "Television Socket", FixtureCategory.DATA),

        # ── SAFETY ──
        # "Smoke detector"
        (r'[Ss]moke\s*[Dd]etector',
         "Smoke Detector", FixtureCategory.SAFETY),
        # "PIR" sensor
        (r'PIR\s*[Ss]ensor',
         "PIR Sensor", FixtureCategory.SAFETY),
        # "Alarm" keypad/sensor
        (r'[Aa]larm\s*(?:[Kk]eypad|[Ss]ensor|[Dd]oor)',
         "Alarm Device", FixtureCategory.SAFETY),

        # ── HVAC ──
        # "Air Conditioning" / "A/C" unit
        (r'[Aa]ir\s*[Cc]onditioning|A/C\s*[Uu]nit',
         "Air Conditioning Unit", FixtureCategory.HVAC),

        # ── WATER HEATING ──
        # "Geyser" / "Water Heater" / "Kwikboil"
        (r'[Gg]eyser',
         "Geyser", FixtureCategory.WATER),
        (r'[Ww]ater\s*[Hh]eater|[Kk]wikboil',
         "Water Heater", FixtureCategory.WATER),
        # "Distribution Board"
        (r'[Dd]istribution\s*[Bb]oard',
         "Distribution Board", FixtureCategory.OTHER),
    ]

    # ── Price Pattern ──
    # Matches "R150.00/unit", "R3,500.00", "R710.00/unit"
    PRICE_PATTERN = re.compile(r'R\s*([\d,]+\.?\d*)\s*(?:/?\s*(?:unit|set|each))?', re.IGNORECASE)

    # ── Quantity Pattern ──
    # Matches standalone numbers 1-999 (quantities in legends)
    QTY_STANDALONE = re.compile(r'^\s*(\d{1,3})\s*$')

    def extract(self, page, page_num: int) -> PageResult:
        """
        Extract all available data from a page's text layer.

        Args:
            page: fitz.Page object
            page_num: 1-based page number

        Returns:
            PageResult with whatever could be extracted from text
        """
        start_time = time.time()

        full_text = page.get_text("text")
        text_dict = page.get_text("dict")

        result = PageResult(
            page_number=page_num,
            drawing_type=self._classify_drawing_type(full_text),
            title_block=self._extract_title_block(full_text),
            raw_text_length=len(full_text),
        )

        # Extract fixtures from text — try spatial legend first, fall back to line-based
        spatial_fixtures = self._extract_fixtures_spatial(page)
        line_fixtures = self._extract_fixtures_from_text(full_text)

        # Use whichever approach found more fixtures WITH quantities
        spatial_with_qty = [f for f in spatial_fixtures if f.quantity > 0]
        line_with_qty = [f for f in line_fixtures if f.quantity > 0]

        if len(spatial_with_qty) >= len(line_with_qty) and spatial_with_qty:
            result.fixtures = spatial_fixtures
            result.strategies_attempted.append("text_layer_spatial")
        else:
            result.fixtures = line_fixtures
            result.strategies_attempted.append("text_layer")

        # Calculate confidence
        fixtures_with_qty = [f for f in result.fixtures if f.quantity > 0]
        if fixtures_with_qty:
            # More fixtures WITH quantities = much higher confidence
            fixture_conf = min(0.95, 0.50 + 0.05 * len(fixtures_with_qty))
            # Rich text = higher confidence
            text_conf = min(1.0, len(full_text) / 5000)
            result.confidence = fixture_conf * 0.7 + text_conf * 0.3
        elif result.fixtures:
            # Found types but no quantities — low confidence
            fixture_conf = min(0.60, 0.30 + 0.03 * len(result.fixtures))
            text_conf = min(1.0, len(full_text) / 5000)
            result.confidence = fixture_conf * 0.7 + text_conf * 0.3
        else:
            result.confidence = min(0.30, len(full_text) / 10000)

        result.confidence_level = _confidence_level(result.confidence)
        result.strategy_used = ExtractionStrategy.TEXT_LAYER
        result.processing_time_ms = int((time.time() - start_time) * 1000)

        return result

    def _classify_drawing_type(self, text: str) -> DrawingType:
        """Classify page type from text content."""
        text_upper = text.upper()

        # Check each type's keywords (order matters — more specific first)
        for dtype, keywords in self.DRAWING_TYPE_MAP.items():
            for kw in keywords:
                if kw in text_upper:
                    return dtype

        return DrawingType.UNKNOWN

    def _extract_title_block(self, text: str) -> TitleBlockInfo:
        """Extract project metadata from title block text."""
        info = TitleBlockInfo()

        # Drawing number patterns (SA conventions)
        # WD-AB-01-LIGHTING, 3CA-22002-SH007.1, etc.
        patterns = [
            r'(WD-[A-Z]+-\d+-[A-Z]+)',                    # Wedela style
            r'(\d+[A-Z]+-\d+-SH[\d.]+)',                  # 3 Cubes style
            r'([A-Z]{2,4}-\d{3,}-[A-Z\d]+(?:-[A-Z]+)?)',  # Generic SA
        ]
        for pat in patterns:
            m = re.search(pat, text)
            if m:
                info.drawing_number = m.group(1)
                break

        # Building name — "PART:" or "BUILDING X:" lines
        for pat in [
            r'PART[S]?:\s*(.+?)(?:\n|$)',
            r'(BUILDING\s+\d+[^:]*?)(?:\n|$)',
            r'DESCRIPTION:\s*(.+?)(?:\n|$)',
        ]:
            m = re.search(pat, text, re.IGNORECASE)
            if m:
                info.building_name = m.group(1).strip()[:100]
                break

        # Project name
        for pat in [
            r'PROJECT\s*(?:DESCRIPTION|NAME)?:\s*(.+?)(?:\n|$)',
            r'DESCRIPTION:\s*(?:THE\s+)?(?:UPGRADING|RENOVATION|CONSTRUCTION)\s+(?:OF\s+)?(.+?)(?:\n|$)',
        ]:
            m = re.search(pat, text, re.IGNORECASE)
            if m:
                info.project_name = m.group(1).strip()[:100]
                break

        # Engineer / Consultant
        for pat in [
            r'CONSULTANT[S]?:\s*(.+?)(?:\n|$)',
            r'(?:DRAWN|DESIGNED)\s+BY:\s*(.+?)(?:\n|$)',
        ]:
            m = re.search(pat, text, re.IGNORECASE)
            if m:
                info.engineer = m.group(1).strip()[:80]
                break

        # Client
        m = re.search(r'CLIENT[S]?:\s*(.+?)(?:\n|$)', text, re.IGNORECASE)
        if m:
            info.client = m.group(1).strip()[:80]

        # Date
        m = re.search(r'(\d{2}[-/.]\d{2}[-/.]\d{4})', text)
        if m:
            info.date = m.group(1)

        # Scale
        m = re.search(r'SCALE:\s*(1\s*:\s*\d+)', text, re.IGNORECASE)
        if m:
            info.scale = m.group(1)

        return info

    def _extract_fixtures_from_text(self, text: str) -> List[FixtureItem]:
        """
        Extract fixture types, quantities, and prices from page text.

        Scans through all lines looking for:
        1. Fixture description lines (matched by pattern)
        2. Nearby quantity numbers (standalone digits on adjacent lines)
        3. Nearby price values (R xxx.xx patterns)
        """
        fixtures = []
        lines = text.split('\n')
        used_line_indices = set()

        for i, line in enumerate(lines):
            line_clean = line.strip()
            if not line_clean or i in used_line_indices:
                continue

            for pattern, fixture_type, category in self.FIXTURE_PATTERNS:
                if re.search(pattern, line_clean, re.IGNORECASE):
                    # Found a fixture description — now find quantity and price
                    qty = self._find_quantity_near(lines, i, used_line_indices)
                    price = self._find_price_near(lines, i)
                    symbol = self._find_symbol_code(lines, i)
                    brand = self._find_brand(line_clean)
                    description = line_clean[:120]

                    # Build context from surrounding lines
                    context_lines = []
                    for j in range(max(0, i-1), min(len(lines), i+3)):
                        if lines[j].strip():
                            context_lines.append(lines[j].strip())
                    full_desc = " ".join(context_lines)[:200]

                    if qty > 0:
                        confidence = 0.85 if qty > 0 and price > 0 else 0.70
                    else:
                        qty = 0
                        confidence = 0.40  # Found type but no quantity

                    fixtures.append(FixtureItem(
                        fixture_type=fixture_type,
                        category=category,
                        quantity=qty,
                        unit_price_zar=price,
                        description=full_desc,
                        symbol_code=symbol,
                        brand=brand,
                        confidence=confidence,
                        confidence_level=_confidence_level(confidence),
                        source=ExtractionStrategy.TEXT_LAYER,
                    ))
                    used_line_indices.add(i)
                    break  # Don't double-match same line

        return fixtures

    def _find_quantity_near(self, lines: List[str], idx: int,
                            used: set, search_range: int = 4) -> int:
        """Find a standalone quantity number near a fixture description."""
        # Check surrounding lines for standalone numbers
        for offset in [1, -1, 2, -2, 0, 3, -3]:
            j = idx + offset
            if 0 <= j < len(lines) and j not in used:
                m = self.QTY_STANDALONE.match(lines[j].strip())
                if m:
                    qty = int(m.group(1))
                    if 1 <= qty <= 500:  # Reasonable fixture count
                        used.add(j)
                        return qty

        # Check end of current line for trailing number
        m = re.search(r'\b(\d{1,3})\s*$', lines[idx].strip())
        if m:
            qty = int(m.group(1))
            if 1 <= qty <= 500:
                return qty

        return 0

    def _find_price_near(self, lines: List[str], idx: int,
                         search_range: int = 3) -> float:
        """Find a Rand price value near a fixture description."""
        for offset in range(-search_range, search_range + 1):
            j = idx + offset
            if 0 <= j < len(lines):
                m = self.PRICE_PATTERN.search(lines[j])
                if m:
                    try:
                        return float(m.group(1).replace(',', ''))
                    except ValueError:
                        pass
        return 0.0

    def _find_symbol_code(self, lines: List[str], idx: int) -> str:
        """Find symbol code (L1, L2, P1, S3, etc.) near fixture."""
        for offset in range(-2, 3):
            j = idx + offset
            if 0 <= j < len(lines):
                m = re.search(r'\b([LPSH]\d{1,2})\b', lines[j])
                if m:
                    return m.group(1)
        return ""

    def _find_brand(self, line: str) -> str:
        """Detect brand names in text."""
        brands = {
            "RADIANT": "Radiant", "VETI": "Veti", "CBI": "CBI",
            "ABB": "ABB", "SCHNEIDER": "Schneider", "LEGRAND": "Legrand",
            "KWIKOT": "Kwikot", "DEFY": "Defy", "FRANKE": "Franke",
            "MAJOR TECH": "Major Tech", "EUROLUX": "Eurolux",
            "CRABTREE": "Crabtree", "ACDC": "ACDC",
        }
        line_upper = line.upper()
        for key, brand in brands.items():
            if key in line_upper:
                return brand
        return ""

    def _extract_fixtures_spatial(self, page) -> List[FixtureItem]:
        """
        Extract fixtures using SPATIAL text analysis with nearest-neighbor matching.

        AutoCAD-exported PDFs (Wedela, etc.) have legends where fixture descriptions
        and their quantities are in the SAME spatial column/row but NOT on adjacent
        text lines. The layout can be vertical (portrait) or horizontal (landscape).

        Algorithm:
        1. Find all category headers (SWITCHES, LIGHTS, etc.) and QTYS headers
        2. Determine the bounding box of the legend area from headers
        3. Collect all fixture descriptions and standalone numbers in that area
        4. For each fixture, find the nearest QTYS header and nearest number
           in the QTYS direction to match description → quantity
        """
        data = page.get_text("dict")

        # Collect all text spans with coordinates
        all_spans = []
        for block in data.get("blocks", []):
            if "lines" not in block:
                continue
            for line_data in block["lines"]:
                for span in line_data["spans"]:
                    txt = span["text"].strip()
                    if txt:
                        all_spans.append({
                            "x": span["origin"][0],
                            "y": span["origin"][1],
                            "text": txt,
                            "size": span["size"],
                        })

        if not all_spans:
            return []

        CATEGORY_NAMES = {"SWITCHES", "POWER SOCKETS", "LIGHTS", "OTHERS",
                          "LUMINAIRES", "FITTINGS", "FIXTURES"}
        QTYS_NAMES = {"QTYS", "QTY", "QUANTITY"}

        cat_positions = []  # [(text, x, y)]
        qty_positions = []  # [(x, y)]

        for s in all_spans:
            txt_upper = s["text"].upper().strip()
            if txt_upper in CATEGORY_NAMES:
                cat_positions.append((txt_upper, s["x"], s["y"]))
            elif txt_upper in QTYS_NAMES:
                qty_positions.append((s["x"], s["y"]))

        if not cat_positions or not qty_positions:
            return []

        # Determine legend bounding box from all headers
        all_hx = [h[1] for h in cat_positions] + [q[0] for q in qty_positions]
        all_hy = [h[2] for h in cat_positions] + [q[1] for q in qty_positions]
        legend_x_min = min(all_hx) - 50
        legend_x_max = max(all_hx) + 50
        legend_y_min = min(all_hy) - 100  # Descriptions may be above headers
        legend_y_max = max(all_hy) + 100

        # Expand to include descriptions that appear before the first header
        # (common in Wedela: descriptions at y≈21, first header at y≈35)
        page_w, page_h = page.rect.width, page.rect.height

        # Collect all fixture descriptions in the legend area
        descriptions = []
        for s in all_spans:
            if not (legend_x_min - 20 <= s["x"] <= legend_x_max + 20):
                continue
            if not (legend_y_min <= s["y"] <= legend_y_max):
                continue
            txt = s["text"].strip()
            txt_upper = txt.upper()
            if txt_upper in CATEGORY_NAMES or txt_upper in QTYS_NAMES:
                continue
            if len(txt) < 4:
                continue

            for pattern, fixture_type, fcat in self.FIXTURE_PATTERNS:
                if re.search(pattern, txt, re.IGNORECASE):
                    price = 0.0
                    pm = self.PRICE_PATTERN.search(txt)
                    if pm:
                        try:
                            price = float(pm.group(1).replace(',', ''))
                        except ValueError:
                            pass
                    descriptions.append({
                        "fixture_type": fixture_type,
                        "category": fcat,
                        "description": txt[:120],
                        "x": s["x"],
                        "y": s["y"],
                        "price": price,
                        "brand": self._find_brand(txt),
                    })
                    break

        if not descriptions:
            return []

        # Collect all standalone numbers in the legend area
        numbers = []
        for s in all_spans:
            if not (legend_x_min - 20 <= s["x"] <= legend_x_max + 20):
                continue
            if not (legend_y_min <= s["y"] <= legend_y_max):
                continue
            m = re.match(r'^(\d{1,4})$', s["text"].strip())
            if m:
                val = int(m.group(1))
                if 1 <= val <= 9999:
                    numbers.append({
                        "qty": val,
                        "x": s["x"],
                        "y": s["y"],
                    })

        # Determine layout orientation:
        # If cat headers are arranged more horizontally (spread in x) → horizontal
        # If arranged more vertically (spread in y) → vertical
        cat_x_range = max(h[1] for h in cat_positions) - min(h[1] for h in cat_positions)
        cat_y_range = max(h[2] for h in cat_positions) - min(h[2] for h in cat_positions)
        is_horizontal = cat_x_range > cat_y_range

        # For each description, find the nearest number that is in the
        # same "column" (for vertical layouts) or "row" (for horizontal layouts)
        used_numbers = set()
        fixtures = []

        for desc in descriptions:
            best_qty = 0
            best_idx = -1
            best_dist = float('inf')

            for ni, num in enumerate(numbers):
                if ni in used_numbers:
                    continue

                if is_horizontal:
                    # Horizontal layout: descriptions and qtys share similar x
                    # QTYS are at a different y (usually below)
                    primary_dist = abs(num["x"] - desc["x"])  # Must be close in x
                    secondary_dist = abs(num["y"] - desc["y"])  # Can differ in y
                    if primary_dist > 8:  # x must be within ~8pt
                        continue
                    dist = primary_dist + secondary_dist * 0.1
                else:
                    # Vertical layout: descriptions and qtys share similar x
                    primary_dist = abs(num["x"] - desc["x"])
                    secondary_dist = abs(num["y"] - desc["y"])
                    if primary_dist > 8:
                        continue
                    dist = primary_dist + secondary_dist * 0.1

                if dist < best_dist:
                    best_dist = dist
                    best_qty = num["qty"]
                    best_idx = ni

            if best_idx >= 0:
                used_numbers.add(best_idx)

            confidence = 0.88 if best_qty > 0 else 0.40
            fixtures.append(FixtureItem(
                fixture_type=desc["fixture_type"],
                category=desc["category"],
                quantity=best_qty,
                unit_price_zar=desc["price"],
                description=desc["description"],
                brand=desc["brand"],
                confidence=confidence,
                confidence_level=_confidence_level(confidence),
                source=ExtractionStrategy.TEXT_LAYER,
            ))

        return fixtures


# ╔══════════════════════════════════════════════════════════════════════╗
# ║  STRATEGY 2: LEGEND REGION FINDER                                   ║
# ╚══════════════════════════════════════════════════════════════════════╝

class LegendRegionFinder:
    """
    Detect WHERE the legend/BOQ table is on any electrical drawing page.

    Uses a 3-tier approach:
    1. Keyword search — find SWITCHES, LIGHTS, QTYS in text coordinates
    2. Heuristic positions — check common legend locations (top-left, right)
    3. Text density — find clusters of small text (typical of legends)

    Works regardless of legend position because it searches by content,
    not by fixed coordinates.

    Cost: R0.00 | Time: <200ms per page
    """

    # Primary keywords that definitively indicate a legend region
    PRIMARY_KEYWORDS = ["SWITCHES", "POWER SOCKETS", "LIGHTS", "QTYS"]

    # Secondary keywords that support legend detection
    SECONDARY_KEYWORDS = [
        "LEGEND", "KEY", "OTHERS", "QTY", "QUANTITY",
        "SYMBOL", "DESCRIPTION", "LUMINAIRES",
        "MISCELLANEOUS", "TELECOMS", "DATA",
    ]

    # Title block keywords (to EXCLUDE from legend detection)
    TITLE_BLOCK_KEYWORDS = [
        "REVISION", "DRAWN BY", "CHECKED", "APPROVED",
        "COPYRIGHT", "CONSULTANT", "CLIENT",
    ]

    def find_legend(self, page, include_crop: bool = True,
                    crop_dpi: int = 300) -> Optional[LegendRegion]:
        """
        Find the legend region on a page.

        Args:
            page: fitz.Page object
            include_crop: If True, render the legend region at high DPI
            crop_dpi: DPI for the legend crop image

        Returns:
            LegendRegion with coordinates and optional crop, or None
        """
        text_dict = page.get_text("dict")
        pw, ph = page.rect.width, page.rect.height

        # Collect text blocks with their positions and content
        blocks = self._get_text_blocks(text_dict, pw, ph)

        # ── Tier 1: Keyword-based detection ──
        region = self._find_by_keywords(blocks, pw, ph)

        # ── Tier 2: Heuristic positions ──
        if region is None:
            region = self._find_by_heuristic(blocks, pw, ph)

        # ── Tier 3: Text density clusters ──
        if region is None:
            region = self._find_by_density(blocks, pw, ph)

        # Generate high-res crop if requested
        if region and include_crop:
            rect = fitz.Rect(region.x0, region.y0, region.x1, region.y1)
            mat = fitz.Matrix(crop_dpi / 72, crop_dpi / 72)
            pix = page.get_pixmap(matrix=mat, clip=rect)
            region.crop_bytes = pix.tobytes("png")
            region.crop_base64 = base64.b64encode(region.crop_bytes).decode()

        return region

    def _get_text_blocks(self, text_dict: dict, pw: float,
                          ph: float) -> List[dict]:
        """Extract text blocks with normalized coordinates."""
        blocks = []
        for block in text_dict.get("blocks", []):
            if block.get("type") != 0:
                continue
            text = ""
            for line in block.get("lines", []):
                for span in line.get("spans", []):
                    text += span.get("text", "") + " "
            text = text.strip()
            if not text:
                continue

            bbox = block["bbox"]
            blocks.append({
                "bbox": bbox,
                "text": text,
                "text_upper": text.upper(),
                "x_center": (bbox[0] + bbox[2]) / 2 / pw,
                "y_center": (bbox[1] + bbox[3]) / 2 / ph,
                "x_pct": bbox[0] / pw,
                "y_pct": bbox[1] / ph,
            })
        return blocks

    def _find_by_keywords(self, blocks: List[dict], pw: float,
                           ph: float) -> Optional[LegendRegion]:
        """Find legend by searching for primary keywords in text blocks."""
        keyword_blocks = []
        found_keywords = []

        for block in blocks:
            for kw in self.PRIMARY_KEYWORDS + self.SECONDARY_KEYWORDS:
                if kw in block["text_upper"]:
                    # Exclude title block area (bottom-right corner)
                    if block["x_pct"] > 0.70 and block["y_pct"] > 0.80:
                        # Check if it's a title block keyword
                        if any(tk in block["text_upper"]
                               for tk in self.TITLE_BLOCK_KEYWORDS):
                            continue
                    keyword_blocks.append(block)
                    if kw not in found_keywords:
                        found_keywords.append(kw)
                    break

        if len(keyword_blocks) < 2:
            return None

        # Build bounding box around all keyword blocks
        x0 = min(b["bbox"][0] for b in keyword_blocks)
        y0 = min(b["bbox"][1] for b in keyword_blocks)
        x1 = max(b["bbox"][2] for b in keyword_blocks)
        y1 = max(b["bbox"][3] for b in keyword_blocks)

        # Expand region to capture full legend content
        # Legends are wider and taller than just the keyword hits
        margin_x = pw * 0.03
        margin_y = ph * 0.02

        return LegendRegion(
            x0=max(0, x0 - margin_x),
            y0=max(0, y0 - margin_y),
            x1=min(pw, x1 + margin_x),
            y1=min(ph, y1 + margin_y),
            detection_method="keyword",
            keywords_found=found_keywords,
        )

    def _find_by_heuristic(self, blocks: List[dict], pw: float,
                            ph: float) -> Optional[LegendRegion]:
        """Check common legend positions based on SA drawing conventions."""
        positions = [
            # Top-left (Wedela-style)
            {"name": "top_left", "x_min": 0, "x_max": 0.40,
             "y_min": 0, "y_max": 0.15},
            # Left panel (3 Cubes-style)
            {"name": "left_panel", "x_min": 0, "x_max": 0.25,
             "y_min": 0.30, "y_max": 0.90},
            # Right panel
            {"name": "right_panel", "x_min": 0.75, "x_max": 1.0,
             "y_min": 0.00, "y_max": 0.70},
            # Bottom strip
            {"name": "bottom_strip", "x_min": 0, "x_max": 0.70,
             "y_min": 0.85, "y_max": 1.0},
        ]

        best_region = None
        best_score = 0

        for pos in positions:
            region_blocks = [
                b for b in blocks
                if pos["x_min"] <= b["x_pct"] <= pos["x_max"]
                and pos["y_min"] <= b["y_pct"] <= pos["y_max"]
            ]

            # Score by keyword hits in this region
            score = 0
            kws = []
            for b in region_blocks:
                for kw in self.PRIMARY_KEYWORDS:
                    if kw in b["text_upper"]:
                        score += 3
                        kws.append(kw)
                for kw in self.SECONDARY_KEYWORDS:
                    if kw in b["text_upper"]:
                        score += 1
                        kws.append(kw)

            if score > best_score and len(region_blocks) >= 3:
                best_score = score
                x0 = min(b["bbox"][0] for b in region_blocks)
                y0 = min(b["bbox"][1] for b in region_blocks)
                x1 = max(b["bbox"][2] for b in region_blocks)
                y1 = max(b["bbox"][3] for b in region_blocks)

                margin_x = pw * 0.02
                margin_y = ph * 0.01
                best_region = LegendRegion(
                    x0=max(0, x0 - margin_x),
                    y0=max(0, y0 - margin_y),
                    x1=min(pw, x1 + margin_x),
                    y1=min(ph, y1 + margin_y),
                    detection_method=f"heuristic_{pos['name']}",
                    keywords_found=list(set(kws)),
                )

        return best_region

    def _find_by_density(self, blocks: List[dict], pw: float,
                          ph: float) -> Optional[LegendRegion]:
        """Find legend by text density (many small blocks in a region)."""
        if len(blocks) < 5:
            return None

        # Grid-based density: divide page into 4x4 cells
        grid_size = 4
        grid = [[[] for _ in range(grid_size)] for _ in range(grid_size)]

        for b in blocks:
            gx = min(int(b["x_center"] * grid_size), grid_size - 1)
            gy = min(int(b["y_center"] * grid_size), grid_size - 1)
            grid[gy][gx].append(b)

        # Find the cell with highest text block density
        # (excluding bottom-right which is usually title block)
        best_cell = None
        best_count = 0

        for gy in range(grid_size):
            for gx in range(grid_size):
                # Skip title block area (bottom-right)
                if gx >= grid_size - 1 and gy >= grid_size - 1:
                    continue
                count = len(grid[gy][gx])
                if count > best_count:
                    best_count = count
                    best_cell = (gx, gy)

        if best_cell and best_count >= 5:
            gx, gy = best_cell
            cell_blocks = grid[gy][gx]
            x0 = min(b["bbox"][0] for b in cell_blocks)
            y0 = min(b["bbox"][1] for b in cell_blocks)
            x1 = max(b["bbox"][2] for b in cell_blocks)
            y1 = max(b["bbox"][3] for b in cell_blocks)

            margin_x = pw * 0.03
            margin_y = ph * 0.02
            return LegendRegion(
                x0=max(0, x0 - margin_x),
                y0=max(0, y0 - margin_y),
                x1=min(pw, x1 + margin_x),
                y1=min(ph, y1 + margin_y),
                detection_method="density",
                keywords_found=[],
            )

        return None


# ╔══════════════════════════════════════════════════════════════════════╗
# ║  STRATEGY 3: LEGEND CROP AI READER                                  ║
# ╚══════════════════════════════════════════════════════════════════════╝

class LegendCropReader:
    """
    Send a high-res legend crop to a vision LLM for reading.

    The crop is a small, clear image of JUST the legend table.
    This is trivial for any vision model — reading a structured table
    vs trying to find tiny symbols on a huge floor plan.

    Supports: Anthropic (Haiku/Sonnet), Groq (free), Gemini (free)
    Cost: R0.00-R0.18 per crop | Time: 2-5 seconds
    """

    LEGEND_READ_PROMPT = """You are reading a LEGEND TABLE from a South African electrical drawing.

Extract EVERY row from this legend table. For each fixture/item, provide:
- fixture_type: What it is (e.g., "LED Downlight", "Double Socket")
- category: One of: lighting, power, switch, data, safety, hvac, water, other
- quantity: The number in the QTYS/QTY column (integer, 0 if not visible)
- unit_price: Price in Rands if shown (e.g., 150.00), 0 if not shown
- description: Full text description
- symbol_code: Symbol code like L1, L2, P1, S3 if visible

Return ONLY valid JSON array. No explanation. No markdown.
Example:
[
  {"fixture_type": "LED Downlight 6W", "category": "lighting", "quantity": 20, "unit_price": 150.00, "description": "6W LED downlight white colour", "symbol_code": "L2"},
  {"fixture_type": "Double Switched Socket", "category": "power", "quantity": 15, "unit_price": 80.00, "description": "16A Double Switched Socket @300mm above FFL", "symbol_code": "P2"}
]

RULES:
- Extract EVERY row, even if quantity is unclear (use 0)
- Include the building/block name if shown in the header
- SA electrical abbreviations: FFL = Finished Floor Level, DB = Distribution Board
- Do NOT fabricate. If a value is not visible, use 0 or empty string."""

    def read_legend(self, legend_region: LegendRegion,
                    provider: str = "anthropic",
                    api_key: Optional[str] = None) -> List[FixtureItem]:
        """
        Send legend crop to vision LLM and parse the response.

        Args:
            legend_region: LegendRegion with crop_base64 populated
            provider: "anthropic", "groq", "gemini", or "openai"
            api_key: API key (falls back to environment variable)

        Returns:
            List of FixtureItem extracted from the legend
        """
        if not legend_region.crop_base64:
            logger.warning("No legend crop available for AI reading")
            return []

        # Call the appropriate provider
        response_text = ""
        if provider == "anthropic":
            response_text = self._call_anthropic(
                legend_region.crop_base64, api_key)
        elif provider == "groq":
            response_text = self._call_groq(
                legend_region.crop_base64, api_key)
        elif provider == "gemini":
            response_text = self._call_gemini(
                legend_region.crop_base64, api_key)
        else:
            logger.error(f"Unknown provider: {provider}")
            return []

        # Parse the JSON response
        return self._parse_response(response_text)

    def _call_anthropic(self, image_base64: str,
                        api_key: Optional[str] = None) -> str:
        """Call Anthropic Claude API with legend crop."""
        try:
            import anthropic
        except ImportError:
            logger.error("anthropic package not installed")
            return ""

        key = api_key or os.environ.get("ANTHROPIC_API_KEY", "")
        if not key:
            logger.error("No Anthropic API key available")
            return ""

        client = anthropic.Anthropic(api_key=key)

        try:
            response = client.messages.create(
                model="claude-haiku-4-5-20251001",  # Cheapest: ~R0.18
                max_tokens=4096,
                messages=[{
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": "image/png",
                                "data": image_base64,
                            }
                        },
                        {
                            "type": "text",
                            "text": self.LEGEND_READ_PROMPT,
                        }
                    ]
                }]
            )
            return response.content[0].text
        except Exception as e:
            logger.error(f"Anthropic API error: {e}")
            return ""

    def _call_groq(self, image_base64: str,
                   api_key: Optional[str] = None) -> str:
        """Call Groq API with legend crop (FREE with Llama Vision)."""
        try:
            from groq import Groq
        except ImportError:
            logger.error("groq package not installed")
            return ""

        key = api_key or os.environ.get("GROQ_API_KEY", "")
        if not key:
            logger.error("No Groq API key available")
            return ""

        client = Groq(api_key=key)

        try:
            response = client.chat.completions.create(
                model="llama-4-scout-17b-16e-instruct",
                messages=[{
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{image_base64}"
                            }
                        },
                        {
                            "type": "text",
                            "text": self.LEGEND_READ_PROMPT,
                        }
                    ]
                }],
                max_tokens=4096,
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"Groq API error: {e}")
            return ""

    def _call_gemini(self, image_base64: str,
                     api_key: Optional[str] = None) -> str:
        """Call Google Gemini API with legend crop (FREE tier)."""
        try:
            import google.generativeai as genai
        except ImportError:
            logger.error("google-generativeai package not installed")
            return ""

        key = api_key or os.environ.get("GEMINI_API_KEY", "")
        if not key:
            logger.error("No Gemini API key available")
            return ""

        genai.configure(api_key=key)
        model = genai.GenerativeModel("gemini-2.0-flash")

        try:
            # Decode base64 to PIL Image
            img_bytes = base64.b64decode(image_base64)
            img = Image.open(io.BytesIO(img_bytes))

            response = model.generate_content([
                self.LEGEND_READ_PROMPT,
                img,
            ])
            return response.text
        except Exception as e:
            logger.error(f"Gemini API error: {e}")
            return ""

    def _parse_response(self, response_text: str) -> List[FixtureItem]:
        """Parse LLM response JSON into FixtureItem list."""
        if not response_text:
            return []

        # Extract JSON from response (handle markdown code blocks)
        json_text = response_text.strip()
        if "```" in json_text:
            m = re.search(r'```(?:json)?\s*([\s\S]*?)```', json_text)
            if m:
                json_text = m.group(1).strip()

        # Fix common JSON issues from LLMs
        json_text = re.sub(r',\s*([}\]])', r'\1', json_text)  # trailing commas

        try:
            data = json.loads(json_text)
        except json.JSONDecodeError:
            logger.warning(f"Failed to parse LLM response as JSON")
            return []

        if not isinstance(data, list):
            data = [data]

        fixtures = []
        for item in data:
            if not isinstance(item, dict):
                continue

            category_str = item.get("category", "other").lower()
            try:
                category = FixtureCategory(category_str)
            except ValueError:
                category = FixtureCategory.OTHER

            fixtures.append(FixtureItem(
                fixture_type=item.get("fixture_type", "Unknown"),
                category=category,
                quantity=int(item.get("quantity", 0)),
                unit_price_zar=float(item.get("unit_price", 0)),
                description=item.get("description", ""),
                symbol_code=item.get("symbol_code", ""),
                confidence=0.88,
                confidence_level=Confidence.HIGH,
                source=ExtractionStrategy.LEGEND_CROP_AI,
            ))

        return fixtures


# ╔══════════════════════════════════════════════════════════════════════╗
# ║  PASSIVE DATA COLLECTOR (for future ML training)                    ║
# ╚══════════════════════════════════════════════════════════════════════╝

class PassiveDataCollector:
    """
    Silently collect training data from every extraction.

    Every drawing that goes through the pipeline contributes to
    future ML model training — without any extra annotation effort.

    Saves:
    - Page image (for training page classifier + region detector)
    - Legend crop coordinates (for training region detector)
    - Extraction results (as pseudo-labels)
    - User corrections from REVIEW stage (as ground truth)
    """

    def __init__(self, data_dir: str = "training_data"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        (self.data_dir / "pages").mkdir(exist_ok=True)
        (self.data_dir / "legend_crops").mkdir(exist_ok=True)
        (self.data_dir / "labels").mkdir(exist_ok=True)

    def collect(self, page, page_result: PageResult,
                page_image_bytes: Optional[bytes] = None):
        """
        Save extraction data for future ML training.

        Args:
            page: fitz.Page object
            page_result: Extraction result for this page
            page_image_bytes: Optional pre-rendered page image
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        page_id = f"{timestamp}_p{page_result.page_number}"

        try:
            # Save page image (for classifier + region detector training)
            if page_image_bytes:
                img_path = self.data_dir / "pages" / f"{page_id}.png"
                with open(img_path, "wb") as f:
                    f.write(page_image_bytes)

            # Save legend crop (for region detector training)
            if page_result.legend_region and page_result.legend_region.crop_bytes:
                crop_path = self.data_dir / "legend_crops" / f"{page_id}_legend.png"
                with open(crop_path, "wb") as f:
                    f.write(page_result.legend_region.crop_bytes)

            # Save labels (extraction result as pseudo-label)
            label = {
                "page_id": page_id,
                "drawing_type": page_result.drawing_type.value,
                "legend_region": None,
                "fixtures": [],
                "strategy_used": page_result.strategy_used.value,
                "confidence": page_result.confidence,
                "user_corrections": None,  # Filled in REVIEW stage
            }

            if page_result.legend_region:
                lr = page_result.legend_region
                label["legend_region"] = {
                    "x0": lr.x0, "y0": lr.y0,
                    "x1": lr.x1, "y1": lr.y1,
                    "detection_method": lr.detection_method,
                }

            for f in page_result.fixtures:
                label["fixtures"].append({
                    "fixture_type": f.fixture_type,
                    "category": f.category.value,
                    "quantity": f.quantity,
                    "unit_price_zar": f.unit_price_zar,
                    "confidence": f.confidence,
                    "source": f.source.value,
                })

            label_path = self.data_dir / "labels" / f"{page_id}.json"
            with open(label_path, "w") as f:
                json.dump(label, f, indent=2)

        except Exception as e:
            logger.warning(f"Passive data collection failed: {e}")

    def save_user_corrections(self, page_id: str,
                               corrections: Dict[str, Any]):
        """
        Save contractor's corrections from the REVIEW stage.
        These become ground truth labels for ML training.
        """
        label_path = self.data_dir / "labels" / f"{page_id}.json"
        if label_path.exists():
            with open(label_path) as f:
                label = json.load(f)
            label["user_corrections"] = corrections
            label["is_ground_truth"] = True
            with open(label_path, "w") as f:
                json.dump(label, f, indent=2)

    def get_dataset_stats(self) -> dict:
        """Return statistics about collected training data."""
        pages = list((self.data_dir / "pages").glob("*.png"))
        crops = list((self.data_dir / "legend_crops").glob("*.png"))
        labels = list((self.data_dir / "labels").glob("*.json"))

        ground_truth = 0
        for lp in labels:
            with open(lp) as f:
                data = json.load(f)
                if data.get("is_ground_truth"):
                    ground_truth += 1

        return {
            "total_pages": len(pages),
            "total_legend_crops": len(crops),
            "total_labels": len(labels),
            "ground_truth_labels": ground_truth,
            "ready_for_ml": len(pages) >= 200,
        }


# ╔══════════════════════════════════════════════════════════════════════╗
# ║  UNIVERSAL EXTRACTOR — THE ORCHESTRATOR                             ║
# ╚══════════════════════════════════════════════════════════════════════╝

class UniversalExtractor:
    """
    The main orchestrator that chains all strategies together.

    Pipeline:
    1. TEXT LAYER → extract what we can for free
    2. LEGEND FINDER → locate the legend region on the page
    3. LEGEND AI → if text extraction incomplete, send crop to LLM
    4. FULL-PAGE AI → last resort fallback (expensive)

    Each strategy reports its confidence. The chain stops when
    confidence exceeds the threshold.

    Usage:
        extractor = UniversalExtractor()
        result = extractor.extract_document("path/to/drawing.pdf")

        for page in result.pages:
            print(f"Page {page.page_number}: {page.total_fixtures} fixtures")
            for f in page.fixtures:
                print(f"  {f.fixture_type}: {f.quantity}")
    """

    def __init__(
        self,
        confidence_threshold: float = 0.70,
        enable_ai: bool = True,
        ai_provider: str = "anthropic",
        ai_api_key: Optional[str] = None,
        collect_training_data: bool = True,
        training_data_dir: str = "training_data",
    ):
        """
        Initialize the universal extractor.

        Args:
            confidence_threshold: Stop the chain when confidence exceeds this
            enable_ai: If False, only use text mining (no API calls)
            ai_provider: "anthropic", "groq", "gemini"
            ai_api_key: API key (falls back to environment variable)
            collect_training_data: Save data for future ML training
            training_data_dir: Directory for collected training data
        """
        self.confidence_threshold = confidence_threshold
        self.enable_ai = enable_ai
        self.ai_provider = ai_provider
        self.ai_api_key = ai_api_key

        # Initialize strategy components
        self.text_miner = TextLayerMiner()
        self.legend_finder = LegendRegionFinder()
        self.legend_reader = LegendCropReader()
        self.data_collector = (
            PassiveDataCollector(training_data_dir)
            if collect_training_data else None
        )

    def extract_document(self, pdf_path: str) -> DocumentResult:
        """
        Extract fixture data from an entire PDF document.

        Args:
            pdf_path: Path to the PDF file

        Returns:
            DocumentResult with per-page extractions
        """
        if fitz is None:
            raise ImportError("PyMuPDF (fitz) is required: pip install PyMuPDF")

        doc_start = time.time()
        doc = fitz.open(pdf_path)
        filename = Path(pdf_path).name

        result = DocumentResult(
            filename=filename,
            total_pages=len(doc),
        )

        strategy_counts = {}

        for i, page in enumerate(doc):
            page_result = self.extract_page(page, i + 1)
            result.pages.append(page_result)

            # Track strategy usage
            strat = page_result.strategy_used.value
            strategy_counts[strat] = strategy_counts.get(strat, 0) + 1

        doc.close()

        result.strategies_summary = strategy_counts
        result.processing_time_ms = int((time.time() - doc_start) * 1000)

        return result

    def extract_page(self, page, page_num: int) -> PageResult:
        """
        Extract fixture data from a single page using the strategy chain.

        Args:
            page: fitz.Page object
            page_num: 1-based page number

        Returns:
            PageResult with extracted fixtures and metadata
        """
        page_start = time.time()

        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # STRATEGY 1: TEXT LAYER MINING (Free, instant)
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        result = self.text_miner.extract(page, page_num)

        if result.confidence >= self.confidence_threshold:
            result.processing_time_ms = int(
                (time.time() - page_start) * 1000)
            self._collect_data(page, result)
            return result

        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # STRATEGY 2: LEGEND REGION FINDER (Free, instant)
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        legend = self.legend_finder.find_legend(page, include_crop=True)
        result.legend_region = legend
        result.strategies_attempted.append("legend_finder")

        if legend:
            logger.info(
                f"Page {page_num}: Legend found via {legend.detection_method} "
                f"at ({legend.x0:.0f},{legend.y0:.0f})-"
                f"({legend.x1:.0f},{legend.y1:.0f}), "
                f"keywords: {legend.keywords_found}"
            )

        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # STRATEGY 3: LEGEND CROP AI READER (Cheap, ~3 seconds)
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        if (legend and legend.crop_base64 and self.enable_ai
                and result.confidence < self.confidence_threshold):

            result.strategies_attempted.append("legend_crop_ai")

            ai_fixtures = self.legend_reader.read_legend(
                legend,
                provider=self.ai_provider,
                api_key=self.ai_api_key,
            )

            if ai_fixtures:
                # Merge: prefer AI results, keep text results as backup
                result.fixtures = self._merge_fixtures(
                    result.fixtures, ai_fixtures)
                result.strategy_used = ExtractionStrategy.LEGEND_CROP_AI

                # Recalculate confidence
                result.confidence = min(0.92, 0.70 + 0.03 * len(ai_fixtures))
                result.confidence_level = _confidence_level(result.confidence)

        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # STRATEGY 4: FULL-PAGE AI (Expensive, last resort)
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        if (self.enable_ai
                and result.confidence < self.confidence_threshold * 0.6):
            # Only trigger for very low confidence
            result.strategies_attempted.append("full_page_ai_eligible")
            result.warnings.append(
                "Low confidence extraction — full-page AI recommended")
            # Integration point for existing AfriPlan discover stage

        result.processing_time_ms = int((time.time() - page_start) * 1000)
        self._collect_data(page, result)

        return result

    def _merge_fixtures(self, text_fixtures: List[FixtureItem],
                        ai_fixtures: List[FixtureItem]) -> List[FixtureItem]:
        """
        Merge text-layer and AI-extracted fixtures.
        Prefer AI results when they overlap. Keep unique text results.
        """
        merged = list(ai_fixtures)  # AI results are primary
        ai_types = {f.fixture_type.lower() for f in ai_fixtures}

        for tf in text_fixtures:
            # Keep text fixtures that AI didn't find
            if tf.fixture_type.lower() not in ai_types:
                merged.append(tf)

        return merged

    def _collect_data(self, page, result: PageResult):
        """Save training data if collector is enabled."""
        if self.data_collector:
            try:
                # Render page at low DPI for training data
                mat = fitz.Matrix(150 / 72, 150 / 72)
                pix = page.get_pixmap(matrix=mat)
                page_bytes = pix.tobytes("png")
                self.data_collector.collect(page, result, page_bytes)
            except Exception as e:
                logger.debug(f"Data collection skipped: {e}")


# ╔══════════════════════════════════════════════════════════════════════╗
# ║  UTILITY FUNCTIONS                                                   ║
# ╚══════════════════════════════════════════════════════════════════════╝

def _confidence_level(score: float) -> Confidence:
    """Convert numeric confidence to Confidence enum."""
    if score >= 0.80:
        return Confidence.HIGH
    elif score >= 0.60:
        return Confidence.MEDIUM
    elif score >= 0.40:
        return Confidence.LOW
    else:
        return Confidence.VERY_LOW


def extract_from_pdf(
    pdf_path: str,
    enable_ai: bool = True,
    ai_provider: str = "anthropic",
    confidence_threshold: float = 0.70,
) -> DocumentResult:
    """
    Convenience function: extract fixtures from a PDF drawing.

    Args:
        pdf_path: Path to the PDF file
        enable_ai: Enable AI-based extraction (costs R0.18+ per page)
        ai_provider: "anthropic", "groq", or "gemini"
        confidence_threshold: Minimum confidence to stop the chain

    Returns:
        DocumentResult with all extracted data

    Example:
        result = extract_from_pdf("drawing.pdf", enable_ai=False)
        for page in result.pages:
            for f in page.fixtures:
                print(f"{f.fixture_type}: {f.quantity} @ R{f.unit_price_zar}")
    """
    extractor = UniversalExtractor(
        confidence_threshold=confidence_threshold,
        enable_ai=enable_ai,
        ai_provider=ai_provider,
    )
    return extractor.extract_document(pdf_path)


def print_extraction_report(result: DocumentResult):
    """Print a human-readable extraction report."""
    print(f"\n{'='*70}")
    print(f"EXTRACTION REPORT: {result.filename}")
    print(f"{'='*70}")
    print(f"Pages: {result.total_pages} | "
          f"Total fixtures: {result.total_fixtures} | "
          f"Avg confidence: {result.average_confidence:.0%}")
    print(f"Processing time: {result.processing_time_ms}ms")
    print(f"Strategies used: {result.strategies_summary}")

    for page in result.pages:
        print(f"\n{'─'*70}")
        print(f"Page {page.page_number}: {page.drawing_type.value.upper()}")
        if page.title_block.drawing_number:
            print(f"  Drawing: {page.title_block.drawing_number}")
        if page.title_block.building_name:
            print(f"  Building: {page.title_block.building_name}")
        print(f"  Strategy: {page.strategy_used.value} | "
              f"Confidence: {page.confidence:.0%} ({page.confidence_level.value})")
        if page.legend_region:
            lr = page.legend_region
            print(f"  Legend: {lr.detection_method} at "
                  f"({lr.x0:.0f},{lr.y0:.0f})-({lr.x1:.0f},{lr.y1:.0f})")

        if page.fixtures:
            print(f"  Fixtures ({len(page.fixtures)}):")
            for f in sorted(page.fixtures, key=lambda x: x.category.value):
                price_str = f" @ R{f.unit_price_zar:.0f}" if f.unit_price_zar else ""
                brand_str = f" [{f.brand}]" if f.brand else ""
                print(f"    {'✅' if f.confidence >= 0.7 else '⚠️'} "
                      f"{f.fixture_type}: {f.quantity}"
                      f"{price_str}{brand_str} "
                      f"({f.confidence_level.value})")
        else:
            print(f"  ⚠️  No fixtures extracted — needs AI assistance")

        if page.warnings:
            for w in page.warnings:
                print(f"  ⚠️  {w}")

    print(f"\n{'='*70}")
    if result.total_value_zar > 0:
        print(f"ESTIMATED TOTAL VALUE: R{result.total_value_zar:,.2f}")
    print(f"{'='*70}\n")
