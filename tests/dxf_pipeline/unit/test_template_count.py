"""
Tests for LDSE mode 3 — legend-glyph template counting
(agent/dxf_pipeline/passes/template_count.py) and its run integration.
"""

from __future__ import annotations

import io

import ezdxf
import pytest

from agent.dxf_pipeline.passes.legend import extract_legend
from agent.dxf_pipeline.passes.template_count import count_by_template
from agent.dxf_pipeline.passes.run import run_dxf_estimator
from agent.shared import ItemConfidence

cv2 = pytest.importorskip("cv2")


def _add_downlight(msp, cx, cy, layer="E-LIGHTING"):
    """A distinctive 3-entity glyph: circle + a cross."""
    msp.add_circle((cx, cy), radius=100, dxfattribs={"layer": layer})
    msp.add_line((cx - 100, cy), (cx + 100, cy), dxfattribs={"layer": layer})
    msp.add_line((cx, cy - 100), (cx, cy + 100), dxfattribs={"layer": layer})


def _doc_with_n_downlights(n: int):
    doc = ezdxf.new(setup=True)
    doc.header["$INSUNITS"] = 4
    doc.header["$EXTMIN"] = (0, 0, 0)
    doc.header["$EXTMAX"] = (20000, 20000, 0)
    msp = doc.modelspace()
    # legend: glyph + description
    _add_downlight(msp, 300, 18000)
    msp.add_text("6W LED downlight", dxfattribs={"layer": "LEGEND"}).set_placement((700, 18000))
    # n instances in the plan
    for i in range(n):
        _add_downlight(msp, 2000 + (i % 5) * 2500, 2000 + (i // 5) * 2500)
    return doc


def test_counts_distinctive_glyph_instances():
    doc = _doc_with_n_downlights(5)
    counts = count_by_template(doc, extract_legend(doc))
    assert counts.get("LED Downlight") == 5   # legend glyph excluded


def test_decoy_shape_not_matched():
    doc = _doc_with_n_downlights(3)
    # add a plain square that should not match the downlight glyph
    doc.modelspace().add_lwpolyline(
        [(15000, 15000), (15400, 15000), (15400, 15400), (15000, 15400)],
        close=True, dxfattribs={"layer": "E-LIGHTING"},
    )
    counts = count_by_template(doc, extract_legend(doc))
    assert counts.get("LED Downlight") == 3


def test_simple_glyph_is_gated_out():
    # a 1-entity glyph (single circle) is too generic → not matched (no garbage)
    doc = ezdxf.new(setup=True)
    doc.header["$INSUNITS"] = 4
    doc.header["$EXTMIN"] = (0, 0, 0); doc.header["$EXTMAX"] = (20000, 20000, 0)
    msp = doc.modelspace()
    msp.add_circle((300, 18000), radius=80, dxfattribs={"layer": "E-LIGHTING"})
    msp.add_text("6W LED downlight", dxfattribs={"layer": "LEGEND"}).set_placement((700, 18000))
    for i in range(4):
        msp.add_circle((2000 + i * 2000, 2000), radius=80, dxfattribs={"layer": "E-LIGHTING"})
    counts = count_by_template(doc, extract_legend(doc))
    assert counts == {}                        # gated: too simple to be reliable


def test_no_legend_returns_empty():
    doc = ezdxf.new(setup=True)
    from agent.shared.legend import Legend
    assert count_by_template(doc, Legend()) == {}


# ─── run integration ─────────────────────────────────────────────────

def test_template_counts_flow_into_the_bill():
    doc = _doc_with_n_downlights(6)
    s = io.StringIO(); doc.write(s)
    run = run_dxf_estimator(s.getvalue().encode("utf-8"), "lights.dxf")
    assert run.success
    tm = [l for l in run.boq.line_items if "template-matched" in l.description]
    assert tm, "expected a template-matched line"
    dl = [l for l in tm if "LED Downlight" in l.description]
    assert dl and dl[0].qty == 6
    assert dl[0].source == ItemConfidence.INFERRED
    # counted → NOT flagged as an uncounted-legend gap
    assert not any("LED Downlight" in g.description for g in run.boq.gaps)
