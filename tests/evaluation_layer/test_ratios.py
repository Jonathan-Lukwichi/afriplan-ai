"""Fitted derived-item ratios — the network's weights, honestly validated."""

import pytest

from evaluation.dataset import reference_available
from evaluation.ratios import RatioModel, Ratio, building_quantities, fit_ratios, input_total
from evaluation.reference import RefBuilding, RefLine, ReferenceBoq


def _line(bld, family, qty, spec="", role="combined", rate=100.0):
    return RefLine(sheet=bld, building=bld, description=family, qty=qty, rate=rate,
                   total=qty * rate, key_family=family, key_spec=spec, role=role)


def _ref(rows):
    """rows: {building: [(family, qty, spec, role)]}"""
    blds = [RefBuilding(name=b, sheet=b, in_summary=True,
                        lines=[_line(b, f, q, s, r) for f, q, s, r in items])
            for b, items in rows.items()]
    return ReferenceBoq(project="t", buildings=blds)


SPEC = [("wall_box|100x100", ["socket_double|*", "isolator|*"])]


def test_exact_ratio_is_recovered_with_zero_loo_error():
    ref = _ref({
        f"B{i}": [("socket_double", n, "", "combined"), ("wall_box", 2 * n, "100x100", "combined")]
        for i, n in enumerate([3, 5, 8, 13])
    })
    model = fit_ratios(ref, specs=SPEC)
    r = model.ratios[0]
    assert r.weight == pytest.approx(2.0)
    assert r.n == 4 and r.loo_mape == pytest.approx(0.0)
    assert r.rate_zar == pytest.approx(100.0)


def test_building_without_the_input_is_excluded():
    ref = _ref({
        "B1": [("socket_double", 4, "", "combined"), ("wall_box", 8, "100x100", "combined")],
        "B2": [("socket_double", 6, "", "combined"), ("wall_box", 12, "100x100", "combined")],
        "Kiosk": [("kiosk", 1, "", "combined")],
    })
    r = fit_ratios(ref, specs=SPEC).ratios[0]
    assert r.n == 2 and r.loo_mape is None          # too few buildings for honest LOO


def test_install_lines_do_not_double_count():
    b = RefBuilding(name="B", sheet="B", lines=[
        _line("B", "swa_cable", 50, "50mm2|4c", "supply"),
        _line("B", "swa_cable", 50, "50mm2|4c", "install"),
    ])
    q = building_quantities(b)
    assert q["swa_cable|50mm2|4c"] == 50 and q["swa_cable|*"] == 50
    assert q["#swa_cable"] == 1                      # number of distinct cable runs


def test_predict_uses_family_wildcards():
    model = RatioModel(project_sources=["t"], ratios=[
        Ratio(target="wall_box|100x100", inputs=["socket_double|*", "isolator|*"],
              weight=2.0, n=4, loo_mape=0.0, unit="No", rate_zar=130.0, bill_section="C"),
    ])
    counts = {"socket_double|": 5, "isolator|": 1}
    assert input_total(counts, ["socket_double|*", "isolator|*"]) == 6
    assert model.predict(counts)["wall_box|100x100"] == pytest.approx(12.0)


@pytest.mark.skipif(not reference_available("wedela"), reason="client reference BOQ kept locally (gitignored)")
def test_wedela_wall_boxes_track_outlets():
    from evaluation.reference import load_reference
    model = fit_ratios(load_reference("wedela"))
    wb = next(r for r in model.ratios if r.target == "wall_box|100x100")
    assert 0.8 <= wb.weight <= 1.3
    assert wb.n >= 5 and wb.loo_mape is not None
