"""DWG/DXF → labelled symbol-image dataset (future CNN training data)."""

from pathlib import Path

import ezdxf
import pytest

from ml.symbol_dataset import SymbolLabel, labels_from_doc, render_sheet, write_sample

cv2 = pytest.importorskip("cv2")


def _doc_with_sockets():
    doc = ezdxf.new()
    blk = doc.blocks.new(name="SOCKET OUTLET 2 GANG")
    blk.add_circle((0, 0), radius=100)
    blk.add_line((-100, 0), (100, 0))
    msp = doc.modelspace()
    doc.layers.add("E-POWER")
    for x in (0, 2000, 4000):
        msp.add_blockref("SOCKET OUTLET 2 GANG", (x, 1000), dxfattribs={"layer": "E-POWER"})
    msp.add_line((0, 0), (5000, 0), dxfattribs={"layer": "A-WALL"})     # architecture, not a symbol
    doc.header["$EXTMIN"] = (-500, -500, 0)
    doc.header["$EXTMAX"] = (5500, 2000, 0)
    return doc


def test_block_instances_become_pixel_boxes(tmp_path):
    doc = _doc_with_sockets()
    w, h, to_px = render_sheet(doc, px_per_unit=0.1, out_png=tmp_path / "s.png")
    assert (tmp_path / "s.png").exists() and w > 0 and h > 0
    labels = labels_from_doc(doc, to_px)
    assert len(labels) == 3
    assert {l.cls for l in labels} == {"socket_double"}
    for l in labels:
        assert 0 <= l.x0 < l.x1 <= w and 0 <= l.y0 < l.y1 <= h
        assert l.source == "block"


def test_yolo_labels_are_normalised(tmp_path):
    labels = [SymbolLabel(cls="socket_double", x0=10, y0=20, x1=30, y1=60, source="block")]
    txt = write_sample(tmp_path, "sheet1", 100, 200, labels, classes=["light_panel", "socket_double"])
    line = txt.read_text().strip().split()
    assert line[0] == "1"
    cx, cy, bw, bh = map(float, line[1:])
    assert cx == pytest.approx(0.2) and cy == pytest.approx(0.2)
    assert bw == pytest.approx(0.2) and bh == pytest.approx(0.2)
