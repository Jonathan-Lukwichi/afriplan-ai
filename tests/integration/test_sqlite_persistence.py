"""
Proves the Phase 11 persistence layer is a real store, not just an
in-memory cache with a different name: a fresh RunStore()/CompareStore()
instance (simulating a process restart, since nothing but the SQLite file
carries state between them) can read back what an earlier instance wrote.
"""

from __future__ import annotations

from datetime import datetime

from agent.comparison.models import PipelineComparison
from agent.dxf_pipeline.passes.run import DxfEstimatorRun
from agent.pdf_pipeline.passes.run import EstimatorRun
from agent.shared import BillOfQuantities, BQLineItem, BQSection, ContractorProfile, ItemConfidence
from core.compare_store import CompareRecord, CompareStore
from core.run_store import RunRecord, RunStore
from db.contractor_profile import load_contractor_profile, save_contractor_profile


def _boq(pipeline: str, run_id: str) -> BillOfQuantities:
    items = [BQLineItem(item_no=1, section=BQSection.LIGHTING, description="LED Downlight",
                         qty=5, unit_price_zar=100.0, total_zar=500.0, source=ItemConfidence.EXTRACTED)]
    return BillOfQuantities(project_name="Persistence Test", pipeline=pipeline, run_id=run_id,
                             line_items=items, subtotal_zar=500.0, total_excl_vat_zar=625.0,
                             total_incl_vat_zar=718.75, items_extracted=1)


def test_run_survives_a_fresh_store_instance():
    run_id = "sqlite-persist-1"
    result = DxfEstimatorRun(run_id=run_id, input_file="test.dxf", boq=_boq("dxf", run_id), success=True)

    writer = RunStore()
    writer.put(RunRecord(run_id=run_id, pipeline="dxf", status="passed", input_file="test.dxf", result=result))

    reader = RunStore()  # simulates a fresh process - only the SQLite file is shared
    record = reader.get(run_id)
    assert record is not None
    assert record.status == "passed"
    assert record.result.boq.project_name == "Persistence Test"
    assert record.result.boq.total_incl_vat_zar == 718.75


def test_sourced_boq_survives_a_fresh_store_instance():
    run_id = "sqlite-persist-2"
    result = EstimatorRun(run_id=run_id, timestamp=datetime.utcnow(), project_name="Persistence Test",
                           boq=_boq("pdf", run_id), success=True)
    sourced = _boq("pdf", run_id).model_copy(update={"subtotal_zar": 450.0})

    writer = RunStore()
    record = RunRecord(run_id=run_id, pipeline="pdf", status="passed", input_file="test.pdf", result=result)
    writer.put(record)
    record.sourced_boq = sourced
    writer.put(record)

    reader = RunStore()
    fetched = reader.get(run_id)
    assert fetched.sourced_boq is not None
    assert fetched.sourced_boq.subtotal_zar == 450.0


def test_comparison_survives_a_fresh_store_instance():
    compare_id = "sqlite-persist-3"
    cmp = PipelineComparison(project_name="Persistence Test", pdf_run_id="p1", dxf_run_id="d1", agreement_score=0.9)

    writer = CompareStore()
    writer.put(CompareRecord(compare_id=compare_id, dxf_run_id="d1", pdf_run_id="p1", status="passed", result=cmp))

    reader = CompareStore()
    fetched = reader.get(compare_id)
    assert fetched is not None
    assert fetched.result.agreement_score == 0.9


def test_contractor_profile_survives_across_calls():
    profile = ContractorProfile(company_name="Persistence Test Electrical", markup_pct=27.5)
    save_contractor_profile(profile)

    reloaded = load_contractor_profile()
    assert reloaded.company_name == "Persistence Test Electrical"
    assert reloaded.markup_pct == 27.5


def test_missing_run_returns_none_not_an_error():
    assert RunStore().get("does-not-exist") is None
