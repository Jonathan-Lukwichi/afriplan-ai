"""
agent.pdf_pipeline.models — data contracts for the PDF pipeline.

Per blueprint §3.2: confidence-scored extraction (because LLMs are
stochastic), with explicit cross-page consistency and baseline-regression
metrics built into the evaluation step.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from agent.shared import (
    BillOfQuantities,
    ComplianceFlag,
    ItemConfidence,
    ProjectMetadata,
)


# ─── Page-type taxonomy ───────────────────────────────────────────────

class PageType(str, Enum):
    REGISTER = "register"
    SLD = "sld"
    LIGHTING_LAYOUT = "lighting_layout"
    PLUGS_LAYOUT = "plugs_layout"
    SCHEDULE = "schedule"
    NOTES = "notes"
    UNKNOWN = "unknown"


class PageClassification(BaseModel):
    page_index: int                       # 0-based
    page_type: PageType
    confidence: float = 0.0
    rationale: str = ""


# ─── Per-domain extracted shapes ──────────────────────────────────────

class CircuitRow(BaseModel):
    """One row in a DB schedule / register."""
    circuit_id: str = ""
    description: str = ""
    breaker_a: int = 0
    breaker_poles: int = 1
    cable_size_mm2: float = 0.0
    cable_cores: int = 0
    num_points: int = 0
    is_spare: bool = False
    notes: str = ""


class DistributionBoard(BaseModel):
    """One DB extracted from an SLD or schedule page."""
    name: str = ""
    location: str = ""
    main_breaker_a: int = 0
    phases: int = 3
    voltage_v: int = 400
    elcb_present: bool = False
    surge_protection: bool = False
    circuits: List[CircuitRow] = Field(default_factory=list)
    page_source: int = -1                 # PDF page index where this DB was extracted


class CircuitSchedule(BaseModel):
    """Standalone schedule table (independent of DB SLD)."""
    title: str = ""
    page_source: int = -1
    rows: List[CircuitRow] = Field(default_factory=list)


class FixtureCounts(BaseModel):
    """Per-room fixture counts read from a layout drawing."""
    room_name: str = ""
    room_type: str = ""
    area_m2: float = 0.0

    # Lighting
    downlights: int = 0
    panel_lights: int = 0
    bulkheads: int = 0
    floodlights: int = 0
    emergency_lights: int = 0
    exit_signs: int = 0
    pool_flood_light: int = 0
    pool_underwater_light: int = 0

    # Outlets
    double_sockets: int = 0
    single_sockets: int = 0
    waterproof_sockets: int = 0
    floor_sockets: int = 0
    data_outlets: int = 0

    # Switches
    switches_1lever: int = 0
    switches_2lever: int = 0
    switches_3lever: int = 0
    isolators: int = 0
    day_night_switches: int = 0

    page_source: int = -1


# ─── Top-level extraction artefact ────────────────────────────────────

class PdfExtraction(BaseModel):
    """Aggregate of everything extracted from the PDF."""

    project: ProjectMetadata = Field(default_factory=ProjectMetadata)
    distribution_boards: List[DistributionBoard] = Field(default_factory=list)
    schedules: List[CircuitSchedule] = Field(default_factory=list)
    fixtures_per_room: Dict[str, FixtureCounts] = Field(default_factory=dict)
    legends: Dict[str, str] = Field(default_factory=dict)
    notes: List[str] = Field(default_factory=list)

    # Confidence diagnostics
    per_field_confidence: Dict[str, float] = Field(default_factory=dict)
    extraction_warnings: List[str] = Field(default_factory=list)

    # Provenance
    pages_processed: List[PageClassification] = Field(default_factory=list)


# ─── Cross-page consistency check ─────────────────────────────────────

class CrossPageDisagreement(BaseModel):
    """When the same value appears differently on two pages."""
    value_kind: str            # e.g. "DB-PFA main_breaker_a"
    page_a: int
    value_a: Any
    page_b: int
    value_b: Any
    severity: str = "warning"  # 'critical' | 'warning' | 'info'


class PdfEvaluation(BaseModel):
    """Result of the LLM-aware evaluation gate."""

    # 1. Confidence aggregation
    mean_confidence: float = 0.0
    min_confidence: float = 0.0
    low_confidence_fields: List[str] = Field(default_factory=list)

    # 2. Cross-page consistency
    cross_page_agreements: int = 0
    cross_page_disagreements: List[CrossPageDisagreement] = Field(default_factory=list)
    consistency_score: float = 1.0

    # 3. Baseline regression
    baseline_project: Optional[str] = None
    baseline_mape: Optional[float] = None

    # 4. SANS compliance
    sans_violations: List[ComplianceFlag] = Field(default_factory=list)
    sans_warnings: List[ComplianceFlag] = Field(default_factory=list)

    # Composite gate
    passed: bool = False
    overall_score: float = 0.0
    failure_reasons: List[str] = Field(default_factory=list)


# ─── Cost / token telemetry ───────────────────────────────────────────

class StageCost(BaseModel):
    stage_name: str
    model_id: str = ""
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_tokens: int = 0
    cache_write_tokens: int = 0
    cost_zar: float = 0.0
    duration_s: float = 0.0
    retry_count: int = 0


# ─── Top-level run object ─────────────────────────────────────────────

class PdfPipelineRun(BaseModel):
    """End-to-end output of one PDF pipeline invocation."""

    run_id: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    input_file: str
    input_sha256: str
    page_count: int

    extraction: PdfExtraction
    evaluation: PdfEvaluation
    boq: Optional[BillOfQuantities] = None

    stage_costs: List[StageCost] = Field(default_factory=list)
    cost_zar: float = 0.0
    duration_s: float = 0.0
    success: bool = False
    error: Optional[str] = None
