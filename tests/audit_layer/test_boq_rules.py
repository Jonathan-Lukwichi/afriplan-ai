"""BOQ audit rules — catch what a human (or a pipeline) got wrong in a bill."""

import pytest

from agent.shared import BillOfQuantities, BQLineItem, BQSection, LineKind
from audit.boq_rules import audit_boq, audit_reference
from evaluation.dataset import reference_available
from evaluation.reference import RefBuilding, RefLine, ReferenceBoq


def _l(desc, qty, rate, total, fam="other", spec="", role="combined", sec="A", code="", row=0):
    return RefLine(sheet="S", building="B", bill_section=sec, code=code, description=desc,
                   qty=qty, rate=rate, total=total, key_family=fam, key_spec=spec,
                   role=role, raw_row=row)


def _ref(lines, **bkw):
    b = RefBuilding(name="B", sheet="S", lines=lines, in_summary=True, **bkw)
    return ReferenceBoq(project="t", buildings=[b], summary={"B": b.total_excl_vat})


def _rules(findings):
    return sorted({f.rule for f in findings})


def test_arithmetic_error():
    f = audit_reference(_ref([_l("x", 10, 5.0, 60.0)]))
    assert "ARITH" in _rules(f)
    assert next(x for x in f if x.rule == "ARITH").value_at_risk_zar == pytest.approx(10)


def test_priced_but_not_totalled():
    f = audit_reference(_ref([_l("Install", 200, 300.0, None, row=5)]))
    hit = next(x for x in f if x.rule == "UNTOTALLED")
    assert hit.value_at_risk_zar == pytest.approx(60_000) and hit.severity == "high"


def test_quantity_without_rate():
    f = audit_reference(_ref([_l("24W Bulkhead Light Outdoor", 4, None, 0.0, fam="light_bulkhead")]))
    assert "NO_RATE" in _rules(f)


def test_clean_line_raises_nothing():
    f = audit_reference(_ref([_l("x", 10, 5.0, 50.0, sec="A")],
                             section_totals={"A": 50.0}, contingency=2.5, total_excl_vat=52.5))
    assert f == []


def test_duplicate_line():
    lines = [_l("DB CR: 3 phase", 1, 150000.0, 150000.0, fam="db", code="A3.1", row=r) for r in (7, 9)]
    assert "DUPLICATE" in _rules(audit_reference(_ref(lines)))


def test_section_rollup_mismatch():
    f = audit_reference(_ref([_l("x", 10, 5.0, 50.0)], section_totals={"A": 40.0}))
    assert "ROLLUP" in _rules(f)


def test_contingency_not_added_to_total():
    f = audit_reference(_ref([_l("x", 100, 1.0, 100.0)], section_totals={"A": 100.0},
                             contingency=5.0, total_excl_vat=100.0))
    assert "TOTAL" in _rules(f)


def test_feeder_without_companions():
    lines = [_l("Supply", 50, 900.0, 45_000.0, fam="swa_cable", spec="50mm2|4c", role="supply")]
    f = audit_reference(_ref(lines))
    msgs = " ".join(x.message for x in f if x.rule == "COMPANION")
    assert "install" in msgs and "termination" in msgs and "earth" in msgs


def test_sheet_not_in_summary_and_error_cells():
    ref = _ref([_l("x", 1, 10.0, 10.0)])
    ref.buildings.append(RefBuilding(name="Heat", sheet="Heat", in_summary=False,
                                     lines=[_l("y", 1, None, None)], errors=["#REF! in 'A- TOTAL'"]))
    assert {"NOT_IN_SUMMARY", "ERROR_CELL"} <= set(_rules(audit_reference(ref)))


def test_pipeline_boq_is_audited_too():
    boq = BillOfQuantities(pipeline="pdf", line_items=[
        BQLineItem(section=BQSection.SUBMAIN_CABLES, description="Supply 50mm² x4C SWA feeder A→B",
                   unit="m", qty=50, unit_price_zar=900, total_zar=45_000, line_kind=LineKind.SUPPLY),
    ])
    rules = _rules(audit_boq(boq, building="B"))
    assert "COMPANION" in rules


@pytest.mark.skipif(not reference_available("wedela"), reason="client reference BOQ kept locally (gitignored)")
def test_real_wedela_reference_defects():
    from evaluation.reference import load_reference
    f = audit_reference(load_reference("wedela"))
    by = {(x.rule, x.building) for x in f}
    assert ("NOT_IN_SUMMARY", "Pool-Heat Pumps") in by
    assert ("UNTOTALLED", "Swimming Pool") in by
    assert ("DUPLICATE", "Swimming Pool") in by
    assert ("NO_RATE", "Small Guard House") in by
    assert ("TOTAL", "Storage") in by
