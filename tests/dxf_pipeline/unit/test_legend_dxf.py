"""
Tests for DXF legend extraction (agent/dxf_pipeline/passes/legend.py) and its
legend-coverage gap integration.
"""

from __future__ import annotations

import ezdxf
import pytest

from agent.dxf_pipeline.passes.legend import extract_legend, legend_block_counts
from agent.dxf_pipeline.passes.run import _add_legend_coverage_gaps
from agent.shared import BillOfQuantities, BQLineItem, BQSection


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
    boq = BillOfQuantities(pipeline="dxf", line_items=[
        BQLineItem(section=BQSection.POWER_OUTLETS, description="16A Double Switched Socket — Office", qty=3),
    ])
    _add_legend_coverage_gaps(boq, leg)
    gap_items = [g.description for g in boq.gaps]
    # the socket is billed → no gap; the flood light + switch are not → gaps
    assert not any("16A Double Switched Socket" in g for g in gap_items)
    assert any("LED Floodlight" in g for g in gap_items)
    assert any("1-Lever Switch" in g for g in gap_items)
