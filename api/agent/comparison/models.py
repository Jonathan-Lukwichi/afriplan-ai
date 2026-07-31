"""
Cross-pipeline comparison data contracts.

This module is **read-only**. It consumes the outputs of both pipelines
and produces a comparison report. It MUST NOT be imported by either
pipeline (CI-enforced).
"""

from __future__ import annotations

from datetime import datetime
from typing import Dict, List, Literal, Optional

from pydantic import BaseModel, Field


class FieldDiscrepancy(BaseModel):
    """One specific field where the two pipelines disagreed."""
    field_path: str            # e.g. "section.LIGHTING.LED Downlight.qty"
    pdf_value: Optional[float] = None
    dxf_value: Optional[float] = None
    delta_abs: float = 0.0
    delta_pct: Optional[float] = None
    note: str = ""


class SectionAgreement(BaseModel):
    section: str               # BQSection.value
    pdf_subtotal: float = 0.0
    dxf_subtotal: float = 0.0
    delta_zar: float = 0.0
    delta_pct: Optional[float] = None
    items_only_in_pdf: List[str] = Field(default_factory=list)
    items_only_in_dxf: List[str] = Field(default_factory=list)
    items_in_both: int = 0


class PipelineComparison(BaseModel):
    """End-to-end comparison output."""
    project_name: str = ""
    pdf_run_id: str = ""
    dxf_run_id: str = ""
    generated_at: datetime = Field(default_factory=datetime.utcnow)

    section_agreements: Dict[str, SectionAgreement] = Field(default_factory=dict)
    field_disagreements: List[FieldDiscrepancy] = Field(default_factory=list)
    agreement_score: float = 0.0          # 0..1

    pdf_cost_zar: float = 0.0
    dxf_cost_zar: float = 0.0
    pdf_total_excl_vat: float = 0.0
    dxf_total_excl_vat: float = 0.0
    total_difference_pct: Optional[float] = None

    pdf_vs_baseline_mape: Optional[float] = None
    dxf_vs_baseline_mape: Optional[float] = None
    winner_vs_baseline: Optional[
        Literal["pdf", "dxf", "tie", "no_baseline"]
    ] = None
