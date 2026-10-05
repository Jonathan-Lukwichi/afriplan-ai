"""A running job shows its progress; a job killed by a server restart says so instead of spinning forever."""

from __future__ import annotations

import uuid

from fastapi.testclient import TestClient

from core.run_progress import clear_progress, set_progress
from core.run_store import RunRecord, run_store
from main import app


def test_runs_left_running_by_a_restart_are_marked_failed_with_the_reason():
    stuck, done = f"stuck-{uuid.uuid4().hex[:6]}", f"done-{uuid.uuid4().hex[:6]}"
    run_store.put(RunRecord(run_id=stuck, pipeline="pdf", status="running", input_file="x.pdf"))
    run_store.put(RunRecord(run_id=done, pipeline="pdf", status="passed", input_file="x.pdf"))

    assert run_store.fail_interrupted("The server restarted while this run was in progress") >= 1

    assert run_store.get(stuck).status == "failed"
    assert "restarted" in run_store.get(stuck).error
    assert run_store.get(done).status == "passed"


def test_a_running_job_returns_its_progress():
    rid = f"prog-{uuid.uuid4().hex[:6]}"
    run_store.put(RunRecord(run_id=rid, pipeline="pdf", status="running", input_file="2 files"))
    set_progress(rid, stage="read", done=7, total=18, message="Reading page 7 of 18",
                 note="Gemini busy (free tier) - waiting 41 s")
    try:
        body = TestClient(app).get(f"/api/runs/{rid}").json()
    finally:
        clear_progress(rid)
    p = body["progress"]
    assert (p["stage"], p["done"], p["total"]) == ("read", 7, 18)
    assert p["note"].startswith("Gemini busy") and p["elapsed_s"] >= 0


def test_a_comparison_shows_its_pdf_run_progress_and_is_cleaned_up_after_a_restart():
    from core.compare_store import CompareRecord, compare_store
    cid, pdf = f"cmp-{uuid.uuid4().hex[:6]}", f"pdf-{uuid.uuid4().hex[:6]}"
    compare_store.put(CompareRecord(compare_id=cid, dxf_run_id="d", pdf_run_id=pdf, status="running"))
    set_progress(pdf, stage="classify", done=3, total=18, message="Sorting the pages")
    try:
        body = TestClient(app).get(f"/api/compare/{cid}").json()
    finally:
        clear_progress(pdf)
    assert body["pdf_progress"]["done"] == 3

    assert compare_store.fail_interrupted("The server restarted") >= 1
    assert compare_store.get(cid).status == "failed"


def test_a_finished_job_has_no_progress():
    rid = f"fin-{uuid.uuid4().hex[:6]}"
    run_store.put(RunRecord(run_id=rid, pipeline="dxf", status="passed", input_file="a.dxf"))
    assert TestClient(app).get(f"/api/runs/{rid}").json()["progress"] is None
