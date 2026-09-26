"""Feeders priced from site-plan route lengths (issue 002), trench billed once per route."""
import pytest

from agent.dxf_pipeline.passes.assemble import DEFAULT_DXF_CONFIG, build_boq_from_recognition
from agent.dxf_pipeline.passes.recognize import DxfRecognition
from agent.dxf_pipeline.passes.sld import SldBoard, SldFacts, SldFeeder
from agent.shared import BQSection, ItemConfidence
from agent.shared.routes import Box, Label, Seg, build_route_network

H = 2.0


def _routes(labels=()):
    # DB-A ── 46 ── ┬ ── 39 up, 52 across, 38 down ── DB-B      (175 m)
    #               └ branch 30 ── DB-C                         (46 + 19 + 30 = 95 m)
    segs = [Seg(4, 1, 50, 1), Seg(50, 1, 50, 40), Seg(50, 40, 102, 40), Seg(102, 40, 102, 2),
            Seg(50, 20, 80, 20)]
    boxes = [Box(0, 0, 4, 2), Box(100, 0, 104, 2), Box(80, 19, 84, 21)]
    tags = [Label("DB-A", -2, 6, H), Label("DB-B Fed from DB-A", 108, 6, H),
            Label("DB-C fed from DB-A", 86, 24, H)]
    return build_route_network(segs, [*tags, *labels], boxes, units_per_m=1.0)


def _sld(*feeders):
    return SldFacts(boards=[SldBoard(name="DB-B", main_breaker_a=63, circuits=[(20, 1)])],
                    feeders=[SldFeeder(from_source=f, to_db=t, cable_size_mm2=s, source="SLD-1") for f, t, s in feeders])


def _lines(boq, word):
    return [l for l in boq.line_items if word in l.description]


def test_feeder_length_comes_from_the_route_plus_allowances():
    boq = build_boq_from_recognition(DxfRecognition(), sld=_sld(("DB-A", "DB-B", 16)), routes=_routes())
    cfg = DEFAULT_DXF_CONFIG
    expected = 175 * (1 + cfg.route_slack_pct / 100) + 2 * cfg.route_end_allowance_m
    supply = [l for l in _lines(boq, "SWA feeder") if l.description.startswith("Supply")][0]
    assert supply.qty == pytest.approx(expected, abs=0.1)
    assert supply.source == ItemConfidence.INFERRED
    assert "175.0 m on the site plan" in supply.assumption
    assert supply.drawing_ref == "SLD-1"
    earth = [l for l in _lines(boq, "BCEW earth") if l.description.startswith("Supply")][0]
    assert earth.qty == supply.qty
    trench = _lines(boq, "Trench")[0]
    assert trench.qty == pytest.approx(175, abs=0.1)            # trench is the route itself, no allowance
    assert not [g for g in boq.gaps if g.severity == "high"]
    assert any("site-plan route" in g.description for g in boq.gaps)


def test_shared_trench_is_billed_once():
    boq = build_boq_from_recognition(
        DxfRecognition(), sld=_sld(("DB-A", "DB-B", 16), ("DB-A", "DB-C", 6)), routes=_routes())
    trench = sum(l.qty for l in _lines(boq, "Trench"))
    assert trench == pytest.approx(175 + 30, abs=0.1)           # the branch adds only its own run


def test_trench_goes_to_the_upstream_feeder_first():
    boq = build_boq_from_recognition(
        DxfRecognition(), sld=_sld(("DB-B", "DB-C", 4), ("DB-A", "DB-B", 16)), routes=_routes())
    by_feeder = {l.description: l.qty for l in _lines(boq, "Trench")}
    assert by_feeder["Trench 600mm for DB-A→DB-B"] == pytest.approx(175, abs=0.1)


def test_feeder_without_a_drawn_route_stays_assumed_and_says_so():
    boq = build_boq_from_recognition(DxfRecognition(), sld=_sld(("DB-A", "DB-Z", 10)), routes=_routes())
    supply = [l for l in _lines(boq, "SWA feeder") if l.description.startswith("Supply")][0]
    assert supply.source == ItemConfidence.ASSUMED and supply.qty == DEFAULT_DXF_CONFIG.assumed_feeder_m
    high = [g for g in boq.gaps if g.severity == "high"]
    assert high and "no drawn route" in high[0].description


def test_written_lengths_that_disagree_with_the_scaled_route_raise_a_gap():
    # written lengths are half the drawn ones: within the scale tolerance, so the drawing scale stands
    labels = [Label("23m", 27, 3, H), Label("10m", 52, 30, H), Label("26m", 76, 42, H), Label("19m", 104, 20, H)]
    boq = build_boq_from_recognition(DxfRecognition(), sld=_sld(("DB-A", "DB-B", 16)), routes=_routes(labels))
    conflict = [g for g in boq.gaps if "written on the site plan" in g.description]
    assert conflict and conflict[0].severity == "medium"


def test_layout_does_not_rebill_a_board_priced_from_the_sld():
    from agent.dxf_pipeline.passes.recognize import CircuitTag
    rec = DxfRecognition(circuit_tags=[CircuitTag("L1", "DB-1", "E", 0, 0, "DB-1/L1"),
                                       CircuitTag("P1", "DB-9", "E", 0, 0, "DB-9/P1")])
    boq = build_boq_from_recognition(rec, known_boards=["DB1"])
    dbs = [l.description.split(":")[0] for l in boq.line_items if l.section == BQSection.DISTRIBUTION]
    assert dbs == ["DB-9"]
