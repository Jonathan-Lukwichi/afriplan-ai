"""scripts/build_symbol_dataset.py reads DXF files saved on any OS."""

from __future__ import annotations

import importlib.util
import io
import sys
from pathlib import Path

import ezdxf

ROOT = Path(__file__).resolve().parents[2]
_spec = importlib.util.spec_from_file_location("build_symbol_dataset", ROOT / "scripts" / "build_symbol_dataset.py")
bsd = importlib.util.module_from_spec(_spec)
sys.modules["build_symbol_dataset"] = bsd
_spec.loader.exec_module(bsd)


def test_a_dxf_with_windows_line_endings_is_read_not_emptied():
    doc = ezdxf.new()
    doc.modelspace().add_line((0, 0), (1000, 0), dxfattribs={"layer": "E-CABLE"})
    s = io.StringIO()
    doc.write(s)
    crlf = s.getvalue().encode("utf-8").replace(b"\n", b"\r\n")
    assert len(bsd._read_dxf(crlf).modelspace()) == 1
