"""
v2 DXF estimator passes — read a CAD file like an electrical estimator.

    Pass 1  isolate       electrical layers only (no walls/furniture)
    Pass 2  recognise     blocks + geometry symbols + circuit tags
    Pass 3  circuits       circuit → DB → points map
    Pass 4  measure        per-circuit / per-layer cable length (mm→m)
    (later) rooms, assemble+price via core.rate_model → A-H BOQ

Deterministic: same DXF in → same result out. No LLM. This subpackage must
never import agent.pdf_pipeline.* (CLAUDE.md single rule).
"""

from agent.dxf_pipeline.passes.recognize import (
    DxfRecognition,
    RecognisedSymbol,
    CircuitTag,
    RoomLabel,
    recognise,
)
from agent.dxf_pipeline.passes.assemble import build_boq_from_recognition
from agent.dxf_pipeline.passes.legend import extract_legend, legend_block_counts
from agent.dxf_pipeline.passes.template_count import count_by_template
from agent.dxf_pipeline.passes.spatial import (
    RoomRegion,
    SpatialResult,
    assign_spatial,
    extract_room_regions,
)
from agent.dxf_pipeline.passes.run import DxfEstimatorRun, run_dxf_estimator

__all__ = [
    "DxfRecognition",
    "RecognisedSymbol",
    "CircuitTag",
    "RoomLabel",
    "recognise",
    "build_boq_from_recognition",
    "extract_legend",
    "legend_block_counts",
    "count_by_template",
    "RoomRegion",
    "SpatialResult",
    "assign_spatial",
    "extract_room_regions",
    "DxfEstimatorRun",
    "run_dxf_estimator",
]
