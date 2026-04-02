"""
AfriPlan Electrical — DXF Extraction Module v1.2

R0.00 cost, <100ms extraction from AutoCAD / ArchiCAD DXF files.

Supports TWO extraction paths:

Path A — Native AutoCAD DXF (named blocks):
  Block INSERTs with short names (DL, DS, SW1) on electrical layers.
  Matched via abbreviation map → regex → layer inference.

Path B — ArchiCAD / PDF-to-DXF exports (text legend + geometry):
  Fixtures drawn as raw geometry (LINE, ARC, CIRCLE) on MEP layers.
  Legend table stored as TEXT/MTEXT on PDF_Text or annotation layers.
  Circuit labels (DB-S3, L1, L2) on B_ELECTRICAL WIRE layer.
  We parse the legend text to extract fixture types and descriptions,
  count circuit labels, and match full-name INSERT blocks.

Author: JLWanalytics
Version: 1.2.0
"""

from __future__ import annotations

import io
import re
import time
import logging
from pathlib import Path
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Optional, Any

try:
    import ezdxf
    HAS_EZDXF = True
except ImportError:
    ezdxf = None
    HAS_EZDXF = False

try:
    from shapely.geometry import Point, Polygon
    HAS_SHAPELY = True
except ImportError:
    Polygon = None
    Point = None
    HAS_SHAPELY = False

from agent.universal_extractor import (
    PageResult, FixtureItem, FixtureCategory, DrawingType,
    TitleBlockInfo, Confidence, ExtractionStrategy, DocumentResult,
    _confidence_level,
)

logger = logging.getLogger(__name__)


# ╔══════════════════════════════════════════════════════════════════════╗
# ║  DXF BLOCK NAME → FIXTURE TYPE MAPPING (Path A — short names)       ║
# ╚══════════════════════════════════════════════════════════════════════╝

DEFAULT_BLOCK_MAP: Dict[str, Tuple[str, FixtureCategory]] = {
    # ── Lighting ──
    "DL": ("LED Downlight", FixtureCategory.LIGHTING),
    "D/L": ("LED Downlight", FixtureCategory.LIGHTING),
    "DOWNLIGHT": ("LED Downlight", FixtureCategory.LIGHTING),
    "LED_DN": ("LED Downlight", FixtureCategory.LIGHTING),
    "FL": ("Fluorescent Light", FixtureCategory.LIGHTING),
    "FLUOR": ("Fluorescent Light", FixtureCategory.LIGHTING),
    "RECESS": ("Recessed Fluorescent", FixtureCategory.LIGHTING),
    "FLOOD": ("Floodlight", FixtureCategory.LIGHTING),
    "FLD": ("Floodlight", FixtureCategory.LIGHTING),
    "BH": ("Bulkhead Light", FixtureCategory.LIGHTING),
    "BULKHEAD": ("Bulkhead Light", FixtureCategory.LIGHTING),
    "VP": ("Vapour Proof Light", FixtureCategory.LIGHTING),
    "VAPOUR": ("Vapour Proof Light", FixtureCategory.LIGHTING),
    "WL": ("Wall Light", FixtureCategory.LIGHTING),
    "WALL_LIGHT": ("Wall Light", FixtureCategory.LIGHTING),
    "CL": ("Ceiling Light", FixtureCategory.LIGHTING),
    "CEILING": ("Ceiling Light", FixtureCategory.LIGHTING),
    "PENDANT": ("Pendant Light", FixtureCategory.LIGHTING),
    "EM": ("Emergency Light", FixtureCategory.SAFETY),
    "EMERGENCY": ("Emergency Light", FixtureCategory.SAFETY),
    "EXIT": ("Exit Sign", FixtureCategory.SAFETY),
    "PANEL": ("LED Panel", FixtureCategory.LIGHTING),
    "BATTEN": ("LED Batten", FixtureCategory.LIGHTING),
    "SPOT": ("Spotlight", FixtureCategory.LIGHTING),
    "LIGHT": ("Light Fitting", FixtureCategory.LIGHTING),
    "LUMINAIRE": ("Luminaire", FixtureCategory.LIGHTING),

    # ── Power / Sockets ──
    "DS": ("Double Socket", FixtureCategory.POWER),
    "DSO": ("Double Socket", FixtureCategory.POWER),
    "DOUBLE_SOCKET": ("Double Socket", FixtureCategory.POWER),
    "SS": ("Single Socket", FixtureCategory.POWER),
    "SSO": ("Single Socket", FixtureCategory.POWER),
    "SINGLE_SOCKET": ("Single Socket", FixtureCategory.POWER),
    "WP": ("Weatherproof Socket", FixtureCategory.POWER),
    "WP_SOCKET": ("Weatherproof Socket", FixtureCategory.POWER),
    "GPO": ("General Power Outlet", FixtureCategory.POWER),
    "FLOOR_SOCKET": ("Floor Socket", FixtureCategory.POWER),
    "FS": ("Floor Socket", FixtureCategory.POWER),
    "SOCKET": ("Socket Outlet", FixtureCategory.POWER),
    "PLUG": ("Plug Point", FixtureCategory.POWER),

    # ── Switches ──
    "SW1": ("1-Lever Switch", FixtureCategory.SWITCH),
    "SW_1": ("1-Lever Switch", FixtureCategory.SWITCH),
    "SW2": ("2-Lever Switch", FixtureCategory.SWITCH),
    "SW_2": ("2-Lever Switch", FixtureCategory.SWITCH),
    "SW3": ("3-Lever Switch", FixtureCategory.SWITCH),
    "SW_3": ("3-Lever Switch", FixtureCategory.SWITCH),
    "SW4": ("4-Lever Switch", FixtureCategory.SWITCH),
    "SW_4": ("4-Lever Switch", FixtureCategory.SWITCH),
    "SW": ("Switch", FixtureCategory.SWITCH),
    "ISO": ("Isolator Switch", FixtureCategory.SWITCH),
    "ISOLATOR": ("Isolator Switch", FixtureCategory.SWITCH),
    "DIM": ("Dimmer Switch", FixtureCategory.SWITCH),
    "DIMMER": ("Dimmer Switch", FixtureCategory.SWITCH),
    "DN": ("Day/Night Switch", FixtureCategory.SWITCH),
    "D/N": ("Day/Night Switch", FixtureCategory.SWITCH),

    # ── Data / Telecoms ──
    "DATA": ("Data Socket", FixtureCategory.DATA),
    "RJ45": ("Data Socket (RJ45)", FixtureCategory.DATA),
    "TEL": ("Telephone Socket", FixtureCategory.DATA),
    "TV": ("Television Socket", FixtureCategory.DATA),

    # ── Safety ──
    "SMOKE": ("Smoke Detector", FixtureCategory.SAFETY),
    "PIR": ("PIR Sensor", FixtureCategory.SAFETY),
    "ALARM": ("Alarm Device", FixtureCategory.SAFETY),
    "MCP": ("Manual Call Point", FixtureCategory.SAFETY),

    # ── Equipment ──
    "DB": ("Distribution Board", FixtureCategory.OTHER),
    "DIST_BOARD": ("Distribution Board", FixtureCategory.OTHER),
    "AC": ("Air Conditioning Unit", FixtureCategory.HVAC),
    "AIRCON": ("Air Conditioning Unit", FixtureCategory.HVAC),
    "GEYSER": ("Geyser", FixtureCategory.WATER),
    "HWC": ("Hot Water Cylinder", FixtureCategory.WATER),
    "EF": ("Extractor Fan", FixtureCategory.HVAC),
    "FAN": ("Extractor Fan", FixtureCategory.HVAC),
}

# Regex patterns for firm-specific block names (e.g., "CHONA_DL_01")
BLOCK_NAME_PATTERNS: List[Tuple[str, str, FixtureCategory]] = [
    (r'(?:^|[_\-])DL(?:[_\-]|\d|$)', "LED Downlight", FixtureCategory.LIGHTING),
    (r'(?:^|[_\-])D/?L(?:[_\-]|\d|$)', "LED Downlight", FixtureCategory.LIGHTING),
    (r'(?:^|[_\-])FLD(?:[_\-]|\d|$)', "Floodlight", FixtureCategory.LIGHTING),
    (r'(?:^|[_\-])BH(?:[_\-]|\d|$)', "Bulkhead Light", FixtureCategory.LIGHTING),
    (r'(?:^|[_\-])VP(?:[_\-]|\d|$)', "Vapour Proof Light", FixtureCategory.LIGHTING),
    (r'(?:^|[_\-])DS(?:O)?(?:[_\-]|\d|$)', "Double Socket", FixtureCategory.POWER),
    (r'(?:^|[_\-])SS(?:O)?(?:[_\-]|\d|$)', "Single Socket", FixtureCategory.POWER),
    (r'(?:^|[_\-])GPO(?:[_\-]|\d|$)', "General Power Outlet", FixtureCategory.POWER),
    (r'(?:^|[_\-])SW(\d)?(?:[_\-]|$)', "Switch", FixtureCategory.SWITCH),
    (r'(?:^|[_\-])ISO(?:[_\-]|\d|$)', "Isolator Switch", FixtureCategory.SWITCH),
    (r'SMOKE', "Smoke Detector", FixtureCategory.SAFETY),
    (r'EMERG', "Emergency Light", FixtureCategory.SAFETY),
    (r'(?:^|[_\-])EM(?:[_\-]|\d|$)', "Emergency Light", FixtureCategory.SAFETY),
]

# ╔══════════════════════════════════════════════════════════════════════╗
# ║  FULL-NAME BLOCK MATCHING (Path B — ArchiCAD-style names)            ║
# ╚══════════════════════════════════════════════════════════════════════╝

# ArchiCAD and PDF-to-DXF converters use full descriptive block names.
# These patterns match common full-name formats.
FULL_NAME_PATTERNS: List[Tuple[str, str, FixtureCategory]] = [
    # Sockets
    (r'socket\s*outlet.*2\s*gang', "Double Socket Outlet", FixtureCategory.POWER),
    (r'socket\s*outlet.*1\s*gang', "Single Socket Outlet", FixtureCategory.POWER),
    (r'socket\s*outlet.*double', "Double Socket Outlet", FixtureCategory.POWER),
    (r'socket\s*outlet.*single', "Single Socket Outlet", FixtureCategory.POWER),
    (r'socket\s*outlet', "Socket Outlet", FixtureCategory.POWER),
    (r'double.*socket', "Double Socket Outlet", FixtureCategory.POWER),
    (r'single.*socket', "Single Socket Outlet", FixtureCategory.POWER),
    (r'floor\s*box', "Floor Box", FixtureCategory.POWER),
    (r'floor\s*socket', "Floor Socket", FixtureCategory.POWER),
    # Switches
    (r'switch\s*\d', "Switch", FixtureCategory.SWITCH),
    (r'switch', "Switch", FixtureCategory.SWITCH),
    (r'isolator', "Isolator Switch", FixtureCategory.SWITCH),
    (r'day.?night', "Day/Night Switch", FixtureCategory.SWITCH),
    # Lighting
    (r'downlight', "LED Downlight", FixtureCategory.LIGHTING),
    (r'flood\s*light', "Floodlight", FixtureCategory.LIGHTING),
    (r'fluor', "Fluorescent Light", FixtureCategory.LIGHTING),
    (r'ceiling\s*light', "Ceiling Light", FixtureCategory.LIGHTING),
    (r'bulkhead', "Bulkhead Light", FixtureCategory.LIGHTING),
    (r'batten', "LED Batten", FixtureCategory.LIGHTING),
    (r'pendant', "Pendant Light", FixtureCategory.LIGHTING),
    (r'led\s*panel', "LED Panel", FixtureCategory.LIGHTING),
    # Safety
    (r'smoke\s*detect', "Smoke Detector", FixtureCategory.SAFETY),
    (r'emergency', "Emergency Light", FixtureCategory.SAFETY),
    (r'exit\s*sign', "Exit Sign", FixtureCategory.SAFETY),
    (r'fire\s*extinguish', "Fire Extinguisher", FixtureCategory.SAFETY),
    (r'extinguisher', "Fire Extinguisher", FixtureCategory.SAFETY),
    # Equipment
    (r'distribution\s*board', "Distribution Board", FixtureCategory.OTHER),
    (r'db\s*board', "Distribution Board", FixtureCategory.OTHER),
    (r'air\s*condition', "Air Conditioning Unit", FixtureCategory.HVAC),
    (r'geyser', "Geyser", FixtureCategory.WATER),
    (r'workstation', None, None),  # Skip — furniture, not electrical
    (r'basin', None, None),        # Skip — plumbing
    (r'cabinet', None, None),      # Skip — furniture
    (r'\bwc\b', None, None),       # Skip — plumbing
    (r'stair', None, None),        # Skip — architectural
    (r'railing', None, None),      # Skip — architectural
    (r'morph', None, None),        # Skip — ArchiCAD geometry
]

# ╔══════════════════════════════════════════════════════════════════════╗
# ║  TEXT LEGEND PARSING (Path B — fixture descriptions from text)        ║
# ╚══════════════════════════════════════════════════════════════════════╝

# Patterns to classify legend text lines into fixture categories.
LEGEND_TEXT_PATTERNS: List[Tuple[str, str, FixtureCategory]] = [
    # Switches
    (r'(\d+)\s*lever.*switch', "{n}-Lever Switch", FixtureCategory.SWITCH),
    (r'day.?night\s*switch', "Day/Night Switch", FixtureCategory.SWITCH),
    (r'(\d+)A\s*isolator\s*switch', "{a}A Isolator Switch", FixtureCategory.SWITCH),
    # Power sockets
    (r'(\d+)A\s*double\s*switched?\s*socket.*?(\d+)\s*mm', "{a}A Double Socket @{h}mm", FixtureCategory.POWER),
    (r'(\d+)A\s*single\s*switched?\s*socket.*?(\d+)\s*mm', "{a}A Single Socket @{h}mm", FixtureCategory.POWER),
    (r'(\d+)A\s*double\s*switched?\s*socket', "{a}A Double Socket", FixtureCategory.POWER),
    (r'(\d+)A\s*single\s*switched?\s*socket', "{a}A Single Socket", FixtureCategory.POWER),
    (r'data\s*socket.*cat\s*(\d+)', "Data Socket CAT{c}", FixtureCategory.DATA),
    (r'data\s*socket', "Data Socket", FixtureCategory.DATA),
    (r'floor\s*box', "Floor Box", FixtureCategory.POWER),
    # Lighting
    (r'(\d+)\s*[xX]\s*(\d+).*recessed.*(\d+)\s*[xX]\s*(\d+)W\s*LED', "Recessed {w}W LED Fluorescent ({d1}x{d2})", FixtureCategory.LIGHTING),
    (r'recessed.*(\d+)\s*[xX]\s*(\d+)W\s*LED', "Recessed {m}x{w}W LED Fluorescent", FixtureCategory.LIGHTING),
    (r'(\d+)W\s*LED\s*flood', "{w}W LED Floodlight", FixtureCategory.LIGHTING),
    (r'(\d+)W\s*LED\s*ceiling', "{w}W LED Ceiling Light", FixtureCategory.LIGHTING),
    (r'(\d+)W\s*LED\s*downlight', "{w}W LED Downlight", FixtureCategory.LIGHTING),
    (r'(\d+)W\s*LED\s*batten', "{w}W LED Batten", FixtureCategory.LIGHTING),
    (r'(\d+)W\s*LED\s*panel', "{w}W LED Panel", FixtureCategory.LIGHTING),
    (r'LED\s*flood', "LED Floodlight", FixtureCategory.LIGHTING),
    (r'LED\s*ceiling', "LED Ceiling Light", FixtureCategory.LIGHTING),
    (r'LED\s*downlight', "LED Downlight", FixtureCategory.LIGHTING),
    (r'fluorescent', "Fluorescent Light", FixtureCategory.LIGHTING),
    # Equipment
    (r'distribution\s*board', "Distribution Board", FixtureCategory.OTHER),
    (r'air\s*condition', "Air Conditioning Unit", FixtureCategory.HVAC),
    (r'A/?C', "Air Conditioning Unit", FixtureCategory.HVAC),
    # Cable management
    (r'power\s*skirting', "Power Skirting", FixtureCategory.OTHER),
    (r'cable\s*tray', "Cable Tray", FixtureCategory.OTHER),
    (r'gable\s*tray', "Cable Tray", FixtureCategory.OTHER),
    (r'trunking|truncking', "Trunking", FixtureCategory.OTHER),
    (r'wire\s*mesh.*basket|busket', "Wire Mesh Basket", FixtureCategory.OTHER),
]

# Layers that contain electrical text (legend, circuit labels, etc.)
ELECTRICAL_TEXT_LAYERS = [
    'PDF_TEXT', 'B_ELECTRICAL', 'E_TEXT', 'ELEC_TEXT',
    'MEP', 'ELECTRICAL',
]

# Layer patterns for electrical layers
ELECTRICAL_LAYER_PATTERNS = [
    r'ELEC', r'MEP', r'B_ELEC', r'PDF_MEP', r'E[-_]',
]

LAYER_CATEGORY_MAP = {
    FixtureCategory.LIGHTING: [
        r'E[-_]?LIGHT', r'ELEC[-_]?LIGHT', r'LIGHTING',
        r'E[-_]?LUM', r'LUMINAIRE',
    ],
    FixtureCategory.POWER: [
        r'E[-_]?POWER', r'E[-_]?PLUG', r'E[-_]?SOCKET',
        r'ELEC[-_]?POWER', r'GPO',
    ],
    FixtureCategory.SWITCH: [
        r'E[-_]?SWITCH', r'E[-_]?SW', r'SWITCHING',
    ],
    FixtureCategory.DATA: [
        r'E[-_]?DATA', r'E[-_]?TELE', r'TELECOMS', r'COMMS',
    ],
    FixtureCategory.SAFETY: [
        r'E[-_]?FIRE', r'E[-_]?ALARM', r'E[-_]?SAFETY', r'FIRE',
    ],
}

ARCH_LAYER_KEYWORDS = [
    'A-WALL', 'ARCH', 'A_WALL', 'WALL',
    'A-ROOM', 'ROOM', 'A-BLDG',
]

ANNO_LAYER_KEYWORDS = ['ROOM', 'TEXT', 'ANNO', 'A-']

# Legend section headers — text items containing these are headers, not fixtures
LEGEND_HEADERS = {'SWITCHES', 'POWER SOCKETS', 'LIGHTS', 'OTHERS', 'QTYS',
                  'LEGEND', 'SCHEDULE', 'KEY', 'DESCRIPTION', 'SYMBOL',
                  'QUANTITY', 'QTY', 'TYPE', 'NOTES', 'NOTE'}


# ╔══════════════════════════════════════════════════════════════════════╗
# ║  DATA CLASSES                                                        ║
# ╚══════════════════════════════════════════════════════════════════════╝

@dataclass
class RoomPolygon:
    """A room boundary detected from the DXF."""
    name: str
    polygon: Any  # Shapely Polygon
    area_m2: float = 0.0
    layer: str = ""


@dataclass
class DXFExtractionResult:
    """Raw DXF extraction data before conversion to PageResult."""
    block_counts: Dict[str, int] = field(default_factory=dict)
    block_counts_by_layer: Dict[str, Dict[str, int]] = field(
        default_factory=dict)
    insert_positions: Dict[str, List[Tuple[float, float]]] = field(
        default_factory=dict)
    rooms: List[RoomPolygon] = field(default_factory=list)
    room_fixtures: Dict[str, Dict[str, int]] = field(default_factory=dict)
    total_inserts: int = 0
    layers_found: List[str] = field(default_factory=list)
    unknown_blocks: List[str] = field(default_factory=list)
    drawing_unit_scale: float = 1.0
    # Text-based data (Path B)
    legend_items: List[Dict[str, Any]] = field(default_factory=list)
    circuit_labels: List[str] = field(default_factory=list)
    room_names: List[str] = field(default_factory=list)
    is_archicad_export: bool = False


# ╔══════════════════════════════════════════════════════════════════════╗
# ║  DXF EXTRACTOR                                                      ║
# ╚══════════════════════════════════════════════════════════════════════╝

class DXFExtractor:
    """
    Extract fixture data from AutoCAD and ArchiCAD DXF files.

    Supports two extraction paths:
    - Path A: Named block INSERTs (native AutoCAD)
    - Path B: Text legend + geometry (ArchiCAD / PDF-to-DXF exports)

    Cost: R0.00 | Time: <100ms
    """

    def __init__(self, custom_block_map: Optional[Dict] = None):
        self.block_map = dict(DEFAULT_BLOCK_MAP)
        if custom_block_map:
            self.block_map.update(custom_block_map)

    def extract(self, dxf_path: str) -> DocumentResult:
        """Extract from a DXF file on disk."""
        if not HAS_EZDXF:
            raise ImportError("ezdxf is required: pip install ezdxf")

        start_time = time.time()

        try:
            doc = ezdxf.readfile(dxf_path)
        except ezdxf.DXFStructureError as e:
            logger.error(f"Corrupt or malformed DXF file: {e}")
            return self._empty_result(Path(dxf_path).name, start_time)
        except ezdxf.DXFVersionError as e:
            logger.error(f"Unsupported DXF version: {e}")
            return self._empty_result(Path(dxf_path).name, start_time)
        except (IOError, OSError) as e:
            logger.error(f"Cannot read DXF file: {e}")
            return self._empty_result(Path(dxf_path).name, start_time)
        except Exception as e:
            logger.error(f"Failed to open DXF: {e}")
            return self._empty_result(Path(dxf_path).name, start_time)

        return self._process_document(doc, Path(dxf_path).name, start_time)

    def extract_from_bytes(self, file_bytes: bytes, filename: str = "upload.dxf") -> DocumentResult:
        """Extract from DXF bytes (in-memory upload)."""
        if not HAS_EZDXF:
            raise ImportError("ezdxf is required: pip install ezdxf")

        start_time = time.time()

        try:
            stream = io.StringIO(file_bytes.decode('utf-8', errors='replace'))
            doc = ezdxf.read(stream)
        except UnicodeDecodeError:
            try:
                stream = io.StringIO(file_bytes.decode('latin-1'))
                doc = ezdxf.read(stream)
            except Exception as e:
                logger.error(f"Cannot decode DXF bytes: {e}")
                return self._empty_result(filename, start_time)
        except ezdxf.DXFStructureError as e:
            logger.error(f"Corrupt or malformed DXF data: {e}")
            return self._empty_result(filename, start_time)
        except Exception as e:
            logger.error(f"Failed to read DXF from bytes: {e}")
            return self._empty_result(filename, start_time)

        return self._process_document(doc, filename, start_time)

    def _empty_result(self, filename: str, start_time: float) -> DocumentResult:
        return DocumentResult(
            filename=filename,
            total_pages=0,
            processing_time_ms=int((time.time() - start_time) * 1000),
        )

    def _process_document(self, doc, filename: str, start_time: float) -> DocumentResult:
        """Process an opened ezdxf document."""
        try:
            msp = doc.modelspace()
        except Exception as e:
            logger.error(f"Cannot access modelspace: {e}")
            return self._empty_result(filename, start_time)

        # Single pass: collect all entities
        raw, room_polys, labels = self._single_pass_collect(msp)

        # Detect drawing units
        raw.drawing_unit_scale = self._detect_unit_scale(doc, raw)

        # Build rooms
        if HAS_SHAPELY and room_polys:
            raw.rooms = self._build_rooms(room_polys, labels, raw.drawing_unit_scale)
            raw.room_fixtures = self._assign_fixtures_to_rooms(
                raw.insert_positions, raw.rooms)

        # Extract metadata
        title_block = self._extract_metadata(doc, labels)

        # Detect if this is an ArchiCAD/PDF export
        raw.is_archicad_export = self._detect_archicad_export(raw)

        # Extract fixtures using appropriate path
        fixtures = []

        # Path A: Named block matching (always run)
        block_fixtures = self._extract_from_blocks(raw)
        fixtures.extend(block_fixtures)

        # Path B: Text legend parsing (for ArchiCAD exports or when blocks yield little)
        if raw.legend_items:
            legend_fixtures = self._extract_from_legend(raw)
            # Merge — avoid duplicating fixtures already found via blocks
            existing_types = {f.fixture_type.upper() for f in fixtures}
            for lf in legend_fixtures:
                if lf.fixture_type.upper() not in existing_types:
                    fixtures.append(lf)
                    existing_types.add(lf.fixture_type.upper())

        # Path B bonus: Count circuit labels for additional context
        circuit_info = self._extract_circuit_info(raw)

        # Calculate confidence
        if fixtures:
            confidence = sum(f.confidence for f in fixtures) / len(fixtures)
        else:
            confidence = 0.0

        # Build warnings
        warnings = self._build_warnings(raw, block_fixtures, fixtures)

        page_result = PageResult(
            page_number=1,
            drawing_type=DrawingType.COMBINED,
            title_block=title_block,
            fixtures=fixtures,
            strategy_used=ExtractionStrategy.DXF_DIRECT,
            strategies_attempted=["dxf_block_match", "dxf_legend_parse"] if raw.legend_items else ["dxf_block_match"],
            confidence=confidence,
            confidence_level=_confidence_level(confidence),
            processing_time_ms=int((time.time() - start_time) * 1000),
            warnings=warnings,
        )

        return DocumentResult(
            filename=filename,
            pages=[page_result],
            total_pages=1,
            processing_time_ms=int((time.time() - start_time) * 1000),
            strategies_summary={"dxf_direct": 1},
        )

    # ────────────────────────────────────────────────────────────────────
    # COLLECTION (single pass)
    # ────────────────────────────────────────────────────────────────────

    def _single_pass_collect(self, msp) -> Tuple[
        DXFExtractionResult, list, list
    ]:
        """Single pass over modelspace to collect all relevant entities."""
        raw = DXFExtractionResult()
        raw.insert_positions = defaultdict(list)
        layers_seen = set()
        room_polys = []
        labels = []

        for entity in msp:
            dxf_type = entity.dxftype()
            layer = entity.dxf.layer
            layer_upper = layer.upper()
            layers_seen.add(layer)

            # ── INSERT entities ──
            if dxf_type == "INSERT":
                block_name = entity.dxf.name
                if block_name.startswith("*") or block_name.startswith("_"):
                    continue

                raw.total_inserts += 1
                raw.block_counts[block_name] = (
                    raw.block_counts.get(block_name, 0) + 1)

                if layer not in raw.block_counts_by_layer:
                    raw.block_counts_by_layer[layer] = {}
                raw.block_counts_by_layer[layer][block_name] = (
                    raw.block_counts_by_layer[layer].get(block_name, 0) + 1)

                try:
                    pos = entity.dxf.insert
                    raw.insert_positions[block_name].append((pos.x, pos.y))
                except Exception:
                    pass

            # ── Closed polylines (room boundaries) ──
            elif dxf_type == "LWPOLYLINE" and HAS_SHAPELY:
                if any(kw in layer_upper for kw in ARCH_LAYER_KEYWORDS):
                    if entity.closed:
                        try:
                            coords = [(p[0], p[1]) for p in entity.get_points()]
                            if len(coords) >= 3:
                                poly = Polygon(coords)
                                if poly.is_valid and poly.area > 1.0:
                                    room_polys.append(poly)
                        except Exception:
                            pass

            # ── Text entities ──
            elif dxf_type in ("TEXT", "MTEXT"):
                text = ""
                try:
                    if dxf_type == "TEXT":
                        text = entity.dxf.text
                    else:
                        text = entity.text
                except Exception:
                    continue

                if not text or not text.strip():
                    continue

                text_clean = self._clean_mtext(text.strip())
                if not text_clean:
                    continue

                try:
                    pos = entity.dxf.insert
                    label_info = {
                        "text": text_clean,
                        "text_raw": text.strip(),
                        "x": pos.x,
                        "y": pos.y,
                        "layer": layer,
                        "layer_upper": layer_upper,
                    }
                    labels.append(label_info)

                    # Classify text by layer
                    is_elec_layer = any(
                        kw in layer_upper
                        for kw in ELECTRICAL_TEXT_LAYERS
                    ) or any(
                        re.search(pat, layer_upper)
                        for pat in ELECTRICAL_LAYER_PATTERNS
                    )

                    if is_elec_layer:
                        text_upper = text_clean.upper().strip()

                        # Skip headers
                        if text_upper in LEGEND_HEADERS:
                            continue

                        # Circuit labels (DB-S3, L1, L2, etc.)
                        if re.match(r'^(DB[-_]?\w+|L\d+|C\d+|P\d+)$', text_upper):
                            raw.circuit_labels.append(text_clean)
                        # Legend fixture descriptions (longer text with fixture keywords)
                        elif len(text_clean) > 5:
                            raw.legend_items.append(label_info)

                    # Room names
                    if any(kw in layer_upper for kw in ['ROOM', 'TEXT BLOCK']):
                        if len(text_clean) > 1 and len(text_clean) < 30:
                            if not any(c.isdigit() for c in text_clean[:3]):
                                raw.room_names.append(text_clean)

                except Exception:
                    pass

        raw.layers_found = sorted(layers_seen)
        return raw, room_polys, labels

    def _clean_mtext(self, text: str) -> str:
        """Strip MTEXT formatting codes to get plain text."""
        if not text:
            return ""
        # Remove MTEXT formatting: {\fArial|b0|i0|c0|p34;...}
        cleaned = re.sub(r'\\[fFpPHLlAa][^;]*;', '', text)
        cleaned = re.sub(r'\\[Ss][^;]*;', '', cleaned)
        # Remove braces
        cleaned = cleaned.replace('{', '').replace('}', '')
        # Remove paragraph marks
        cleaned = cleaned.replace('\\P', '\n')
        # Remove remaining backslash codes
        cleaned = re.sub(r'\\[a-zA-Z]', '', cleaned)
        # Clean up whitespace
        cleaned = ' '.join(cleaned.split())
        return cleaned.strip()

    # ────────────────────────────────────────────────────────────────────
    # DETECTION
    # ────────────────────────────────────────────────────────────────────

    def _detect_archicad_export(self, raw: DXFExtractionResult) -> bool:
        """Detect if this DXF is from ArchiCAD or a PDF-to-DXF converter."""
        indicators = 0
        layers_str = ' '.join(raw.layers_found).upper()

        # ArchiCAD indicators
        if 'PDF_TEXT' in layers_str or 'PDF_MEP' in layers_str:
            indicators += 2
        if 'B_ELECTRICAL' in layers_str:
            indicators += 1
        if 'CADDIE' in layers_str:
            indicators += 1
        if any('_PEN_NO_' in l.upper() for l in raw.layers_found):
            indicators += 1

        # Check for structural blocks (Wall_1, Column_1, Morph_1)
        structural_blocks = sum(
            1 for name in raw.block_counts
            if re.match(r'^(Wall|Column|Slab|Roof|Morph|Stair|Railing)_\d+$', name)
        )
        if structural_blocks > 10:
            indicators += 2

        return indicators >= 2

    def _detect_unit_scale(self, doc, raw: DXFExtractionResult) -> float:
        """Detect drawing units and return multiplier to meters."""
        try:
            header = doc.header
            insunits = header.get("$INSUNITS", 0)
            unit_map = {
                1: 0.0254,   # inches
                2: 0.3048,   # feet
                4: 0.001,    # mm
                5: 0.01,     # cm
                6: 1.0,      # meters
            }
            if insunits in unit_map:
                return unit_map[insunits]
        except Exception:
            pass

        max_coord = 0.0
        for positions in raw.insert_positions.values():
            for x, y in positions:
                max_coord = max(max_coord, abs(x), abs(y))

        if max_coord > 1_000:
            return 0.001
        elif max_coord > 100:
            return 0.01
        else:
            return 1.0

    # ────────────────────────────────────────────────────────────────────
    # PATH A: BLOCK INSERT MATCHING
    # ────────────────────────────────────────────────────────────────────

    def _extract_from_blocks(self, raw: DXFExtractionResult) -> List[FixtureItem]:
        """Extract fixtures from block INSERT names."""
        fixtures = []

        for block_name, count in raw.block_counts.items():
            fixture_type, category, match_confidence = self._resolve_block_name(
                block_name, raw.block_counts_by_layer)

            if fixture_type:
                fixtures.append(FixtureItem(
                    fixture_type=fixture_type,
                    category=category,
                    quantity=count,
                    description=f"DXF block: {block_name}",
                    confidence=match_confidence,
                    confidence_level=_confidence_level(match_confidence),
                    source=ExtractionStrategy.DXF_DIRECT,
                ))
            elif not self._is_structural_block(block_name):
                raw.unknown_blocks.append(block_name)

        return fixtures

    def _is_structural_block(self, block_name: str) -> bool:
        """Check if a block is structural/architectural (not electrical)."""
        # Common non-electrical blocks in ArchiCAD exports
        if re.match(r'^(Wall|Column|Slab|Roof|Morph|Stair|Railing)_\d+$', block_name):
            return True
        name_lower = block_name.lower()
        skip_keywords = [
            'wall', 'column', 'slab', 'roof', 'morph', 'stair',
            'railing', 'door', 'window', 'furniture', 'swing reel',
        ]
        return any(kw in name_lower for kw in skip_keywords)

    def _resolve_block_name(
        self, block_name: str,
        counts_by_layer: Dict[str, Dict[str, int]]
    ) -> Tuple[Optional[str], FixtureCategory, float]:
        """
        Resolve a DXF block name to a fixture type.

        Strategies (in order):
        1. Exact match in abbreviation map (1.0)
        2. Normalized exact match (0.95)
        3. Full-name pattern match for ArchiCAD names (0.90)
        4. Regex abbreviation pattern match (0.85)
        5. Substring match (0.70)
        6. Layer-based inference (0.50)
        """
        name_upper = block_name.upper().strip()
        name_normalized = re.sub(r'[-_ /]+', '_', name_upper).strip('_')
        # Strip trailing numbers (e.g., "switch 1" → "switch", "Socket Outlet 2 Gangs 23" keep "2 gangs")
        name_lower = block_name.lower().strip()

        # Skip known non-electrical blocks
        for pattern, fixture_type, category in FULL_NAME_PATTERNS:
            if fixture_type is None and re.search(pattern, name_lower):
                return None, FixtureCategory.OTHER, 0.0

        # Strategy 1: Exact match
        for key, (fixture_type, category) in self.block_map.items():
            if name_upper == key.upper():
                return fixture_type, category, 1.0

        # Strategy 2: Normalized match
        for key, (fixture_type, category) in self.block_map.items():
            key_normalized = re.sub(r'[-_ /]+', '_', key.upper()).strip('_')
            if name_normalized == key_normalized:
                return fixture_type, category, 0.95

        # Strategy 3: Full-name pattern match (ArchiCAD-style)
        for pattern, fixture_type, category in FULL_NAME_PATTERNS:
            if fixture_type is not None and re.search(pattern, name_lower):
                return fixture_type, category, 0.90

        # Strategy 4: Regex abbreviation patterns
        for pattern, fixture_type, category in BLOCK_NAME_PATTERNS:
            if re.search(pattern, name_upper, re.IGNORECASE):
                return fixture_type, category, 0.85

        # Strategy 5: Substring match (key >= 3 chars)
        for key, (fixture_type, category) in self.block_map.items():
            key_upper = key.upper()
            if len(key_upper) >= 3:
                if key_upper in name_upper or name_upper in key_upper:
                    return fixture_type, category, 0.70

        # Strategy 6: Layer-based inference
        for layer, blocks in counts_by_layer.items():
            if block_name in blocks:
                layer_upper = layer.upper()
                for category, patterns in LAYER_CATEGORY_MAP.items():
                    for pat in patterns:
                        if re.search(pat, layer_upper):
                            return (
                                f"{category.value.title()} fixture ({block_name})",
                                category, 0.50,
                            )

        return None, FixtureCategory.OTHER, 0.0

    # ────────────────────────────────────────────────────────────────────
    # PATH B: TEXT LEGEND PARSING
    # ────────────────────────────────────────────────────────────────────

    def _extract_from_legend(self, raw: DXFExtractionResult) -> List[FixtureItem]:
        """
        Parse text legend to extract fixture types.

        ArchiCAD exports store the fixture schedule as TEXT/MTEXT entities
        on layers like PDF_Text. We match each text line against known
        fixture description patterns.
        """
        fixtures = []
        seen_types = set()

        for item in raw.legend_items:
            text = item["text"]
            text_upper = text.upper().strip()

            # Skip headers and very short text
            if text_upper in LEGEND_HEADERS or len(text) < 5:
                continue

            # Try to match against legend patterns
            fixture_type, category = self._classify_legend_text(text)
            if fixture_type and fixture_type.upper() not in seen_types:
                seen_types.add(fixture_type.upper())
                fixtures.append(FixtureItem(
                    fixture_type=fixture_type,
                    category=category,
                    quantity=1,  # Quantity from legend (text-only, no count)
                    description=text,
                    confidence=0.75,
                    confidence_level=Confidence.MEDIUM,
                    source=ExtractionStrategy.DXF_DIRECT,
                ))

        return fixtures

    def _classify_legend_text(self, text: str) -> Tuple[Optional[str], FixtureCategory]:
        """Classify a legend text line into a fixture type."""
        text_clean = text.strip()

        for pattern, name_template, category in LEGEND_TEXT_PATTERNS:
            match = re.search(pattern, text_clean, re.IGNORECASE)
            if match:
                # Build fixture name from template and match groups
                fixture_type = text_clean  # Use the full description
                return fixture_type, category

        return None, FixtureCategory.OTHER

    # ────────────────────────────────────────────────────────────────────
    # CIRCUIT LABEL ANALYSIS
    # ────────────────────────────────────────────────────────────────────

    def _extract_circuit_info(self, raw: DXFExtractionResult) -> Dict[str, Any]:
        """Analyze circuit labels for distribution board info."""
        if not raw.circuit_labels:
            return {}

        label_counts = Counter(raw.circuit_labels)
        db_boards = set()
        circuit_types = defaultdict(int)

        for label in raw.circuit_labels:
            label_upper = label.upper()
            # DB board references (DB-S3, DB-CA, etc.)
            if label_upper.startswith('DB'):
                db_boards.add(label)
            # Lighting circuits (L1, L2, L3)
            elif re.match(r'^L\d+$', label_upper):
                circuit_types["lighting"] += 1
            # Power circuits (P1, P2)
            elif re.match(r'^P\d+$', label_upper):
                circuit_types["power"] += 1
            # General circuits (C1, C2)
            elif re.match(r'^C\d+$', label_upper):
                circuit_types["general"] += 1

        return {
            "db_boards": sorted(db_boards),
            "circuit_types": dict(circuit_types),
            "total_circuit_labels": len(raw.circuit_labels),
            "label_counts": dict(label_counts),
        }

    # ────────────────────────────────────────────────────────────────────
    # ROOM & METADATA
    # ────────────────────────────────────────────────────────────────────

    def _build_rooms(
        self, room_polys: list, labels: list, unit_scale: float
    ) -> List[RoomPolygon]:
        rooms = []
        for poly in room_polys:
            room_name = "Unknown Room"
            for label in labels:
                if any(kw in label["layer_upper"] for kw in ANNO_LAYER_KEYWORDS):
                    try:
                        pt = Point(label["x"], label["y"])
                        if poly.contains(pt):
                            room_name = label["text"]
                            break
                    except Exception:
                        pass
            area_m2 = poly.area * (unit_scale ** 2)
            rooms.append(RoomPolygon(
                name=room_name, polygon=poly, area_m2=round(area_m2, 2),
            ))
        return rooms

    def _assign_fixtures_to_rooms(
        self,
        insert_positions: Dict[str, List[Tuple[float, float]]],
        rooms: List[RoomPolygon],
    ) -> Dict[str, Dict[str, int]]:
        room_fixtures: Dict[str, Dict[str, int]] = defaultdict(
            lambda: defaultdict(int))
        for block_name, positions in insert_positions.items():
            for x, y in positions:
                try:
                    pt = Point(x, y)
                    assigned = "Outside/Unassigned"
                    for room in rooms:
                        if room.polygon.contains(pt):
                            assigned = room.name
                            break
                    room_fixtures[assigned][block_name] += 1
                except Exception:
                    room_fixtures["Outside/Unassigned"][block_name] += 1
        return dict(room_fixtures)

    def _extract_metadata(self, doc, labels: list) -> TitleBlockInfo:
        info = TitleBlockInfo()

        try:
            header = doc.header
            for var_name in ("$PROJECTNAME",):
                if var_name in header:
                    val = str(header[var_name])
                    if val:
                        info.project_name = val
        except Exception:
            pass

        for label in labels:
            text = label["text"]
            text_upper = text.upper().strip()

            if re.match(r'^[A-Z]{2,4}[-_]\d{3,}', text_upper):
                if not info.drawing_number:
                    info.drawing_number = text.strip()
            if "BUILDING" in text_upper and not info.building_name:
                info.building_name = text.strip()[:100]
            if ("CONSULTANT" in text_upper or "ENGINEER" in text_upper) and not info.engineer:
                info.engineer = text.strip()[:80]
            if "CLIENT" in text_upper and not info.client:
                info.client = text.strip()[:80]
            if re.match(r'^REV\s*[A-Z0-9]', text_upper) and not info.revision:
                info.revision = text.strip()[:20]
            if re.match(r'^\d{4}[-/]\d{2}[-/]\d{2}', text.strip()) and not info.date:
                info.date = text.strip()[:10]
            if "SCALE" in text_upper and not info.scale:
                info.scale = text.strip()[:30]
            # Detect floor/slab description for drawing description
            if ("FLOOR" in text_upper and ("SLAB" in text_upper or "PLAN" in text_upper)
                    and not info.description):
                info.description = text.strip()[:100]

        return info

    # ────────────────────────────────────────────────────────────────────
    # WARNINGS
    # ────────────────────────────────────────────────────────────────────

    def _build_warnings(
        self,
        raw: DXFExtractionResult,
        block_fixtures: List[FixtureItem],
        all_fixtures: List[FixtureItem],
    ) -> List[str]:
        warnings = []

        if raw.is_archicad_export:
            warnings.append(
                "ArchiCAD/PDF export detected. "
                "Fixtures extracted from text legend and named blocks. "
                "Quantities may need manual verification."
            )

        if not all_fixtures:
            warnings.append(
                "No electrical fixtures found. "
                "The DXF may not contain electrical drawings, "
                "or fixtures use unrecognized naming conventions."
            )

        if raw.unknown_blocks:
            # Filter out structural blocks for the warning
            real_unknown = [
                b for b in raw.unknown_blocks
                if not self._is_structural_block(b)
            ]
            if real_unknown:
                examples = real_unknown[:5]
                warnings.append(
                    f"{len(real_unknown)} unrecognized block(s): "
                    f"{', '.join(examples)}"
                    + (" ..." if len(real_unknown) > 5 else "")
                )

        if not HAS_SHAPELY:
            warnings.append("shapely not installed — room assignment skipped.")

        if raw.circuit_labels:
            db_boards = set()
            for label in raw.circuit_labels:
                if label.upper().startswith('DB'):
                    db_boards.add(label)
            if db_boards:
                warnings.append(
                    f"Circuit labels found referencing DB boards: "
                    f"{', '.join(sorted(db_boards))}"
                )

        if raw.room_names:
            unique_rooms = sorted(set(raw.room_names))
            warnings.append(
                f"Rooms detected: {', '.join(unique_rooms[:10])}"
                + (" ..." if len(unique_rooms) > 10 else "")
            )

        return warnings

    # ────────────────────────────────────────────────────────────────────
    # UTILITY
    # ────────────────────────────────────────────────────────────────────

    def get_unknown_blocks(self, dxf_path: str) -> List[Tuple[str, int, str]]:
        """Get unrecognized block names for user mapping."""
        if not HAS_EZDXF:
            return []
        try:
            doc = ezdxf.readfile(dxf_path)
        except Exception as e:
            logger.error(f"Cannot read DXF: {e}")
            return []

        msp = doc.modelspace()
        raw, _, _ = self._single_pass_collect(msp)
        self._extract_from_blocks(raw)

        unknown = []
        for block_name in raw.unknown_blocks:
            if self._is_structural_block(block_name):
                continue
            count = raw.block_counts.get(block_name, 0)
            layer = ""
            for l, blocks in raw.block_counts_by_layer.items():
                if block_name in blocks:
                    layer = l
                    break
            unknown.append((block_name, count, layer))

        return sorted(unknown, key=lambda x: -x[1])


# ╔══════════════════════════════════════════════════════════════════════╗
# ║  CONVENIENCE FUNCTIONS                                               ║
# ╚══════════════════════════════════════════════════════════════════════╝

def extract_from_dxf(
    dxf_path: str,
    custom_block_map: Optional[Dict] = None,
) -> DocumentResult:
    """Extract fixtures from a DXF file on disk."""
    extractor = DXFExtractor(custom_block_map=custom_block_map)
    return extractor.extract(dxf_path)


def extract_from_dxf_bytes(
    file_bytes: bytes,
    filename: str = "upload.dxf",
    custom_block_map: Optional[Dict] = None,
) -> DocumentResult:
    """Extract fixtures from DXF bytes (in-memory upload)."""
    extractor = DXFExtractor(custom_block_map=custom_block_map)
    return extractor.extract_from_bytes(file_bytes, filename)


def is_dxf_file(file_path: str) -> bool:
    """Check if a file is a DXF by extension."""
    return Path(file_path).suffix.lower() == ".dxf"
