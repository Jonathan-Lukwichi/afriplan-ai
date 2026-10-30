"""agent/shared/companions.py: convention-A wiring lines derived from the route (RULES.md CO-C*).
Synthetic findings only — invented numbers, never client data."""

from __future__ import annotations

import pytest

from agent.shared.companions import companion_findings
from agent.shared.findings import Evidence, Findings, ItemFinding, WireFinding


def _hall(with_wiring: bool = True) -> Findings:
    f = Findings()
    if with_wiring:
        f.wires.append(WireFinding(description="1.5mm2 lighting reticulation wire — circuit L1",
                                   size_key="1.5mm2", metres=40.0, circuit="L1", building="Hall",
                                   evidence=Evidence.MEASURED))
        f.wires.append(WireFinding(description="2.5mm2 power reticulation wire — circuit P1",
                                   size_key="2.5mm2", metres=30.0, circuit="P1", building="Hall",
                                   evidence=Evidence.MEASURED))
    f.items.append(ItemFinding(description="Double Socket Outlet — Hall", item="Double Socket Outlet",
                               qty=4, building="Hall", evidence=Evidence.COUNTED))
    f.items.append(ItemFinding(description="1-Lever Switch — Hall", item="1-Lever Switch",
                               qty=3, building="Hall", evidence=Evidence.COUNTED))
    f.items.append(ItemFinding(description="LED Downlight — Hall", item="LED Downlight",
                               qty=10, building="Hall", evidence=Evidence.COUNTED))
    return f


def _conduit(found):
    return [i for i in found if "conduit" in i.description.lower()]


def test_conduit_is_the_measured_route_plus_one_drop_per_wall_point():
    """CO-C1: R = 40 + 30 m; D = 4 sockets × (3.0 − 0.5) + 3 switches × (3.0 − 1.3) = 10 + 5.1."""
    [c] = _conduit(companion_findings(_hall()))
    assert c.qty == pytest.approx(85.1)
    assert c.unit == "m" and c.building == "Hall"
    assert "CO-C1" in c.assumption


def test_an_assumed_ceiling_height_is_flagged_for_the_estimator():
    [c] = _conduit(companion_findings(_hall()))
    assert any("ceiling" in g.description.lower() for g in c.gaps)


def test_no_measured_route_means_no_conduit_line():
    """CO-C2 (the points × allowance fallback) is low confidence: it may only flag, never emit."""
    assert _conduit(companion_findings(_hall(with_wiring=False))) == []


def test_the_one_pricer_bills_the_derived_conduit():
    from agent.shared.pricing import price_findings
    boq = price_findings(_hall(), pipeline="dxf")
    conduit = [ln for ln in boq.line_items if "conduit" in ln.description.lower()]
    assert len(conduit) == 1 and conduit[0].qty == pytest.approx(85.1)
    assert any("ceiling" in g.description.lower() for g in boq.gaps)


def test_conduit_a_reader_already_counted_wins():
    f = _hall()
    f.items.append(ItemFinding(description="20mm PVC conduit — Hall", qty=12.0, unit="m", building="Hall"))
    assert _conduit(companion_findings(f)) == []
