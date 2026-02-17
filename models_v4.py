"""
AfriPlan Electrical v4.0 — Data Models
SINGLE SOURCE OF TRUTH for all data shapes.

v4.0 changes from v3.0:
- Multi-building/block support (BuildingBlock → rooms, DBs grouped per block)
- Expanded fixture types (12 light types, 8 socket types, 7 switch types)
- Heavy equipment models (pool pumps, heat pumps, VSD drives, HVAC)
- Cable containment (trunking, cable trays, wire mesh baskets)
- Site infrastructure (cable runs with actual distances, trenching, pole lights)
- Supply hierarchy (multiple Eskom connections)
- Legend model (symbol → description mapping per building block)
- Cross-document link models (circuit ref ↔ layout fixture)
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field, computed_field


# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║  ENUMS                                                                      ║
# ╚══════════════════════════════════════════════════════════════════════════════╝

class ServiceTier(str, Enum):
    RESIDENTIAL = "residential"
    COMMERCIAL = "commercial"
    INDUSTRIAL = "industrial"
    MAINTENANCE = "maintenance"
    MIXED = "mixed"                       # e.g. Wedela: offices + pool + hall
    UNKNOWN = "unknown"


class PipelineStage(str, Enum):
    INGEST = "INGEST"
    CLASSIFY = "CLASSIFY"
    DISCOVER = "DISCOVER"
    VALIDATE = "VALIDATE"
    PRICE = "PRICE"
    OUTPUT = "OUTPUT"


class ExtractionMode(str, Enum):
    AS_BUILT = "as_built"
    ESTIMATION = "estimation"
    INSPECTION = "inspection"
    HYBRID = "hybrid"                     # some blocks have SLDs, some don't


class PageType(str, Enum):
    REGISTER = "register"
    SLD = "sld"
    LAYOUT_LIGHTING = "layout_lighting"
    LAYOUT_PLUGS = "layout_plugs"
    LAYOUT_COMBINED = "layout_combined"   # lighting + plugs on same sheet
    OUTSIDE_LIGHTS = "outside_lights"     # site-wide external lighting plan
    SCHEDULE = "schedule"
    DETAIL = "detail"
    PHOTO = "photo"
    SPECIFICATION = "spec"
    UNKNOWN = "unknown"


class Severity(str, Enum):
    CRITICAL = "critical"
    WARNING = "warning"
    INFO = "info"


class ConfidenceLevel(str, Enum):
    HIGH = "high"       # >= 0.70
    MEDIUM = "medium"   # >= 0.40
    LOW = "low"         # < 0.40


class PhaseConfig(str, Enum):
    SINGLE = "1PH"
    THREE = "3PH"


# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║  LEGEND & SYMBOL MAPPING                                                    ║
# ╚══════════════════════════════════════════════════════════════════════════════╝

class LegendItem(BaseModel):
    """Maps a drawing symbol to its real-world description and specs."""
    symbol_id: str = ""                  # e.g. "LT-REC", "PS-DS300"
    category: str = ""                   # "light", "socket", "switch", "equipment", "containment"
    description: str = ""                # Full legend text
    short_name: str = ""                 # e.g. "600x1200 Recessed LED"
    wattage_w: float = 0.0              # For lights
    mounting_height_mm: int = 0          # e.g. 300, 1100, 1200, 2000
    ip_rating: str = ""                  # e.g. "IP20", "IP65"
    notes: str = ""


class BuildingLegend(BaseModel):
    """Complete legend for a building block — varies per block."""
    block_name: str = ""
    switches: List[LegendItem] = []
    sockets: List[LegendItem] = []
    lights: List[LegendItem] = []
    equipment: List[LegendItem] = []
    containment: List[LegendItem] = []


# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║  PAGE & DOCUMENT MODELS                                                     ║
# ╚══════════════════════════════════════════════════════════════════════════════╝

class PageInfo(BaseModel):
    """A single page extracted from a document."""
    page_number: int
    page_type: PageType = PageType.UNKNOWN
    image_base64: str = ""
    text_content: str = ""
    width_px: int = 0
    height_px: int = 0
    classification_confidence: float = 0.0
    drawing_number: str = ""             # e.g. "TJM-SLD-001", "WD-PB-01-LIGHTING"
    drawing_title: str = ""              # e.g. "MAIN DB GROUND FLOOR + COMMON AREA"
    building_block: str = ""             # e.g. "NewMark Office", "Pool Block"
    source_document: str = ""            # Which PDF this page came from


class DocumentInfo(BaseModel):
    """A single uploaded PDF."""
    filename: str = ""
    mime_type: str = ""
    num_pages: int = 0
    file_size_bytes: int = 0
    pages: List[PageInfo] = []


class DocumentSet(BaseModel):
    """
    Multiple uploaded PDFs that together describe one project.
    v4.0 key change: supports multi-document upload.
    """
    documents: List[DocumentInfo] = []
    total_pages: int = 0

    # Aggregated page counts
    num_register_pages: int = 0
    num_sld_pages: int = 0
    num_lighting_pages: int = 0
    num_plugs_pages: int = 0
    num_outside_light_pages: int = 0
    num_photo_pages: int = 0
    num_other_pages: int = 0

    # Detected building blocks
    building_blocks_detected: List[str] = []

    @computed_field
    @property
    def all_pages(self) -> List[PageInfo]:
        pages = []
        for doc in self.documents:
            pages.extend(doc.pages)
        return pages

    def pages_by_type(self, page_type: PageType) -> List[PageInfo]:
        return [p for p in self.all_pages if p.page_type == page_type]

    def pages_by_block(self, block_name: str) -> List[PageInfo]:
        return [p for p in self.all_pages if p.building_block == block_name]


# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║  EXTRACTION MODELS — What the AI returns                                    ║
# ╚══════════════════════════════════════════════════════════════════════════════╝

# --- Project Metadata ---

class ProjectMetadata(BaseModel):
    """Project-level info from drawing register and title blocks."""
    project_name: str = ""
    client_name: str = ""
    consultant_name: str = ""
    contractor_name: str = ""
    drawing_numbers: List[str] = []
    revision: Optional[int] = None
    date: str = ""
    standard: str = "SANS 10142-1"
    description: str = ""
    building_blocks: List[str] = []      # ["NewMark Office", "Ablution Retail Block", ...]


# --- Circuits ---

class Circuit(BaseModel):
    """A single circuit on a distribution board."""
    id: str = ""                         # e.g. "P1", "L2", "AC1", "DB-S1"
    type: str = "power"                  # power, lighting, ac, dedicated, sub_board_feed,
                                         # geyser, pump, hvac, spare, isolator
    description: str = ""
    wattage_w: float = 0.0
    wattage_formula: str = ""            # e.g. "5x54W", "8x48W" — raw from drawing
    cable_size_mm2: float = 2.5
    cable_cores: int = 3
    cable_type: str = "GP WIRE"          # "GP WIRE", "PVC SWA PVC", "SURFIX"
    breaker_a: int = 20
    breaker_poles: int = 1               # 1, 2, 3
    num_points: int = 0
    is_spare: bool = False
    has_isolator: bool = False
    isolator_rating_a: int = 0           # 20A or 30A
    has_vsd: bool = False                # Variable Speed Drive (pool pumps)

    # For sub-board feeds
    feeds_board: Optional[str] = None
    feed_cable_length_m: float = 0.0     # If marked on drawing

    # Cross-reference
    page_source: str = ""                # Which page this was read from


# --- Distribution Boards ---

class DistributionBoard(BaseModel):
    """A distribution board extracted from an SLD."""
    name: str = ""
    description: str = ""
    location: str = ""
    building_block: str = ""             # Which block this DB belongs to
    supply_from: str = ""
    supply_cable: str = ""
    supply_cable_size_mm2: float = 0.0
    supply_cable_cores: int = 4
    supply_cable_type: str = ""          # "PVC SWA PVC", "GP WIRE"
    supply_cable_length_m: float = 0.0   # If marked on outside lights drawing
    main_breaker_a: int = 0
    earth_leakage: bool = False
    earth_leakage_rating_a: int = 0      # e.g. 63A
    surge_protection: bool = False
    circuits: List[Circuit] = []
    spare_ways: int = 0
    total_wattage_w: float = 0.0
    phase: PhaseConfig = PhaseConfig.THREE
    voltage_v: int = 400
    fault_level_ka: float = 15.0         # e.g. 6kA, 15kA

    # SLD drawing reference
    sld_drawing_number: str = ""         # e.g. "WD-PB-01-SLD", "TJM-SLD-001"
    page_source: str = ""

    @computed_field
    @property
    def active_circuits(self) -> List[Circuit]:
        return [c for c in self.circuits if not c.is_spare]

    @computed_field
    @property
    def total_ways(self) -> int:
        return len(self.circuits) + self.spare_ways

    @computed_field
    @property
    def sub_board_feeds(self) -> List[Circuit]:
        return [c for c in self.circuits if c.feeds_board]


# --- Supply Hierarchy ---

class SupplyPoint(BaseModel):
    """An electrical supply source (Eskom connection, transformer, etc.)."""
    name: str = ""                       # "Eskom Kiosk Metering", "Existing Mini Sub"
    type: str = "eskom_kiosk"            # eskom_kiosk, mini_sub, transformer, generator
    main_breaker_a: int = 0
    cable_to_first_db: str = ""          # Cable spec to first DB downstream
    cable_length_m: float = 0.0
    feeds_db: str = ""                   # Name of first DB downstream
    building_block: str = ""
    notes: str = ""


# --- Expanded Fixture Counts ---

class FixtureCounts(BaseModel):
    """
    All fixture types encountered across the Wedela project.
    v4.0: expanded from 3 light types to 12, sockets from 2 to 8, switches from 3 to 7.
    """
    # === LIGHTS ===
    recessed_led_600x1200: int = 0       # 600×1200 Recessed 3×18W LED (54W) — most common
    surface_mount_led_18w: int = 0        # 18W LED ceiling light surface mount
    flood_light_30w: int = 0              # 30W LED flood light (external)
    flood_light_200w: int = 0             # 200W LED flood light (pool area)
    downlight_led_6w: int = 0             # 6W LED downlight white
    vapor_proof_2x24w: int = 0            # 2×24W double vapor proof LED (ablutions, wet areas)
    vapor_proof_2x18w: int = 0            # 2×18W double vapor proof (community hall, pool)
    prismatic_2x18w: int = 0              # 2×18W double prismatic LED (guard houses)
    bulkhead_26w: int = 0                 # 26W bulkhead outdoor (large guard house, pool)
    bulkhead_24w: int = 0                 # 24W bulkhead outdoor (small guard house)
    fluorescent_50w_5ft: int = 0          # 50W 5ft single fluorescent (community hall — non-LED)
    pole_light_60w: int = 0              # Outdoor pole light 2300mm, 60W ES (site perimeter)

    # === POWER SOCKETS ===
    double_socket_300: int = 0           # 16A double switched @300mm
    single_socket_300: int = 0           # 16A single switched @300mm
    double_socket_1100: int = 0          # 16A double switched @1100mm (counter height)
    single_socket_1100: int = 0          # 16A single switched @1100mm
    double_socket_waterproof: int = 0    # 16A double switched waterproof @300mm
    double_socket_ceiling: int = 0       # 16A double switched ceiling mount
    data_points_cat6: int = 0            # CAT 6 data outlet
    floor_box: int = 0                   # Floor-mounted socket box

    # === SWITCHES ===
    switch_1lever_1way: int = 0          # 1-lever 1-way @1200mm
    switch_2lever_1way: int = 0          # 2-lever 1-way @1200mm
    switch_1lever_2way: int = 0          # 1-lever 2-way @1200mm (corridors)
    day_night_switch: int = 0            # Day/night @2000mm
    isolator_30a: int = 0                # 30A isolator @2000mm (geyser/heavy)
    isolator_20a: int = 0                # 20A isolator @2000mm (AC)
    master_switch: int = 0               # Master switch (community hall)

    # === EQUIPMENT ===
    ac_units: int = 0
    geyser_50l: int = 0                  # 50L geyser
    geyser_100l: int = 0
    geyser_150l: int = 0
    geyser_200l: int = 0

    # Computed totals
    @computed_field
    @property
    def total_lights(self) -> int:
        return (self.recessed_led_600x1200 + self.surface_mount_led_18w +
                self.flood_light_30w + self.flood_light_200w + self.downlight_led_6w +
                self.vapor_proof_2x24w + self.vapor_proof_2x18w + self.prismatic_2x18w +
                self.bulkhead_26w + self.bulkhead_24w + self.fluorescent_50w_5ft +
                self.pole_light_60w)

    @computed_field
    @property
    def total_sockets(self) -> int:
        return (self.double_socket_300 + self.single_socket_300 +
                self.double_socket_1100 + self.single_socket_1100 +
                self.double_socket_waterproof + self.double_socket_ceiling +
                self.floor_box)

    @computed_field
    @property
    def total_switches(self) -> int:
        return (self.switch_1lever_1way + self.switch_2lever_1way +
                self.switch_1lever_2way + self.day_night_switch +
                self.isolator_30a + self.isolator_20a + self.master_switch)

    @computed_field
    @property
    def total_light_wattage(self) -> float:
        return (self.recessed_led_600x1200 * 54 + self.surface_mount_led_18w * 18 +
                self.flood_light_30w * 30 + self.flood_light_200w * 200 +
                self.downlight_led_6w * 6 + self.vapor_proof_2x24w * 48 +
                self.vapor_proof_2x18w * 36 + self.prismatic_2x18w * 36 +
                self.bulkhead_26w * 26 + self.bulkhead_24w * 24 +
                self.fluorescent_50w_5ft * 50 + self.pole_light_60w * 60)


# --- Rooms ---

class Room(BaseModel):
    """A room/area extracted from layout drawings."""
    name: str = ""
    room_number: int = 0                  # Room number if shown on drawing
    type: str = ""                        # office_suite, ablution, kitchen, hall, passage, etc.
    area_m2: float = 0.0
    floor: str = ""
    building_block: str = ""
    fixtures: FixtureCounts = FixtureCounts()
    circuit_refs: List[str] = []          # e.g. ["DB-S3 L1", "DB-S3 P1", "DB-S3 AC1"]
    is_wet_area: bool = False             # Ablutions, pool areas — affects IP ratings
    has_ac: bool = False
    has_geyser: bool = False
    notes: List[str] = []
    page_source: str = ""                 # Which page this was extracted from


# --- Heavy Equipment (Pool Pumps, Heat Pumps, HVAC) ---

class HeavyEquipment(BaseModel):
    """Pool pumps, heat pumps, HVAC systems, circulation pumps."""
    name: str = ""                        # "Pool Pump 1", "Heat Pump 3", "60KW HVAC"
    type: str = ""                        # pool_pump, heat_pump, circulation_pump, hvac, vsd
    rating_kw: float = 0.0
    cable_size_mm2: float = 4.0
    cable_type: str = "PVC SWA PVC"
    cable_length_m: float = 0.0
    breaker_a: int = 32
    has_vsd: bool = False                 # Variable Speed Drive
    has_dol: bool = False                 # Direct On Line starter
    isolator_a: int = 0
    fed_from_db: str = ""                 # Which DB feeds this
    building_block: str = ""
    qty: int = 1
    notes: str = ""


# --- Cable Containment ---

class CableContainment(BaseModel):
    """Cable trays, trunking, wire mesh baskets, power skirting."""
    type: str = ""                        # cable_tray, gable_tray, wire_mesh, power_skirting, conduit
    description: str = ""                 # e.g. "200mm Galvanized Gable Tray P8000 Trunking"
    size_mm: int = 0                      # Width in mm (150, 200, etc.)
    material: str = ""                    # galvanized, pvc, steel_grey
    mounting: str = ""                    # surface, recessed, underground
    estimated_length_m: float = 0.0
    building_block: str = ""
    notes: str = ""


# --- Site Cable Runs ---

class SiteCableRun(BaseModel):
    """A cable run between buildings/DBs — from outside lights drawing."""
    from_point: str = ""                  # "Kiosk", "DB-CR"
    to_point: str = ""                    # "DB-PFA", "DB-AB1"
    cable_spec: str = ""                  # "95mm² 4C Copper PVC SWA PVC"
    cable_size_mm2: float = 0.0
    cable_cores: int = 4
    cable_type: str = "PVC SWA PVC"
    length_m: float = 0.0                 # Actual length from drawing
    is_underground: bool = True           # Most site cables are underground
    needs_trenching: bool = True
    notes: str = ""


# --- Underground Sleeves/Ducts ---

class UndergroundSleeve(BaseModel):
    """Underground sleeve/duct provision (e.g. for future solar cables)."""
    size_mm: int = 0                      # 50mm, 75mm, 110mm
    qty: int = 1
    purpose: str = ""                     # "solar cables", "future provision"
    building_block: str = ""


# --- Defects (Maintenance/COC) ---

class Defect(BaseModel):
    """A defect identified during inspection."""
    code: str = ""
    description: str = ""
    severity: Severity = Severity.WARNING
    location: str = ""
    qty: int = 1
    estimated_fix: str = ""


# --- Building Block ---

class BuildingBlock(BaseModel):
    """
    A distinct building within the project.
    v4.0 key model: groups DBs, rooms, equipment per building.
    """
    name: str = ""                        # "NewMark Office Building", "Pool Block"
    description: str = ""
    total_area_m2: float = 0.0
    num_floors: int = 1

    # Electrical data for this block
    distribution_boards: List[DistributionBoard] = []
    rooms: List[Room] = []
    heavy_equipment: List[HeavyEquipment] = []
    cable_containment: List[CableContainment] = []
    legend: Optional[BuildingLegend] = None

    # Supply info
    supply_from: str = ""                 # Which supply point or parent DB
    supply_cable: str = ""

    # Drawing references
    sld_drawings: List[str] = []          # ["WD-PB-01-SLD"]
    layout_drawings: List[str] = []       # ["WD-PB-01-LIGHTING", "WD-PB-01-PLUG"]

    @computed_field
    @property
    def total_dbs(self) -> int:
        return len(self.distribution_boards)

    @computed_field
    @property
    def total_circuits(self) -> int:
        return sum(len(db.circuits) for db in self.distribution_boards)

    @computed_field
    @property
    def total_wattage_w(self) -> float:
        return sum(db.total_wattage_w for db in self.distribution_boards)


# --- Complete Extraction Result ---

class ExtractionResult(BaseModel):
    """
    Complete extraction output — THE data contract between agent and UI.
    v4.0: organized by building block, supports multi-supply, site infrastructure.
    """
    extraction_mode: ExtractionMode = ExtractionMode.ESTIMATION

    # Project-level
    metadata: ProjectMetadata = ProjectMetadata()

    # Building blocks (the main organizational unit)
    building_blocks: List[BuildingBlock] = []

    # Site-wide infrastructure (not tied to a single block)
    supply_points: List[SupplyPoint] = []
    site_cable_runs: List[SiteCableRun] = []
    underground_sleeves: List[UndergroundSleeve] = []
    outside_lights: Optional[FixtureCounts] = None   # Site-wide external lighting

    # Flat access (convenience — auto-aggregated from blocks)
    @computed_field
    @property
    def all_distribution_boards(self) -> List[DistributionBoard]:
        dbs = []
        for block in self.building_blocks:
            dbs.extend(block.distribution_boards)
        return dbs

    @computed_field
    @property
    def all_rooms(self) -> List[Room]:
        rooms = []
        for block in self.building_blocks:
            rooms.extend(block.rooms)
        return rooms

    @computed_field
    @property
    def all_heavy_equipment(self) -> List[HeavyEquipment]:
        equip = []
        for block in self.building_blocks:
            equip.extend(block.heavy_equipment)
        return equip

    # Maintenance mode
    defects: List[Defect] = []

    # Totals
    @computed_field
    @property
    def total_area_m2(self) -> float:
        return sum(b.total_area_m2 for b in self.building_blocks)

    @computed_field
    @property
    def total_dbs(self) -> int:
        return sum(b.total_dbs for b in self.building_blocks)

    @computed_field
    @property
    def total_circuits(self) -> int:
        return sum(b.total_circuits for b in self.building_blocks)

    @computed_field
    @property
    def total_site_cable_m(self) -> float:
        return sum(r.length_m for r in self.site_cable_runs)

    # Quality
    pages_processed: int = 0
    pages_with_data: int = 0
    extraction_warnings: List[str] = []
    missing_data: List[str] = []

    @computed_field
    @property
    def completeness(self) -> float:
        if self.pages_processed == 0:
            return 0.0
        return self.pages_with_data / self.pages_processed

    @computed_field
    @property
    def has_sld_data(self) -> bool:
        return len(self.all_distribution_boards) > 0

    @computed_field
    @property
    def has_room_data(self) -> bool:
        return len(self.all_rooms) > 0


# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║  CROSS-REFERENCE & VALIDATION MODELS                                        ║
# ╚══════════════════════════════════════════════════════════════════════════════╝

class CircuitRoomLink(BaseModel):
    """Links a circuit from the SLD to the rooms it serves on layouts."""
    circuit_id: str = ""                  # "DB-S3 L1"
    db_name: str = ""                     # "DB-S3"
    circuit_label: str = ""               # "L1"
    rooms_served: List[str] = []          # ["Suite 3"]
    sld_wattage_w: float = 0.0           # Wattage from SLD schedule
    layout_wattage_w: float = 0.0        # Calculated from fixture count on layout
    sld_points: int = 0                  # Point count from SLD schedule
    layout_points: int = 0               # Fixture count from layout
    match_status: str = "unmatched"      # "matched", "partial", "conflict", "unmatched"
    conflict_notes: str = ""


class CrossReferenceResult(BaseModel):
    """Result of cross-page validation between SLDs and layouts."""
    links: List[CircuitRoomLink] = []
    matched: int = 0
    partial: int = 0
    conflicts: int = 0
    unmatched_sld: int = 0               # Circuits in SLD but not on layout
    unmatched_layout: int = 0            # Circuit refs on layout but not in SLD


class ValidationFlag(BaseModel):
    """A single validation check result."""
    rule_name: str
    message: str
    severity: Severity = Severity.WARNING
    passed: bool = True
    auto_corrected: bool = False
    corrected_value: str = ""
    related_circuit: str = ""
    related_board: str = ""
    related_block: str = ""              # Building block name
    standard_ref: str = "SANS 10142-1"


class ValidationResult(BaseModel):
    """Complete validation output."""
    flags: List[ValidationFlag] = []
    cross_references: Optional[CrossReferenceResult] = None
    passed: int = 0
    failed: int = 0
    warnings: int = 0
    auto_corrections: int = 0
    compliance_score: float = 100.0
    corrections_applied: List[str] = []

    @computed_field
    @property
    def has_critical_issues(self) -> bool:
        return any(f.severity == Severity.CRITICAL and not f.passed for f in self.flags)


# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║  PRICING MODELS                                                             ║
# ╚══════════════════════════════════════════════════════════════════════════════╝

class BQSection(str, Enum):
    """Groups BQ line items by section for professional quotation layout."""
    SUPPLY = "A - Supply Infrastructure"
    DISTRIBUTION = "B - Distribution Boards"
    CABLES = "C - Cables & Wiring"
    CONTAINMENT = "D - Cable Containment"
    LIGHTS = "E - Light Fittings"
    SOCKETS = "F - Socket Outlets & Switches"
    EQUIPMENT = "G - Heavy Equipment"
    DEDICATED = "H - Dedicated Circuits"
    COMPLIANCE = "I - Compliance Additions"
    SITE_WORKS = "J - Site Works & Trenching"
    LABOUR = "K - Labour"
    PROVISIONAL = "L - Provisional Sums"


class BQLineItem(BaseModel):
    """A single line in the Bill of Quantities."""
    item_no: int = 0
    section: BQSection = BQSection.CABLES
    category: str = ""
    description: str = ""
    unit: str = "each"
    qty: float = 1.0
    unit_price_zar: float = 0.0
    total_zar: float = 0.0
    source: str = "extracted"            # "extracted", "estimated", "compliance_add", "provisional"
    building_block: str = ""             # Which block this item belongs to
    notes: str = ""


class BlockPricingSummary(BaseModel):
    """Pricing summary for a single building block."""
    block_name: str = ""
    subtotal_materials_zar: float = 0.0
    subtotal_labour_zar: float = 0.0
    subtotal_equipment_zar: float = 0.0
    subtotal_site_works_zar: float = 0.0
    block_total_zar: float = 0.0
    item_count: int = 0


class PricingResult(BaseModel):
    """Complete pricing output."""
    line_items: List[BQLineItem] = []

    # Per-block summaries
    block_summaries: List[BlockPricingSummary] = []

    # Project totals
    subtotal_materials_zar: float = 0.0
    subtotal_labour_zar: float = 0.0
    subtotal_equipment_zar: float = 0.0
    subtotal_site_works_zar: float = 0.0
    subtotal_compliance_zar: float = 0.0
    subtotal_provisional_zar: float = 0.0

    # Adjustments
    complexity_factor: float = 1.0
    complexity_description: str = "New installation"
    contractor_margin_pct: float = 20.0
    contingency_pct: float = 5.0         # v4.0: contingency for large projects

    # Totals
    subtotal_zar: float = 0.0
    contingency_zar: float = 0.0
    margin_zar: float = 0.0
    total_excl_vat_zar: float = 0.0
    vat_zar: float = 0.0
    total_incl_vat_zar: float = 0.0

    # Payment schedule
    payment_terms: str = "40/40/20"
    deposit_zar: float = 0.0
    second_payment_zar: float = 0.0
    final_payment_zar: float = 0.0

    # Quality indicators
    items_from_extraction: int = 0
    items_estimated: int = 0
    items_compliance: int = 0
    items_provisional: int = 0

    @computed_field
    @property
    def pricing_confidence(self) -> float:
        total = (self.items_from_extraction + self.items_estimated +
                 self.items_compliance + self.items_provisional)
        if total == 0:
            return 0.0
        return self.items_from_extraction / total


# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║  PIPELINE RESULT MODELS                                                     ║
# ╚══════════════════════════════════════════════════════════════════════════════╝

class StageResult(BaseModel):
    """Result from a single pipeline stage."""
    stage: PipelineStage
    success: bool = False
    confidence: float = 0.0
    data: Dict[str, Any] = {}
    model_used: Optional[str] = None
    tokens_used: int = 0
    cost_zar: float = 0.0
    processing_time_ms: int = 0
    errors: List[str] = []
    warnings: List[str] = []


class PipelineResult(BaseModel):
    """
    Top-level pipeline output.
    v4.0: supports multi-document, multi-block results.
    """
    stages: List[StageResult] = []
    success: bool = False

    # Classification
    tier: ServiceTier = ServiceTier.UNKNOWN
    tier_confidence: float = 0.0
    extraction_mode: ExtractionMode = ExtractionMode.ESTIMATION

    # Core results
    document_set: DocumentSet = DocumentSet()
    extraction: ExtractionResult = ExtractionResult()
    validation: Optional[ValidationResult] = None
    pricing: Optional[PricingResult] = None

    # Aggregates
    overall_confidence: float = 0.0
    total_cost_zar: float = 0.0
    total_tokens: int = 0
    errors: List[str] = []
    warnings: List[str] = []

    @computed_field
    @property
    def confidence_level(self) -> ConfidenceLevel:
        if self.overall_confidence >= 0.70:
            return ConfidenceLevel.HIGH
        elif self.overall_confidence >= 0.40:
            return ConfidenceLevel.MEDIUM
        return ConfidenceLevel.LOW

    @computed_field
    @property
    def needs_escalation(self) -> bool:
        return self.overall_confidence < 0.40

    @computed_field
    @property
    def stage_summary(self) -> Dict[str, bool]:
        return {s.stage.value: s.success for s in self.stages}

    @computed_field
    @property
    def num_building_blocks(self) -> int:
        return len(self.extraction.building_blocks)


# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║  LEGACY COMPATIBILITY                                                       ║
# ╚══════════════════════════════════════════════════════════════════════════════╝

class ProjectTier(str, Enum):
    RESIDENTIAL = "residential"
    COMMERCIAL = "commercial"
    MAINTENANCE = "maintenance"
    INDUSTRIAL = "industrial"
    INFRASTRUCTURE = "infrastructure"
    UNKNOWN = "unknown"


class AnalysisResult(BaseModel):
    tier: ProjectTier = ProjectTier.UNKNOWN
    confidence: float = 0.0
    subtype: Optional[str] = None
    extracted_data: Dict[str, Any] = {}
    reasoning: Any = None
    warnings: List[str] = []


TIER_DISPLAY = {
    ServiceTier.RESIDENTIAL: {
        "icon": "🏠", "name": "Residential",
        "color": "#22C55E", "description": "Houses, flats, domestic installations"
    },
    ServiceTier.COMMERCIAL: {
        "icon": "🏢", "name": "Commercial",
        "color": "#3B82F6", "description": "Offices, retail, hospitality, healthcare"
    },
    ServiceTier.INDUSTRIAL: {
        "icon": "🏭", "name": "Industrial",
        "color": "#8B5CF6", "description": "Factories, plants, heavy equipment"
    },
    ServiceTier.MAINTENANCE: {
        "icon": "🔧", "name": "Maintenance & COC",
        "color": "#F59E0B", "description": "Inspections, repairs, DB upgrades"
    },
    ServiceTier.MIXED: {
        "icon": "🏗️", "name": "Mixed Use",
        "color": "#EC4899", "description": "Multi-building complex"
    },
    ServiceTier.UNKNOWN: {
        "icon": "❓", "name": "Unknown",
        "color": "#64748b", "description": "Could not determine project type"
    },
}


def get_tier_display_info(tier: ServiceTier) -> dict:
    return TIER_DISPLAY.get(tier, TIER_DISPLAY[ServiceTier.UNKNOWN])
