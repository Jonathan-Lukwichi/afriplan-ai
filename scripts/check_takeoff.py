"""
Check AfriPlan's take-off against hand counts on known drawings (/check-takeoff).

    python scripts/check_takeoff.py                    # the synthetic sample + every local case
    python scripts/check_takeoff.py data/takeoff_tests/house-a/raw

A case is a folder holding one drawing (.dxf/.dwg) and `expected.csv`
(`item,unit,expected,tolerance_pct`, item = an ItemKey from `evaluation.taxonomy`).
Client cases live in `data/takeoff_tests/<name>/raw/`, gitignored (ADR-0005). The DXF engine
runs twice per case; the output must be identical. Exit code 0 = PASS, 1 = FAIL.
"""

from __future__ import annotations

import csv
import sys
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "api"))

from agent.dxf_pipeline.passes.run import run_dxf_estimator  # noqa: E402
from evaluation.metrics import pred_lines_from_boq  # noqa: E402


@dataclass(frozen=True)
class Expected:
    item: str              # an ItemKey (`evaluation.taxonomy`), e.g. light_downlight, surfix|2.5mm2
    unit: str
    expected: float
    tolerance_pct: float


@dataclass(frozen=True)
class Row:
    item: str
    unit: str
    expected: float
    found: float
    difference: float
    ok: bool


@dataclass(frozen=True)
class CaseResult:
    name: str
    rows: list
    identical_twice: bool

    @property
    def ok(self) -> bool:
        return self.identical_twice and all(r.ok for r in self.rows)


def write_sample(folder: Path):
    """A synthetic drawing with known quantities, so the check runs without client data:
    11 downlights, 13 double sockets, 1 board, 34.25 m of 2.5 mm² wiring (one run curved; AfriPlan
    bills drawn final-circuit wiring as GP wire), and 2 unknown symbols. Ported from the playbook's three-layer-check pack. Returns (drawing, csv)."""
    import math
    import ezdxf

    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    doc = ezdxf.new("R2018", setup=True)
    doc.units = 4  # millimetres
    msp = doc.modelspace()
    for name in ("E-LIGHTING", "E-POWER", "E-CABLE-2.5"):
        doc.layers.add(name)
    doc.blocks.new("LIGHT_DOWNLIGHT").add_circle((0, 0), 150)
    doc.blocks.new("SOCKET_DOUBLE").add_lwpolyline([(-150, -75), (150, -75), (150, 75), (-150, 75)], close=True)
    doc.blocks.new("DB_MAIN").add_lwpolyline([(-300, -200), (300, -200), (300, 200), (-300, 200)], close=True)
    doc.blocks.new("MYSTERY_SYMBOL").add_line((-100, 0), (100, 0))
    for i in range(11):
        msp.add_blockref("LIGHT_DOWNLIGHT", (1000 + i * 1200, 8000), dxfattribs={"layer": "E-LIGHTING"})
    for i in range(13):
        msp.add_blockref("SOCKET_DOUBLE", (800 + i * 1000, 500), dxfattribs={"layer": "E-POWER"})
    msp.add_blockref("DB_MAIN", (14000, 4000), dxfattribs={"layer": "E-POWER"})
    for i in range(2):
        msp.add_blockref("MYSTERY_SYMBOL", (5000 + i * 2000, 4000), dxfattribs={"layer": "E-POWER"})
    # cable: 10 + 8 + 7 m straight, plus a half circle of 9.25 m = 34.25 m
    msp.add_line((0, 0), (10000, 0), dxfattribs={"layer": "E-CABLE-2.5"})
    msp.add_lwpolyline([(0, 1000), (5000, 1000), (5000, 4000)], dxfattribs={"layer": "E-CABLE-2.5"})
    msp.add_lwpolyline([(0, 2000), (7000, 2000)], dxfattribs={"layer": "E-CABLE-2.5"})
    msp.add_arc((20000, 0), 9250 / math.pi, 0, 180, dxfattribs={"layer": "E-CABLE-2.5"})

    drawing, expected = folder / "sample-house.dxf", folder / "expected.csv"
    doc.saveas(drawing)
    expected.write_text("item,unit,expected,tolerance_pct\nlight_downlight,no,11,0\nsocket_double,no,13,0\n"
                        "db,no,1,0\ngp_wire|2.5mm2,m,34.25,0.5\n", encoding="utf-8")
    return drawing, expected


def check_case(drawing: Path, expected_csv: Path) -> CaseResult:
    """Run the DXF engine twice on one drawing and compare with the hand counts."""
    drawing = Path(drawing)
    data = drawing.read_bytes()
    takes = []
    for _ in range(2):
        run = run_dxf_estimator(data, drawing.name)
        takes.append(quantities(run.boq) if run.boq else {})
    return CaseResult(drawing.stem, compare(takes[0], read_expected(expected_csv)), takes[0] == takes[1])


def read_expected(path: Path) -> list:
    """`item,unit,expected,tolerance_pct` rows (the playbook pack's format). Tolerates the BOM
    Excel writes and `#` comment rows."""
    with open(path, newline="", encoding="utf-8-sig") as f:
        rows = [r for r in csv.DictReader(f) if r.get("item") and not r["item"].startswith("#")]
    return [Expected(r["item"].strip(), r["unit"].strip(), float(r["expected"]), float(r["tolerance_pct"] or 0))
            for r in rows]


def quantities(boq) -> dict:
    """Total quantity per ItemKey, as the scorer reads the bill. An install line repeats its
    supply line's quantity, so it is not added again."""
    out: dict = {}
    for ln in pred_lines_from_boq(boq, building=""):
        if ln.role == "install":
            continue
        key = f"{ln.family}|{ln.spec}" if ln.spec else ln.family
        out[key] = round(out.get(key, 0) + ln.qty, 3)
    return out


def compare(found: dict, expected: list) -> list:
    """One row per expected item. A count (tolerance 0) must match exactly; a length may differ
    by its tolerance %. An item the take-off never produced is found 0."""
    rows = []
    for e in expected:
        got = found.get(e.item, 0)
        diff = round(got - e.expected, 3)
        rows.append(Row(e.item, e.unit, e.expected, got, diff,
                        abs(diff) <= e.expected * e.tolerance_pct / 100))
    return rows


def _case_files(folder: Path):
    drawings = sorted(p for p in folder.iterdir() if p.suffix.lower() in (".dxf", ".dwg"))
    expected = folder / "expected.csv"
    if len(drawings) != 1 or not expected.exists():
        return None
    return drawings[0], expected


def main(argv=None) -> int:
    import argparse
    import tempfile

    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cases", nargs="*", type=Path, help="case folders (default: sample + data/takeoff_tests/*/raw)")
    args = ap.parse_args(argv)

    root = Path(__file__).resolve().parent.parent
    with tempfile.TemporaryDirectory() as tmp:
        cases = args.cases or [None, *sorted((root / "data" / "takeoff_tests").glob("*/raw"))]
        results, not_tested = [], []
        for folder in cases:
            files = write_sample(Path(tmp) / "sample") if folder is None else _case_files(folder)
            if files is None:
                not_tested.append(str(folder))
                continue
            results.append(check_case(*files))

    for res in results:
        print(f"\n{res.name}: {'PASS' if res.ok else 'FAIL'}"
              f"{'' if res.identical_twice else '  (output differed between two runs)'}")
        print(f"  {'item':<22}{'unit':<6}{'expected':>10}{'found':>10}{'diff':>10}  result")
        for r in res.rows:
            print(f"  {r.item:<22}{r.unit:<6}{r.expected:>10g}{r.found:>10g}{r.difference:>10g}  {'ok' if r.ok else 'FAIL'}")
    for folder in not_tested:
        print(f"\nnot tested: {folder} (needs exactly one .dxf/.dwg and expected.csv)")
    ok = bool(results) and all(r.ok for r in results)
    print(f"\nOVERALL: {'PASS' if ok else 'FAIL'} ({sum(r.ok for r in results)}/{len(results)} cases)")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
