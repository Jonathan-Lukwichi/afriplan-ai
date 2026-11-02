"""Fittings identified by a short label: the legend row beside the label says what it is, and each
copy of the label on the plan is one fitting. Synthetic sheets, no client data."""

from __future__ import annotations

import io

import ezdxf
import pytest

from agent.dxf_pipeline.passes.labels import count_labelled_fittings
from agent.dxf_pipeline.passes.run import run_dxf_estimator, run_dxf_project

SOLAR = "100W LED Solar power light post lantern"
MAST = "2x600W LED flood light, 10m post Hight Masts"


def _sheet(solar: int = 3, mast: int = 2):
    doc = ezdxf.new(setup=True)
    doc.header["$INSUNITS"] = 4
    msp = doc.modelspace()

    def text(s, x, y, h=146):
        msp.add_text(s, height=h, dxfattribs={"layer": "PDF_Text"}).set_placement((x, y))

    # the legend table: label, then its description to the right on the same row
    text("FL", 1000, 5000); text(MAST, 1700, 4950, 231)
    text("PS", 1000, 4400); text(SOLAR, 1700, 4380, 231)
    text("MS", 11000, 5000); text("Master switch", 11700, 4950, 231)
    # the plan
    for i in range(solar):
        text("PS", 30000 + i * 5000, 20000)
    for i in range(mast):
        text("FL", 30000 + i * 5000, 40000)
    for i in range(2):
        text("MS", 60000 + i * 5000, 40000)
    text("UP", 70000, 40000)         # a label no legend row explains
    return doc


def _bytes(doc) -> bytes:
    s = io.StringIO()
    doc.write(s)
    return s.getvalue().encode("utf-8")


def test_each_label_on_the_plan_is_one_fitting_and_the_legend_copy_is_not():
    found = {f.description: f.qty for f in count_labelled_fittings(_sheet())}
    assert found == {SOLAR: 3, MAST: 2}


def test_a_legend_row_with_nothing_on_the_plan_is_not_a_fitting():
    assert {f.description: f.qty for f in count_labelled_fittings(_sheet(solar=0))} == {MAST: 2}


def test_labelled_lights_reach_the_bill_at_their_real_price():
    run = run_dxf_estimator(_bytes(_sheet()), "WD-PB-01-LIGHTING.dxf")
    [solar] = [l for l in run.boq.line_items if "Solar" in l.description]
    assert solar.qty == 3 and solar.unit_price_zar > 18000     # solar_post_light_100w + markup


def test_lights_repeated_on_two_sheets_of_a_set_count_once_at_the_higher_count():
    """A lighting and a plug sheet of one building share the background (skill: count once)."""
    run = run_dxf_project([(_bytes(_sheet(solar=3)), "WD-PB-01-LIGHTING.dxf"),
                           (_bytes(_sheet(solar=2)), "WD-PB-01-PLUG.dxf")])
    assert sum(l.qty for l in run.boq.line_items if "Solar" in l.description) == pytest.approx(3)


def test_solar_post_lights_and_high_masts_have_their_own_names_in_the_legend():
    from agent.shared.legend import classify_description
    assert classify_description(SOLAR)[0] == "Solar Post Light"
    assert classify_description(MAST)[0] == "High-Mast Light"
    assert classify_description("30W LED flood light")[0] == "LED Floodlight"     # plain floods unchanged
