"""A feeder the drawings give two lengths for carries both, so a person can choose. No client data."""

from __future__ import annotations

import pytest

from agent.dxf_pipeline.passes.assemble import findings_from_recognition
from agent.dxf_pipeline.passes.recognize import DxfRecognition
from agent.dxf_pipeline.passes.sld import SldFacts, SldFeeder
from agent.shared.routes import Box, Label, Seg, build_route_network


def _routes(*, written=False):
    labels = [Label("DB-A", -2, 3, 1.0), Label("DB-B Fed from DB-A", 103, -3, 1.0),
              Label("DB-C Fed from DB-B", 102, 62, 1.0)]
    if written:
        labels += [Label(f"{n}m", 50, 2, 1.0) for n in (10, 20, 30, 15)]
    return build_route_network([Seg(0, 0, 100, 0), Seg(100, 0, 100, 60)], labels, [Box(98, -2, 102, 2)], units_per_m=1.0)


def _feeder(source, routes):
    sld = SldFacts(feeders=[SldFeeder(from_source=source, to_db="DB-C", cable_size_mm2=16)])
    return findings_from_recognition(DxfRecognition(), sld=sld, routes=routes).feeders[0]


def test_a_feeder_the_plan_and_the_sld_disagree_on_carries_both_lengths():
    f = _feeder("DB-A", _routes())
    assert f.length_options["As the site plan draws it"] == pytest.approx(60 * 1.05 + 3)
    assert f.length_options["As the SLD says, from DB-A"] == pytest.approx(160 * 1.05 + 3)


def test_a_feeder_nobody_disputes_carries_none():
    assert _feeder("DB-B", _routes()).length_options == {}


def test_a_written_length_that_differs_is_offered():
    routes = _routes()
    routes.edges[-1].label_m = 90.0
    f = _feeder("DB-B", routes)
    assert f.length_options["Written on the site plan"] == 90
