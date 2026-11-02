"""A building's lighting and plug sheets are one building: its conduit is one line, and each building's
can be compared with a bill. Synthetic sheets, no client data."""

from __future__ import annotations

import io

import ezdxf
import pytest

from agent.dxf_pipeline.passes.run import building_of_sheet, run_dxf_project


def _sheet(tag: str, metres: float) -> bytes:
    doc = ezdxf.new(setup=True)
    doc.header["$INSUNITS"] = 4  # mm
    msp = doc.modelspace()
    msp.add_line((0, 0), (metres * 1000, 0), dxfattribs={"layer": "E-CABLE-WIRE"})
    msp.add_text(tag, dxfattribs={"layer": "E-CABLE-WIRE"}).set_placement((1000, 200))
    s = io.StringIO()
    doc.write(s)
    return s.getvalue().encode()


def _conduit(run):
    return [l for l in run.boq.line_items if "PVC conduit" in l.description]


@pytest.mark.parametrize("name, building", [
    ("WD-AB-01-LIGHTING 250325.dwg", "WD-AB-01"),
    ("WD-AB-01-PLUG 250325.dwg", "WD-AB-01"),
    ("WD-PB-01-LIGHTING  100425.dwg", "WD-PB-01"),
    ("WD-SGH-01-POWER 280225.dwg", "WD-SGH-01"),
    ("Site Plan.dwg", "Site Plan"),
])
def test_a_sheets_building_is_its_name_without_the_discipline(name, building):
    assert building_of_sheet(name) == building


def test_a_buildings_lighting_and_plug_conduit_are_one_line():
    run = run_dxf_project([(_sheet("L1", 40), "WD-AB-01-LIGHTING 250325.dxf"),
                           (_sheet("P1", 25), "WD-AB-01-PLUG 250325.dxf")])
    [line] = _conduit(run)
    assert line.description.endswith("WD-AB-01") and line.qty == pytest.approx(65)


def test_two_buildings_keep_two_conduit_lines():
    run = run_dxf_project([(_sheet("L1", 40), "WD-AB-01-LIGHTING 250325.dxf"),
                           (_sheet("L1", 12), "WD-SGH-01-LIGHTING 280225.dxf")])
    assert sorted(l.qty for l in _conduit(run)) == pytest.approx([12, 40])


def test_every_conduit_line_names_its_building():
    run = run_dxf_project([(_sheet("P1", 25), "WD-AB-01-PLUG 250325.dxf"),
                           (_sheet("P1", 9), "WD-SGH-01-PLUG 280225.dxf")])
    assert all(" — WD-" in l.description for l in _conduit(run))
