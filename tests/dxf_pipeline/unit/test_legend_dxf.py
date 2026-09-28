"""
Tests for DXF legend extraction (agent/dxf_pipeline/passes/legend.py) and its
legend-coverage gap integration.
"""

from __future__ import annotations

import ezdxf
import pytest

from agent.dxf_pipeline.passes.legend import extract_legend, legend_block_counts
from agent.dxf_pipeline.passes.run import _legend_coverage_gaps
from agent.shared import BQSection
from agent.shared.findings import Findings, ItemFinding


def _doc_with_legend():
    doc = ezdxf.new(setup=True)
    msp = doc.modelspace()
    # a legend column of descriptions
    msp.add_text("16A Double Switched Socket @300mm", dxfattribs={"layer": "LEGEND"}).set_placement((1000, 900))
    msp.add_text("30W LED flood light", dxfattribs={"layer": "LEGEND"}).set_placement((1000, 800))
    msp.add_text("1 lever 1 way switch", dxfattribs={"layer": "LEGEND"}).set_placement((1000, 700))
    msp.add_text("LIGHTS", dxfattribs={"layer": "LEGEND"}).set_placement((1000, 1000))  # header
    # a switch block glyph next to the switch description
    if "SW" not in doc.blocks:
        doc.blocks.new("SW")
    msp.add_blockref("SW", (950, 700), dxfattribs={"layer": "LEGEND"})
    # two switch instances out in the plan
    msp.add_blockref("SW", (5000, 5000), dxfattribs={"layer": "E-POWER"})
    msp.add_blockref("SW", (6000, 5000), dxfattribs={"layer": "E-POWER"})
    return doc


def test_legend_dictionary_built_from_text():
    leg = extract_legend(_doc_with_legend())
    items = {e.canonical_item for e in leg.entries}
    assert "16A Double Switched Socket" in items
    assert "LED Floodlight" in items
    assert "1-Lever Switch" in items
    # header is not an item
    assert all(e.canonical_item != "LIGHTS" for e in leg.entries)


def test_block_paired_and_counted():
    doc = _doc_with_legend()
    leg = extract_legend(doc)
    sw = [e for e in leg.entries if e.canonical_item == "1-Lever Switch"]
    assert sw and sw[0].symbol_key == "SW"
    counts = legend_block_counts(doc, leg)
    assert counts.get("1-Lever Switch") == 2   # two SW instances in the plan


def test_exploded_legend_yields_no_false_block_counts():
    # legend text but NO blocks → no block counts (honest; needs geometry matching)
    doc = ezdxf.new(setup=True)
    doc.modelspace().add_text(
        "16A Double Switched Socket", dxfattribs={"layer": "LEGEND"}
    ).set_placement((0, 0))
    leg = extract_legend(doc)
    assert leg.entries and leg.entries[0].symbol_key == ""
    assert legend_block_counts(doc, leg) == {}


def test_legend_coverage_gaps_flag_uncounted_items():
    leg = extract_legend(_doc_with_legend())
    found = Findings(items=[
        ItemFinding(section=BQSection.POWER_OUTLETS, description="16A Double Switched Socket — Office", qty=3),
    ])
    gap_items = [g.description for g in _legend_coverage_gaps(found, leg)]
    # the socket is billed → no gap; the flood light + switch are not → gaps
    assert not any("16A Double Switched Socket" in g for g in gap_items)
    assert any("LED Floodlight" in g for g in gap_items)
    assert any("1-Lever Switch" in g for g in gap_items)


# ─── legend region: glyphs in the legend table are not plan symbols (issue 006) ──

def _doc_legend_and_plan():
    doc = _doc_with_legend()
    msp = doc.modelspace()
    # a DB label out on the plan is classifiable text too — must not stretch the region
    msp.add_text("DB-AB1", dxfattribs={"layer": "E-POWER"}).set_placement((20000, 20000))
    # like the Wedela Revit exports: a legend glyph on the ELECTRICAL layer
    msp.add_blockref("SW", (955, 900), dxfattribs={"layer": "E-POWER"})
    doc.header["$EXTMIN"] = (0, 0, 0)
    doc.header["$EXTMAX"] = (25000, 25000, 0)
    return doc


def test_legend_region_covers_the_table_not_the_plan():
    from agent.dxf_pipeline.passes.legend import legend_region, in_region
    region = legend_region(_doc_legend_and_plan())
    assert region is not None
    assert in_region(950, 700, region)            # the glyph beside its description
    assert not in_region(5000, 5000, region)      # a plan instance
    assert not in_region(20000, 20000, region)    # the stray DB label


def test_run_excludes_legend_glyphs_from_the_bill():
    import io
    from agent.dxf_pipeline.passes.run import run_dxf_estimator
    doc = _doc_legend_and_plan()
    s = io.StringIO(); doc.write(s)
    run = run_dxf_estimator(s.getvalue().encode(), "WD-X-01-LIGHTING.dxf")
    assert run.symbol_count == 2                  # the two plan switches, not the legend glyph
