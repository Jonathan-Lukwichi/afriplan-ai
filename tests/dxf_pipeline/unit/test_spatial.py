"""
Tests for the spatial pass (agent/dxf_pipeline/passes/spatial.py):
room-region extraction, point-in-polygon, shoelace area, and symbol assignment.
"""

from __future__ import annotations

import ezdxf
import pytest

from agent.dxf_pipeline.passes.recognize import DxfRecognition, RecognisedSymbol
from agent.dxf_pipeline.passes.spatial import (
    assign_spatial,
    extract_room_regions,
    _point_in_polygon,
    _shoelace_area,
)


# ─── geometry primitives ─────────────────────────────────────────────

def test_shoelace_area_of_rectangle():
    poly = [(0, 0), (4, 0), (4, 3), (0, 3)]
    assert _shoelace_area(poly) == 12.0


def test_point_in_polygon():
    sq = [(0, 0), (10, 0), (10, 10), (0, 10)]
    assert _point_in_polygon(5, 5, sq) is True
    assert _point_in_polygon(15, 5, sq) is False


def test_point_in_polygon_needs_three_points():
    assert _point_in_polygon(1, 1, [(0, 0), (2, 2)]) is False


# ─── room extraction ─────────────────────────────────────────────────

def _doc_with_rooms():
    doc = ezdxf.new(setup=True)
    doc.header["$INSUNITS"] = 4  # mm
    msp = doc.modelspace()
    # a 5000 x 4000 mm room polygon on an area layer, labelled OFFICE
    msp.add_lwpolyline(
        [(0, 0), (5000, 0), (5000, 4000), (0, 4000)],
        close=True, dxfattribs={"layer": "A-AREA"},
    )
    msp.add_text("OFFICE", dxfattribs={"layer": "A-AREA-IDEN"}).set_placement((2500, 2000))
    # a far-away room label with no polygon (point region)
    msp.add_text("STORE", dxfattribs={"layer": "Text_ Room Names"}).set_placement((20000, 20000))
    return doc


def test_extract_named_polygon_with_area():
    doc = _doc_with_rooms()
    regions = extract_room_regions(doc, units_to_metre=0.001)
    office = [r for r in regions if r.name == "OFFICE"]
    assert office and office[0].polygon is not None
    # 5m x 4m = 20 m² (mm² × 0.001² )
    assert office[0].area_m2 == pytest.approx(20.0, abs=0.01)


def test_extract_point_region_for_unbounded_label():
    regions = extract_room_regions(_doc_with_rooms(), units_to_metre=0.001)
    store = [r for r in regions if r.name == "STORE"]
    assert store and store[0].polygon is None


# ─── assignment ──────────────────────────────────────────────────────

def _rec_with_symbols(coords):
    rec = DxfRecognition(units_to_metre=0.001)
    for (x, y) in coords:
        rec.symbols.append(RecognisedSymbol(
            canonical_name="Double Socket", category="power", layer="E-POWER",
            x=x, y=y, source="block",
        ))
    return rec


def test_symbol_inside_polygon_assigned_to_that_room():
    doc = _doc_with_rooms()
    rec = _rec_with_symbols([(2500, 2000)])   # inside OFFICE polygon
    result = assign_spatial(rec, doc, building="Block A")
    assert rec.symbols[0].room == "OFFICE"
    assert rec.symbols[0].building == "Block A"
    assert result.counts_by_room["OFFICE"]["Double Socket"] == 1


def test_symbol_outside_polygons_goes_to_nearest_label():
    doc = _doc_with_rooms()
    rec = _rec_with_symbols([(20500, 20500)])  # near STORE label, outside OFFICE
    assign_spatial(rec, doc, building="Block A")
    assert rec.symbols[0].room == "STORE"


def test_building_tag_applied_to_all_symbols():
    doc = _doc_with_rooms()
    rec = _rec_with_symbols([(2500, 2000), (20500, 20500)])
    assign_spatial(rec, doc, building="Ablution Block")
    assert all(s.building == "Ablution Block" for s in rec.symbols)


def test_no_rooms_leaves_symbols_unassigned():
    doc = ezdxf.new(setup=True)
    rec = _rec_with_symbols([(1, 1)])
    result = assign_spatial(rec, doc, building="X")
    assert rec.symbols[0].room == ""
    assert "(unassigned)" in result.counts_by_room
