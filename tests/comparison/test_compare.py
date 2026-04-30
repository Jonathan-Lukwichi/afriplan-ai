"""Tests for the cross-pipeline comparison layer."""

from __future__ import annotations

from datetime import datetime

import pytest

from agent.comparison import compare_runs
from agent.dxf_pipeline.models import (
    DxfEvaluation,
    DxfExtraction,
    DxfIngestResult,
    DxfLayerAnalysis,
    DxfPipelineRun,
)
from agent.pdf_pipeline.models import (
    PdfEvaluation,
    PdfExtraction,
    PdfPipelineRun,
)
from agent.shared import (
    BillOfQuantities,
    BQLineItem,
    BQSection,
    ItemConfidence,
    ProjectMetadata,
)


def _make_boq(pipeline: str, run_id: str, items: list[tuple[str, BQSection, float, float]]) -> BillOfQuantities:
    """Build a BoQ with (description, section, qty, unit_price) tuples."""
    line_items = []
    for i, (desc, section, qty, price) in enumerate(items, start=1):
        line_items.append(
            BQLineItem(
                item_no=i,
                section=section,
                description=desc,
                qty=qty,
                unit_price_zar=price,
                total_zar=round(qty * price, 2),
                source=ItemConfidence.EXTRACTED,
            )
        )
    subtotal = sum(it.total_zar for it in line_items)
    return BillOfQuantities(
        project_name="Test Project",
        pipeline=pipeline,
        run_id=run_id,
        line_items=line_items,
        subtotal_zar=subtotal,
        total_excl_vat_zar=round(subtotal * 1.25, 2),
        total_incl_vat_zar=round(subtotal * 1.25 * 1.15, 2),
        items_extracted=len(line_items),
    )


def _make_pdf_run(boq: BillOfQuantities, mape=None) -> PdfPipelineRun:
    return PdfPipelineRun(
        run_id=boq.run_id,
        timestamp=datetime.utcnow(),
        input_file="test.pdf",
        input_sha256="a" * 64,
        page_count=3,
        extraction=PdfExtraction(),
        evaluation=PdfEvaluation(passed=True, overall_score=0.9, baseline_mape=mape),
        boq=boq,
        cost_zar=4.20,
        duration_s=42.0,
        success=True,
    )


def _make_dxf_run(boq: BillOfQuantities, mape=None) -> DxfPipelineRun:
    return DxfPipelineRun(
        run_id=boq.run_id,
        timestamp=datetime.utcnow(),
        input_file="test.dxf",
        input_sha256="b" * 64,
        drawing_units="mm",
        project=ProjectMetadata(),
        ingest=DxfIngestResult(file_name="test.dxf", file_size_bytes=1, file_sha256="b"*64),
        layer_analysis=DxfLayerAnalysis(),
        extraction=DxfExtraction(),
        evaluation=DxfEvaluation(passed=True, overall_score=0.95, baseline_mape=mape),
        boq=boq,
        cost_zar=0.0,
        duration_s=1.4,
        success=True,
    )


# ─── Tests ────────────────────────────────────────────────────────────

def test_identical_boqs_produce_perfect_agreement():
    items = [
        ("LED Downlight", BQSection.LIGHTING, 12, 220.0),
        ("Double Socket", BQSection.POWER_OUTLETS, 8, 160.0),
    ]
    pdf_run = _make_pdf_run(_make_boq("pdf", "p1", items))
    dxf_run = _make_dxf_run(_make_boq("dxf", "d1", items))

    cmp = compare_runs(pdf_run=pdf_run, dxf_run=dxf_run)

    assert cmp.agreement_score == 1.0
    assert cmp.field_disagreements == []
    assert cmp.total_difference_pct == 0.0


def test_section_only_in_pdf_flagged():
    pdf_items = [
        ("LED Downlight", BQSection.LIGHTING, 10, 220.0),
        ("Data Outlet CAT6", BQSection.DATA_COMMS, 16, 450.0),  # PDF-only
    ]
    dxf_items = [
        ("LED Downlight", BQSection.LIGHTING, 10, 220.0),
    ]
    cmp = compare_runs(
        pdf_run=_make_pdf_run(_make_boq("pdf", "p1", pdf_items)),
        dxf_run=_make_dxf_run(_make_boq("dxf", "d1", dxf_items)),
    )

    data_section = cmp.section_agreements[BQSection.DATA_COMMS.value]
    assert data_section.pdf_subtotal > 0
    assert data_section.dxf_subtotal == 0
    assert "Data Outlet CAT6" in data_section.items_only_in_pdf


def test_qty_disagreement_recorded():
    pdf_items = [("LED Downlight", BQSection.LIGHTING, 10, 220.0)]
    dxf_items = [("LED Downlight", BQSection.LIGHTING, 12, 220.0)]
    cmp = compare_runs(
        pdf_run=_make_pdf_run(_make_boq("pdf", "p1", pdf_items)),
        dxf_run=_make_dxf_run(_make_boq("dxf", "d1", dxf_items)),
    )

    assert len(cmp.field_disagreements) == 1
    fd = cmp.field_disagreements[0]
    assert fd.field_path == "qty.LED Downlight"
    assert fd.pdf_value == 10
    assert fd.dxf_value == 12


def test_winner_vs_baseline_picks_lower_mape():
    items = [("LED Downlight", BQSection.LIGHTING, 10, 220.0)]
    cmp = compare_runs(
        pdf_run=_make_pdf_run(_make_boq("pdf", "p1", items), mape=0.024),
        dxf_run=_make_dxf_run(_make_boq("dxf", "d1", items), mape=0.012),
    )
    assert cmp.winner_vs_baseline == "dxf"
    assert cmp.dxf_vs_baseline_mape == 0.012


def test_no_baseline_means_no_winner():
    items = [("LED Downlight", BQSection.LIGHTING, 10, 220.0)]
    cmp = compare_runs(
        pdf_run=_make_pdf_run(_make_boq("pdf", "p1", items)),
        dxf_run=_make_dxf_run(_make_boq("dxf", "d1", items)),
    )
    assert cmp.winner_vs_baseline == "no_baseline"


def test_one_pipeline_failed_returns_empty():
    items = [("LED Downlight", BQSection.LIGHTING, 10, 220.0)]
    pdf_run = _make_pdf_run(_make_boq("pdf", "p1", items))
    dxf_run = _make_dxf_run(_make_boq("dxf", "d1", items))
    dxf_run = dxf_run.model_copy(update={"boq": None, "success": False})

    cmp = compare_runs(pdf_run=pdf_run, dxf_run=dxf_run)
    assert cmp.section_agreements == {}
    assert cmp.field_disagreements == []


def test_pdf_export_nonempty():
    """The comparison PDF export should produce non-empty bytes."""
    from agent.comparison.report import export_comparison_to_pdf

    items = [
        ("LED Downlight", BQSection.LIGHTING, 12, 220.0),
        ("Double Socket", BQSection.POWER_OUTLETS, 8, 160.0),
    ]
    cmp = compare_runs(
        pdf_run=_make_pdf_run(_make_boq("pdf", "p1", items)),
        dxf_run=_make_dxf_run(_make_boq("dxf", "d1", items)),
    )
    pdf_bytes = export_comparison_to_pdf(cmp)
    assert pdf_bytes.startswith(b"%PDF")
    assert len(pdf_bytes) > 1000
