"""scripts/check_takeoff.py: a take-off is checked against hand counts on known drawings."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
_spec = importlib.util.spec_from_file_location("check_takeoff", ROOT / "scripts" / "check_takeoff.py")
ct = importlib.util.module_from_spec(_spec)
sys.modules["check_takeoff"] = ct       # dataclasses look their module up here
_spec.loader.exec_module(ct)


def _exp(item, expected, tol=0.0, unit="no"):
    return ct.Expected(item=item, unit=unit, expected=expected, tolerance_pct=tol)


def test_counts_must_match_exactly_and_lengths_within_tolerance():
    rows = ct.compare(
        {"light_downlight": 11, "socket_double": 12, "surfix|2.5mm2": 34.4},
        [_exp("light_downlight", 11), _exp("socket_double", 13), _exp("surfix|2.5mm2", 34.25, tol=0.5, unit="m")],
    )
    assert [(r.item, r.ok) for r in rows] == [
        ("light_downlight", True), ("socket_double", False), ("surfix|2.5mm2", True)]
    assert rows[1].found == 12 and rows[1].difference == -1


def test_bill_lines_are_totalled_per_item_and_install_lines_are_not_counted_twice():
    from types import SimpleNamespace
    from agent.shared.boq import BQLineItem, LineKind
    boq = SimpleNamespace(line_items=[
        BQLineItem(description="Downlight LED 12W recessed", qty=6, unit="No"),
        BQLineItem(description="Downlight LED 12W recessed", qty=5, unit="No"),
        BQLineItem(description="Surfix cable 2.5mm2 3-core", qty=34.25, unit="m", line_kind=LineKind.SUPPLY),
        BQLineItem(description="Surfix cable 2.5mm2 3-core", qty=34.25, unit="m", line_kind=LineKind.INSTALL),
    ])
    assert ct.quantities(boq) == {"light_downlight": 11, "surfix|2.5mm2": 34.25}


def test_expected_counts_read_from_csv_saved_by_excel(tmp_path):
    csv = tmp_path / "expected.csv"
    csv.write_text("﻿item,unit,expected,tolerance_pct\n# a comment row\nlight_downlight,no,11,0\n"
                   "surfix|2.5mm2,m,34.25,0.5\n", encoding="utf-8")
    assert ct.read_expected(csv) == [
        ct.Expected("light_downlight", "no", 11.0, 0.0), ct.Expected("surfix|2.5mm2", "m", 34.25, 0.5)]


def test_the_sample_drawing_is_written_with_its_hand_counts(tmp_path):
    drawing, expected = ct.write_sample(tmp_path)
    assert drawing.suffix == ".dxf" and drawing.exists()
    assert {e.item: e.expected for e in ct.read_expected(expected)} == {
        "light_downlight": 11, "socket_double": 13, "db": 1, "surfix|2.5mm2": 34.25}


def test_the_same_drawing_twice_gives_identical_take_offs(tmp_path):
    drawing, expected = ct.write_sample(tmp_path)
    result = ct.check_case(drawing, expected)
    assert result.identical_twice is True


@pytest.mark.xfail(strict=True, reason="issue 015: the DXF engine recognises the sample's 27 symbols "
                   "and 34.25 m of cable, then drops them from the bill without a gap")
def test_the_sample_drawing_take_off_matches_its_hand_counts(tmp_path):
    drawing, expected = ct.write_sample(tmp_path)
    result = ct.check_case(drawing, expected)
    assert result.ok, [r for r in result.rows if not r.ok]


def test_an_expected_item_the_take_off_never_produced_is_found_zero_and_fails():
    [row] = ct.compare({}, [_exp("db", 1)])
    assert (row.found, row.ok) == (0, False)
