"""
Integration tests for the audit + completion endpoints (routers/audit.py and the
`complete` / markup-default behaviour of routers/export.py), over real HTTP via
FastAPI's TestClient. No network, no LLM.
"""

from __future__ import annotations

import io
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from agent.dxf_pipeline.passes.run import DxfEstimatorRun
from agent.shared import BillOfQuantities, BQLineItem, BQSection, ItemConfidence, LineKind
from core.run_store import RunRecord, run_store

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "evaluation_layer"))
from test_reference import _synthetic  # noqa: E402  (synthetic priced-BOQ workbook)

from main import app  # noqa: E402

client = TestClient(app)


def _seed(run_id: str, input_file: str = "WD-X-01-SLD.dxf", markup_pct: float = 0.0) -> None:
    items = [
        BQLineItem(item_no=1, section=BQSection.POWER_OUTLETS, description="Double Socket — Office",
                   unit="No", qty=6, unit_price_zar=400, total_zar=2400, source=ItemConfidence.EXTRACTED),
        BQLineItem(item_no=1, section=BQSection.SUBMAIN_CABLES, description="Supply 16mm² x4C SWA feeder A→B",
                   unit="m", qty=30, unit_price_zar=300, total_zar=9000, line_kind=LineKind.SUPPLY),
    ]
    boq = BillOfQuantities(project_name="Audit Test", pipeline="dxf", run_id=run_id, line_items=items,
                           subtotal_zar=11400, contractor_markup_pct=markup_pct)
    run_store.put(RunRecord(run_id=run_id, pipeline="dxf", status="passed", input_file=input_file,
                            result=DxfEstimatorRun(run_id=run_id, input_file=input_file, boq=boq, success=True)))


def test_json_export_defaults_markup_to_the_bills_own_value():
    _seed("audit-t1")
    body = client.get("/api/export/json/audit-t1").json()
    assert body["contractor_markup_pct"] == 0.0 and body["markup_zar"] == 0.0   # never twice


def test_explicit_markup_still_applies():
    _seed("audit-t2")
    body = client.get("/api/export/json/audit-t2?markup=10").json()
    assert body["markup_zar"] == pytest.approx(1140.0)


def test_complete_adds_inferred_lines_when_a_ratio_model_exists():
    from audit.completer import available_ratio_model
    if available_ratio_model() is None:
        pytest.skip("no fitted ratio model on this machine (client data is local only)")
    _seed("audit-t3")
    plain = client.get("/api/export/json/audit-t3").json()
    done = client.get("/api/export/json/audit-t3?complete=true").json()
    assert len(done["line_items"]) > len(plain["line_items"])
    assert any(l["source"] == "inferred" for l in done["line_items"])


def test_audit_run_reports_findings():
    _seed("audit-t4")
    body = client.get("/api/audit/run/audit-t4").json()
    rules = {f["rule"] for f in body["findings"]}
    assert "COMPANION" in rules                      # feeder without earth / terminations
    assert body["summary"]["count"] == len(body["findings"])


def test_coverage_for_a_dxf_sld_run():
    _seed("audit-t5", input_file="WD-AB-01-SLD 050425.dwg")
    body = client.get("/api/audit/coverage/audit-t5").json()
    assert body["uploaded"] == ["sld"]
    assert "lighting_layout" in body["requests"] and "plug_layout" in body["requests"]


def test_audit_uploaded_workbook(tmp_path):
    xlsx = _synthetic(tmp_path).read_bytes()
    r = client.post("/api/audit/boq", files={"file": ("boq.xlsx", io.BytesIO(xlsx),
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["bills"] and body["summary"]["count"] >= 1
    assert {"ERROR_CELL", "NOT_IN_SUMMARY"} & {f["rule"] for f in body["findings"]}


def test_audit_rejects_non_workbook():
    r = client.post("/api/audit/boq", files={"file": ("x.xlsx", io.BytesIO(b"not excel"), "application/octet-stream")})
    assert r.status_code == 400


def test_ratio_model_status():
    assert "available" in client.get("/api/audit/ratio-model").json()


def test_excel_and_pdf_export_without_explicit_markup():
    """Regression: markup omitted -> bill default; the contractor profile must get a number."""
    _seed("audit-t6")
    xl = client.get("/api/export/excel/audit-t6?complete=true")
    pdf = client.get("/api/export/pdf/audit-t6")
    assert xl.status_code == 200 and xl.content.startswith(b"PK")
    assert pdf.status_code == 200 and pdf.content.startswith(b"%PDF")


def test_pdf_export_with_gap_report():
    """Regression (pre-existing on main): the gap-report page crashed fpdf2 ('Not enough
    horizontal space') whenever a bill had gaps — e.g. every SLD with assumed feeder lengths."""
    from agent.shared import GapItem
    _seed("audit-t7")
    rec = run_store.get("audit-t7")
    rec.result.boq.gaps = [GapItem(section=BQSection.SUBMAIN_CABLES, description="Feeder A→B length not on the SLD",
                                   assumption="Assumed 30 m.", suggested_action="Measure on the site plan.",
                                   severity="high")] * 2
    run_store.put(rec)
    pdf = client.get("/api/export/pdf/audit-t7")
    assert pdf.status_code == 200 and pdf.content.startswith(b"%PDF")
