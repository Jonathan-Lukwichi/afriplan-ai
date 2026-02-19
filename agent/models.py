"""
AfriPlan Electrical v4.5 — Data Models
SINGLE SOURCE OF TRUTH for all data shapes.

v4.1 philosophy change from v4.0:
  The tool is a QUANTITY TAKE-OFF ACCELERATOR, not an automatic quotation machine.
  The AI extracts quantities. The contractor reviews/corrects. Then applies their prices.

v4.1 additions:
- ContractorProfile (saved preferences: markup, labour rates, supplier)
- SiteConditions (renovation?, access?, soil type?, scaffolding?)
- CorrectionLog (tracks contractor edits for accuracy learning)
- Dual BQ output: quantity-only (primary) + estimated (ballpark)
- 7-stage pipeline: INGEST → CLASSIFY → DISCOVER → REVIEW → VALIDATE → PRICE → OUTPUT
- Confidence flags per extracted item (green/yellow/red in UI)
- All v4.0 models retained (multi-building, 12 lights, heavy equipment, etc.)

v4.3 additions (Universal SLD Extraction):
- Circuit: vsd_rating_kw, starter_type, has_day_night, has_bypass, controlled_circuits
- HeavyEquipment: circuit_ref, starter_type, vsd_rating_kw
- Support for ISO, PP, HP, CP, HVAC, RWB, D/N circuit types
- Pump station extraction (pool pumps, heat pumps with VSD)
- Day/night switch detection with bypass

v4.4 additions (Layout Drawing Enhancements - Wedela Lighting & Plugs PDF):
- FixtureCounts: pool_flood_light, pool_underwater_light (FL, PS symbols)
- Legend validation support (cross-check room totals vs legend QTYS)
- Enhanced socket/switch types already in model (waterproof, ceiling, master switch)

v4.5 additions (Universal Electrical Project Schema - from Wedela SLD analysis):
- SystemParameters: voltage, phases, frequency, fault levels (3PH+N+E, 400V, 50Hz, 15kA)
- Circuit: breaker_type (MCB/MCCB/ACB/Fuse), phase designation (R1/W1/B1)
- SiteCableRun: material (copper/aluminium), installation_method enum
- HeavyEquipment: expanded types (meter, ups, generator, solar_inverter, ev_charger, etc.)
- HeavyEquipment: overload_relay field for motor circuits
- SupplyPoint: rating_kva, voltage_primary, voltage_secondary, status
- BreakerType and InstallationMethod enums for standardized values
"""

from __future__ import annotations

from enum import Enum
from datetime import datetime
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
    MIXED = "mixed"
    UNKNOWN = "unknown"


class PipelineStage(str, Enum):
    INGEST = "INGEST"
    CLASSIFY = "CLASSIFY"
    DISCOVER = "DISCOVER"
    REVIEW = "REVIEW"           # NEW: contractor review/edit step
    VALIDATE = "VALIDATE"
    PRICE = "PRICE"
    OUTPUT = "OUTPUT"


class ExtractionMode(str, Enum):
    AS_BUILT = "as_built"
    ESTIMATION = "estimation"
    INSPECTION = "inspection"
    HYBRID = "hybrid"


class PageType(str, Enum):
    REGISTER = "register"
    SLD = "sld"
    LAYOUT_LIGHTING = "layout_lighting"
    LAYOUT_PLUGS = "layout_plugs"
    LAYOUT_COMBINED = "layout_combined"
    OUTSIDE_LIGHTS = "outside_lights"
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
    HIGH = "high"       # >= 0.70  → green in UI
    MEDIUM = "medium"   # >= 0.40  → yellow in UI
    LOW = "low"         # < 0.40   → red in UI


class ItemConfidence(str, Enum):
    """Per-item confidence flag — shown as colour in the review UI."""
    EXTRACTED = "extracted"     # Read directly from drawing → green
    INFERRED = "inferred"       # Calculated from related data → yellow
    ESTIMATED = "estimated"     # Default/guessed → red, needs review
    MANUAL = "manual"           # Entered/corrected by contractor → blue


class PhaseConfig(str, Enum):
    SINGLE = "1PH"
    THREE = "3PH"


# v4.5 - New enums for universal electrical project support
class BreakerType(str, Enum):
    """Circuit breaker types - affects pricing significantly."""
    MCB = "mcb"           # Miniature Circuit Breaker (6A-63A) - most common
    MCCB = "mccb"         # Moulded Case Circuit Breaker (100A-1600A) - 5-10x cost
    ACB = "acb"           # Air Circuit Breaker (800A-6300A) - industrial
    FUSE = "fuse"         # HRC fuses, NH types
    RCBO = "rcbo"         # Combined MCB + RCD
    UNKNOWN = "unknown"


class CableMaterial(str, Enum):
    """Cable conductor material - affects pricing and current capacity."""
    COPPER = "copper"
    ALUMINIUM = "aluminium"
    UNKNOWN = "unknown"


class InstallationMethod(str, Enum):
    """Cable installation method - affects labour and containment pricing."""
    UNDERGROUND = "underground"           # Buried in trench
    BURIED_DIRECT = "buried_direct"       # Direct burial without conduit
    TRUNKING = "trunking"                 # Surface trunking
    CONDUIT = "conduit"                   # PVC or steel conduit
    CABLE_TRAY = "cable_tray"             # Open cable tray
    CABLE_LADDER = "cable_ladder"         # Cable ladder rack
    WALL_MOUNTED = "wall_mounted"         # Surface mounted on wall
    CEILING_VOID = "ceiling_void"         # In ceiling space
    UNKNOWN = "unknown"


class EquipmentStatus(str, Enum):
    """Equipment/installation status."""
    EXISTING = "existing"     # Already installed
    NEW = "new"               # To be installed (new work)
    PROPOSED = "proposed"     # Future/planned
    REMOVE = "remove"         # To be removed


class EquipmentType(str, Enum):
    """v4.5 - Comprehensive equipment types for universal extraction."""
    # Pumps
    POOL_PUMP = "pool_pump"
    HEAT_PUMP = "heat_pump"
    CIRCULATION_PUMP = "circulation_pump"
    BOREHOLE_PUMP = "borehole_pump"
    FIRE_PUMP = "fire_pump"
    SUMP_PUMP = "sump_pump"
    IRRIGATION_PUMP = "irrigation_pump"
    # HVAC
    HVAC = "hvac"
    AIR_CON = "air_con"
    VENTILATION_FAN = "ventilation_fan"
    COMPRESSOR = "compressor"
    # Water heating
    GEYSER = "geyser"
    SOLAR_GEYSER = "solar_geyser"
    HEAT_PUMP_GEYSER = "heat_pump_geyser"
    # Power systems
    GENERATOR = "generator"
    UPS = "ups"
    SOLAR_INVERTER = "solar_inverter"
    BATTERY_STORAGE = "battery_storage"
    # Metering
    METER = "meter"
    PREPAID_METER = "prepaid_meter"
    CT_METER = "ct_meter"
    # Access/Security
    GATE_MOTOR = "gate_motor"
    GARAGE_MOTOR = "garage_motor"
    SECURITY_SYSTEM = "security_system"
    CCTV = "cctv"
    ACCESS_CONTROL = "access_control"
    # Fire systems
    FIRE_PANEL = "fire_panel"
    SMOKE_DETECTOR = "smoke_detector"
    # Building management
    BMS = "bms"
    # Transport
    LIFT = "lift"
    ESCALATOR = "escalator"
    CONVEYOR = "conveyor"
    # EV
    EV_CHARGER = "ev_charger"
    # Kitchen
    STOVE = "stove"
    OVEN = "oven"
    # Other
    OTHER = "other"


# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║  CONTRACTOR PROFILE — Saved preferences per user                            ║
# ╚══════════════════════════════════════════════════════════════════════════════╝

class LabourRates(BaseModel):
    """Contractor's actual labour rates."""
    electrician_daily_zar: float = 1800.0      # Qualified electrician per day
    assistant_daily_zar: float = 650.0         # Assistant/labourer per day
    foreman_daily_zar: float = 2500.0          # Site foreman per day
    team_size_electricians: int = 2
    team_size_assistants: int = 2
    travel_rate_per_km_zar: float = 5.50

    @computed_field
    @property
    def team_daily_rate_zar(self) -> float:
        return (self.electrician_daily_zar * self.team_size_electricians +
                self.assistant_daily_zar * self.team_size_assistants)


class ContractorProfile(BaseModel):
    """
    Contractor's saved preferences. Persisted in Streamlit session or local storage.
    Used to personalize BQ pricing instead of generic defaults.
    """
    # Company info
    company_name: str = ""
    registration_number: str = ""          # ECSA or CIDB
    contact_name: str = ""
    contact_phone: str = ""
    contact_email: str = ""
    physical_address: str = ""
    vat_number: str = ""

    # Financial defaults
    markup_pct: float = 20.0               # Default contractor margin
    contingency_pct: float = 5.0
    vat_pct: float = 15.0
    payment_terms: str = "40/40/20"

    # Labour
    labour_rates: LabourRates = Field(default_factory=LabourRates)

    # Preferred supplier (affects pricing)
    preferred_supplier: str = ""           # e.g. "Voltex", "ARB", "Major Tech", "Eurolux"

    # Custom unit prices (overrides defaults — keyed by item description)
    custom_prices: Dict[str, float] = Field(default_factory=dict)

    # Location
    base_location: str = ""                # e.g. "Johannesburg"
    max_travel_km: int = 100

    # BQ format preference
    bq_format: str = "detailed"            # "detailed", "summary", "jbcc"

    created_at: str = ""
    updated_at: str = ""


# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║  SITE CONDITIONS — Filled by contractor before pricing                      ║
# ╚══════════════════════════════════════════════════════════════════════════════╝

class SiteConditions(BaseModel):
    """
    Site-specific factors that affect pricing but aren't on any drawing.
    Contractor fills this in after extraction, before pricing.
    Each factor produces a multiplier on the relevant BQ section.
    """
    # Project type
    is_renovation: bool = False            # True = existing building, chasing walls, etc.
    is_new_build: bool = True
    is_occupied: bool = False              # Working in occupied building = slower

    # Access conditions
    access_difficulty: str = "normal"      # "easy", "normal", "difficult", "restricted"
    # easy = open site, ground floor → ×0.95
    # normal = standard access → ×1.00
    # difficult = narrow passages, multi-story, no lift → ×1.20
    # restricted = security clearance, limited hours → ×1.35

    # Working at height
    needs_scaffolding: bool = False        # ×1.15 on labour if True
    max_working_height_m: float = 3.0

    # Trenching conditions
    soil_type: str = "normal"              # "soft", "normal", "hard_clay", "rock"
    # soft → ×0.80 on trenching
    # normal → ×1.00
    # hard_clay → ×1.40
    # rock → ×2.50

    # Existing conditions (renovation)
    has_asbestos_risk: bool = False         # Requires specialist removal
    existing_wiring_condition: str = "unknown"  # "good", "fair", "poor", "unknown"
    walls_brick_or_dry: str = "brick"      # "brick" (chasing), "dry_wall" (easier), "concrete" (hardest)

    # Logistics
    distance_from_base_km: float = 0.0
    distance_from_supplier_km: float = 0.0
    site_storage_available: bool = True
    security_required: bool = False

    # Timeline
    is_rush_job: bool = False              # ×1.25 on labour
    estimated_duration_days: int = 0       # Contractor's own estimate
    working_hours: str = "standard"        # "standard" (07-17), "extended", "night_work"

    # Additional notes
    notes: str = ""


# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║  SYSTEM PARAMETERS — v4.5 Electrical system specs                            ║
# ╚══════════════════════════════════════════════════════════════════════════════╝

class SystemParameters(BaseModel):
    """
    v4.5 - Electrical system parameters extracted from SLD drawings.
    Critical for breaker coordination, cable sizing, and fault calculations.
    """
    # Voltage
    voltage_v: int = 400                        # System voltage (230V single, 400V three-phase)
    voltage_single_phase_v: int = 230           # Single-phase voltage

    # Phase configuration
    phases: str = "3PH+N+E"                     # "1PH+N+E", "3PH+N+E", "3PH+N"
    num_phases: int = 3                         # 1 or 3

    # Frequency
    frequency_hz: int = 50                      # SA = 50Hz

    # Fault levels (kA)
    fault_level_main_ka: float = 15.0           # Main board fault level
    fault_level_sub_ka: float = 6.0             # Sub-board fault level (smaller boards)

    # Standards
    standard: str = "SANS 10142-1"              # Primary standard
    additional_standards: List[str] = Field(default_factory=list)  # OHS Act, NRS 034, etc.

    # Phase designation convention
    phase_designation: str = "RWB"              # "RWB" (Red/White/Blue) or "L1L2L3"

    # Confidence
    confidence: ItemConfidence = ItemConfidence.INFERRED

    @computed_field
    @property
    def is_three_phase(self) -> bool:
        return self.num_phases == 3 or "3PH" in self.phases


    @computed_field
    @property
    def labour_multiplier(self) -> float:
        """Combined labour adjustment factor."""
        m = 1.0
        if self.is_renovation:
            m *= 1.30
        if self.is_occupied:
            m *= 1.15
        access_map = {"easy": 0.95, "normal": 1.0, "difficult": 1.20, "restricted": 1.35}
        m *= access_map.get(self.access_difficulty, 1.0)
        if self.needs_scaffolding:
            m *= 1.15
        if self.is_rush_job:
            m *= 1.25
        if self.walls_brick_or_dry == "concrete":
            m *= 1.20
        return round(m, 2)

    @computed_field
    @property
    def trenching_multiplier(self) -> float:
        soil_map = {"soft": 0.80, "normal": 1.0, "hard_clay": 1.40, "rock": 2.50}
        return soil_map.get(self.soil_type, 1.0)

    @computed_field
    @property
    def transport_cost_zar(self) -> float:
        """Estimated transport based on distance. 2 trips minimum."""
        if self.distance_from_base_km <= 50:
            return 5000.0
        elif self.distance_from_base_km <= 100:
            return 8000.0
        else:
            return 8000.0 + (self.distance_from_base_km - 100) * 12.0


# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║  CORRECTION LOG — Tracks contractor edits for accuracy learning             ║
# ╚══════════════════════════════════════════════════════════════════════════════╝

class CorrectionEntry(BaseModel):
    """A single correction made by the contractor during the REVIEW stage."""
    field_path: str = ""                   # e.g. "blocks.Pool Block.rooms.Male Changing.fixtures.vapor_proof_2x18w"
    original_value: Any = None             # What the AI extracted
    corrected_value: Any = None            # What the contractor changed it to
    item_type: str = ""                    # "fixture_count", "cable_size", "breaker_rating", "cable_length", etc.
    building_block: str = ""
    page_source: str = ""                  # Which drawing page the data came from
    timestamp: str = ""


class CorrectionLog(BaseModel):
    """
    All corrections made by the contractor on a single project.
    Stored after review for future prompt improvement.
    """
    project_name: str = ""
    corrections: List[CorrectionEntry] = Field(default_factory=list)
    total_ai_items: int = 0               # How many items the AI extracted
    total_corrected: int = 0              # How many the contractor changed
    total_added: int = 0                  # Items contractor added that AI missed
    total_removed: int = 0                # Items AI hallucinated that contractor deleted

    @computed_field
    @property
    def accuracy_pct(self) -> float:
        """What % of AI extractions were correct (not changed by contractor)."""
        if self.total_ai_items == 0:
            return 0.0
        correct = self.total_ai_items - self.total_corrected - self.total_removed
        return round(max(0, correct) / self.total_ai_items * 100, 1)


# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║  LEGEND & SYMBOL MAPPING                                                    ║
# ╚══════════════════════════════════════════════════════════════════════════════╝

class LegendItem(BaseModel):
    symbol_id: str = ""
    category: str = ""
    description: str = ""
    short_name: str = ""
    wattage_w: float = 0.0
    mounting_height_mm: int = 0
    ip_rating: str = ""
    notes: str = ""


class BuildingLegend(BaseModel):
    block_name: str = ""
    switches: List[LegendItem] = Field(default_factory=list)
    sockets: List[LegendItem] = Field(default_factory=list)
    lights: List[LegendItem] = Field(default_factory=list)
    equipment: List[LegendItem] = Field(default_factory=list)
    containment: List[LegendItem] = Field(default_factory=list)


# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║  PAGE & DOCUMENT MODELS                                                     ║
# ╚══════════════════════════════════════════════════════════════════════════════╝

class PageInfo(BaseModel):
    page_number: int = 0
    page_type: PageType = PageType.UNKNOWN
    image_base64: str = ""
    text_content: str = ""
    width_px: int = 0
    height_px: int = 0
    classification_confidence: float = 0.0
    drawing_number: str = ""
    drawing_title: str = ""
    building_block: str = ""
    source_document: str = ""


class DocumentInfo(BaseModel):
    filename: str = ""
    mime_type: str = ""
    num_pages: int = 0
    file_size_bytes: int = 0
    pages: List[PageInfo] = Field(default_factory=list)


class DocumentSet(BaseModel):
    documents: List[DocumentInfo] = Field(default_factory=list)
    total_pages: int = 0
    num_register_pages: int = 0
    num_sld_pages: int = 0
    num_lighting_pages: int = 0
    num_plugs_pages: int = 0
    num_outside_light_pages: int = 0
    num_photo_pages: int = 0
    num_other_pages: int = 0
    building_blocks_detected: List[str] = Field(default_factory=list)

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

class ProjectMetadata(BaseModel):
    project_name: str = ""
    client_name: str = ""
    consultant_name: str = ""
    contractor_name: str = ""
    drawing_numbers: List[str] = Field(default_factory=list)
    revision: Optional[int] = None
    date: str = ""
    standard: str = "SANS 10142-1"
    description: str = ""
    building_blocks: List[str] = Field(default_factory=list)

    # v4.5 - System parameters
    system_parameters: Optional[SystemParameters] = None

    # v4.5 - Enhanced contact details
    client_address: str = ""
    client_tel: str = ""
    client_email: str = ""
    consultant_address: str = ""
    consultant_tel: str = ""
    consultant_email: str = ""
    site_address: str = ""


class Circuit(BaseModel):
    id: str = ""
    type: str = "power"
    description: str = ""
    wattage_w: float = 0.0
    wattage_formula: str = ""
    cable_size_mm2: float = 2.5
    cable_cores: int = 3
    cable_type: str = "GP WIRE"
    breaker_a: int = 20
    breaker_poles: int = 1
    num_points: int = 0
    is_spare: bool = False
    has_isolator: bool = False
    isolator_rating_a: int = 0
    has_vsd: bool = False
    feeds_board: Optional[str] = None
    feed_cable_length_m: float = 0.0
    confidence: ItemConfidence = ItemConfidence.EXTRACTED   # NEW: per-item confidence
    page_source: str = ""

    # v4.3 - VSD and starter fields for pump/motor circuits
    vsd_rating_kw: float = 0.0               # VSD power rating in kW
    starter_type: str = ""                   # "vsd", "dol", "star_delta", "soft_starter"

    # v4.3 - Day/night switch control
    has_day_night: bool = False              # Circuit has day/night switch
    has_bypass: bool = False                 # Day/night has bypass switch
    controlled_circuits: List[str] = Field(default_factory=list)  # IDs of circuits controlled

    # v4.3 - ISO circuit equipment type
    equipment_type: str = ""                 # For ISO circuits: "geyser", "ac", "pump", etc.

    # v4.5 - Breaker type (affects pricing significantly)
    breaker_type: str = "mcb"                # "mcb", "mccb", "acb", "fuse", "rcbo"

    # v4.5 - Phase designation for 3-phase load balancing
    phase: str = ""                          # "R1", "W1", "B1", "R2", "W2", "B2", etc.

    # v4.5 - Cable material
    cable_material: str = "copper"           # "copper" or "aluminium"

    # v4.5 - Overload relay for motor circuits
    has_overload_relay: bool = False


class DistributionBoard(BaseModel):
    name: str = ""
    description: str = ""
    location: str = ""
    building_block: str = ""
    supply_from: str = ""
    supply_cable: str = ""
    supply_cable_size_mm2: float = 0.0
    supply_cable_cores: int = 4
    supply_cable_type: str = ""
    supply_cable_length_m: float = 0.0
    main_breaker_a: int = 0
    earth_leakage: bool = False
    earth_leakage_rating_a: int = 0
    surge_protection: bool = False
    circuits: List[Circuit] = Field(default_factory=list)
    spare_ways: int = 0
    total_wattage_w: float = 0.0
    phase: PhaseConfig = PhaseConfig.THREE
    voltage_v: int = 400
    fault_level_ka: float = 15.0
    sld_drawing_number: str = ""
    confidence: ItemConfidence = ItemConfidence.EXTRACTED
    page_source: str = ""

    # v4.5 - Enhanced main breaker info
    main_breaker_type: str = "mccb"          # "mcb", "mccb", "acb" - affects pricing
    main_breaker_poles: int = 4              # 3P, 3P+N, 4P

    # v4.5 - Cable material
    supply_cable_material: str = "copper"    # "copper" or "aluminium"

    # v4.5 - Earth leakage details
    earth_leakage_ma: int = 30               # 30mA personal, 100mA fire, 300mA equipment
    earth_leakage_type: str = "rcd"          # "rcd", "rcbo", "elcb"

    # v4.5 - Surge protection details
    surge_type: str = ""                     # "type1", "type2", "type3", "type1+2"

    # v4.5 - Board status
    status: str = "new"                      # "existing", "new", "proposed"

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


class SupplyPoint(BaseModel):
    """
    Power supply point - where electrical power enters the installation.
    v4.5: Enhanced to support transformers, generators, solar, UPS sources.
    """
    name: str = ""
    type: str = "eskom_kiosk"                # See below for types
    # Types: "eskom_kiosk", "mini_sub", "transformer", "generator", "solar_inverter",
    #        "ups", "grid_supply", "mdb_feed", "existing_db"

    # Rating
    main_breaker_a: int = 0
    rating_kva: float = 0.0                  # Transformer/generator kVA rating

    # Voltage
    voltage_primary_v: int = 11000           # Primary voltage (for transformers)
    voltage_secondary_v: int = 400           # Secondary voltage / supply voltage

    # Phase configuration
    phases: str = "3PH+N+E"                  # "1PH+N+E", "3PH+N+E"

    # Cable to first DB
    cable_to_first_db: str = ""
    cable_size_mm2: float = 0.0
    cable_cores: int = 4
    cable_type: str = "PVC SWA PVC"
    cable_material: str = "copper"
    cable_length_m: float = 0.0

    # Metering
    has_meter: bool = True
    meter_type: str = "ct"                   # "direct", "ct", "prepaid"
    meter_location: str = ""

    # Destination
    feeds_db: str = ""
    building_block: str = ""

    # Status
    status: str = "new"                      # "existing", "new", "proposed"

    # Fault level
    fault_level_ka: float = 15.0             # Prospective fault current

    # Notes and confidence
    notes: str = ""
    confidence: ItemConfidence = ItemConfidence.EXTRACTED


class FixtureCounts(BaseModel):
    """All fixture types — 14 lights (v4.4), 8 sockets, 7 switches, equipment."""
    # === LIGHTS ===
    recessed_led_600x1200: int = 0
    surface_mount_led_18w: int = 0
    flood_light_30w: int = 0
    flood_light_200w: int = 0
    downlight_led_6w: int = 0
    vapor_proof_2x24w: int = 0
    vapor_proof_2x18w: int = 0
    prismatic_2x18w: int = 0
    bulkhead_26w: int = 0
    bulkhead_24w: int = 0
    fluorescent_50w_5ft: int = 0
    pole_light_60w: int = 0

    # v4.4 - Pool lighting types (from Wedela Lighting & Plugs PDF)
    pool_flood_light: int = 0        # FL - pool area flood light (150W)
    pool_underwater_light: int = 0   # PS - underwater pool light (35W)

    # === POWER SOCKETS ===
    double_socket_300: int = 0
    single_socket_300: int = 0
    double_socket_1100: int = 0
    single_socket_1100: int = 0
    double_socket_waterproof: int = 0
    double_socket_ceiling: int = 0
    data_points_cat6: int = 0
    floor_box: int = 0

    # === SWITCHES ===
    switch_1lever_1way: int = 0
    switch_2lever_1way: int = 0
    switch_1lever_2way: int = 0
    day_night_switch: int = 0
    isolator_30a: int = 0
    isolator_20a: int = 0
    master_switch: int = 0

    # === EQUIPMENT ===
    ac_units: int = 0
    geyser_50l: int = 0
    geyser_100l: int = 0
    geyser_150l: int = 0
    geyser_200l: int = 0

    @computed_field
    @property
    def total_lights(self) -> int:
        return (self.recessed_led_600x1200 + self.surface_mount_led_18w +
                self.flood_light_30w + self.flood_light_200w + self.downlight_led_6w +
                self.vapor_proof_2x24w + self.vapor_proof_2x18w + self.prismatic_2x18w +
                self.bulkhead_26w + self.bulkhead_24w + self.fluorescent_50w_5ft +
                self.pole_light_60w + self.pool_flood_light + self.pool_underwater_light)

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
                self.fluorescent_50w_5ft * 50 + self.pole_light_60w * 60 +
                self.pool_flood_light * 150 + self.pool_underwater_light * 35)

    @computed_field
    @property
    def total_points(self) -> int:
        """Total electrical points (lights + sockets + switches). Used for labour calc."""
        return self.total_lights + self.total_sockets + self.total_switches


class Room(BaseModel):
    name: str = ""
    room_number: int = 0
    type: str = ""
    area_m2: float = 0.0
    floor: str = ""
    building_block: str = ""
    fixtures: FixtureCounts = Field(default_factory=FixtureCounts)
    circuit_refs: List[str] = Field(default_factory=list)
    is_wet_area: bool = False
    has_ac: bool = False
    has_geyser: bool = False
    confidence: ItemConfidence = ItemConfidence.EXTRACTED
    notes: List[str] = Field(default_factory=list)
    page_source: str = ""


class HeavyEquipment(BaseModel):
    """
    Heavy equipment that requires dedicated circuits.
    v4.5: Expanded to support all equipment types from universal schema.
    """
    name: str = ""
    type: str = ""                           # See EquipmentType enum for all supported types
    rating_kw: float = 0.0
    rating_kva: float = 0.0                  # For transformers, UPS, generators
    cable_size_mm2: float = 4.0
    cable_type: str = "PVC SWA PVC"
    cable_length_m: float = 0.0
    breaker_a: int = 32
    has_vsd: bool = False
    has_dol: bool = False
    isolator_a: int = 0
    fed_from_db: str = ""
    building_block: str = ""
    qty: int = 1
    confidence: ItemConfidence = ItemConfidence.EXTRACTED
    notes: str = ""

    # v4.3 - Circuit reference and starter type
    circuit_ref: str = ""                    # Circuit ID linking back to DB (e.g., "PP1", "HP3")
    starter_type: str = ""                   # "vsd", "dol", "star_delta", "soft_starter", "contactor", "direct"
    vsd_rating_kw: float = 0.0               # VSD power rating (when has_vsd=True)

    # v4.5 - Motor protection
    has_overload_relay: bool = False         # Thermal overload relay for motor protection
    overload_setting_a: float = 0.0          # Overload relay current setting

    # v4.5 - Enhanced breaker info
    breaker_type: str = "mcb"                # "mcb", "mccb", "acb", "fuse"
    breaker_poles: int = 3                   # 1, 2, or 3 poles

    # v4.5 - Cable material
    cable_material: str = "copper"           # "copper" or "aluminium"

    # v4.5 - Equipment status
    status: str = "new"                      # "existing", "new", "proposed", "remove"

    # v4.5 - Voltage (for transformers, inverters)
    voltage_primary_v: int = 0               # Primary voltage (transformers)
    voltage_secondary_v: int = 0             # Secondary voltage (transformers)

    # v4.5 - Backup power specific
    backup_runtime_hours: float = 0.0        # For UPS/battery systems
    fuel_type: str = ""                      # For generators: "diesel", "petrol", "gas"

    # v4.5 - EV charger specific
    ev_charger_type: str = ""                # "ac_type2", "dc_ccs", "dc_chademo"
    ev_charger_kw: float = 0.0               # Charger power rating


class CableContainment(BaseModel):
    type: str = ""
    description: str = ""
    size_mm: int = 0
    material: str = ""
    mounting: str = ""
    estimated_length_m: float = 0.0
    building_block: str = ""
    confidence: ItemConfidence = ItemConfidence.ESTIMATED
    notes: str = ""


class SiteCableRun(BaseModel):
    from_point: str = ""
    to_point: str = ""
    cable_spec: str = ""
    cable_size_mm2: float = 0.0
    cable_cores: int = 4
    cable_type: str = "PVC SWA PVC"
    length_m: float = 0.0
    is_underground: bool = True
    needs_trenching: bool = True
    confidence: ItemConfidence = ItemConfidence.EXTRACTED  # lengths from drawing = high confidence
    notes: str = ""

    # v4.5 - Enhanced cable attributes
    material: str = "copper"                 # "copper" or "aluminium"
    is_armoured: bool = True                 # SWA = Steel Wire Armoured
    installation_method: str = "underground" # underground, trunking, conduit, cable_tray, etc.

    # v4.5 - Trench details (when underground)
    trench_depth_mm: int = 600               # Standard depth for LV cables
    trench_width_mm: int = 300               # Standard trench width
    requires_warning_tape: bool = True       # Underground cable warning tape
    requires_sand_bedding: bool = True       # Sand bed for cable protection


class UndergroundSleeve(BaseModel):
    size_mm: int = 0
    qty: int = 1
    purpose: str = ""
    building_block: str = ""


class BuildingBlock(BaseModel):
    name: str = ""
    description: str = ""
    total_area_m2: float = 0.0
    num_floors: int = 1
    distribution_boards: List[DistributionBoard] = Field(default_factory=list)
    rooms: List[Room] = Field(default_factory=list)
    heavy_equipment: List[HeavyEquipment] = Field(default_factory=list)
    cable_containment: List[CableContainment] = Field(default_factory=list)
    legend: Optional[BuildingLegend] = None
    supply_from: str = ""
    supply_cable: str = ""
    sld_drawings: List[str] = Field(default_factory=list)
    layout_drawings: List[str] = Field(default_factory=list)

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

    @computed_field
    @property
    def total_points(self) -> int:
        return sum(r.fixtures.total_points for r in self.rooms)


class ExtractionResult(BaseModel):
    extraction_mode: ExtractionMode = ExtractionMode.ESTIMATION
    metadata: ProjectMetadata = Field(default_factory=ProjectMetadata)
    building_blocks: List[BuildingBlock] = Field(default_factory=list)
    supply_points: List[SupplyPoint] = Field(default_factory=list)
    site_cable_runs: List[SiteCableRun] = Field(default_factory=list)
    underground_sleeves: List[UndergroundSleeve] = Field(default_factory=list)
    outside_lights: Optional[FixtureCounts] = None

    # NEW: track review state
    review_completed: bool = False
    corrections: Optional[CorrectionLog] = None

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

    defects: List[Any] = Field(default_factory=list)   # Maintenance/COC mode

    pages_processed: int = 0
    pages_with_data: int = 0
    extraction_warnings: List[str] = Field(default_factory=list)
    missing_data: List[str] = Field(default_factory=list)

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
    def total_points(self) -> int:
        return sum(b.total_points for b in self.building_blocks)


# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║  VALIDATION MODELS                                                          ║
# ╚══════════════════════════════════════════════════════════════════════════════╝

class CircuitRoomLink(BaseModel):
    circuit_id: str = ""
    db_name: str = ""
    circuit_label: str = ""
    rooms_served: List[str] = Field(default_factory=list)
    sld_wattage_w: float = 0.0
    layout_wattage_w: float = 0.0
    sld_points: int = 0
    layout_points: int = 0
    match_status: str = "unmatched"
    conflict_notes: str = ""


class CrossReferenceResult(BaseModel):
    links: List[CircuitRoomLink] = Field(default_factory=list)
    matched: int = 0
    partial: int = 0
    conflicts: int = 0
    unmatched_sld: int = 0
    unmatched_layout: int = 0


class ValidationFlag(BaseModel):
    rule_name: str = ""
    message: str = ""
    severity: Severity = Severity.WARNING
    passed: bool = True
    auto_corrected: bool = False
    corrected_value: str = ""
    related_circuit: str = ""
    related_board: str = ""
    related_block: str = ""
    standard_ref: str = "SANS 10142-1"


class ValidationResult(BaseModel):
    flags: List[ValidationFlag] = Field(default_factory=list)
    cross_references: Optional[CrossReferenceResult] = None
    passed: int = 0
    failed: int = 0
    warnings: int = 0
    auto_corrections: int = 0
    compliance_score: float = 100.0
    corrections_applied: List[str] = Field(default_factory=list)

    @computed_field
    @property
    def has_critical_issues(self) -> bool:
        return any(f.severity == Severity.CRITICAL and not f.passed for f in self.flags)


# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║  PRICING MODELS — Dual output: quantities + estimated                       ║
# ╚══════════════════════════════════════════════════════════════════════════════╝

class BQSection(str, Enum):
    """
    v4.2 BoQ Sections (11 sections A-K) per specification.

    Changes from v4.1:
    - Removed SUPPLY (merged into DISTRIBUTION)
    - Split SOCKETS into SWITCHES (E) and SOCKETS (F)
    - Removed EQUIPMENT (AC now has dedicated section G)
    - Removed DEDICATED (merged into relevant sections)
    - Added EXTERNAL (H) for external/solar work
    - Added EARTHING (I) for earthing & bonding
    - Removed COMPLIANCE (now part of relevant sections)
    - SITE_WORKS → TESTING (J)
    - LABOUR/PROVISIONAL → PRELIMS (K)
    """
    DISTRIBUTION = "A - Distribution Boards & Protection"
    CABLES = "B - Cables & Wiring"
    CONTAINMENT = "C - Cable Containment"
    LIGHTS = "D - Lighting"
    SWITCHES = "E - Switches & Controls"
    SOCKETS = "F - Power Sockets"
    AC_ELECTRICAL = "G - Air Conditioning Electrical"
    EXTERNAL = "H - External & Solar"
    EARTHING = "I - Earthing & Bonding"
    TESTING = "J - Testing & Commissioning"
    PRELIMS = "K - Preliminaries & General"


class BQLineItem(BaseModel):
    """A single BQ line. unit_price and total may be 0.0 in quantity-only mode."""
    item_no: int = 0
    section: BQSection = BQSection.CABLES
    category: str = ""
    description: str = ""
    unit: str = "each"
    qty: float = 1.0
    unit_price_zar: float = 0.0          # 0.0 = contractor fills this in
    total_zar: float = 0.0               # 0.0 = formula in Excel: =qty × unit_price
    source: ItemConfidence = ItemConfidence.EXTRACTED
    building_block: str = ""
    notes: str = ""
    is_rate_only: bool = False            # True = contractor must supply rate


class BlockPricingSummary(BaseModel):
    block_name: str = ""
    item_count: int = 0
    subtotal_materials_zar: float = 0.0
    subtotal_labour_zar: float = 0.0
    subtotal_equipment_zar: float = 0.0
    subtotal_site_works_zar: float = 0.0
    block_total_zar: float = 0.0


class PricingResult(BaseModel):
    """
    Dual output:
    - quantity_bq: Items with descriptions + quantities, unit_price=0 (contractor fills in)
    - estimated_bq: Same items with default prices filled in (ballpark only)
    """
    # Primary output: quantity-only BQ (THE deliverable)
    quantity_bq: List[BQLineItem] = Field(default_factory=list)

    # Secondary output: estimated BQ (ballpark reference)
    estimated_bq: List[BQLineItem] = Field(default_factory=list)

    # Per-block summaries (from estimated BQ)
    block_summaries: List[BlockPricingSummary] = Field(default_factory=list)

    # Estimated project totals (from estimated BQ — clearly labelled "ESTIMATE")
    estimate_subtotal_zar: float = 0.0
    estimate_contingency_zar: float = 0.0
    estimate_margin_zar: float = 0.0
    estimate_total_excl_vat_zar: float = 0.0
    estimate_vat_zar: float = 0.0
    estimate_total_incl_vat_zar: float = 0.0

    # Adjustment factors applied
    site_labour_multiplier: float = 1.0
    site_trenching_multiplier: float = 1.0
    contractor_markup_pct: float = 20.0
    contingency_pct: float = 5.0

    # Payment schedule (based on estimate)
    payment_terms: str = "40/40/20"
    deposit_zar: float = 0.0
    second_payment_zar: float = 0.0
    final_payment_zar: float = 0.0

    # Quality
    total_items: int = 0
    items_from_extraction: int = 0
    items_estimated: int = 0
    items_compliance: int = 0
    items_rate_only: int = 0              # Items where contractor must supply rate

    @computed_field
    @property
    def quantity_confidence(self) -> float:
        if self.total_items == 0:
            return 0.0
        return self.items_from_extraction / self.total_items


# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║  PIPELINE RESULT                                                            ║
# ╚══════════════════════════════════════════════════════════════════════════════╝

class StageResult(BaseModel):
    stage: PipelineStage = PipelineStage.INGEST
    success: bool = False
    confidence: float = 0.0
    data: Dict[str, Any] = Field(default_factory=dict)
    model_used: Optional[str] = None
    tokens_used: int = 0
    cost_zar: float = 0.0
    processing_time_ms: int = 0
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)


class PipelineResult(BaseModel):
    """
    Top-level output. 7 stages: INGEST → CLASSIFY → DISCOVER → REVIEW → VALIDATE → PRICE → OUTPUT
    """
    stages: List[StageResult] = Field(default_factory=list)
    success: bool = False

    # Classification
    tier: ServiceTier = ServiceTier.UNKNOWN
    tier_confidence: float = 0.0
    extraction_mode: ExtractionMode = ExtractionMode.ESTIMATION

    # Core results
    document_set: DocumentSet = Field(default_factory=DocumentSet)
    extraction: ExtractionResult = Field(default_factory=ExtractionResult)
    validation: Optional[ValidationResult] = None
    pricing: Optional[PricingResult] = None

    # Contractor inputs
    contractor_profile: Optional[ContractorProfile] = None
    site_conditions: Optional[SiteConditions] = None

    # Aggregates
    overall_confidence: float = 0.0
    total_cost_zar: float = 0.0
    total_tokens: int = 0
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)

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

    @computed_field
    @property
    def review_completed(self) -> bool:
        return self.extraction.review_completed


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
    extracted_data: Dict[str, Any] = Field(default_factory=dict)
    reasoning: Any = None
    warnings: List[str] = Field(default_factory=list)


TIER_DISPLAY = {
    ServiceTier.RESIDENTIAL: {"icon": "🏠", "name": "Residential", "color": "#22C55E", "description": "Houses, flats, domestic"},
    ServiceTier.COMMERCIAL: {"icon": "🏢", "name": "Commercial", "color": "#3B82F6", "description": "Offices, retail, hospitality"},
    ServiceTier.INDUSTRIAL: {"icon": "🏭", "name": "Industrial", "color": "#8B5CF6", "description": "Factories, plants, heavy equipment"},
    ServiceTier.MAINTENANCE: {"icon": "🔧", "name": "Maintenance & COC", "color": "#F59E0B", "description": "Inspections, repairs, DB upgrades"},
    ServiceTier.MIXED: {"icon": "🏗️", "name": "Mixed Use Complex", "color": "#EC4899", "description": "Multi-building project"},
    ServiceTier.UNKNOWN: {"icon": "❓", "name": "Unknown", "color": "#64748b", "description": "Could not determine"},
}


def get_tier_display_info(tier: ServiceTier) -> dict:
    return TIER_DISPLAY.get(tier, TIER_DISPLAY[ServiceTier.UNKNOWN])
