"""
Integration tests for routers/pricing.py — the full request -> compare ->
apply flow against a real run_store record, plus the RFQ draft path. RFQ
reply parsing needs ANTHROPIC_API_KEY (not set in test env) so that path is
covered by sourcing_layer's own offline QuoteParser tests instead.
"""

from __future__ import annotations

import pytest
from fastapi import HTTPException

from agent.dxf_pipeline.passes.run import DxfEstimatorRun
from agent.shared import BillOfQuantities, BQLineItem, BQSection, ItemConfidence
from core.run_store import RunRecord, run_store
from routers.pricing import (
    ApplyQuotesBody,
    DraftRfqBody,
    QuoteRequestBody,
    apply_chosen_quotes,
    draft_rfq_email,
    get_requests,
    request_quotes,
)


def _seed_run(run_id: str) -> BillOfQuantities:
    # A real DxfEstimatorRun - run_store now round-trips every record through
    # JSON (SQLite-backed, Phase 11), so a fake stand-in without
    # model_dump_json()/model_validate_json() no longer works here.
    items = [
        BQLineItem(item_no=1, section=BQSection.LIGHTING, description="LED Downlight",
                   qty=40, unit_price_zar=260.0, total_zar=10400.0, source=ItemConfidence.EXTRACTED),
        BQLineItem(item_no=2, section=BQSection.POWER_OUTLETS, description="Double Socket",
                   qty=55, unit_price_zar=175.0, total_zar=9625.0, source=ItemConfidence.EXTRACTED),
    ]
    boq = BillOfQuantities(
        project_name="Pricing Test", pipeline="dxf", run_id=run_id,
        line_items=items, subtotal_zar=20025.0, total_excl_vat_zar=25031.25,
        total_incl_vat_zar=28785.94, items_extracted=2,
    )
    result = DxfEstimatorRun(run_id=run_id, input_file="test.dxf", boq=boq, success=True)
    run_store.put(RunRecord(run_id=run_id, pipeline="dxf", status="passed", input_file="test.dxf", result=result))
    return boq


def test_get_requests_lists_material_lines_and_suppliers():
    _seed_run("pricing-test-1")
    data = get_requests("pricing-test-1")
    assert len(data["requests"]) == 2
    assert len(data["suppliers"]) == 4  # default_mock_suppliers() panel size


def test_request_quotes_produces_a_report():
    _seed_run("pricing-test-2")
    refs = [r["item_ref"] for r in get_requests("pricing-test-2")["requests"]]
    report = request_quotes("pricing-test-2", QuoteRequestBody(item_refs=refs))
    assert report["items_sourced"] == 2
    assert report["suppliers_contacted"] == 4
    for res in report["results"]:
        assert len(res["quotes"]) == 4


def test_apply_quotes_writes_sourced_boq_and_export_uses_it():
    run_id = "pricing-test-3"
    base_boq = _seed_run(run_id)
    refs = [r["item_ref"] for r in get_requests(run_id)["requests"]]
    report = request_quotes(run_id, QuoteRequestBody(item_refs=refs))

    choices = {res["request"]["item_ref"]: res["recommended_supplier_id"] for res in report["results"]}
    result = apply_chosen_quotes(run_id, ApplyQuotesBody(choices=choices))

    assert result["applied"] == 2
    record = run_store.get(run_id)
    assert record.sourced_boq is not None
    assert record.sourced_boq.subtotal_zar != base_boq.subtotal_zar

    # export.py's _priced_boq_for must now read the sourced_boq, not the raw pipeline result.
    from routers.export import export_json
    exported = export_json(run_id, markup=0.0, contingency=0.0, vat=0.0)
    assert exported["subtotal_zar"] == record.sourced_boq.subtotal_zar


def test_draft_rfq_email_contains_items_and_contact():
    run_id = "pricing-test-4"
    _seed_run(run_id)
    refs = [r["item_ref"] for r in get_requests(run_id)["requests"]]
    suppliers = get_requests(run_id)["suppliers"]
    draft = draft_rfq_email(run_id, DraftRfqBody(item_refs=refs, supplier_id=suppliers[0]["supplier_id"], contractor_name="ACME"))
    assert "Request for Quotation" in draft["subject"]
    assert "ACME" in draft["body"]
    assert "@" in draft["to"]


def test_apply_quotes_without_report_raises_404():
    run_id = "pricing-test-5"
    _seed_run(run_id)
    with pytest.raises(HTTPException) as exc_info:
        apply_chosen_quotes(run_id, ApplyQuotesBody(choices={}))
    assert exc_info.value.status_code == 404
