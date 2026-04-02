"""
AfriPlan Electrical — DXF Extraction Module v1.1

Accurate, R0.00 cost, <100ms extraction from AutoCAD DXF files.

Every fixture placed by the drafter in AutoCAD is stored as a named
block INSERT entity with exact coordinates. This module:
1. Reads the DXF file with ezdxf (from path or bytes)
2. Counts every block INSERT by layer (E-LIGHTING, E-POWER, etc.)
3. Maps block names to fixture types using multi-strategy fuzzy matching
4. Assigns fixtures to rooms using point-in-polygon geometry (if shapely available)
5. Auto-detects drawing units (mm vs m) for correct area calculation
6. Returns the same data models as the PDF extractor

Author: JLWanalytics
Version: 1.1.0
"""

from __future__ import annotations

import io
import re
import time
import logging
from pathlib import Path
from collections import defaultdict
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
# ║  DXF BLOCK NAME → FIXTURE TYPE MAPPING                              ║
# ╚══════════════════════════════════════════════════════════════════════╝

# SA electrical drafters use different block naming conventions.
# This mapping covers common abbreviations plus SA-specific patterns.
# Matching is done via exact → prefix → substring → regex → layer fallback.

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
    "LUM": ("Luminaire", FixtureCategory.LIGHTING),

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

# Regex patterns for firm-specific block names (e.g., "CHONA_DL_01", "KC-FLR-01")
# These catch blocks with known fixture keywords embedded in longer names.
BLOCK_NAME_PATTERNS: List[Tuple[str, str, FixtureCategory]] = [
    (r'(?:^|[_\-])DL(?:[_\-]|\d|$)', "LED Downlight", FixtureCategory.LIGHTING),
    (r'(?:^|[_\-])D/?L(?:[_\-]|\d|$)', "LED Downlight", FixtureCategory.LIGHTING),
    (r'(?:^|[_\-])FL(?:OOR)?(?:[_\-]|\d|$)', "Fluorescent Light", FixtureCategory.LIGHTING),
    (r'(?:^|[_\-])FLD(?:[_\-]|\d|$)', "Floodlight", FixtureCategory.LIGHTING),
    (r'(?:^|[_\-])BH(?:[_\-]|\d|$)', "Bulkhead Light", FixtureCategory.LIGHTING),
    (r'(?:^|[_\-])VP(?:[_\-]|\d|$)', "Vapour Proof Light", FixtureCategory.LIGHTING),
    (r'(?:^|[_\-])DS(?:O)?(?:[_\-]|\d|$)', "Double Socket", FixtureCategory.POWER),
    (r'(?:^|[_\-])SS(?:O)?(?:[_\-]|\d|$)', "Single Socket", FixtureCategory.POWER),
    (r'(?:^|[_\-])GPO(?:[_\-]|\d|$)', "General Power Outlet", FixtureCategory.POWER),
    (r'(?:^|[_\-])SW(\d)?(?:[_\-]|$)', "Switch", FixtureCategory.SWITCH),
    (r'(?:^|[_\-])ISO(?:[_\-]|\d|$)', "Isolator Switch", FixtureCategory.SWITCH),
    (r'LIGHT', "Light Fitting", FixtureCategory.LIGHTING),
    (r'SOCKET', "Socket Outlet", FixtureCategory.POWER),
    (r'SWITCH', "Switch", FixtureCategory.SWITCH),
    (r'SMOKE', "Smoke Detector", FixtureCategory.SAFETY),
    (r'EMERG', "Emergency Light", FixtureCategory.SAFETY),
    (r'(?:^|[_\-])EM(?:[_\-]|\d|$)', "Emergency Light", FixtureCategory.SAFETY),
]

# Layer name patterns for categorizing fixtures
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

# Architecture layer keywords for room boundary detection
ARCH_LAYER_KEYWORDS = [
    'A-WALL', 'ARCH', 'A_WALL', 'WALL',
    'A-ROOM', 'ROOM', 'A-BLDG',
]

# Annotation layer keywords for room labels
ANNO_LAYER_KEYWORDS = ['ROOM', 'TEXT', 'ANNO', 'A-']


# ╔══════════════════════════════════════════════════════════════════════╗
# ║  DXF EXTRACTOR                                                      ║
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
    drawing_unit_scale: float = 1.0  # multiplier to convert to meters


class DXFExtractor:
    """
    Extract fixture data directly from AutoCAD DXF files.

    Every fixture placed by the drafter is a block INSERT entity.
    We count them by name and layer, then map to fixture types.
    Room assignment uses Shapely point-in-polygon geometry.

    Cost: R0.00 | Time: <100ms | Accuracy: high (depends on block naming)
    """

    def __init__(self, custom_block_map: Optional[Dict] = None):
        """
        Initialize with optional custom block name mappings.

        Args:
            custom_block_map: Override or extend default block mappings.
                Format: {"BLOCK_NAME": ("Fixture Type", FixtureCategory.XXX)}
        """
        self.block_map = dict(DEFAULT_BLOCK_MAP)
        if custom_block_map:
            self.block_map.update(custom_block_map)

    def extract(self, dxf_path: str) -> DocumentResult:
        """
        Extract all fixture data from a DXF file on disk.

        Args:
            dxf_path: Path to the DXF file

        Returns:
            DocumentResult with extracted data
        """
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
        """
        Extract all fixture data from DXF bytes (in-memory upload).

        Args:
            file_bytes: Raw DXF file content as bytes
            filename: Original filename for the result

        Returns:
            DocumentResult with extracted data
        """
        if not HAS_EZDXF:
            raise ImportError("ezdxf is required: pip install ezdxf")

        start_time = time.time()

        try:
            stream = io.StringIO(file_bytes.decode('utf-8', errors='replace'))
            doc = ezdxf.read(stream)
        except UnicodeDecodeError:
            # Some DXF files use other encodings
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
        """Return an empty result for failed extractions."""
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

        # Single pass: collect all entities by type
        raw, arch_layers, room_polys, labels = self._single_pass_collect(msp)

        # Detect drawing units (mm vs m)
        raw.drawing_unit_scale = self._detect_unit_scale(doc, raw)

        # Build rooms from collected data
        if HAS_SHAPELY and room_polys:
            raw.rooms = self._build_rooms(room_polys, labels, raw.drawing_unit_scale)
            raw.room_fixtures = self._assign_fixtures_to_rooms(
                raw.insert_positions, raw.rooms)

        # Extract title block / metadata
        title_block = self._extract_metadata(doc, labels)

        # Map block names to fixture types
        fixtures = self._map_blocks_to_fixtures(raw)

        # Calculate confidence based on how many blocks were recognized
        recognized = len(fixtures)
        total_unique = len(raw.block_counts)
        confidence = recognized / max(total_unique, 1)
        if total_unique == 0:
            confidence = 0.0

        # Build result
        page_result = PageResult(
            page_number=1,
            drawing_type=DrawingType.COMBINED,
            title_block=title_block,
            fixtures=fixtures,
            strategy_used=ExtractionStrategy.DXF_DIRECT,
            strategies_attempted=["dxf_direct"],
            confidence=confidence,
            confidence_level=_confidence_level(confidence),
            processing_time_ms=int((time.time() - start_time) * 1000),
            warnings=self._build_warnings(raw),
        )

        return DocumentResult(
            filename=filename,
            pages=[page_result],
            total_pages=1,
            processing_time_ms=int((time.time() - start_time) * 1000),
            strategies_summary={"dxf_direct": 1},
        )

    def _single_pass_collect(self, msp) -> Tuple[
        DXFExtractionResult, set, list, list
    ]:
        """
        Single pass over modelspace to collect all relevant entities.

        Returns:
            (raw_result, arch_layers, room_polygons, text_labels)
        """
        raw = DXFExtractionResult()
        raw.insert_positions = defaultdict(list)
        layers_seen = set()
        arch_layers = set()
        room_polys = []
        labels = []

        for entity in msp:
            dxf_type = entity.dxftype()
            layer = entity.dxf.layer
            layer_upper = layer.upper()
            layers_seen.add(layer)

            # ── INSERT entities (fixtures) ──
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

                # Store position for room assignment
                try:
                    pos = entity.dxf.insert
                    raw.insert_positions[block_name].append((pos.x, pos.y))
                except Exception:
                    pass

            # ── Closed polylines (potential room boundaries) ──
            elif dxf_type == "LWPOLYLINE" and HAS_SHAPELY:
                if any(kw in layer_upper for kw in ARCH_LAYER_KEYWORDS):
                    arch_layers.add(layer)
                    if entity.closed:
                        try:
                            coords = [(p[0], p[1]) for p in entity.get_points()]
                            if len(coords) >= 3:
                                poly = Polygon(coords)
                                if poly.is_valid and poly.area > 1.0:
                                    room_polys.append(poly)
                        except Exception:
                            pass

            # ── Text entities (room labels, metadata) ──
            elif dxf_type in ("TEXT", "MTEXT"):
                text = ""
                try:
                    if dxf_type == "TEXT":
                        text = entity.dxf.text
                    else:
                        text = entity.text
                except Exception:
                    continue

                if text and len(text.strip()) > 0:
                    try:
                        pos = entity.dxf.insert
                        labels.append({
                            "text": text.strip(),
                            "x": pos.x,
                            "y": pos.y,
                            "layer": layer,
                            "layer_upper": layer_upper,
                        })
                    except Exception:
                        pass

        raw.layers_found = sorted(layers_seen)
        return raw, arch_layers, room_polys, labels

    def _detect_unit_scale(self, doc, raw: DXFExtractionResult) -> float:
        """
        Detect whether the drawing uses mm, cm, or m and return a
        multiplier to convert raw units to meters.

        Most SA drawings are in millimeters.
        """
        # Check DXF header for $INSUNITS
        try:
            header = doc.header
            insunits = header.get("$INSUNITS", 0)
            # ezdxf INSUNITS: 1=inches, 2=feet, 4=mm, 5=cm, 6=m
            unit_map = {
                1: 0.0254,     # inches to meters
                2: 0.3048,     # feet to meters
                4: 0.001,      # mm to meters
                5: 0.01,       # cm to meters
                6: 1.0,        # meters
            }
            if insunits in unit_map:
                return unit_map[insunits]
        except Exception:
            pass

        # Heuristic: if any insert coordinate > 10,000, likely millimeters
        max_coord = 0.0
        for positions in raw.insert_positions.values():
            for x, y in positions:
                max_coord = max(max_coord, abs(x), abs(y))

        if max_coord > 100_000:
            return 0.001  # millimeters
        elif max_coord > 1_000:
            return 0.001  # millimeters (typical drawing range)
        elif max_coord > 100:
            return 0.01   # centimeters
        else:
            return 1.0    # meters

    def _build_rooms(
        self, room_polys: list, labels: list, unit_scale: float
    ) -> List[RoomPolygon]:
        """Build room objects from collected polygons and labels."""
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

            # Convert area from drawing units² to m²
            area_raw = poly.area
            area_m2 = area_raw * (unit_scale ** 2)

            rooms.append(RoomPolygon(
                name=room_name,
                polygon=poly,
                area_m2=round(area_m2, 2),
            ))

        return rooms

    def _assign_fixtures_to_rooms(
        self,
        insert_positions: Dict[str, List[Tuple[float, float]]],
        rooms: List[RoomPolygon],
    ) -> Dict[str, Dict[str, int]]:
        """Assign each fixture to a room using point-in-polygon."""
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
        """Extract project metadata from DXF header and text entities."""
        info = TitleBlockInfo()

        # Check DXF header variables
        try:
            header = doc.header
            for var_name in ("$PROJECTNAME",):
                if var_name in header:
                    val = str(header[var_name])
                    if val:
                        info.project_name = val
        except Exception:
            pass

        # Search collected text labels for title block keywords
        for label in labels:
            text = label["text"]
            text_upper = text.upper().strip()

            # Drawing number pattern (e.g., "EE-001", "ELEC-0042")
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

        return info

    def _map_blocks_to_fixtures(self, raw: DXFExtractionResult) -> List[FixtureItem]:
        """Map DXF block names to FixtureItem objects using multi-strategy matching."""
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
            else:
                raw.unknown_blocks.append(block_name)
                logger.info(f"Unknown DXF block: {block_name} (x{count})")

        return fixtures

    def _resolve_block_name(
        self, block_name: str,
        counts_by_layer: Dict[str, Dict[str, int]]
    ) -> Tuple[Optional[str], FixtureCategory, float]:
        """
        Resolve a DXF block name to a fixture type.

        Uses 5 strategies in order of confidence:
        1. Exact match in block map (confidence: 1.0)
        2. Normalized exact match (confidence: 0.95)
        3. Regex pattern match for firm-specific names (confidence: 0.85)
        4. Substring match (confidence: 0.70)
        5. Layer-based inference (confidence: 0.50)
        """
        name_upper = block_name.upper().strip()
        name_normalized = re.sub(r'[-_ /]+', '_', name_upper).strip('_')

        # Strategy 1: Exact match (case-insensitive)
        for key, (fixture_type, category) in self.block_map.items():
            if name_upper == key.upper():
                return fixture_type, category, 1.0

        # Strategy 2: Normalized match (strip separators)
        for key, (fixture_type, category) in self.block_map.items():
            key_normalized = re.sub(r'[-_ /]+', '_', key.upper()).strip('_')
            if name_normalized == key_normalized:
                return fixture_type, category, 0.95

        # Strategy 3: Regex pattern match (handles "CHONA_DL_01" style names)
        for pattern, fixture_type, category in BLOCK_NAME_PATTERNS:
            if re.search(pattern, name_upper, re.IGNORECASE):
                return fixture_type, category, 0.85

        # Strategy 4: Substring match (one contains the other)
        for key, (fixture_type, category) in self.block_map.items():
            key_upper = key.upper()
            # Only match if the key is at least 3 chars to avoid false positives
            if len(key_upper) >= 3:
                if key_upper in name_upper or name_upper in key_upper:
                    return fixture_type, category, 0.70

        # Strategy 5: Layer-based inference
        for layer, blocks in counts_by_layer.items():
            if block_name in blocks:
                layer_upper = layer.upper()
                for category, patterns in LAYER_CATEGORY_MAP.items():
                    for pat in patterns:
                        if re.search(pat, layer_upper):
                            return (
                                f"{category.value.title()} fixture ({block_name})",
                                category,
                                0.50,
                            )

        return None, FixtureCategory.OTHER, 0.0

    def _build_warnings(self, raw: DXFExtractionResult) -> List[str]:
        """Build warning messages for the result."""
        warnings = []

        if raw.total_inserts == 0:
            warnings.append("No block INSERT entities found — DXF may be empty or use non-standard geometry.")

        if raw.unknown_blocks:
            count = len(raw.unknown_blocks)
            examples = raw.unknown_blocks[:5]
            warnings.append(
                f"{count} unrecognized block name(s): {', '.join(examples)}"
                + (" ..." if count > 5 else "")
                + ". Consider adding custom_block_map entries."
            )

        if not HAS_SHAPELY:
            warnings.append("shapely not installed — room assignment skipped. Install with: pip install shapely")

        if not raw.rooms and HAS_SHAPELY:
            warnings.append("No room boundaries detected — fixtures not assigned to rooms.")

        return warnings

    def get_unknown_blocks(self, dxf_path: str) -> List[Tuple[str, int, str]]:
        """
        Get list of unrecognized block names for user mapping.

        Returns list of (block_name, count, layer) tuples for blocks
        that couldn't be automatically mapped to fixture types.
        Useful for building custom_block_map.
        """
        if not HAS_EZDXF:
            return []

        try:
            doc = ezdxf.readfile(dxf_path)
        except Exception as e:
            logger.error(f"Cannot read DXF for block analysis: {e}")
            return []

        msp = doc.modelspace()
        raw, _, _, _ = self._single_pass_collect(msp)
        self._map_blocks_to_fixtures(raw)

        unknown = []
        for block_name in raw.unknown_blocks:
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
    """
    Extract fixtures from a DXF file on disk.

    Args:
        dxf_path: Path to the DXF file
        custom_block_map: Optional custom block name -> fixture type mapping

    Returns:
        DocumentResult with extracted data
    """
    extractor = DXFExtractor(custom_block_map=custom_block_map)
    return extractor.extract(dxf_path)


def extract_from_dxf_bytes(
    file_bytes: bytes,
    filename: str = "upload.dxf",
    custom_block_map: Optional[Dict] = None,
) -> DocumentResult:
    """
    Extract fixtures from DXF bytes (in-memory upload).

    Args:
        file_bytes: Raw DXF file content
        filename: Original filename
        custom_block_map: Optional custom block name -> fixture type mapping

    Returns:
        DocumentResult with extracted data
    """
    extractor = DXFExtractor(custom_block_map=custom_block_map)
    return extractor.extract_from_bytes(file_bytes, filename)


def is_dxf_file(file_path: str) -> bool:
    """Check if a file is a DXF by extension."""
    return Path(file_path).suffix.lower() == ".dxf"
