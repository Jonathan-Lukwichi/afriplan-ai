"""
agent.comparison — read-only cross-pipeline comparison layer.

Consumes the public output shape of both v2 estimators (agent.dxf_pipeline
.passes.run.DxfEstimatorRun, agent.pdf_pipeline.passes.run.EstimatorRun) —
duck-typed on `.boq`/`.run_id`/`.cost_zar`, matching how compare_runs was
already written. This package MUST NOT be imported by either pipeline
(CI-enforced).
"""

from agent.comparison.compare import compare_runs
from agent.comparison.models import (
    FieldDiscrepancy,
    PipelineComparison,
    SectionAgreement,
)
from agent.comparison.report import export_comparison_to_pdf

__all__ = [
    "compare_runs",
    "PipelineComparison",
    "SectionAgreement",
    "FieldDiscrepancy",
    "export_comparison_to_pdf",
]
