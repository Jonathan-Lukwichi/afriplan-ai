"""BOQ completer — add derived items the pipelines never calculate, visibly."""

import pytest

from agent.shared import BillOfQuantities, BQLineItem, BQSection, ItemConfidence
from audit.completer import complete_boq
from evaluation.ratios import Ratio, RatioModel


def _model(loo=0.1):
    return RatioModel(project_sources=["t"], ratios=[
        Ratio(target="wall_box|100x100", inputs=["socket_double|*", "isolator|*"], weight=1.0,
              n=6, loo_mape=loo, unit="No", rate_zar=130.0, bill_section="C"),
        Ratio(target="termination|*", inputs=["#swa_cable"], weight=4.0,
              n=7, loo_mape=0.18, unit="Ea", rate_zar=240.0, bill_section="A"),
    ])


def _boq():
    boq = BillOfQuantities(pipeline="dxf", contingency_pct=5.0, vat_pct=15.0, line_items=[
        BQLineItem(item_no=1, section=BQSection.POWER_OUTLETS, description="Double Socket — Office",
                   unit="No", qty=6, unit_price_zar=400, total_zar=2400),
        BQLineItem(item_no=2, section=BQSection.POWER_OUTLETS, description="Isolator Switch",
                   unit="No", qty=2, unit_price_zar=350, total_zar=700),
    ])
    boq.subtotal_zar = 3100
    return boq


def test_adds_derived_line_and_never_mutates_input():
    boq = _boq()
    out = complete_boq(boq, _model(), building="H")
    assert len(boq.line_items) == 2                        # original untouched
    added = [l for l in out.line_items if "wall box" in l.description.lower()]
    assert len(added) == 1
    wb = added[0]
    assert wb.qty == 8 and wb.unit_price_zar == 130.0 and wb.total_zar == pytest.approx(1040)
    assert wb.source == ItemConfidence.INFERRED and "ratio" in wb.assumption.lower()
    assert any("wall box" in g.description.lower() for g in out.gaps)


def test_totals_are_recomputed():
    out = complete_boq(_boq(), _model(), building="H")
    assert out.subtotal_zar == pytest.approx(3100 + 1040)
    assert out.contingency_zar == pytest.approx(out.subtotal_zar * 0.05)
    assert out.total_incl_vat_zar == pytest.approx((out.subtotal_zar + out.contingency_zar) * 1.15)


def test_existing_family_is_not_duplicated():
    boq = _boq()
    boq.line_items.append(BQLineItem(section=BQSection.POWER_OUTLETS, description="100x100 Wall box",
                                     unit="No", qty=3, unit_price_zar=130, total_zar=390))
    out = complete_boq(boq, _model(), building="H")
    assert sum("wall box" in l.description.lower() for l in out.line_items) == 1


def test_unreliable_ratio_becomes_a_gap_not_a_line():
    out = complete_boq(_boq(), _model(loo=0.9), building="H")
    assert not any("wall box" in l.description.lower() for l in out.line_items)
    assert any("not inferred" in g.description.lower() for g in out.gaps)


def test_no_inputs_no_line():
    out = complete_boq(_boq(), _model(), building="H")
    assert not any("termination" in l.description.lower() for l in out.line_items)   # no cables
