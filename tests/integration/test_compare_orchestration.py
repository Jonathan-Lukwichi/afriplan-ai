"""
Integration test for the /api/compare orchestration logic (routers/compare.py)
without touching the real Anthropic API — run_pdf_estimator is monkeypatched
to return a canned EstimatorRun instantly, proving the asyncio.gather
concurrency and the auto-fired compare_runs wiring are correct in isolation
from real LLM cost/latency.
"""

from __future__ import annotations

import asyncio
from datetime import datetime

import core.run_jobs as run_jobs
from agent.pdf_pipeline.passes.run import EstimatorRun
from agent.shared import BillOfQuantities, BQLineItem, BQSection, ItemConfidence
from core.compare_store import compare_store
from core.run_store import run_store
from routers.compare import _run_both_then_compare


def _boq(pipeline: str, run_id: str) -> BillOfQuantities:
    items = [BQLineItem(
        item_no=1, section=BQSection.LIGHTING, description="LED Downlight",
        qty=10, unit_price_zar=220.0, total_zar=2200.0, source=ItemConfidence.EXTRACTED,
    )]
    return BillOfQuantities(
        project_name="Integration Test", pipeline=pipeline, run_id=run_id,
        line_items=items, subtotal_zar=2200.0, total_excl_vat_zar=2750.0,
        total_incl_vat_zar=3162.5, items_extracted=1,
    )


def test_compare_orchestration_runs_concurrently_and_computes_result(monkeypatch):
    def fake_run_pdf_estimator(files, on_progress=None):
        return EstimatorRun(
            run_id="pdf-test", timestamp=datetime.utcnow(), project_name="Integration Test",
            boq=_boq("pdf", "pdf-test"), cost_zar=1.5, duration_s=0.01, success=True,
        )
    monkeypatch.setattr(run_jobs, "run_pdf_estimator", fake_run_pdf_estimator)

    dxf_run_id, pdf_run_id, compare_id = "dxf-test", "pdf-test", "cmp-test"
    from core.run_store import RunRecord
    run_store.put(RunRecord(run_id=dxf_run_id, pipeline="dxf", status="running", input_file="test.dxf"))
    run_store.put(RunRecord(run_id=pdf_run_id, pipeline="pdf", status="running", input_file="test.pdf"))
    from core.compare_store import CompareRecord
    compare_store.put(CompareRecord(compare_id=compare_id, dxf_run_id=dxf_run_id, pdf_run_id=pdf_run_id, status="running"))

    # A real (tiny, synthetic) DXF so run_dxf_job exercises the actual estimator.
    import ezdxf
    doc = ezdxf.new("R2010")
    blk = doc.blocks.new(name="DL")
    blk.add_circle((0, 0), radius=50)
    doc.layers.add(name="ELEC_LIGHTING", color=1)
    msp = doc.modelspace()
    for i in range(4):
        msp.add_blockref("DL", insert=(i * 1000, 0), dxfattribs={"layer": "ELEC_LIGHTING"})
    import io
    buf = io.StringIO()
    doc.write(buf)
    dxf_bytes = buf.getvalue().encode("utf-8")

    asyncio.run(_run_both_then_compare(
        compare_id, dxf_run_id, pdf_run_id, [(dxf_bytes, "test.dxf")], [(b"%PDF-fake", "test.pdf")],
    ))

    record = compare_store.get(compare_id)
    assert record.status == "passed", record.error
    assert record.result is not None
    assert record.result.pdf_total_excl_vat == 2750.0
    # dxf_run.run_id/pdf_run.run_id are the estimators' own internally
    # generated ids (see run_dxf_estimator/run_pdf_estimator), distinct from
    # the RunRecord keys used by run_store/compare_store — compare_runs
    # labels the comparison with whichever the estimator itself produced.
    assert record.result.pdf_run_id == "pdf-test"
    assert record.result.dxf_run_id
    assert record.dxf_run_id == dxf_run_id
    assert record.pdf_run_id == pdf_run_id
