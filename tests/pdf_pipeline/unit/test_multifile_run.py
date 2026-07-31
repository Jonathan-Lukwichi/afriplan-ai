"""
Tests for the v2 multi-file ingest, file classifier, and run entry
(agent/pdf_pipeline/passes/run.py). All offline via MockAnthropic.
"""

from __future__ import annotations

import fitz  # PyMuPDF
import pytest

from agent.pdf_pipeline.models import PageType
from agent.pdf_pipeline.passes.run import (
    classify_files,
    ingest_files,
    run_pdf_estimator,
)


def _pdf(titles) -> bytes:
    doc = fitz.open()
    for t in titles:
        page = doc.new_page(width=595, height=842)
        page.insert_text((50, 100), t, fontsize=20)
    data = doc.tobytes()
    doc.close()
    return data


PROJECT_CTX = {"project_name": "Wedela", "buildings": ["Hall"], "free_issue_items": []}
POWER_SPINE = {
    "distribution_boards": [{"name": "DB-CR", "main_breaker_a": 250, "phases": 3, "circuits": [], "confidence": 0.9}],
    "feeders": [{"from_source": "Mini-Sub", "to_db": "DB-CR", "cable_size_mm2": 95,
                 "cable_cores": 4, "earth_size_mm2": 70, "length_m": 35,
                 "length_annotated": True, "is_underground": True}],
    "incoming_supply": {"supply_source": "mini_sub", "kiosk_present": True, "meter_count": 1},
}
LAYOUT = {"rooms": [{"room_name": "Hall", "served_by_db": "DB-CR",
                     "panel_lights": 4, "double_sockets": 6, "confidence": 0.9}]}


# ─── ingest_files ────────────────────────────────────────────────────

def test_ingest_files_gives_global_indices():
    files = [(_pdf(["A", "B"]), "one.pdf"), (_pdf(["C"]), "two.pdf")]
    pages, file_ingests = ingest_files(files)
    assert [p.page_index for p in pages] == [0, 1, 2]     # globally unique
    assert file_ingests[0].file_name == "one.pdf"
    assert file_ingests[1].first_global_index == 2
    assert len(file_ingests[1].pages) == 1


# ─── classify_files: manual override forces all pages ────────────────

def test_manual_tag_forces_file_type(mock_llm):
    files = [(_pdf(["p1", "p2", "p3"]), "mystery.pdf")]
    _, file_ingests = ingest_files(files)
    llm = mock_llm()  # would classify "unknown" — but manual overrides
    page_classes, file_classes, costs = classify_files(
        llm, file_ingests, manual_types={"mystery.pdf": "sld"}
    )
    assert costs == []                                   # no LLM calls when tagged
    assert all(pc.page_type == PageType.SLD for pc in page_classes)
    assert file_classes[0].manual is True
    assert file_classes[0].sheet_type == PageType.SLD


def test_low_confidence_file_flagged_for_manual(mock_llm):
    files = [(_pdf(["p1", "p2"]), "blurry.pdf")]
    _, file_ingests = ingest_files(files)
    # default mock classify returns confidence 0.5 (< floor 0.6)
    llm = mock_llm()
    _, file_classes, _ = classify_files(llm, file_ingests)
    assert file_classes[0].needs_manual is True


# ─── run_pdf_estimator: full set → priced bill ───────────────────────

def test_run_estimator_over_a_set(mock_llm):
    files = [(_pdf(["SLD"]), "sld.pdf"), (_pdf(["Layout"]), "layout.pdf")]
    llm = mock_llm(tool_responses={
        "read_project_context": PROJECT_CTX,
        "read_power_spine": POWER_SPINE,
        "read_layout_takeoff": LAYOUT,
    })
    run = run_pdf_estimator(
        files, llm=llm,
        manual_types={"sld.pdf": "sld", "layout.pdf": "lighting_layout"},
    )
    assert run.success is True
    assert run.boq is not None and run.boq.line_items
    assert run.boq.total_incl_vat_zar > 0
    assert run.page_count == 2
    assert len(run.files) == 2
    # the 35m feeder survived end-to-end through the multi-file path
    assert any(l.qty == 35.0 for l in run.boq.line_items)


def test_run_estimator_no_pages_fails_gracefully(mock_llm):
    # No files at all → no pages → graceful failure, not a crash
    run = run_pdf_estimator([], llm=mock_llm())
    assert run.success is False
    assert "no pages" in (run.error or "").lower()


def test_run_estimator_is_deterministic_given_same_facts(mock_llm):
    files = [(_pdf(["SLD"]), "sld.pdf")]
    responses = {"read_power_spine": POWER_SPINE}
    llm1 = mock_llm(tool_responses=responses)
    llm2 = mock_llm(tool_responses=responses)
    r1 = run_pdf_estimator(files, llm=llm1, manual_types={"sld.pdf": "sld"})
    r2 = run_pdf_estimator(files, llm=llm2, manual_types={"sld.pdf": "sld"})
    # Bills must match (exclude wall-clock + random run_id provenance)
    assert r1.boq.model_dump(exclude={"generated_at", "run_id"}) == \
           r2.boq.model_dump(exclude={"generated_at", "run_id"})
