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


def _building(dn: int):
    """A legend row keyed 'D/N', and that label on the plan."""
    doc = ezdxf.new(setup=True)
    doc.header["$INSUNITS"] = 4
    msp = doc.modelspace()

    def text(s, x, y, h=231):
        msp.add_text(s, height=h, dxfattribs={"layer": "PDF_Text"}).set_placement((x, y))

    text("D/N", 1000, 5000)
    text("Day/night switch @ 2000mm Abone FFL.", 2300, 4900)
    for i in range(dn):
        text("D/N", 30000 + i * 5000, 20000)
    return doc


def test_the_row_of_a_key_is_the_nearest_description_a_table_width_away():
    """Real legends leave about ten text heights between a key and its row."""
    from agent.dxf_pipeline.passes.labels import _row_description, _Text
    key = _Text("D/N", 1000, 5000, 146)
    near = _Text("Day/night switch", 2512, 4900, 146)
    far = _Text("30W LED flood light", 2700, 4900, 146)
    assert _row_description(key, [far, near]) == near.text
    assert _row_description(key, [_Text("Next column", 12000, 4900, 146)]) == ""


def test_a_two_way_switch_is_not_a_plain_switch():
    from agent.shared.legend import classify_description
    assert classify_description("1lever ,2 Way Switch @ 1200mm above FFL.")[0] == "1-Lever 2-Way Switch"
    assert classify_description("1lever ,1 Way Switch @ 1200mm above FFL.")[0] == "1-Lever Switch"


def test_a_label_with_a_slash_counts_too():
    assert [(f.label, f.qty) for f in count_labelled_fittings(_building(2))] == [("D/N", 2)]


def test_a_day_night_switch_is_priced_as_a_switch():
    from agent.shared.symbol_catalogue import catalogue_item
    from core import constants
    run = run_dxf_estimator(_bytes(_building(2)), "WD-AB-01-LIGHTING.dxf")
    [line] = [l for l in run.boq.line_items if "Day/night" in l.description]
    assert catalogue_item("Day/Night Switch").price_map == "switch"
    assert line.qty == 2 and line.unit_price_zar > 0
    assert constants.SWITCH_PRICES.get(catalogue_item("Day/Night Switch").price_key, 0) > 0


def test_the_same_label_in_different_buildings_adds_up():
    """One building's lighting and plug sheets repeat a fitting; two buildings do not."""
    run = run_dxf_project([(_bytes(_building(2)), "WD-AB-01-LIGHTING 250325.dxf"),
                           (_bytes(_building(2)), "WD-AB-01-PLUG 250325.dxf"),
                           (_bytes(_building(1)), "WD-LGH-01-LIGHTING 280225.dxf")])
    assert sum(l.qty for l in run.boq.line_items if "Day/night" in l.description) == pytest.approx(3)


def test_a_labelled_fitting_is_not_counted_again_as_a_named_shape():
    doc = _building(2)
    msp = doc.modelspace()
    for i in range(3):
        x = 30000 + i * 5000
        msp.add_circle((x, 40000), 300, dxfattribs={"layer": "E-LIGHTING"})
        msp.add_line((x - 300, 40000), (x + 300, 40000), dxfattribs={"layer": "E-LIGHTING"})

    def namer(groups, legend_lines):
        return {g.signature: ("Day/Night Switch", "ai") for g in groups}, 0.0

    run = run_dxf_project([(_bytes(doc), "WD-AB-01-LIGHTING.dxf")], name_shapes=namer)
    assert sum(l.qty for l in run.boq.line_items if "day/night" in l.description.lower()) == pytest.approx(2)


def test_solar_post_lights_and_high_masts_have_their_own_names_in_the_legend():
    from agent.shared.legend import classify_description
    assert classify_description(SOLAR)[0] == "Solar Post Light"
    assert classify_description(MAST)[0] == "High-Mast Light"
    assert classify_description("30W LED flood light")[0] == "LED Floodlight"     # plain floods unchanged
