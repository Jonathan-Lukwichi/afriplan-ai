"""The frozen scorer — how well a predicted BOQ reproduces the reference."""

from pathlib import Path

import pytest

from agent.shared import BillOfQuantities, BQLineItem, BQSection, LineKind
from evaluation.metrics import PredLine, pred_lines_from_boq, pred_lines_from_reference, score
from evaluation.network import DrawingType as D
from evaluation.reference import RefBuilding, RefLine, ReferenceBoq

ALL = set(D)


def _l(fam, qty, rate, spec="", role="combined", bld="H"):
    return RefLine(sheet=bld, building=bld, description=fam, qty=qty, rate=rate,
                   total=qty * rate, key_family=fam, key_spec=spec, role=role)


@pytest.fixture
def ref():
    lines = [
        _l("socket_double", 10, 400),            # 4 000
        _l("light_panel", 20, 2000),             # 40 000
        _l("swa_cable", 50, 900, "50mm2|4c", "supply"),    # 45 000
        _l("swa_cable", 50, 100, "50mm2|4c", "install"),   #  5 000
        _l("wall_box", 10, 600, "100x100"),      # 6 000   → total 100 000
    ]
    return ReferenceBoq(project="t", buildings=[
        RefBuilding(name="H", sheet="H", lines=lines, in_summary=True)])


def test_perfect_prediction_scores_one(ref):
    card = score(pred_lines_from_reference(ref), ref, uploaded=ALL)
    for m in ("coverage", "precision", "qty_accuracy", "rate_accuracy",
              "total_accuracy", "reproduction_score"):
        assert getattr(card, m) == pytest.approx(1.0), m


def test_missing_item_lowers_coverage_and_rs(ref):
    pred = [p for p in pred_lines_from_reference(ref) if p.family != "wall_box"]
    card = score(pred, ref, uploaded=ALL)
    assert card.coverage == pytest.approx(0.94)
    assert card.reproduction_score == pytest.approx(0.94)
    assert card.precision == pytest.approx(1.0)
    assert any("wall_box" in s for s in card.unmatched_reference)


def test_quantity_error_is_value_weighted(ref):
    pred = pred_lines_from_reference(ref)
    for p in pred:
        if p.family == "light_panel":           # 40 % of value, qty 50 % high
            p.qty, p.total = 30, 30 * 2000
    card = score(pred, ref, uploaded=ALL)
    assert card.coverage == pytest.approx(1.0)
    assert card.qty_accuracy == pytest.approx(0.8)          # 1 - 0.4*0.5
    assert card.reproduction_score == pytest.approx(0.8)


def test_supply_install_split_matches_a_combined_line(ref):
    pred = [p for p in pred_lines_from_reference(ref) if p.family != "swa_cable"]
    pred.append(PredLine(building="H", family="swa_cable", spec="50mm2|4c", role="combined",
                         qty=50, rate=1000, total=50_000, description="SWA 50mm2 combined"))
    card = score(pred, ref, uploaded=ALL)
    assert card.reproduction_score == pytest.approx(1.0)


def test_extra_prediction_lowers_precision_only(ref):
    pred = pred_lines_from_reference(ref) + [
        PredLine(building="H", family="light_flood", qty=5, rate=2000, total=10_000, description="x")]
    card = score(pred, ref, uploaded=ALL)
    assert card.coverage == pytest.approx(1.0)
    assert card.precision == pytest.approx(100_000 / 110_000)
    assert card.unmatched_predicted


def test_scoped_metrics_only_count_what_the_drawings_allow(ref):
    only_plugs = [p for p in pred_lines_from_reference(ref) if p.family in ("socket_double", "wall_box")]
    card = score(only_plugs, ref, uploaded={D.PLUGS})
    assert card.coverage == pytest.approx(0.10)             # 10 000 of 100 000
    assert card.scoped["coverage"] == pytest.approx(1.0)    # everything plugs can give
    assert card.scoped["reference_value"] == pytest.approx(10_000)


def test_boq_adapter_reads_pipeline_wording():
    boq = BillOfQuantities(pipeline="pdf", line_items=[
        BQLineItem(section=BQSection.SUBMAIN_CABLES, description="Supply 50mm² x4C SWA feeder A→B",
                   unit="m", qty=50, unit_price_zar=900, total_zar=45_000, line_kind=LineKind.SUPPLY),
        BQLineItem(section=BQSection.POWER_OUTLETS, description="16A double switched socket — Office",
                   unit="No", qty=4, unit_price_zar=400, total_zar=1_600),
    ])
    lines = pred_lines_from_boq(boq, building="H")
    assert [(l.family, l.spec, l.role) for l in lines] == [
        ("swa_cable", "50mm2|4c", "supply"), ("socket_double", "", "combined")]


def test_scorer_is_marked_frozen():
    src = Path(__file__).resolve().parents[2] / "evaluation" / "metrics.py"
    assert "FROZEN SCORER" in src.read_text(encoding="utf-8")
