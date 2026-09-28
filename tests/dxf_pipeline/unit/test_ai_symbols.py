"""ADR-0007 — unnamed symbols: geometry counts, an injected namer names, the bill prices."""
import io

import ezdxf
import pytest

from agent.dxf_pipeline.passes.run import run_dxf_project


def _dxf(n_lights: int) -> bytes:
    doc = ezdxf.new()
    msp = doc.modelspace()
    for i in range(n_lights):
        x = i * 4000
        msp.add_circle((x, 0), 300, dxfattribs={"layer": "E-LIGHTING"})
        msp.add_line((x - 300, -300), (x + 300, 300), dxfattribs={"layer": "E-LIGHTING"})
        msp.add_line((x - 300, 300), (x + 300, -300), dxfattribs={"layer": "E-LIGHTING"})
    msp.add_text("DB-A/L1", dxfattribs={"layer": "E-LIGHTING"}).set_placement((0, 5000))
    s = io.StringIO()
    doc.write(s)
    return s.getvalue().encode()


def _namer(item="Bulkhead Light", by="ai"):
    calls = []

    def namer(groups, legend_lines):
        calls.append([g.signature for g in groups])
        return {g.signature: (item, by) for g in groups}, 1.25
    namer.calls = calls
    return namer


def test_named_shapes_become_priced_lines_counted_by_geometry():
    namer = _namer()
    run = run_dxf_project([(_dxf(5), "L-01.dxf"), (_dxf(3), "L-02.dxf")], name_shapes=namer)
    lines = {l.drawing_ref: l for l in run.boq.line_items if l.description.startswith("Bulkhead Light")}
    assert lines["L-01"].qty == 5 and lines["L-02"].qty == 3
    assert all(l.source.value == "inferred" and l.unit_price_zar > 0 for l in lines.values())
    assert len(namer.calls) == 1                           # one naming request for the whole set
    assert run.ai_cost_zar == pytest.approx(1.25)
    sym = run.ai_symbols[0]
    assert sym.item == "Bulkhead Light" and sym.count == 8 and sym.image_png_b64
    assert any("recognised as 'Bulkhead Light' by AI" in g.description for g in run.boq.gaps)


def test_a_name_a_person_gave_needs_no_check():
    run = run_dxf_project([(_dxf(2), "L-01.dxf")], name_shapes=_namer(by="person"))
    assert not any("by AI" in g.description for g in run.boq.gaps)
    assert run.ai_symbols[0].named_by == "person"


def test_shapes_named_not_electrical_are_not_billed():
    run = run_dxf_project([(_dxf(4), "L-01.dxf")], name_shapes=_namer(item="Not an electrical symbol"))
    assert not any(l.description.startswith("Not an electrical") for l in run.boq.line_items)
    assert run.ai_symbols[0].item == "Not an electrical symbol"


def test_without_a_namer_the_run_is_the_deterministic_one():
    run = run_dxf_project([(_dxf(3), "L-01.dxf"), (_dxf(3), "L-02.dxf")])
    assert run.ai_symbols == [] and run.ai_cost_zar == 0
    assert not any(l.description.startswith("Bulkhead Light") for l in run.boq.line_items)
