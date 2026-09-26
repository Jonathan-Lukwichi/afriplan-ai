"""Drawing sufficiency — complete vs partial BOQ from what was uploaded."""

import pytest

from audit.sufficiency import render_sufficiency, sufficiency, sufficiency_for_project
from evaluation.dataset import reference_available
from evaluation.network import DrawingType as D
from evaluation.reference import RefBuilding, RefLine, ReferenceBoq


def _l(fam, value):
    return RefLine(sheet="H", building="H", description=fam, qty=1, rate=value, total=value,
                   key_family=fam)


@pytest.fixture
def ref():
    return ReferenceBoq(project="t", buildings=[RefBuilding(
        name="H", sheet="H", in_summary=True,
        lines=[_l("light_panel", 600), _l("switch", 100), _l("socket_double", 200), _l("db", 100)])])


def test_lighting_only_upload(ref):
    rep = sufficiency({D.LIGHTING}, building="H", ref=ref)
    assert "light_panel" in rep.reproducible_families
    assert rep.coverage_possible_pct == pytest.approx(0.7)
    assert rep.requests == {"plug_layout": ["socket_double"], "sld": ["db"]}
    assert rep.complete is False


def test_full_set_is_complete(ref):
    rep = sufficiency({D.LIGHTING, D.PLUGS, D.SLD}, building="H", ref=ref)
    assert rep.coverage_possible_pct == pytest.approx(1.0) and rep.complete


def test_without_reference_lists_requirements_only():
    rep = sufficiency({D.PLUGS}, building="X")
    assert rep.coverage_possible_pct is None
    assert "lighting_layout" in rep.requests and "sld" in rep.requests


@pytest.mark.skipif(not reference_available("wedela"), reason="client reference BOQ kept locally (gitignored)")
def test_project_report_renders():
    from evaluation.reference import load_reference
    reps = sufficiency_for_project("wedela", load_reference("wedela"))
    names = {r.building for r in reps}
    assert "Storage" in names and "Main Kiosk" in names
    md = render_sufficiency(reps)
    assert "Drawing requirements" in md and "Storage" in md
