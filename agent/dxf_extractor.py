"""
AfriPlan Electrical — DXF Extraction Module v2.0

R0.00 cost extraction from AutoCAD / ArchiCAD DXF files.

Fully integrated with the Universal Extractor infrastructure:
- Uses TextLayerMiner.FIXTURE_PATTERNS for fixture classification (same as PDF path)
- Uses scan_circuit_labels() for circuit label counting (DB-S3, L1, L2)
- Ports the spatial QTYS matching algorithm from _extract_fixtures_spatial()
- Block INSERT matching for native AutoCAD DXF files

Data flow:
  DXF → ezdxf → single-pass entity collection
                 ├── Block INSERTs → name matching → FixtureItem[]
                 ├── Text labels → spatial QTYS matching → FixtureItem[]
                 └── Circuit labels → scan_circuit_labels() → quantity estimates

Author: JLWanalytics
Version: 2.0.0
"""

from __future__ import annotations

import io
import os
import re
import time
import tempfile
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
    TextLayerMiner, _confidence_level,
)

from agent.extractors.circuit_label_scanner import (
    scan_circuit_labels, CircuitLabelScanResult,
)

logger = logging.getLogger(__name__)


# ╔══════════════════════════════════════════════════════════════════════╗
# ║  BLOCK INSERT MATCHING (Native AutoCAD short-name blocks)            ║
# ╚══════════════════════════════════════════════════════════════════════╝

# Short abbreviation map for native AutoCAD block names.
BLOCK_ABBREV_MAP: Dict[str, Tuple[str, FixtureCategory]] = {
    "DL": ("LED Downlight", FixtureCategory.LIGHTING),
    "D/L": ("LED Downlight", FixtureCategory.LIGHTING),
    "DOWNLIGHT": ("LED Downlight", FixtureCategory.LIGHTING),
    "FL": ("Fluorescent Light", FixtureCategory.LIGHTING),
    "FLUOR": ("Fluorescent Light", FixtureCategory.LIGHTING),
    "FLOOD": ("Floodlight", FixtureCategory.LIGHTING),
    "FLD": ("Floodlight", FixtureCategory.LIGHTING),
    "BH": ("Bulkhead Light", FixtureCategory.LIGHTING),
    "VP": ("Vapour Proof Light", FixtureCategory.LIGHTING),
    "WL": ("Wall Light", FixtureCategory.LIGHTING),
    "CL": ("Ceiling Light", FixtureCategory.LIGHTING),
    "PENDANT": ("Pendant Light", FixtureCategory.LIGHTING),
    "PANEL": ("LED Panel", FixtureCategory.LIGHTING),
    "BATTEN": ("LED Batten", FixtureCategory.LIGHTING),
    "SPOT": ("Spotlight", FixtureCategory.LIGHTING),
    "EM": ("Emergency Light", FixtureCategory.SAFETY),
    "EMERGENCY": ("Emergency Light", FixtureCategory.SAFETY),
    "EXIT": ("Exit Sign", FixtureCategory.SAFETY),
    "DS": ("Double Socket", FixtureCategory.POWER),
    "DSO": ("Double Socket", FixtureCategory.POWER),
    "SS": ("Single Socket", FixtureCategory.POWER),
    "SSO": ("Single Socket", FixtureCategory.POWER),
    "WP": ("Weatherproof Socket", FixtureCategory.POWER),
    "GPO": ("General Power Outlet", FixtureCategory.POWER),
    "FS": ("Floor Socket", FixtureCategory.POWER),
    "SW1": ("1-Lever Switch", FixtureCategory.SWITCH),
    "SW2": ("2-Lever Switch", FixtureCategory.SWITCH),
    "SW3": ("3-Lever Switch", FixtureCategory.SWITCH),
    "SW": ("Switch", FixtureCategory.SWITCH),
    "ISO": ("Isolator Switch", FixtureCategory.SWITCH),
    "DIM": ("Dimmer Switch", FixtureCategory.SWITCH),
    "DN": ("Day/Night Switch", FixtureCategory.SWITCH),
    "D/N": ("Day/Night Switch", FixtureCategory.SWITCH),
    "DATA": ("Data Socket", FixtureCategory.DATA),
    "RJ45": ("Data Socket (RJ45)", FixtureCategory.DATA),
    "TEL": ("Telephone Socket", FixtureCategory.DATA),
    "TV": ("Television Socket", FixtureCategory.DATA),
    "SMOKE": ("Smoke Detector", FixtureCategory.SAFETY),
    "PIR": ("PIR Sensor", FixtureCategory.SAFETY),
    "DB": ("Distribution Board", FixtureCategory.OTHER),
    "AC": ("Air Conditioning Unit", FixtureCategory.HVAC),
    "AIRCON": ("Air Conditioning Unit", FixtureCategory.HVAC),
    "GEYSER": ("Geyser", FixtureCategory.WATER),
    "HWC": ("Hot Water Cylinder", FixtureCategory.WATER),
    "EF": ("Extractor Fan", FixtureCategory.HVAC),
}

# Full-name block patterns for ArchiCAD exports (e.g., "Socket Outlet 2 Gangs 23")
# Uses the same regex approach as TextLayerMiner.FIXTURE_PATTERNS
FULL_NAME_BLOCK_PATTERNS: List[Tuple[str, str, FixtureCategory]] = [
    (r'socket\s*outlet.*2\s*gang', "Double Socket Outlet", FixtureCategory.POWER),
    (r'socket\s*outlet.*1\s*gang', "Single Socket Outlet", FixtureCategory.POWER),
    (r'socket\s*outlet', "Socket Outlet", FixtureCategory.POWER),
    (r'switch\s*\d', "Switch", FixtureCategory.SWITCH),
    (r'switch', "Switch", FixtureCategory.SWITCH),
    (r'extinguisher', "Fire Extinguisher", FixtureCategory.SAFETY),
    (r'distribution\s*board', "Distribution Board", FixtureCategory.OTHER),
    (r'air\s*condition', "Air Conditioning Unit", FixtureCategory.HVAC),
]

# Blocks to always skip (architectural / furniture / plumbing)
SKIP_BLOCK_PATTERNS = [
    r'^(Wall|Column|Slab|Roof|Morph|Stair|Railing)_\d+$',
    r'workstation', r'basin', r'cabinet', r'\bwc\b', r'door', r'window',
    r'furniture', r'swing\s*reel',
]

# Electrical text layer names (where legend / circuit labels live)
ELECTRICAL_TEXT_LAYERS = {'PDF_TEXT', 'B_ELECTRICAL', 'E_TEXT', 'ELEC_TEXT'}
ELECTRICAL_LAYER_PATTERNS = [r'ELEC', r'MEP', r'B_ELEC', r'PDF_MEP', r'E[-_]']

# Legend headers to skip
LEGEND_HEADERS = {'SWITCHES', 'POWER SOCKETS', 'LIGHTS', 'OTHERS', 'QTYS',
                  'LEGEND', 'SCHEDULE', 'KEY', 'DESCRIPTION', 'SYMBOL',
                  'QUANTITY', 'QTY', 'TYPE', 'NOTES', 'NOTE'}

# Category header names (same as TextLayerMiner)
CATEGORY_NAMES = {"SWITCHES", "POWER SOCKETS", "LIGHTS", "OTHERS",
                  "LUMINAIRES", "FITTINGS", "FIXTURES"}
QTYS_NAMES = {"QTYS", "QTY", "QUANTITY"}


# ╔══════════════════════════════════════════════════════════════════════╗
# ║  DATA CLASSES                                                        ║
# ╚══════════════════════════════════════════════════════════════════════╝

@dataclass
class RoomPolygon:
    """A room boundary detected from the DXF."""
    name: str
    polygon: Any
    area_m2: float = 0.0


@dataclass
class DXFCollectedData:
    """All data collected in a single pass over modelspace."""
    # Block INSERTs
    block_counts: Dict[str, int] = field(default_factory=dict)
    block_counts_by_layer: Dict[str, Dict[str, int]] = field(default_factory=dict)
    insert_positions: Dict[str, List[Tuple[float, float]]] = field(default_factory=dict)
    total_inserts: int = 0
    # Text with coordinates (for spatial matching)
    text_spans: List[Dict[str, Any]] = field(default_factory=list)
    # Electrical text only (for circuit labels)
    electrical_text: str = ""
    # Room detection
    room_polys: list = field(default_factory=list)
    room_labels: list = field(default_factory=list)
    # Metadata
    layers_found: List[str] = field(default_factory=list)
    is_archicad_export: bool = False
    drawing_unit_scale: float = 1.0


# ╔══════════════════════════════════════════════════════════════════════╗
# ║  DXF EXTRACTOR                                                      ║
# ╚══════════════════════════════════════════════════════════════════════╝

class DXFExtractor:
    """
    Extract fixture data from AutoCAD and ArchiCAD DXF files.

    Integrated with the Universal Extractor infrastructure:
    - TextLayerMiner.FIXTURE_PATTERNS for text classification
    - scan_circuit_labels() for circuit counting
    - Spatial QTYS matching for legend quantity extraction

    Cost: R0.00 | Time: <2s
    """

    def __init__(self, custom_block_map: Optional[Dict] = None):
        self.block_map = dict(BLOCK_ABBREV_MAP)
        if custom_block_map:
            self.block_map.update(custom_block_map)
        # Reuse FIXTURE_PATTERNS from TextLayerMiner (single source of truth)
        self._fixture_patterns = TextLayerMiner.FIXTURE_PATTERNS
        self._price_pattern = TextLayerMiner.PRICE_PATTERN
        self._find_brand = TextLayerMiner._find_brand

    def extract(self, dxf_path: str) -> DocumentResult:
        """Extract from a DXF file on disk."""
        if not HAS_EZDXF:
            raise ImportError("ezdxf is required: pip install ezdxf")
        start_time = time.time()
        try:
            doc = ezdxf.readfile(dxf_path)
        except Exception as e:
            logger.error(f"Failed to open DXF: {e}")
            return self._empty_result(Path(dxf_path).name, start_time)
        return self._process_document(doc, Path(dxf_path).name, start_time)

    def extract_from_bytes(self, file_bytes: bytes, filename: str = "upload.dxf") -> DocumentResult:
        """Extract from DXF bytes (in-memory upload via Streamlit)."""
        if not HAS_EZDXF:
            raise ImportError("ezdxf is required: pip install ezdxf")
        start_time = time.time()
        tmp_path = None
        try:
            with tempfile.NamedTemporaryFile(suffix='.dxf', delete=False) as tmp:
                tmp.write(file_bytes)
                tmp_path = tmp.name
            doc = ezdxf.readfile(tmp_path)
            return self._process_document(doc, filename, start_time)
        except Exception as e:
            logger.error(f"Failed to read DXF: {e}")
            return self._empty_result(filename, start_time)
        finally:
            if tmp_path:
                try:
                    os.unlink(tmp_path)
                except OSError:
                    pass

    def _empty_result(self, filename: str, start_time: float) -> DocumentResult:
        return DocumentResult(
            filename=filename, total_pages=0,
            processing_time_ms=int((time.time() - start_time) * 1000),
        )

    # ────────────────────────────────────────────────────────────────────
    # MAIN PROCESSING
    # ────────────────────────────────────────────────────────────────────

    def _process_document(self, doc, filename: str, start_time: float) -> DocumentResult:
        try:
            msp = doc.modelspace()
        except Exception as e:
            logger.error(f"Cannot access modelspace: {e}")
            return self._empty_result(filename, start_time)

        # Step 1: Single-pass collection
        data = self._collect_entities(msp)
        data.drawing_unit_scale = self._detect_unit_scale(doc, data)
        data.is_archicad_export = self._detect_archicad(data)

        # Step 2: Extract fixtures from block INSERTs
        block_fixtures = self._extract_from_blocks(data)

        # Step 3: Extract fixtures from text legend using spatial QTYS matching
        #         (same algorithm as TextLayerMiner._extract_fixtures_spatial)
        legend_fixtures = self._extract_fixtures_spatial(data)

        # Step 4: Parse circuit labels using scan_circuit_labels()
        circuit_scan = scan_circuit_labels(data.electrical_text)

        # Step 5: Merge results — legend fixtures with quantities take priority
        fixtures = self._merge_fixtures(block_fixtures, legend_fixtures, circuit_scan)

        # Step 6: Build rooms (if shapely available)
        rooms = []
        if HAS_SHAPELY and data.room_polys:
            rooms = self._build_rooms(data)

        # Step 7: Metadata
        title_block = self._extract_metadata(doc, data)

        # Step 8: Calculate confidence
        confidence = self._calculate_confidence(fixtures, circuit_scan, data)

        # Step 9: Build warnings
        warnings = self._build_warnings(data, fixtures, circuit_scan)

        strategies = ["dxf_block_match"]
        if legend_fixtures:
            strategies.append("dxf_spatial_legend")
        if circuit_scan.labels:
            strategies.append("dxf_circuit_labels")

        page_result = PageResult(
            page_number=1,
            drawing_type=DrawingType.COMBINED,
            title_block=title_block,
            fixtures=fixtures,
            strategy_used=ExtractionStrategy.DXF_DIRECT,
            strategies_attempted=strategies,
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
    # STEP 1: SINGLE-PASS ENTITY COLLECTION
    # ────────────────────────────────────────────────────────────────────

    def _collect_entities(self, msp) -> DXFCollectedData:
        """Single pass over modelspace — collect INSERTs, text, polylines."""
        data = DXFCollectedData()
        data.insert_positions = defaultdict(list)
        layers_seen = set()
        electrical_text_parts = []

        for entity in msp:
            dxf_type = entity.dxftype()
            layer = entity.dxf.layer
            layer_upper = layer.upper()
            layers_seen.add(layer)

            if dxf_type == "INSERT":
                block_name = entity.dxf.name
                if block_name.startswith("*") or block_name.startswith("_"):
                    continue
                data.total_inserts += 1
                data.block_counts[block_name] = data.block_counts.get(block_name, 0) + 1
                if layer not in data.block_counts_by_layer:
                    data.block_counts_by_layer[layer] = {}
                data.block_counts_by_layer[layer][block_name] = (
                    data.block_counts_by_layer[layer].get(block_name, 0) + 1)
                try:
                    pos = entity.dxf.insert
                    data.insert_positions[block_name].append((pos.x, pos.y))
                except Exception:
                    pass

            elif dxf_type == "LWPOLYLINE" and HAS_SHAPELY:
                arch_kws = ['A-WALL', 'ARCH', 'A_WALL', 'WALL', 'A-ROOM', 'ROOM']
                if any(kw in layer_upper for kw in arch_kws) and entity.closed:
                    try:
                        coords = [(p[0], p[1]) for p in entity.get_points()]
                        if len(coords) >= 3:
                            poly = Polygon(coords)
                            if poly.is_valid and poly.area > 1.0:
                                data.room_polys.append(poly)
                    except Exception:
                        pass

            elif dxf_type in ("TEXT", "MTEXT"):
                text = ""
                try:
                    text = entity.dxf.text if dxf_type == "TEXT" else entity.text
                except Exception:
                    continue
                if not text or not text.strip():
                    continue

                text_clean = self._clean_mtext(text.strip())
                if not text_clean:
                    continue

                try:
                    pos = entity.dxf.insert
                except Exception:
                    continue

                # Store as a span (same structure as TextLayerMiner uses)
                span = {
                    "x": pos.x,
                    "y": pos.y,
                    "text": text_clean,
                    "layer": layer,
                    "layer_upper": layer_upper,
                }
                data.text_spans.append(span)

                # Collect electrical text for circuit label scanning
                is_elec = (
                    any(kw in layer_upper for kw in ELECTRICAL_TEXT_LAYERS)
                    or any(re.search(p, layer_upper) for p in ELECTRICAL_LAYER_PATTERNS)
                )
                if is_elec:
                    electrical_text_parts.append(text_clean)

                # Room labels
                if any(kw in layer_upper for kw in ['ROOM', 'TEXT BLOCK']):
                    if 1 < len(text_clean) < 30:
                        data.room_labels.append(span)

        data.layers_found = sorted(layers_seen)
        data.electrical_text = "\n".join(electrical_text_parts)
        return data

    def _clean_mtext(self, text: str) -> str:
        """Strip MTEXT formatting codes to get plain text."""
        if not text:
            return ""
        cleaned = re.sub(r'\\[fFpPHLlAa][^;]*;', '', text)
        cleaned = re.sub(r'\\[Ss][^;]*;', '', cleaned)
        cleaned = cleaned.replace('{', '').replace('}', '')
        cleaned = cleaned.replace('\\P', '\n')
        cleaned = re.sub(r'\\[a-zA-Z]', '', cleaned)
        cleaned = ' '.join(cleaned.split())
        return cleaned.strip()

    # ────────────────────────────────────────────────────────────────────
    # STEP 2: BLOCK INSERT MATCHING
    # ────────────────────────────────────────────────────────────────────

    def _extract_from_blocks(self, data: DXFCollectedData) -> List[FixtureItem]:
        """Match block INSERT names to fixture types."""
        fixtures = []

        for block_name, count in data.block_counts.items():
            # Skip structural blocks
            if self._is_structural(block_name):
                continue

            result = self._resolve_block(block_name)
            if result:
                fixture_type, category, confidence = result
                fixtures.append(FixtureItem(
                    fixture_type=fixture_type,
                    category=category,
                    quantity=count,
                    description=f"DXF block: {block_name}",
                    confidence=confidence,
                    confidence_level=_confidence_level(confidence),
                    source=ExtractionStrategy.DXF_DIRECT,
                ))

        return fixtures

    def _is_structural(self, block_name: str) -> bool:
        name_lower = block_name.lower()
        for pattern in SKIP_BLOCK_PATTERNS:
            if re.search(pattern, name_lower if not pattern.startswith('^') else block_name):
                return True
        return False

    def _resolve_block(self, block_name: str) -> Optional[Tuple[str, FixtureCategory, float]]:
        """Resolve block name → (fixture_type, category, confidence)."""
        name_upper = block_name.upper().strip()
        name_norm = re.sub(r'[-_ /]+', '_', name_upper).strip('_')

        # Strategy 1: Exact abbreviation match (1.0)
        for key, (ftype, cat) in self.block_map.items():
            if name_upper == key.upper():
                return ftype, cat, 1.0

        # Strategy 2: Normalized match (0.95)
        for key, (ftype, cat) in self.block_map.items():
            key_norm = re.sub(r'[-_ /]+', '_', key.upper()).strip('_')
            if name_norm == key_norm:
                return ftype, cat, 0.95

        # Strategy 3: Full-name pattern match using FIXTURE_PATTERNS (0.90)
        name_lower = block_name.lower()
        for pattern, ftype, cat in FULL_NAME_BLOCK_PATTERNS:
            if re.search(pattern, name_lower):
                return ftype, cat, 0.90

        # Strategy 4: Use TextLayerMiner.FIXTURE_PATTERNS on block name (0.85)
        for pattern, ftype, cat in self._fixture_patterns:
            if re.search(pattern, block_name, re.IGNORECASE):
                return ftype, cat, 0.85

        return None

    # ────────────────────────────────────────────────────────────────────
    # STEP 3: SPATIAL QTYS MATCHING (ported from TextLayerMiner)
    # ────────────────────────────────────────────────────────────────────

    def _extract_fixtures_spatial(self, data: DXFCollectedData) -> List[FixtureItem]:
        """
        Extract fixtures from DXF text using spatial nearest-neighbor matching.

        This is the same algorithm as TextLayerMiner._extract_fixtures_spatial()
        adapted for DXF text coordinates instead of PDF page coordinates.

        Algorithm:
        1. Find category headers (SWITCHES, LIGHTS, etc.) and QTYS headers
        2. Determine legend bounding box
        3. Match fixture descriptions against FIXTURE_PATTERNS
        4. For each fixture, find nearest standalone number (quantity)
        """
        spans = data.text_spans
        if not spans:
            return []

        # Find category and QTYS header positions
        cat_positions = []
        qty_positions = []

        for s in spans:
            txt_upper = s["text"].upper().strip()
            if txt_upper in CATEGORY_NAMES:
                cat_positions.append((txt_upper, s["x"], s["y"]))
            elif txt_upper in QTYS_NAMES:
                qty_positions.append((s["x"], s["y"]))

        if not cat_positions or not qty_positions:
            # No structured legend — fall back to pattern-only extraction
            return self._extract_fixtures_text_only(data)

        # Legend bounding box from headers
        all_hx = [h[1] for h in cat_positions] + [q[0] for q in qty_positions]
        all_hy = [h[2] for h in cat_positions] + [q[1] for q in qty_positions]
        legend_x_min = min(all_hx) - 2000  # DXF units (mm typically)
        legend_x_max = max(all_hx) + 2000
        legend_y_min = min(all_hy) - 4000
        legend_y_max = max(all_hy) + 4000

        # Collect fixture descriptions in the legend area
        descriptions = []
        for s in spans:
            if not (legend_x_min <= s["x"] <= legend_x_max):
                continue
            if not (legend_y_min <= s["y"] <= legend_y_max):
                continue
            txt = s["text"].strip()
            txt_upper = txt.upper()
            if txt_upper in CATEGORY_NAMES or txt_upper in QTYS_NAMES:
                continue
            if txt_upper in LEGEND_HEADERS:
                continue
            if len(txt) < 4:
                continue

            # Match against FIXTURE_PATTERNS (same patterns as PDF extractor)
            for pattern, fixture_type, fcat in self._fixture_patterns:
                if re.search(pattern, txt, re.IGNORECASE):
                    price = 0.0
                    pm = self._price_pattern.search(txt)
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
                        "brand": self._find_brand(self, txt),
                    })
                    break

        if not descriptions:
            return self._extract_fixtures_text_only(data)

        # Collect standalone numbers in the legend area
        numbers = []
        for s in spans:
            if not (legend_x_min <= s["x"] <= legend_x_max):
                continue
            if not (legend_y_min <= s["y"] <= legend_y_max):
                continue
            m = re.match(r'^(\d{1,4})$', s["text"].strip())
            if m:
                val = int(m.group(1))
                if 1 <= val <= 9999:
                    numbers.append({"qty": val, "x": s["x"], "y": s["y"]})

        # Determine layout orientation
        cat_x_range = max(h[1] for h in cat_positions) - min(h[1] for h in cat_positions)
        cat_y_range = max(h[2] for h in cat_positions) - min(h[2] for h in cat_positions)
        is_horizontal = cat_x_range > cat_y_range

        # DXF coordinates are in mm — tolerance is wider than PDF points
        tolerance = 500  # 500mm = ~50cm column alignment tolerance

        # Nearest-neighbor matching (same algorithm as TextLayerMiner)
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
                    primary_dist = abs(num["x"] - desc["x"])
                    secondary_dist = abs(num["y"] - desc["y"])
                else:
                    primary_dist = abs(num["x"] - desc["x"])
                    secondary_dist = abs(num["y"] - desc["y"])

                if primary_dist > tolerance:
                    continue

                dist = primary_dist + secondary_dist * 0.1

                if dist < best_dist:
                    best_dist = dist
                    best_qty = num["qty"]
                    best_idx = ni

            if best_idx >= 0:
                used_numbers.add(best_idx)

            # Confidence: 0.88 if qty found, 0.40 if only type (same as TextLayerMiner)
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
                source=ExtractionStrategy.DXF_DIRECT,
            ))

        return fixtures

    def _extract_fixtures_text_only(self, data: DXFCollectedData) -> List[FixtureItem]:
        """
        Fallback: extract fixture types from DXF text without spatial QTYS matching.
        Used when no structured legend (SWITCHES/LIGHTS/QTYS headers) is found.
        """
        fixtures = []
        seen = set()

        for s in data.text_spans:
            txt = s["text"].strip()
            if len(txt) < 5:
                continue
            txt_upper = txt.upper()
            if txt_upper in LEGEND_HEADERS:
                continue

            for pattern, fixture_type, fcat in self._fixture_patterns:
                if re.search(pattern, txt, re.IGNORECASE):
                    if fixture_type not in seen:
                        seen.add(fixture_type)
                        price = 0.0
                        pm = self._price_pattern.search(txt)
                        if pm:
                            try:
                                price = float(pm.group(1).replace(',', ''))
                            except ValueError:
                                pass
                        fixtures.append(FixtureItem(
                            fixture_type=fixture_type,
                            category=fcat,
                            quantity=0,  # Unknown without QTYS column
                            unit_price_zar=price,
                            description=txt[:120],
                            brand=self._find_brand(self, txt),
                            confidence=0.40,
                            confidence_level=Confidence.LOW,
                            source=ExtractionStrategy.DXF_DIRECT,
                        ))
                    break

        return fixtures

    # ────────────────────────────────────────────────────────────────────
    # STEP 5: MERGE RESULTS
    # ────────────────────────────────────────────────────────────────────

    def _merge_fixtures(
        self,
        block_fixtures: List[FixtureItem],
        legend_fixtures: List[FixtureItem],
        circuit_scan: CircuitLabelScanResult,
    ) -> List[FixtureItem]:
        """
        Merge fixtures from blocks, legend, and circuit labels.

        Priority:
        1. Legend fixtures with qty > 0 (spatial match found quantity)
        2. Block fixtures with real INSERT counts
        3. Legend fixtures with qty = 0 (type detected, no quantity)

        Circuit label counts are added as supplementary info.
        """
        merged = []
        seen_types = set()

        # First: legend fixtures WITH quantities (highest confidence)
        for f in legend_fixtures:
            if f.quantity > 0:
                merged.append(f)
                seen_types.add(f.fixture_type.upper())

        # Second: block fixtures (real counts from INSERTs)
        for f in block_fixtures:
            if f.fixture_type.upper() not in seen_types:
                merged.append(f)
                seen_types.add(f.fixture_type.upper())

        # Third: legend fixtures WITHOUT quantities (type only)
        for f in legend_fixtures:
            if f.quantity == 0 and f.fixture_type.upper() not in seen_types:
                merged.append(f)
                seen_types.add(f.fixture_type.upper())

        # Add circuit label summary as a fixture if meaningful
        if circuit_scan.total_lighting_points > 0:
            label_detail = ", ".join(
                f"{k}: {v}" for k, v in sorted(circuit_scan.by_type.get("lighting", {}).items())
            )
            if "LIGHTING" not in {f.category.name for f in merged if f.quantity > 0}:
                merged.append(FixtureItem(
                    fixture_type="Lighting Points (from circuit labels)",
                    category=FixtureCategory.LIGHTING,
                    quantity=circuit_scan.total_lighting_points,
                    description=f"Circuit labels: {label_detail}",
                    confidence=circuit_scan.confidence,
                    confidence_level=_confidence_level(circuit_scan.confidence),
                    source=ExtractionStrategy.DXF_DIRECT,
                ))

        if circuit_scan.total_power_points > 0:
            label_detail = ", ".join(
                f"{k}: {v}" for k, v in sorted(circuit_scan.by_type.get("power", {}).items())
            )
            if "POWER" not in {f.category.name for f in merged if f.quantity > 0}:
                merged.append(FixtureItem(
                    fixture_type="Power Points (from circuit labels)",
                    category=FixtureCategory.POWER,
                    quantity=circuit_scan.total_power_points,
                    description=f"Circuit labels: {label_detail}",
                    confidence=circuit_scan.confidence,
                    confidence_level=_confidence_level(circuit_scan.confidence),
                    source=ExtractionStrategy.DXF_DIRECT,
                ))

        return merged

    # ────────────────────────────────────────────────────────────────────
    # HELPERS
    # ────────────────────────────────────────────────────────────────────

    def _detect_archicad(self, data: DXFCollectedData) -> bool:
        layers_str = ' '.join(data.layers_found).upper()
        indicators = 0
        if 'PDF_TEXT' in layers_str or 'PDF_MEP' in layers_str:
            indicators += 2
        if 'B_ELECTRICAL' in layers_str:
            indicators += 1
        if any('_PEN_NO_' in l.upper() for l in data.layers_found):
            indicators += 1
        structural = sum(1 for n in data.block_counts if re.match(r'^(Wall|Column|Slab|Roof|Morph)_\d+$', n))
        if structural > 10:
            indicators += 2
        return indicators >= 2

    def _detect_unit_scale(self, doc, data: DXFCollectedData) -> float:
        try:
            insunits = doc.header.get("$INSUNITS", 0)
            unit_map = {1: 0.0254, 2: 0.3048, 4: 0.001, 5: 0.01, 6: 1.0}
            if insunits in unit_map:
                return unit_map[insunits]
        except Exception:
            pass
        max_coord = 0.0
        for positions in data.insert_positions.values():
            for x, y in positions:
                max_coord = max(max_coord, abs(x), abs(y))
        return 0.001 if max_coord > 1_000 else (0.01 if max_coord > 100 else 1.0)

    def _build_rooms(self, data: DXFCollectedData) -> List[RoomPolygon]:
        rooms = []
        unit_scale = data.drawing_unit_scale
        for poly in data.room_polys:
            room_name = "Unknown Room"
            for label in data.room_labels:
                try:
                    pt = Point(label["x"], label["y"])
                    if poly.contains(pt):
                        room_name = label["text"]
                        break
                except Exception:
                    pass
            rooms.append(RoomPolygon(
                name=room_name, polygon=poly,
                area_m2=round(poly.area * (unit_scale ** 2), 2),
            ))
        return rooms

    def _extract_metadata(self, doc, data: DXFCollectedData) -> TitleBlockInfo:
        info = TitleBlockInfo()
        try:
            if "$PROJECTNAME" in doc.header:
                info.project_name = str(doc.header["$PROJECTNAME"])
        except Exception:
            pass

        for s in data.text_spans:
            txt = s["text"]
            txt_upper = txt.upper().strip()
            if re.match(r'^[A-Z]{2,4}[-_]\d{3,}', txt_upper) and not info.drawing_number:
                info.drawing_number = txt.strip()
            if "BUILDING" in txt_upper and not info.building_name:
                info.building_name = txt.strip()[:100]
            if ("CONSULTANT" in txt_upper or "ENGINEER" in txt_upper) and not info.engineer:
                info.engineer = txt.strip()[:80]
            if "CLIENT" in txt_upper and not info.client:
                info.client = txt.strip()[:80]
            if "FLOOR" in txt_upper and ("SLAB" in txt_upper or "PLAN" in txt_upper) and not info.description:
                info.description = txt.strip()[:100]
        return info

    def _calculate_confidence(
        self, fixtures: List[FixtureItem],
        circuit_scan: CircuitLabelScanResult,
        data: DXFCollectedData,
    ) -> float:
        if not fixtures:
            return 0.0

        # Weighted average: fixtures with quantities count more
        total_weight = 0.0
        weighted_conf = 0.0
        for f in fixtures:
            weight = 2.0 if f.quantity > 0 else 0.5
            weighted_conf += f.confidence * weight
            total_weight += weight

        base_conf = weighted_conf / total_weight if total_weight > 0 else 0.0

        # Boost if circuit labels corroborate
        if circuit_scan.labels:
            base_conf = min(0.95, base_conf + 0.05)

        return round(base_conf, 2)

    def _build_warnings(
        self, data: DXFCollectedData,
        fixtures: List[FixtureItem],
        circuit_scan: CircuitLabelScanResult,
    ) -> List[str]:
        warnings = []

        if data.is_archicad_export:
            warnings.append(
                "ArchiCAD/PDF export detected — using text legend parsing + circuit label counting."
            )

        fixtures_with_qty = [f for f in fixtures if f.quantity > 0]
        fixtures_no_qty = [f for f in fixtures if f.quantity == 0]

        if fixtures_no_qty:
            types = ", ".join(f.fixture_type for f in fixtures_no_qty[:5])
            warnings.append(
                f"{len(fixtures_no_qty)} fixture type(s) found but quantity not extracted: {types}"
            )

        if not fixtures:
            warnings.append("No electrical fixtures found in this DXF file.")

        if circuit_scan.db_refs_found:
            warnings.append(
                f"DB boards detected from circuit labels: {', '.join(circuit_scan.db_refs_found)}"
            )

        if circuit_scan.labels:
            warnings.append(
                f"Circuit labels: {circuit_scan.total_lighting_points} lighting points, "
                f"{circuit_scan.total_power_points} power points, "
                f"{circuit_scan.total_dedicated_points} dedicated circuits"
            )

        if not HAS_SHAPELY:
            warnings.append("shapely not installed — room assignment skipped.")

        # Room names detected
        room_names = sorted(set(s["text"] for s in data.room_labels))
        if room_names:
            display = room_names[:8]
            warnings.append(
                f"Rooms: {', '.join(display)}"
                + (" ..." if len(room_names) > 8 else "")
            )

        return warnings

    def get_unknown_blocks(self, dxf_path: str) -> List[Tuple[str, int, str]]:
        """Get unrecognized block names for custom mapping."""
        if not HAS_EZDXF:
            return []
        try:
            doc = ezdxf.readfile(dxf_path)
        except Exception:
            return []
        msp = doc.modelspace()
        data = self._collect_entities(msp)

        unknown = []
        for block_name, count in data.block_counts.items():
            if self._is_structural(block_name):
                continue
            if self._resolve_block(block_name) is None:
                layer = ""
                for l, blocks in data.block_counts_by_layer.items():
                    if block_name in blocks:
                        layer = l
                        break
                unknown.append((block_name, count, layer))
        return sorted(unknown, key=lambda x: -x[1])


# ╔══════════════════════════════════════════════════════════════════════╗
# ║  CONVENIENCE FUNCTIONS                                               ║
# ╚══════════════════════════════════════════════════════════════════════╝

def extract_from_dxf(dxf_path: str, custom_block_map: Optional[Dict] = None) -> DocumentResult:
    """Extract fixtures from a DXF file on disk."""
    return DXFExtractor(custom_block_map=custom_block_map).extract(dxf_path)

def extract_from_dxf_bytes(file_bytes: bytes, filename: str = "upload.dxf",
                           custom_block_map: Optional[Dict] = None) -> DocumentResult:
    """Extract fixtures from DXF bytes (in-memory upload)."""
    return DXFExtractor(custom_block_map=custom_block_map).extract_from_bytes(file_bytes, filename)

def is_dxf_file(file_path: str) -> bool:
    """Check if a file is a DXF by extension."""
    return Path(file_path).suffix.lower() == ".dxf"
