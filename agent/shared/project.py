"""
Project metadata + contractor profile + site conditions.

These describe the project context (who, where, what) and the
contractor's pricing preferences. They are inputs to either pipeline
and they are not produced by extraction.
"""

from __future__ import annotations

from enum import Enum
from typing import Dict, List, Optional

from pydantic import BaseModel, Field, computed_field


# ─── Electrical-system enums (used by either pipeline) ────────────────

class PhaseConfig(str, Enum):
    SINGLE = "1PH"
    THREE = "3PH"


class BreakerType(str, Enum):
    MCB = "mcb"
    MCCB = "mccb"
    ACB = "acb"
    FUSE = "fuse"
    RCBO = "rcbo"
    UNKNOWN = "unknown"


class CableMaterial(str, Enum):
    COPPER = "copper"
    ALUMINIUM = "aluminium"
    UNKNOWN = "unknown"


class InstallationMethod(str, Enum):
    UNDERGROUND = "underground"
    BURIED_DIRECT = "buried_direct"
    TRUNKING = "trunking"
    CONDUIT = "conduit"
    CABLE_TRAY = "cable_tray"
    CABLE_LADDER = "cable_ladder"
    WALL_MOUNTED = "wall_mounted"
    CEILING_VOID = "ceiling_void"
    UNKNOWN = "unknown"


class EquipmentStatus(str, Enum):
    EXISTING = "existing"
    NEW = "new"
    REPLACE = "replace"
    REMOVE = "remove"
    UNKNOWN = "unknown"


# ─── System parameters (voltage, fault levels, phase) ─────────────────

class SystemParameters(BaseModel):
    """Electrical system parameters extracted from drawings."""
    voltage: int = 400                        # 230 (1PH) or 400 (3PH)
    phases: PhaseConfig = PhaseConfig.THREE
    frequency_hz: int = 50
    fault_level_ka: float = 15.0
    earthing_system: str = "TN-S"             # TN-S, TN-C-S, TT, IT
    standard: str = "SANS 10142-1:2017"


# ─── Project metadata ─────────────────────────────────────────────────

class ProjectMetadata(BaseModel):
    """Identifies the project. Filled from title block or contractor input."""
    project_name: str = ""
    client_name: str = ""
    consultant_name: str = ""
    contractor_name: str = ""

    drawing_numbers: List[str] = Field(default_factory=list)
    revision: Optional[int] = None
    date: str = ""
    standard: str = "SANS 10142-1:2017"
    description: str = ""

    # Multi-block projects (e.g. Wedela has 4 blocks)
    building_blocks: List[str] = Field(default_factory=list)

    # Optional system parameters
    system_parameters: Optional[SystemParameters] = None

    # Contact details
    client_address: str = ""
    client_tel: str = ""
    client_email: str = ""
    consultant_address: str = ""
    consultant_tel: str = ""
    consultant_email: str = ""
    site_address: str = ""


# ─── Contractor profile ───────────────────────────────────────────────

class LabourRates(BaseModel):
    """Per-trade daily rates in ZAR. Contractor sets once, reused per project."""
    electrician_daily_zar: float = 1800.0
    assistant_daily_zar: float = 950.0
    foreman_daily_zar: float = 2500.0
    team_size_electricians: int = 2
    team_size_assistants: int = 2
    travel_rate_per_km_zar: float = 5.50

    @computed_field
    @property
    def team_daily_rate_zar(self) -> float:
        return (
            self.electrician_daily_zar * self.team_size_electricians
            + self.assistant_daily_zar * self.team_size_assistants
        )


class ContractorProfile(BaseModel):
    """
    Saved contractor preferences. Used to personalise BQ pricing
    instead of generic SA defaults.
    """
    company_name: str = ""
    registration_number: str = ""
    contact_name: str = ""
    contact_phone: str = ""
    contact_email: str = ""
    physical_address: str = ""
    vat_number: str = ""

    # Financial defaults
    markup_pct: float = 20.0
    contingency_pct: float = 5.0
    vat_pct: float = 15.0
    payment_terms: str = "40/40/20"

    labour_rates: LabourRates = Field(default_factory=LabourRates)

    preferred_supplier: str = ""
    custom_prices: Dict[str, float] = Field(default_factory=dict)

    base_location: str = ""
    max_travel_km: int = 100

    bq_format: str = "detailed"

    created_at: str = ""
    updated_at: str = ""


# ─── Site conditions ──────────────────────────────────────────────────

class SiteConditions(BaseModel):
    """
    Site factors that affect pricing but aren't on any drawing.
    Filled in by the contractor; multiplies relevant BQ sections.
    """
    is_renovation: bool = False
    is_new_build: bool = True
    is_occupied: bool = False

    access_difficulty: str = "normal"     # easy | normal | difficult | restricted

    needs_scaffolding: bool = False
    max_working_height_m: float = 3.0

    soil_type: str = "normal"             # soft | normal | hard_clay | rock

    has_asbestos_risk: bool = False
    existing_wiring_condition: str = "unknown"
    walls_brick_or_dry: str = "brick"

    distance_from_base_km: float = 0.0
    distance_from_supplier_km: float = 0.0
    site_storage_available: bool = True
    security_required: bool = False

    is_rush_job: bool = False
    estimated_duration_days: int = 0
    working_hours: str = "standard"

    notes: str = ""
