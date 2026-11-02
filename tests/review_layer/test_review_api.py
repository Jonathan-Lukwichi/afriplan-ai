"""The review over a stored run: answers kept apart from what was read, undone, carried to a re-upload,
and asked again when the drawings change. Synthetic run, no client data."""

from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient

from agent.dxf_pipeline.passes.run import DxfEstimatorRun, DxfFileNote
from agent.shared.boq import BQSection, GapItem, ItemConfidence
from agent.shared.findings import Evidence, FeederFinding, Findings
from agent.shared.pricing import price_findings
from core.run_store import RunRecord, run_store
from main import app

client = TestClient(app)
QID = "feeder:DBA>DBC"


def _run(sheet="A-01-LIGHTING 010125.dwg", sha="one", project=None) -> str:
    """A stored run; `project` makes the file names, so tests do not share answers."""
    gap = GapItem(section=BQSection.SUBMAIN_CABLES, description="Feeder DB-A→DB-C has no drawn route on the site plan",
                  assumption="Assumed 30 m.", suggested_action="Confirm.", severity="high", drawing_ref="sld")
    findings = Findings(feeders=[FeederFinding(
        from_board="DB-A", to_board="DB-C", cable_size_mm2=35, length_m=30, trench_m=30, evidence=Evidence.ASSUMED,
        confidence=ItemConfidence.ASSUMED, gaps=[gap])])
    run_id = uuid.uuid4().hex[:12]
    boq = price_findings(findings, pipeline="dxf", project_name="Test", run_id=run_id)
    result = DxfEstimatorRun(run_id=run_id, input_file=sheet, findings=findings, boq=boq, success=True,
                             files=[DxfFileNote(file_name=f"{project}-{sheet}", sha256=sha)])
    run_store.put(RunRecord(run_id=run_id, pipeline="dxf", status="passed", input_file=sheet, result=result))
    return run_id


@pytest.fixture
def project():
    return uuid.uuid4().hex[:8]


def _answer(run_id, values=None):
    return client.put(f"/api/review/{run_id}/answers",
                      json={"question_id": QID, "values": values or {"length_m": 55, "trench_m": 10}})


def _question(payload):
    return next(q for g in payload["groups"] for q in g["questions"] if q["id"] == QID)


def test_a_run_lists_its_questions(project):
    p = client.get(f"/api/review/{_run(project=project)}").json()
    assert p["available"] and p["open"] == 1 and p["change_zar"] == 0
    assert _question(p)["status"] == "open"


def test_an_answer_updates_the_bill_and_every_export_path(project):
    run_id = _run(project=project)
    before = client.get(f"/api/export/json/{run_id}").json()["subtotal_zar"]
    p = _answer(run_id).json()
    assert p["open"] == 0 and p["answered"] == 1 and p["change_zar"] != 0
    assert _question(p)["answer"]["values"]["length_m"] == 55
    after = client.get(f"/api/export/json/{run_id}").json()
    assert after["subtotal_zar"] != before
    assert any(l["qty"] == 55 for l in after["line_items"])


def test_the_stored_run_keeps_what_the_reader_found(project):
    run_id = _run(project=project)
    _answer(run_id)
    stored = run_store.get(run_id).result
    assert stored.findings.feeders[0].length_m == 30
    assert any(l.qty == 30 for l in stored.boq.line_items)


def test_an_answer_can_be_undone(project):
    run_id = _run(project=project)
    before = client.get(f"/api/export/json/{run_id}").json()["subtotal_zar"]
    _answer(run_id)
    p = client.delete(f"/api/review/{run_id}/answers", params={"question_id": QID}).json()
    assert p["open"] == 1 and p["change_zar"] == 0
    assert client.get(f"/api/export/json/{run_id}").json()["subtotal_zar"] == before


def test_who_answered_and_when_is_kept(project):
    run_id = _run(project=project)
    client.put(f"/api/review/{run_id}/answers", json={"question_id": QID, "values": {"length_m": 55}, "by": "Thandi"})
    a = _question(client.get(f"/api/review/{run_id}").json())["answer"]
    assert a["by"] == "Thandi" and a["at"]


def test_the_same_drawings_uploaded_again_keep_their_answers(project):
    _answer(_run(project=project))
    p = client.get(f"/api/review/{_run(project=project)}").json()
    assert _question(p)["status"] == "answered" and p["change_zar"] != 0


def test_revised_drawings_ask_again_and_do_not_apply_the_old_answer(project):
    _answer(_run(project=project))
    revised = _run(sheet="A-01-LIGHTING 020225.dwg", sha="two", project=project)
    p = client.get(f"/api/review/{revised}").json()
    q = _question(p)
    assert q["status"] == "recheck" and q["answer"]["values"]["length_m"] == 55
    assert p["change_zar"] == 0 and p["recheck"] == 1


def test_a_drawing_changed_under_the_same_name_asks_again(project):
    _answer(_run(project=project))
    assert _question(client.get(f"/api/review/{_run(sha='two', project=project)}").json())["status"] == "recheck"


def test_confirming_an_old_answer_applies_it_to_the_new_drawings(project):
    _answer(_run(project=project))
    revised = _run(sheet="A-01-LIGHTING 020225.dwg", sha="two", project=project)
    p = _answer(revised).json()
    assert _question(p)["status"] == "answered" and p["recheck"] == 0


def test_another_project_never_sees_these_answers(project):
    _answer(_run(project=project))
    assert _question(client.get(f"/api/review/{_run(project=project + 'x')}").json())["status"] == "open"


def test_an_unknown_question_is_refused(project):
    r = client.put(f"/api/review/{_run(project=project)}/answers", json={"question_id": "nope", "values": {}})
    assert r.status_code == 404


@pytest.mark.parametrize("values", [{"length_m": -1}, {"length_m": "far"}, {"trench_m": 5}, {"length_m": 5, "made_up": 1}])
def test_a_bad_answer_is_refused(project, values):
    assert _answer(_run(project=project), values).status_code == 422


def test_an_unknown_run_is_404():
    assert client.get("/api/review/nope").status_code == 404


def test_a_run_with_no_findings_has_no_review(project):
    run_id = uuid.uuid4().hex[:12]
    run_store.put(RunRecord(run_id=run_id, pipeline="dxf", status="running", input_file="x.dwg"))
    assert client.get(f"/api/review/{run_id}").json() == {"available": False}


def test_supplier_prices_survive_an_answer(project):
    run_id = _run(project=project)
    record = run_store.get(run_id)
    sourced = record.result.boq.model_copy(deep=True)
    sourced.line_items[0].unit_price_zar = 9999.0
    record.sourced_boq = sourced
    run_store.put(record)
    _answer(run_id)
    lines = client.get(f"/api/export/json/{run_id}").json()["line_items"]
    assert any(l["unit_price_zar"] == 9999.0 and l["qty"] == 55 for l in lines)
