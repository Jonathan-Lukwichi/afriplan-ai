"""
Tests for the v2 DXF recognition pass and its helpers.

Covers the diagnosed bug fixes: electrical-layer isolation for cable length,
geometry-symbol recognition, circuit-tag parsing, and DWG-conversion fallback.
Uses a synthetic in-memory DXF (no fixture files) plus the real project DXF
when present.
"""

from __future__ import annotations

import math
import os

import ezdxf
import pytest

from agent.dxf_pipeline.dwg import ensure_dxf_bytes, is_dwg
from agent.dxf_pipeline.passes.recognize import recognise
from agent.dxf_pipeline.patterns import (
    classify_geometry_symbol,
    parse_circuit_tag,
)
from core.layer_aliases import (
    is_architectural_layer,
    is_electrical_layer,
    is_wiring_layer,
)


# ─── Circuit-tag parsing ─────────────────────────────────────────────

@pytest.mark.parametrize("text,expected", [
    ("DB-S3", (None, "DB-S3")),
    ("L1", ("L1", None)),
    ("L2 DB-S4", ("L2", "DB-S4")),
    ("P3", ("P3", None)),
    ("L-12", ("L12", None)),
    ("P8000", (None, None)),          # trunking code, not a circuit
    ("random text", (None, None)),
    ("", (None, None)),
])
def test_parse_circuit_tag(text, expected):
    assert parse_circuit_tag(text) == expected


# ─── Geometry symbol recognition (layer-driven) ──────────────────────

def test_circle_on_lighting_layer_is_a_light():
    spec = classify_geometry_symbol("CIRCLE", "E-LIGHTING")
    assert spec is not None and spec.category.value == "lighting"


def test_circle_on_wall_layer_is_not_a_symbol():
    assert classify_geometry_symbol("CIRCLE", "Walls_Exterior") is None


def test_line_is_never_a_geometry_symbol():
    assert classify_geometry_symbol("LINE", "E-LIGHTING") is None


# ─── Layer isolation ─────────────────────────────────────────────────

def test_architectural_layer_detection():
    assert is_architectural_layer("Walls_ Exterior_Pen_No__1") is True
    assert is_architectural_layer("Structural - Bearing") is True
    assert is_architectural_layer("B_ELECTRICAL WIRE") is False   # electrical wins


def test_electrical_layer_detection():
    assert is_electrical_layer("B_ELECTRICAL WIRE") is True
    assert is_electrical_layer("Walls_ Exterior") is False


def test_aia_layers_are_architectural():
    # Standard AIA discipline codes seen in the real Wedela Revit DWGs
    for lyr in ("A-DOOR", "P-SANR-FIXT", "C-PRKG", "S-COLS", "I-FURN", "A-GLAZ"):
        assert is_architectural_layer(lyr) is True, lyr


def test_wiring_vs_symbol_electrical_layer():
    # only actual wiring layers are measured for cable
    assert is_wiring_layer("B_ELECTRICAL WIRE") is True
    assert is_wiring_layer("E-CABLE") is True
    assert is_wiring_layer("PDF_MEP$$$Electrical") is False   # symbol layer, not wiring
    assert is_wiring_layer("E-LIGHTING") is False


def test_symbol_linework_on_nonwiring_layer_not_counted_as_cable():
    rec = recognise(_synthetic_doc())
    # the 9m symbol line on E-LIGHTING must not be counted; only the 5m wire is
    assert "E-LIGHTING" not in rec.cable_length_m_by_layer
    assert rec.electrical_cable_length_m == pytest.approx(5.0, abs=1e-6)


# ─── Recognition on a synthetic DXF ──────────────────────────────────

def _synthetic_doc():
    doc = ezdxf.new(setup=True)
    doc.header["$INSUNITS"] = 4  # mm
    msp = doc.modelspace()
    # a wall polyline on an architectural layer — must NOT count as cable
    msp.add_lwpolyline([(0, 0), (10000, 0)], dxfattribs={"layer": "Walls_Exterior"})
    # a cable run on a WIRING layer — 5000mm = 5m
    msp.add_line((0, 0), (5000, 0), dxfattribs={"layer": "E-CABLE-WIRE"})
    # symbol line-work on an electrical-but-not-wiring layer — must NOT count as cable
    msp.add_line((0, 0), (9000, 0), dxfattribs={"layer": "E-LIGHTING"})
    # a light drawn as a circle on the lighting layer
    msp.add_circle((100, 100), radius=150, dxfattribs={"layer": "E-LIGHTING"})
    # circuit tag text on the wiring layer
    msp.add_text("L1 DB-S3", dxfattribs={"layer": "E-CABLE-WIRE"}).set_placement((2500, 50))
    return doc


def test_cable_length_excludes_architectural_layers():
    rec = recognise(_synthetic_doc())
    # only the 5m electrical line counts; the 10m wall does not
    assert rec.electrical_cable_length_m == pytest.approx(5.0, abs=1e-6)
    assert "Walls_Exterior" not in rec.cable_length_m_by_layer


def test_geometry_light_recognised():
    rec = recognise(_synthetic_doc())
    assert any("light" in s.category for s in rec.symbols)


def test_circuit_tag_extracted_and_cable_assigned():
    rec = recognise(_synthetic_doc())
    assert "L1" in rec.circuit_ids()
    assert "DB-S3" in rec.db_refs()
    assert rec.cable_length_m_by_circuit.get("L1") == pytest.approx(5.0, abs=1e-6)


def test_units_mm_to_metre():
    rec = recognise(_synthetic_doc())
    assert rec.units_to_metre == 0.001


# ─── Real project DXF (skips gracefully if absent) ───────────────────

_REAL_DXF = "Electrical plan/DXF FILES/Firat Floor Lights 300925.dxf"


@pytest.mark.skipif(not os.path.exists(_REAL_DXF), reason="real DXF not present")
def test_real_dxf_measures_only_electrical_cable():
    doc = ezdxf.readfile(_REAL_DXF)
    rec = recognise(doc)
    # electrical-only total is well below the old wall-polluted 208.8m figure,
    # and it is concentrated on the electrical wiring layer
    assert rec.electrical_cable_length_m > 0
    assert any("ELECTRICAL" in lyr.upper() for lyr in rec.cable_length_m_by_layer)
    assert rec.circuit_ids()          # L1/L2/L3 present
    assert rec.db_refs()              # DB-S3/S4 present
    assert "P8000" not in rec.circuit_ids()   # trunking excluded


# ─── DWG conversion fallback ─────────────────────────────────────────

def test_is_dwg():
    assert is_dwg("x.dwg") and is_dwg("X.DWG")
    assert not is_dwg("x.dxf")


def test_ensure_dxf_passthrough_for_dxf():
    res = ensure_dxf_bytes(b"DXF-BYTES", "x.dxf")
    assert res.ok and res.dxf_bytes == b"DXF-BYTES"


def test_ensure_dxf_dwg_without_converter_returns_clear_error(monkeypatch):
    import agent.dxf_pipeline.dwg as dwgmod
    monkeypatch.setattr(dwgmod, "find_dwg2dxf", lambda: None)
    monkeypatch.setattr(dwgmod, "find_oda_converter", lambda: None)
    res = ensure_dxf_bytes(b"DWGDATA", "x.dwg")
    assert res.ok is False
    assert "converter" in res.error.lower()
