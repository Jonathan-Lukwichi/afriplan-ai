"""
Tests for the scoring harness (scoring/harness.py).

Deterministic: hand-built BOQs scored against synthetic + real baselines.
"""

from __future__ import annotations

import pytest

from agent.shared import BillOfQuantities, BQLineItem, BQSection
from scoring import load_baseline, score_boq
from scoring.harness import _ape


def _boq(**kw) -> BillOfQuantities:
    return BillOfQuantities(pipeline="pdf", **kw)


# ─── APE primitive ───────────────────────────────────────────────────

def test_ape_exact_match_is_zero():
    assert _ape(100, 100) == 0.0


def test_ape_handles_zero_actual():
    assert _ape(0, 0) == 0.0
    assert _ape(5, 0) == 1.0


def test_ape_half_off():
    assert _ape(50, 100) == 0.5


# ─── Total scoring ───────────────────────────────────────────────────

def test_perfect_total_scores_full_accuracy():
    boq = _boq(total_excl_vat_zar=1000.0, total_incl_vat_zar=1150.0)
    report = score_boq(boq, {"total_excl_vat_zar": 1000.0, "total_incl_vat_zar": 1150.0})
    assert report.overall_accuracy == 1.0
    assert all(m.accuracy == 1.0 for m in report.metrics)


def test_total_10pct_low_scores_90pct():
    boq = _boq(total_excl_vat_zar=900.0)
    report = score_boq(boq, {"total_excl_vat_zar": 1000.0})
    assert report.metrics[0].accuracy == pytest.approx(0.9)


def test_missing_baseline_field_not_scored():
    boq = _boq(total_excl_vat_zar=1000.0)
    report = score_boq(boq, {"total_excl_vat_zar": 1000.0})  # no incl-vat key
    names = [m.name for m in report.metrics]
    assert "Total incl VAT" not in names


# ─── Fixture count scoring (matches descriptions) ────────────────────

def test_fixture_counts_matched_from_descriptions():
    boq = _boq(line_items=[
        BQLineItem(section=BQSection.LIGHTING, description="6W LED downlight — Office", qty=75),
        BQLineItem(section=BQSection.POWER_OUTLETS, description="16A double switched socket — Hall", qty=25),
    ])
    baseline = {"fixture_counts": {"downlights": 75, "double_sockets": 25}}
    report = score_boq(boq, baseline)
    fixtures = {m.name: m.accuracy for m in report.metrics if m.group == "fixture"}
    assert fixtures["Count · downlights"] == 1.0
    assert fixtures["Count · double_sockets"] == 1.0


def test_fixture_undercount_penalised():
    boq = _boq(line_items=[
        BQLineItem(description="6W LED downlight", qty=60),
    ])
    report = score_boq(boq, {"fixture_counts": {"downlights": 75}})
    assert report.metrics[0].accuracy == pytest.approx(1 - 15 / 75)


# ─── Building total scoring ───────────────────────────────────────────

def test_building_total_grouped_by_building_block():
    boq = _boq(line_items=[
        BQLineItem(description="a", qty=1, unit_price_zar=100, total_zar=100, building_block="Community Hall"),
        BQLineItem(description="b", qty=1, unit_price_zar=400, total_zar=400, building_block="Community Hall"),
        BQLineItem(description="c", qty=1, unit_price_zar=50, total_zar=50, building_block="Storage"),
    ])
    baseline = {"building_totals_zar": {"Community Hall": 500.0, "Storage": 50.0}}
    report = score_boq(boq, baseline)
    acc = {m.name: m.accuracy for m in report.metrics}
    assert acc["Building · Community Hall"] == 1.0
    assert acc["Building · Storage"] == 1.0


def test_unmatched_building_notes_a_warning():
    boq = _boq(line_items=[BQLineItem(description="x", total_zar=100, building_block="DB-CR")])
    report = score_boq(boq, {"building_totals_zar": {"Nonexistent Wing": 100.0}})
    assert any("No BOQ lines matched" in n for n in report.notes)


# ─── Real baselines load & are shaped right ──────────────────────────
# baselines/wedela.json and trichard.json hold client totals: kept locally, gitignored.

def _have(name: str) -> bool:
    from pathlib import Path
    return (Path(__file__).resolve().parents[2] / "baselines" / f"{name}.json").is_file()


_needs_wedela = pytest.mark.skipif(not _have("wedela"), reason="client baseline kept locally (gitignored)")
_needs_trichard = pytest.mark.skipif(not _have("trichard"), reason="client baseline kept locally (gitignored)")


@_needs_wedela
def test_wedela_baseline_loads():
    b = load_baseline("wedela")
    assert b["structure"] == "per_building"
    assert b["total_excl_vat_zar"] > 0
    assert "Swimming Pool" in b["building_totals_zar"]


@_needs_trichard
def test_trichard_baseline_loads():
    b = load_baseline("trichard")
    assert b["structure"] == "single"
    assert b["fixture_counts"]["downlights"] == 75
    assert b["total_incl_vat_zar"] > 0


@_needs_wedela
def test_report_renders_without_error():
    boq = _boq(total_excl_vat_zar=6_000_000, total_incl_vat_zar=6_900_000)
    report = score_boq(boq, load_baseline("wedela"))
    text = report.render()
    assert "Overall accuracy" in text
    assert "Wedela" in text
