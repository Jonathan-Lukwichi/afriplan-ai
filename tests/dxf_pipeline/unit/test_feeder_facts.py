"""What an SLD leaves out of a feeder: its core count follows the board it feeds, and where a site plan
draws the cable from another board, the plan says where it runs. Synthetic, no client data."""

from __future__ import annotations

import pytest

from agent.dxf_pipeline.passes.assemble import findings_from_recognition
from agent.dxf_pipeline.passes.recognize import DxfRecognition
from agent.dxf_pipeline.passes.sld import SldBoard, SldFacts, SldFeeder
from agent.shared.routes import Box, Label, Seg, build_route_network


def _sld(*, phases=3, source="DB-A"):
    return SldFacts(boards=[SldBoard(name="DB-C", phases=phases, main_breaker_a=63, ka=6)],
                    feeders=[SldFeeder(from_source=source, to_db="DB-C", cable_size_mm2=16)])


def _routes():
    """DB-A — 100 m — DB-B — 60 m — DB-C, with the plan's tag saying DB-C is fed from DB-B."""
    segs = [Seg(0, 0, 100, 0), Seg(100, 0, 100, 60)]       # a corner at DB-B: it stays a node
    labels = [Label("DB-A", -2, 3, 1.0), Label("DB-B Fed from DB-A", 103, -3, 1.0),
              Label("DB-C Fed from DB-B", 102, 62, 1.0)]
    return build_route_network(segs, labels, [Box(98, -2, 102, 2)], units_per_m=1.0)


def test_a_single_phase_board_is_fed_by_three_core_cable():
    [fd] = findings_from_recognition(DxfRecognition(), sld=_sld(phases=1)).feeders
    assert fd.cable_cores == 3


def test_a_three_phase_board_keeps_four_core_cable():
    [fd] = findings_from_recognition(DxfRecognition(), sld=_sld(phases=3)).feeders
    assert fd.cable_cores == 4


def test_a_core_count_the_sld_states_is_kept():
    sld = _sld(phases=1)
    sld.feeders[0].cable_cores = 4
    sld.feeders[0].cores_stated = True
    [fd] = findings_from_recognition(DxfRecognition(), sld=sld).feeders
    assert fd.cable_cores == 4


def test_the_length_follows_the_route_the_site_plan_draws():
    routes = _routes()
    assert routes.fed_from["DBC"] == "DBB" and routes.found
    [fd] = findings_from_recognition(DxfRecognition(), sld=_sld(source="DB-A"), routes=routes).feeders
    assert fd.from_board == "DB-A" and fd.cable_size_mm2 == 16                      # the SLD's cable
    assert fd.length_m == pytest.approx(60 * 1.05 + 3)                              # the plan's run
    assert "DB-B" in fd.assumption


def test_feeders_that_agree_are_measured_as_before():
    [fd] = findings_from_recognition(DxfRecognition(), sld=_sld(source="DB-B"), routes=_routes()).feeders
    assert fd.length_m == pytest.approx(60 * 1.05 + 3) and "as the site plan draws it" not in fd.assumption


def test_the_conflict_says_what_was_done():
    from agent.dxf_pipeline.passes.run import _route_gaps
    [gap] = [g for g in _route_gaps(_routes(), _sld(source="DB-A"), "site") if "fed from" in g.description]
    assert "site plan" in gap.assumption and "SLD" in gap.assumption
