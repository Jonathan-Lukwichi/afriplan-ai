"""ADR-0007 — repeated unnamed symbols are grouped by shape, whatever their position or angle."""
import math

import ezdxf

from agent.dxf_pipeline.passes.shapes import find_shape_groups


def _light(msp, x, y, r=300):
    """'circle with a cross' — the usual light-fitting symbol, drawn as loose line-work."""
    msp.add_circle((x, y), r, dxfattribs={"layer": "E-LIGHTING"})
    msp.add_line((x - r, y - r), (x + r, y + r), dxfattribs={"layer": "E-LIGHTING"})
    msp.add_line((x - r, y + r), (x + r, y - r), dxfattribs={"layer": "E-LIGHTING"})


def _batten(msp, x, y, angle_deg=0.0, length=1200, width=150):
    """a long thin double-line fitting (vapour-proof batten), possibly rotated"""
    a = math.radians(angle_deg)
    ux, uy, vx, vy = math.cos(a), math.sin(a), -math.sin(a), math.cos(a)
    corners = [(x + ux * s * length / 2 + vx * t * width / 2, y + uy * s * length / 2 + vy * t * width / 2)
               for s, t in ((-1, -1), (1, -1), (1, 1), (-1, 1))]
    msp.add_lwpolyline(corners + [corners[0]], dxfattribs={"layer": "E-LIGHTING"})


def _doc():
    doc = ezdxf.new()
    msp = doc.modelspace()
    for i in range(5):
        _light(msp, i * 4000, 0)
    for i, ang in enumerate((0, 90, 37)):
        _batten(msp, i * 4000, 8000, ang)
    return doc


def test_identical_symbols_are_counted_once_per_shape():
    groups = find_shape_groups(_doc(), "L-01")
    counts = sorted(g.count for g in groups)
    assert counts == [3, 5]
    assert all(g.sheet == "L-01" for g in groups)


def test_rotated_copies_are_the_same_shape():
    battens = [g for g in find_shape_groups(_doc()) if g.count == 3]
    assert len(battens) == 1                        # 0°, 90° and 37° copies group together


def test_each_shape_carries_one_picture():
    import base64
    for g in find_shape_groups(_doc()):
        assert base64.b64decode(g.image_png_b64)[:4] == b"\x89PNG"


def test_architecture_is_not_a_symbol():
    doc = _doc()
    for i in range(10):
        doc.modelspace().add_circle((i * 5000, 20000), 300, dxfattribs={"layer": "A-FURN"})
    assert sorted(g.count for g in find_shape_groups(doc)) == [3, 5]
