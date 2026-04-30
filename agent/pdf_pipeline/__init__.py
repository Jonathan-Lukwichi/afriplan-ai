"""
agent.pdf_pipeline — vision-LLM PDF → BoQ pipeline.

Public surface (only this package is allowed to be imported by the UI
and the comparison layer):

    from agent.pdf_pipeline import run_pdf_pipeline, PdfPipelineRun, PdfLLM

INDEPENDENCE RULES (CI-enforced):
- This package MUST NOT import from agent.dxf_pipeline.
- This package MAY import anthropic, agent.shared, and core.
"""

from agent.pdf_pipeline.llm import LLMError, PdfLLM, ToolCallResult, build_default_pdf_llm
from agent.pdf_pipeline.models import (
    CircuitRow,
    CircuitSchedule,
    CrossPageDisagreement,
    DistributionBoard,
    FixtureCounts,
    PageClassification,
    PageType,
    PdfEvaluation,
    PdfExtraction,
    PdfPipelineRun,
    StageCost,
)
from agent.pdf_pipeline.pipeline import run_pdf_pipeline

__all__ = [
    "run_pdf_pipeline",
    "PdfPipelineRun",
    "PdfExtraction",
    "PdfEvaluation",
    "PageClassification",
    "PageType",
    "DistributionBoard",
    "CircuitRow",
    "CircuitSchedule",
    "FixtureCounts",
    "CrossPageDisagreement",
    "StageCost",
    "PdfLLM",
    "ToolCallResult",
    "LLMError",
    "build_default_pdf_llm",
]
