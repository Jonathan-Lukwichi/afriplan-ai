"""A whole drawing set as one DXF run: SLD feeders priced on site-plan routes (issue 002)."""
import io

import ezdxf
import pytest

from agent.dxf_pipeline.passes.run import run_dxf_project


def _bytes(doc) -> bytes:
    s = io.StringIO()
    doc.write(s)
    return s.getvalue().encode()


def _sld():
    doc = ezdxf.new()
    msp = doc.modelspace()
    msp.add_text("DB-B  400V, 63A, 6kA, 50Hz, 3PH+N+E").set_placement((0, 1000))
    for i, a in enumerate(["20A", "10A"]):
        msp.add_text(a).set_placement((50 * i, 800))
    msp.add_mtext("DB-B FED FROM DB-A \n Incoming main cable 16mm²").set_location((0, 1200))
    msp.add_mtext("DB-Z FED FROM DB-A \n Incoming main cable 6mm²").set_location((0, 1400))
    return doc


def _site_plan():
    """Drawn in mm: DB-A ─ 46 m ─ 39 m up ─ 52 m ─ 38 m down ─ DB-B; written lengths beside."""
    doc = ezdxf.new(units=4)
    doc.linetypes.add("DASHED2", [5.0, 3.0, -2.0], description="dashed")
    msp = doc.modelspace()
    k = 1000.0
    route = [(4, 1), (50, 1), (50, 40), (102, 40), (102, 2)]
    msp.add_lwpolyline([(x * k, y * k) for x, y in route], dxfattribs={"linetype": "DASHED2"})
    for x0, y0, x1, y1 in ((0, 0, 4, 2), (100, 0, 104, 2)):         # DB symbols: rectangle + diagonal
        pts = [(x0 * k, y0 * k), (x1 * k, y0 * k), (x1 * k, y1 * k), (x0 * k, y1 * k), (x0 * k, y0 * k)]
        for p, q in zip(pts, pts[1:]):
            msp.add_line(p, q)
        msp.add_line((x0 * k, y0 * k), (x1 * k, y1 * k))
    for text, x, y in (("DB-A", -2, 6), ("DB-B Fed from DB-A", 108, 6),
                       ("46m", 27, 3), ("39m", 52, 20), ("52m", 76, 42), ("38m", 104, 20)):
        msp.add_mtext(text, dxfattribs={"char_height": 2 * k}).set_location((x * k, y * k))
    return doc


def _layout():
    doc = ezdxf.new()
    msp = doc.modelspace()
    msp.add_text("DB-B/L1", dxfattribs={"layer": "E-LIGHTING"}).set_placement((0, 0))
    return doc


def _run():
    return run_dxf_project([(_bytes(_sld()), "WD-B-01-SLD.dxf"),
                            (_bytes(_site_plan()), "WD-OL-001 SITE.dxf"),
                            (_bytes(_layout()), "WD-B-01-LIGHTING.dxf")])


def test_project_run_measures_the_feeder_on_the_site_plan():
    run = _run()
    assert run.success, run.error
    assert run.site_plan_file == "WD-OL-001 SITE.dxf"
    assert run.routes_measured == 1
    roles = {n.file_name: n.role for n in run.files}
    assert roles["WD-OL-001 SITE.dxf"] == "site plan" and roles["WD-B-01-SLD.dxf"] == "SLD"
    swa = {l.description: l for l in run.boq.line_items if l.description.startswith("Supply") and "SWA" in l.description}
    ab = next(l for d, l in swa.items() if "DB-A→DB-B" in d)
    assert ab.qty == pytest.approx(175 * 1.05 + 3, abs=0.2)
    assert ab.drawing_ref == "WD-B-01-SLD"
    az = next(l for d, l in swa.items() if "DB-A→DB-Z" in d)
    assert az.source.value == "assumed"                   # DB-Z is not on the site plan


def test_board_priced_from_the_sld_is_not_billed_again_from_the_layout():
    run = _run()
    boards = [l for l in run.boq.line_items if l.description.startswith("DB-B")]
    assert len(boards) == 1 and boards[0].drawing_ref == "WD-B-01-SLD"


def test_a_board_tagged_on_two_layouts_is_billed_once():
    lighting, plugs = _layout(), _layout()
    for d in (lighting, plugs):
        d.modelspace().add_text("DB-Q/P1", dxfattribs={"layer": "E-POWER"}).set_placement((5, 5))
    run = run_dxf_project([(_bytes(_sld()), "S.dxf"), (_bytes(lighting), "L.dxf"), (_bytes(plugs), "P.dxf")])
    assert len([l for l in run.boq.line_items if l.description.startswith("DB-Q")]) == 1


def test_totals_cover_every_drawing():
    run = _run()
    assert run.boq.subtotal_zar == pytest.approx(sum(l.total_zar for l in run.boq.line_items), abs=0.05)
    refs = {l.drawing_ref for l in run.boq.line_items}
    assert "WD-B-01-SLD" in refs


def test_a_set_without_a_site_plan_asks_for_one():
    run = run_dxf_project([(_bytes(_sld()), "WD-B-01-SLD.dxf"), (_bytes(_layout()), "L.dxf")])
    assert run.site_plan_file == ""
    assert any("No site plan" in g.description for g in run.boq.gaps)


def test_unreadable_drawing_is_reported_not_fatal():
    run = run_dxf_project([(_bytes(_sld()), "WD-B-01-SLD.dxf"), (b"not a drawing", "broken.dwg")])
    assert run.success
    bad = [n for n in run.files if not n.ok]
    assert bad and bad[0].file_name == "broken.dwg"
