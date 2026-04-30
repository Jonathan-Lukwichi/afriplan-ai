"""
agent.dxf_pipeline.models — data contracts for the DXF pipeline.

Per blueprint §4.2: deterministic outputs, no confidence scores. Every
value here is exact unless ezdxf raised an error.
"""

from __future__ import annotations

from datetime import datetime
from typing import Dict, List, Optional, Tuple

from pydantic import BaseModel, Field

from agent.shared import (
    BillOfQuantities,
    ComplianceFlag,
    ProjectMetadata,
)


# ─── Geometry primitives ──────────────────────────────────────────────

class Point2D(BaseModel):
    x: float
    y: float


class LayerInfo(BaseModel):
    name: str
    color: int = 7
    is_electrical: bool = False
    entity_count: int = 0


class DxfBlock(BaseModel):
    """One INSERT block reference in the model space."""
    block_name: str
    raw_block_name: str          # what ezdxf returned, before any normalisation
    layer: str
    position: Point2D
    rotation_deg: float = 0.0
    fixture_canonical: Optional[str] = None    # mapped name from patterns.py
    fixture_category: Optional[str] = None     # FixtureCategory.value
    recognised: bool = False                   # did we map it?


class DxfText(BaseModel):
    """One TEXT or MTEXT entity."""
    text: str
    layer: str
    position: Point2D
    height: float = 0.0


class DxfPolyline(BaseModel):
    """LINE / LWPOLYLINE / POLYLINE — used for cable run lengths."""
    layer: str
    length_m: float                             # length in metres after unit conversion
    point_count: int
    is_closed: bool = False


class DxfCircle(BaseModel):
    """CIRCLE entity. Layer-0 circles are flagged as potential mis-blocked lights."""
    layer: str
    center: Point2D
    radius: float


# ─── Per-stage outputs ────────────────────────────────────────────────

class DxfIngestResult(BaseModel):
    file_name: str
    file_size_bytes: int
    file_sha256: str
    drawing_units: str = "mm"
    units_to_metre_factor: float = 0.001       # 0.001 if mm, 1.0 if metres
    dxf_version: str = ""
    layer_count: int = 0
    entity_count: int = 0
    open_ok: bool = True
    error: Optional[str] = None


class DxfLayerAnalysis(BaseModel):
    """Result of stage D2 — layer classification and indexing."""
    layers: List[LayerInfo] = Field(default_factory=list)
    electrical_layers: List[str] = Field(default_factory=list)
    building_blocks_detected: List[str] = Field(default_factory=list)
    layers_named_electrical_with_no_blocks: List[str] = Field(default_factory=list)


class DxfExtraction(BaseModel):
    """Result of stage D3 — pure deterministic extraction."""
    layers: List[LayerInfo] = Field(default_factory=list)
    blocks: List[DxfBlock] = Field(default_factory=list)
    texts: List[DxfText] = Field(default_factory=list)
    polylines: List[DxfPolyline] = Field(default_factory=list)
    circles_layer_0: List[DxfCircle] = Field(default_factory=list)

    block_counts_by_type: Dict[str, int] = Field(default_factory=dict)
    raw_block_names_unrecognised: List[str] = Field(default_factory=list)
    fixture_counts_by_category: Dict[str, int] = Field(default_factory=dict)

    total_polyline_length_m: float = 0.0

    extraction_warnings: List[str] = Field(default_factory=list)


class DxfEvaluation(BaseModel):
    """Result of stage D4 — deterministic gate."""

    # Coverage
    total_blocks: int = 0
    recognised_blocks: int = 0
    coverage_score: float = 0.0

    # Baseline regression
    baseline_project: Optional[str] = None
    baseline_mape: Optional[float] = None

    # Compliance
    sans_violations: List[ComplianceFlag] = Field(default_factory=list)
    sans_warnings: List[ComplianceFlag] = Field(default_factory=list)

    # Anomalies
    orphan_layer_0_circles: int = 0
    layers_named_electrical_with_no_blocks: List[str] = Field(default_factory=list)
    suspiciously_long_polylines_m: List[float] = Field(default_factory=list)

    # Gate
    passed: bool = False
    overall_score: float = 0.0
    failure_reasons: List[str] = Field(default_factory=list)


# ─── Top-level run ────────────────────────────────────────────────────

class DxfPipelineRun(BaseModel):
    """End-to-end output of one DXF pipeline invocation."""

    run_id: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    input_file: str
    input_sha256: str
    drawing_units: str

    project: ProjectMetadata = Field(default_factory=ProjectMetadata)
    ingest: DxfIngestResult
    layer_analysis: DxfLayerAnalysis
    extraction: DxfExtraction
    evaluation: DxfEvaluation
    boq: Optional[BillOfQuantities] = None

    cost_zar: float = 0.0          # always 0 for the deterministic pipeline
    duration_s: float = 0.0
    success: bool = False
    error: Optional[str] = None
