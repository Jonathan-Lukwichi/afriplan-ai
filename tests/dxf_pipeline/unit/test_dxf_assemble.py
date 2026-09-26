"""
Tests for the v2 DXF assembler + run entry.

Key guarantees: DXF quantities are EXTRACTED (measured), not ASSUMED; the bill
is deterministic; DBs emit gaps for unknown ratings; the run entry ties
conversion → recognition → assembly and handles the no-content case.
"""

from __future__ import annotations

import ezdxf
import pytest

from agent.dxf_pipeline.passes.assemble import build_boq_from_recognition
from agent.dxf_pipeline.passes.recognize import recognise
from agent.dxf_pipeline.passes.run import run_dxf_estimator
from agent.shared import BQSection, ItemConfidence, LineKind


def _doc_with_electrical():
    doc = ezdxf.new(setup=True)
    doc.header["$INSUNITS"] = 4  # mm
    msp = doc.modelspace()
    msp.add_lwpolyline([(0, 0), (10000, 0)], dxfattribs={"layer": "Walls"})     # ignored
    msp.add_line((0, 0), (5000, 0), dxfattribs={"layer": "E-CABLE-WIRE"})        # 5 m L1
    msp.add_text("L1 DB-S3", dxfattribs={"layer": "E-CABLE-WIRE"}).set_placement((2500, 10))
    # two recognised socket blocks
    for i in range(2):
        blk_name = "Socket Outlet 2 Gangs"
        if blk_name not in doc.blocks:
            doc.blocks.new(blk_name)
        msp.add_blockref(blk_name, (i * 1000, 0), dxfattribs={"layer": "E-POWER"})
    return doc


def _dxf_bytes(doc) -> bytes:
    import io
    s = io.StringIO()
    doc.write(s)
    return s.getvalue().encode("utf-8")


def _bill():
    return build_boq_from_recognition(recognise(_doc_with_electrical()), project_name="T")


# ─── Provenance: measured, not assumed ───────────────────────────────

def test_all_dxf_lines_are_extracted_not_assumed():
    boq = _bill()
    assert boq.line_items
    assert all(l.source == ItemConfidence.EXTRACTED for l in boq.line_items)
    assert boq.items_assumed == 0


def test_reticulation_cable_is_measured():
    boq = _bill()
    retic = [l for l in boq.line_items if l.section == BQSection.FINAL_CABLES]
    assert retic
    # 5m line on circuit L1 → measured qty, EXTRACTED
    l1 = [l for l in retic if "L1" in l.description]
    assert l1 and l1[0].qty == pytest.approx(5.0, abs=1e-6)
    assert l1[0].source == ItemConfidence.EXTRACTED


def test_socket_count_is_exact():
    boq = _bill()
    sockets = [l for l in boq.line_items if "Socket" in l.description]
    assert sockets and sockets[0].qty == 2.0


# ─── DBs → lines + gaps ──────────────────────────────────────────────

def test_db_line_and_gap_emitted():
    boq = _bill()
    dbs = [l for l in boq.line_items if l.section == BQSection.DISTRIBUTION]
    assert any("DB-S3" in l.description for l in dbs)
    assert any("rating" in g.description.lower() for g in boq.gaps)


# ─── Totals ──────────────────────────────────────────────────────────

def test_totals_contingency_and_vat():
    boq = _bill()
    assert boq.subtotal_zar > 0
    assert boq.contingency_zar == pytest.approx(boq.subtotal_zar * 0.05, abs=0.01)
    assert boq.vat_zar == pytest.approx(boq.total_excl_vat_zar * 0.15, abs=0.01)


# ─── Determinism ─────────────────────────────────────────────────────

def test_same_recognition_identical_bill():
    rec = recognise(_doc_with_electrical())
    a = build_boq_from_recognition(rec, project_name="T", run_id="x")
    b = build_boq_from_recognition(rec, project_name="T", run_id="x")
    assert a.model_dump(exclude={"generated_at"}) == b.model_dump(exclude={"generated_at"})


# ─── Run entry ───────────────────────────────────────────────────────

def test_run_dxf_estimator_end_to_end():
    run = run_dxf_estimator(_dxf_bytes(_doc_with_electrical()), "test.dxf")
    assert run.success is True
    assert run.boq is not None and run.boq.line_items
    assert run.electrical_cable_length_m == pytest.approx(5.0, abs=1e-6)
    assert "DB-S3" in run.db_refs
    assert run.converted_from_dwg is False


def test_run_dxf_estimator_dwg_without_converter(monkeypatch):
    import agent.dxf_pipeline.dwg as dwgmod
    monkeypatch.setattr(dwgmod, "find_dwg2dxf", lambda: None)
    monkeypatch.setattr(dwgmod, "find_oda_converter", lambda: None)
    run = run_dxf_estimator(b"DWGDATA", "drawing.dwg")
    assert run.success is False
    assert "converter" in (run.error or "").lower()


def test_markup_is_declared_as_baked_into_rates():
    """Built-up rates already carry the x1.3 material markup: no second markup (issue 009)."""
    boq = _bill()
    assert boq.contractor_markup_pct == 0.0 and boq.markup_zar == 0.0
