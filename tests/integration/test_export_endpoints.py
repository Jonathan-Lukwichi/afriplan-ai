"""
Integration tests for routers/export.py — exercises the real reprice ->
export chain against a run_store record, and the email flow's cover-note
fallback (no ANTHROPIC_API_KEY / RESEND_API_KEY configured in test env, so
this proves the graceful-degradation path, not a live send).
"""

from __future__ import annotations

from datetime import datetime

from agent.shared import BillOfQuantities, BQLineItem, BQSection, ItemConfidence
from core.run_store import RunRecord, run_store
from routers.export import EmailBoqRequest, email_boq, export_excel, export_json, export_pdf


class _FakeResult:
    def __init__(self, boq):
        self.boq = boq


def _seed_run(run_id: str) -> None:
    items = [
        BQLineItem(item_no=1, section=BQSection.LIGHTING, description="LED Downlight",
                   qty=24, unit_price_zar=220.0, total_zar=5280.0, source=ItemConfidence.EXTRACTED),
    ]
    boq = BillOfQuantities(
        project_name="Export Test", pipeline="dxf", run_id=run_id,
        line_items=items, subtotal_zar=5280.0, total_excl_vat_zar=6600.0,
        total_incl_vat_zar=7590.0, items_extracted=1,
    )
    run_store.put(RunRecord(
        run_id=run_id, pipeline="dxf", status="passed", input_file="test.dxf",
        result=_FakeResult(boq),
    ))


def test_export_excel_produces_valid_xlsx():
    # Query(...) defaults only resolve through FastAPI's request handling,
    # not a direct Python call - pass explicit values, matching what a real
    # request without query params would receive.
    _seed_run("export-test-1")
    resp = export_excel("export-test-1", markup=20.0, contingency=5.0, vat=15.0, quote_ref=None, validity_days=30)
    assert resp.body.startswith(b"PK")


def test_export_pdf_produces_valid_pdf():
    _seed_run("export-test-2")
    resp = export_pdf("export-test-2", markup=20.0, contingency=5.0, vat=15.0, quote_ref=None, validity_days=30)
    assert resp.body.startswith(b"%PDF")


def test_export_json_reflects_repriced_totals():
    _seed_run("export-test-3")
    data = export_json("export-test-3", markup=10.0, contingency=0.0, vat=15.0)
    # subtotal 5280 * 1.10 markup = 5808 excl vat; incl vat = 5808 * 1.15
    assert data["contractor_markup_pct"] == 10.0
    assert abs(data["total_excl_vat_zar"] - 5808.0) < 0.01


def test_email_boq_degrades_gracefully_without_provider_keys():
    """No RESEND_API_KEY / ANTHROPIC_API_KEY in the test environment -
    proves the endpoint still completes and reports sent=False rather than
    raising, with the templated fallback subject."""
    _seed_run("export-test-4")
    result = email_boq(EmailBoqRequest(run_id="export-test-4", to="client@example.com"))
    assert result["sent"] is False
    assert "Export Test" in result["subject"]
