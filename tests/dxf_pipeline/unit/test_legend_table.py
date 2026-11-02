"""The legend table is the drawing's own dictionary: found whole, and it names the symbols beside its
rows without any AI. Synthetic sheets, no client data."""

from __future__ import annotations

import io

import ezdxf
import pytest

from agent.dxf_pipeline.passes.legend import in_region, legend_region
from agent.dxf_pipeline.passes.run import run_dxf_project
from agent.dxf_pipeline.passes.shapes import legend_shape_names, shape_kind

FLOOD = "30W LED flood light"
BULKHEAD = "26W Bulkhead Light Outdoor"


@pytest.fixture(autouse=True)
def _no_template_matching(monkeypatch):
    """Not under test here, and it renders the whole plan at symbol scale: minutes on these sheets."""
    monkeypatch.setattr("agent.dxf_pipeline.passes.run.count_by_template", lambda *a, **k: {})


def _flood(msp, x, y, r=6.0):
    """Two circles and four lines: distinctive enough to be named from its legend row."""
    msp.add_circle((x, y), r)
    msp.add_circle((x, y), r * 0.5)
    for dx, dy in ((1, 1), (1, -1), (-1, 1), (-1, -1)):
        msp.add_line((x, y), (x + dx * r * 0.7, y + dy * r * 0.7))


def _board(msp, x, y, s=12.0):
    msp.add_lwpolyline([(x, y), (x + s, y), (x + s, y + s / 2), (x, y + s / 2)], close=True)
    msp.add_line((x, y), (x + s, y + s / 2))
    msp.add_line((x, y + s / 2), (x + s, y))
    msp.add_line((x + s / 2, y), (x + s / 2, y + s / 2))


def _sheet(*, floods: int = 3, doors: int = 4, board_symbols: int = 2, flood_glyph: bool = True):
    """A 4-column legend (the columns far enough apart to cluster separately), then the plan."""
    doc = ezdxf.new(setup=True)
    doc.header["$EXTMIN"] = (0, 0, 0)
    doc.header["$EXTMAX"] = (20000, 20000, 0)
    msp = doc.modelspace()

    def text(s, x, y, h=23.1):
        msp.add_text(s, height=h, dxfattribs={"layer": "PDF_Text"}).set_placement((x, y))

    columns = [
        (2000, ("1 lever 1 Way Switch @ 1200mm", "2 lever 1 Way Switch @ 1200mm", "30A Isolator Switch")),
        (3100, ("16A Single Switched Socket", "16A Double Switched Socket", "16A Single Switched Socket @1100mm")),
        (4200, (FLOOD, BULKHEAD, "6W LED downlight white colour")),
        (5300, ("Distribution Board", "50L Geyser", "Air Conditioning Unit")),
    ]
    for x, rows in columns:
        for i, row in enumerate(rows):
            text(row, x, 19000 - i * 60)
    text("DB-AB1", 19000, 100)                                        # a label far out on the plan, as real sheets have
    if flood_glyph:
        _flood(msp, 4200 - 70, 19000)                           # the glyph left of its row
    _board(msp, 5300 - 70, 19000)
    msp.add_lwpolyline([(5230, 18880), (5245, 18880), (5245, 18890), (5230, 18890)], close=True)  # A/C: a box

    for i in range(floods):
        _flood(msp, 2000 + i * 100, 17000, r=5.0)                 # same shape, drawn a little smaller
    for i in range(board_symbols):
        _board(msp, 2000 + i * 100, 17200, s=10.0)
    for i in range(doors):                                            # plain boxes: doors, windows
        x = 2000 + i * 100
        msp.add_lwpolyline([(x, 17400), (x + 12, 17400), (x + 12, 17408), (x, 17408)], close=True)
    return doc


def _bytes(doc) -> bytes:
    s = io.StringIO()
    doc.write(s)
    return s.getvalue().encode("utf-8")


def test_the_legend_region_takes_in_every_column_of_the_table():
    region = legend_region(_sheet())
    assert all(in_region(x, 19000, region) for x in (2000, 3100, 4200, 5300))
    assert in_region(4200 - 70, 19000, region)                     # a glyph of the third column
    assert not in_region(2000, 17000, region)                       # a symbol on the plan


def test_columns_a_little_over_four_gaps_apart_are_one_table():
    """A real sheet: columns 10 263 units apart, on a 125 923 unit drawing."""
    from agent.dxf_pipeline.passes.legend import _whole_table
    column = [(0.0, 0.0), (0.0, 100.0), (0.0, 200.0)]
    beside = [(408.0, y) for _, y in column]
    assert len(_whole_table(column, [beside], 100.0)) == 6


def test_a_cluster_of_labels_far_from_the_table_stays_out_of_it():
    doc = _sheet()
    for i, s in enumerate(("Isolator Switch", "Geyser 150L", "LED downlight")):
        doc.modelspace().add_text(s, height=23.1).set_placement((15000, 19000 - i * 60))
    assert not in_region(15000, 19000, legend_region(doc))


def test_a_shape_is_named_by_the_legend_row_beside_it_whatever_its_drawn_size():
    doc = _sheet()
    names = legend_shape_names(doc)
    assert FLOOD and names[shape_kind("LINE4,CIRCLE2|s32|a1.0")] == "LED Floodlight"


def test_plain_boxes_and_board_symbols_are_never_named_from_the_legend():
    """A rectangle matches every door; boards are billed from the SLD, not as fittings."""
    assert set(legend_shape_names(_sheet()).values()) == {"LED Floodlight"}


def test_the_legend_names_shapes_on_a_run_without_any_ai():
    run = run_dxf_project([(_bytes(_sheet(floods=3)), "L-01.dxf"), (_bytes(_sheet(floods=2)), "L-02.dxf")])
    floods = [l for l in run.boq.line_items if l.description.startswith("LED Floodlight")]
    assert sum(l.qty for l in floods) == 5 and all(l.unit_price_zar > 0 for l in floods)
    assert run.ai_cost_zar == 0


def test_the_legend_beats_a_remembered_ai_name_and_nothing_is_sent_to_the_ai():
    sent = []

    def namer(groups, legend_lines):
        sent.extend(g for g in groups if not g.legend_item)
        return {g.signature: ("Pole Light", "ai") for g in groups if "CIRCLE2" in g.signature}, 0.0

    run = run_dxf_project([(_bytes(_sheet()), "L-01.dxf")], name_shapes=namer)
    assert any(l.description.startswith("LED Floodlight") for l in run.boq.line_items)
    assert not any(l.description.startswith("Pole Light") for l in run.boq.line_items)
    assert not any("LINE4,CIRCLE2" in g.signature for g in sent)


def test_a_name_a_person_gave_beats_the_legend():
    def namer(groups, legend_lines):
        return {g.signature: ("Pole Light", "person") for g in groups if "CIRCLE2" in g.signature}, 0.0

    run = run_dxf_project([(_bytes(_sheet()), "L-01.dxf")], name_shapes=namer)
    assert any(l.description.startswith("Pole Light") for l in run.boq.line_items)
    assert not any(l.description.startswith("LED Floodlight") for l in run.boq.line_items)


def test_a_shape_the_legend_names_needs_no_check_by_a_person():
    run = run_dxf_project([(_bytes(_sheet()), "L-01.dxf")])
    assert not any("by AI" in g.description for g in run.boq.gaps)
    assert [s.named_by for s in run.ai_symbols if s.item == "LED Floodlight"] == ["legend"]


def test_two_rows_with_one_glyph_name_nothing():
    """The same picture on two rows: the legend cannot say which, so the AI or a person decides."""
    doc = _sheet()
    _flood(doc.modelspace(), 4200 - 70, 19000 - 60)               # also beside the bulkhead row
    assert legend_shape_names(doc) == {}


def test_the_tables_own_grid_lines_are_not_part_of_a_glyph():
    doc = _sheet()
    msp = doc.modelspace()
    for y in (18970, 19030):
        msp.add_line((1900, y), (5900, y))                            # rows of the table, touching the glyphs
    for x in (4100, 4160):
        msp.add_line((x, 18800), (x, 19100))
    assert legend_shape_names(doc) == {"LINE4,CIRCLE2|a1.0": "LED Floodlight"}


def test_one_sheets_legend_in_a_set_is_not_enough():
    """Legends differ between sheets of a real set: a name must hold on two of them."""
    plain = _sheet(flood_glyph=False)
    run = run_dxf_project([(_bytes(_sheet()), "L-01.dxf"), (_bytes(plain), "L-02.dxf")])
    assert not any(l.description.startswith("LED Floodlight") for l in run.boq.line_items)


def test_vapour_proof_lights_are_not_panels():
    from agent.shared.legend import classify_description
    assert classify_description("2x24W,4ft double vapor proof LED fluorescent light")[0] == "Vapour Proof Light"
    assert classify_description("2x18W  double vapor proof fluorescent light")[0] == "Vapour Proof Light"
    assert classify_description("600 x 1200 Recessed 3 x 18W LED fluorescent light")[0] == "Recessed LED Panel"


def test_the_size_class_is_not_part_of_the_shape_kind():
    assert shape_kind("LINE4,CIRCLE2|s32|a0.9") == shape_kind("LINE4,CIRCLE2|s35|a0.9")
    assert shape_kind("LINE4,CIRCLE2|s32|a0.9") != shape_kind("LINE4,CIRCLE1|s32|a0.9")


@pytest.mark.parametrize("sig", ["LWPOLYLINE1|s30|a0.5", "LINE2|s30|a0.1"])
def test_the_simplest_shapes_are_not_distinctive(sig):
    from agent.dxf_pipeline.passes.shapes import is_distinctive
    assert not is_distinctive(sig)
