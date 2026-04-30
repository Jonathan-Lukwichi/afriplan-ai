"""
agent.dxf_pipeline — deterministic DXF → BoQ pipeline.

Public surface (only this package is allowed to be imported by the UI
and the comparison layer):

    from agent.dxf_pipeline import run_dxf_pipeline, DxfPipelineRun

INDEPENDENCE RULES (CI-enforced):
- This package MUST NOT import from agent.pdf_pipeline.
- This package MUST NOT import anthropic, openai, or any LLM SDK.
- This package MAY import from agent.shared and core.
"""

from agent.dxf_pipeline.models import (
    DxfBlock,
    DxfCircle,
    DxfEvaluation,
    DxfExtraction,
    DxfIngestResult,
    DxfLayerAnalysis,
    DxfPipelineRun,
    DxfPolyline,
    DxfText,
    LayerInfo,
    Point2D,
)
from agent.dxf_pipeline.patterns import (
    EXACT_BLOCK_MAP,
    REGEX_BLOCK_PATTERNS,
    FixtureCategory,
    FixtureSpec,
    classify_block_name,
)
from agent.dxf_pipeline.pipeline import run_dxf_pipeline

__all__ = [
    "run_dxf_pipeline",
    "DxfPipelineRun",
    "DxfIngestResult",
    "DxfLayerAnalysis",
    "DxfExtraction",
    "DxfEvaluation",
    "DxfBlock",
    "DxfText",
    "DxfPolyline",
    "DxfCircle",
    "LayerInfo",
    "Point2D",
    "FixtureCategory",
    "FixtureSpec",
    "EXACT_BLOCK_MAP",
    "REGEX_BLOCK_PATTERNS",
    "classify_block_name",
]
