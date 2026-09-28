"""
Findings + the one pricer (ADR-0008): whatever reader found a board, feeder, item or wire,
it is priced the same way, and every line keeps where it came from.
"""

from __future__ import annotations

import pytest

from agent.shared import BQSection, GapItem, ItemConfidence, LineKind
from agent.shared.findings import (
    BoardFinding,
    Evidence,
    FeederFinding,
    Findings,
    ItemFinding,
    WireFinding,
)
from agent.shared.pricing import DEFAULT_PRICING, price_findings
from core import constants
from core.rate_model import DEFAULT_PARAMS, build_rate, db_build_up


def test_evidence_is_ranked_measured_first():
    order = [Evidence.MEASURED, Evidence.COUNTED, Evidence.WRITTEN, Evidence.SEEN, Evidence.ASSUMED]
    assert [e.rank for e in order] == sorted((e.rank for e in order), reverse=True)


def test_board_is_priced_from_its_contents():
    b = BoardFinding(name="DB-A", phases=3, main_breaker_a=100, ka=15, circuits=[(20, 1), (32, 3)],
                     spares=2, motor_starters=1, sheet="SLD-1")
    boq = price_findings(Findings(boards=[b]), pipeline="dxf")
    [line] = boq.line_items
    expected = db_build_up(ways=4, phases=3, main_breaker_a=100, circuits=[(20, 1), (32, 3)],
                           motor_starters=1).combined_rate
    assert line.unit_price_zar == round(expected, 2)
    assert line.section == BQSection.DISTRIBUTION
    assert line.description.startswith("DB-A: 3ph 100A, 15kA, 4-way (2 spare)")
    assert "1 motor starters" in line.description
    assert line.drawing_ref == "SLD-1" and line.building_block == "DB-A"


def test_main_kiosk_is_one_complete_item_plus_its_plinth():
    b = BoardFinding(name="KIOSK", main_breaker_a=400, circuits=[(100, 3)], main_kiosk=True)
    lines = price_findings(Findings(boards=[b]), pipeline="dxf").line_items
    assert len(lines) == 2
    board = db_build_up(ways=1, phases=3, main_breaker_a=400, circuits=[(100, 3)]).combined_rate
    housing = constants.DB_PRICES["kiosk_lv_outdoor"] * DEFAULT_PARAMS.material_markup
    assert lines[0].unit_price_zar == round(board + housing, 2)
    assert lines[0].source == ItemConfidence.INFERRED and lines[0].assumption
    assert "plinth" in lines[1].description


def test_board_seen_only_as_a_tag_gets_a_nominal_price():
    b = BoardFinding(name="DB-X", contents_known=False)
    [line] = price_findings(Findings(boards=[b]), pipeline="dxf").line_items
    assert line.unit_price_zar == DEFAULT_PRICING.tag_only_board_price
    assert "rating per SLD" in line.description


def test_feeder_gives_cable_earth_terminations_and_trench():
    f = FeederFinding(from_board="KIOSK", to_board="DB-A", cable_size_mm2=16, cable_cores=4,
                      length_m=120.0, trench_m=80.0, evidence=Evidence.MEASURED,
                      confidence=ItemConfidence.INFERRED, assumption="route measured")
    lines = price_findings(Findings(feeders=[f]), pipeline="dxf").line_items
    descs = [l.description for l in lines]
    assert descs[0] == "Supply 16mm² x4C SWA feeder KIOSK→DB-A"
    assert [l.qty for l in lines[:4]] == [120.0] * 4
    term = next(l for l in lines if l.description.startswith("Terminate"))
    assert term.qty == 2 and term.source == ItemConfidence.EXTRACTED and term.assumption == ""
    trench = next(l for l in lines if l.description.startswith("Trench"))
    assert trench.qty == 80.0 and trench.section == BQSection.UNDERGROUND
    assert trench.unit_price_zar == DEFAULT_PRICING.trench_rate_per_m
    assert lines[0].line_kind == LineKind.SUPPLY and lines[0].source == ItemConfidence.INFERRED


def test_feeder_earth_size_read_from_the_drawing_wins():
    f = FeederFinding(from_board="A", to_board="B", cable_size_mm2=95, earth_size_mm2=70, length_m=10)
    lines = price_findings(Findings(feeders=[f]), pipeline="pdf").line_items
    assert any(l.description == "Supply 70mm² BCEW earth" for l in lines)


def test_feeder_whose_trench_is_already_billed_gets_no_trench_line():
    f = FeederFinding(from_board="A", to_board="B", cable_size_mm2=16, length_m=50, trench_m=0)
    lines = price_findings(Findings(feeders=[f]), pipeline="dxf").line_items
    assert not any(l.section == BQSection.UNDERGROUND for l in lines)


def test_item_is_built_up_from_material_and_install():
    it = ItemFinding(description="LED Downlight — Office", section=BQSection.LIGHTING, qty=12,
                     material_zar=150.0, install_zar=85.0, evidence=Evidence.COUNTED)
    [line] = price_findings(Findings(items=[it]), pipeline="dxf").line_items
    assert line.unit_price_zar == round(build_rate(material_cost=150.0, install_labour=85.0).combined_rate, 2)
    assert line.total_zar == round(12 * line.unit_price_zar, 2)


def test_free_issue_item_is_install_only_and_fixed_price_item_is_kept():
    free = ItemFinding(description="Pole light", section=BQSection.LIGHTING, qty=2,
                       material_zar=900.0, install_zar=85.0, free_issue=True)
    fixed = ItemFinding(description="Plinth", section=BQSection.DISTRIBUTION, unit="Sum", qty=1,
                        price_zar=6500.0)
    lines = price_findings(Findings(items=[free, fixed]), pipeline="pdf").line_items
    by = {l.description: l for l in lines}
    assert by["Pole light"].unit_price_zar == 85.0
    assert by["Plinth"].unit_price_zar == 6500.0


def test_wire_is_priced_per_metre_by_size():
    w = WireFinding(description="1.5mm2 lighting reticulation wire — circuit L1", size_key="1.5mm2",
                    metres=42.5, circuit="L1", evidence=Evidence.MEASURED)
    [line] = price_findings(Findings(wires=[w]), pipeline="dxf").line_items
    material = constants.CABLE_PRICES.get("surfix_1.5mm2_3c", 0.0)
    assert line.unit_price_zar == round(build_rate(material_cost=material, install_labour=25.0).combined_rate, 2)
    assert line.qty == 42.5 and line.unit == "m" and line.circuit_details == "L1"


def test_bill_carries_gaps_totals_and_provenance_counts():
    f = Findings(
        items=[ItemFinding(description="a", section=BQSection.LIGHTING, qty=1, price_zar=100.0),
               ItemFinding(description="b", section=BQSection.POWER_OUTLETS, qty=2, price_zar=10.0,
                           confidence=ItemConfidence.ASSUMED, assumption="guess")],
        gaps=[GapItem(description="check me")],
    )
    boq = price_findings(f, pipeline="pdf", project_name="P", run_id="r1")
    assert boq.pipeline == "pdf" and boq.project_name == "P" and boq.run_id == "r1"
    assert boq.subtotal_zar == 120.0
    assert boq.total_excl_vat_zar == pytest.approx(120.0 * (1 + DEFAULT_PARAMS.contingency_pct))
    assert boq.items_extracted == 1 and boq.items_assumed == 1
    assert [g.description for g in boq.gaps] == ["check me"]
    assert [l.item_no for l in boq.line_items] == [1, 1]        # numbered within each section
    assert boq.contractor_markup_pct == 0.0                      # markup already in the rates


def test_findings_round_trip_through_json():
    f = Findings(boards=[BoardFinding(name="DB-A", circuits=[(20, 1)])],
                 feeders=[FeederFinding(from_board="A", to_board="B", length_m=5)])
    again = Findings.model_validate_json(f.model_dump_json())
    assert again == f
