"""
agent.comparison — read-only cross-pipeline comparison layer.

Imports allowed: agent.shared, agent.pdf_pipeline.models,
agent.dxf_pipeline.models (read-only consumption of their public types).

This package MUST NOT be imported by either pipeline (CI-enforced).
"""

from agent.comparison.compare import compare_runs
from agent.comparison.models import (
    FieldDiscrepancy,
    PipelineComparison,
    SectionAgreement,
)
from agent.comparison.report import (
    export_comparison_to_pdf,
    render_comparison_panel,
)

__all__ = [
    "compare_runs",
    "PipelineComparison",
    "SectionAgreement",
    "FieldDiscrepancy",
    "render_comparison_panel",
    "export_comparison_to_pdf",
]
