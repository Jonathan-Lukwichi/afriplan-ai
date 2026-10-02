"""
Tests for the deterministic brain (Pass 4+5): agent/pdf_pipeline/passes/assemble.py.

Central guarantee: the same facts always produce the identical bill. Plus the
estimator rules — feeder → cable+earth+2 terminations+trench, annotated vs
assumed lengths, free-issue install-only, point-method reticulation, VAT.
"""

from __future__ import annotations

import pytest

from agent.pdf_pipeline.passes.assemble import DEFAULT_CONFIG, build_boq_from_facts
from agent.pdf_pipeline.passes.facts import (
    Feeder,
    IncomingSupply,
    LayoutTakeoff,
    PdfFacts,
    PowerSpine,
    ProjectContext,
    SpineDB,
    TakeoffRoom,
)
from agent.shared import BQSection, ItemConfidence, LineKind


def _wedela_like_facts() -> PdfFacts:
    return PdfFacts(
        context=ProjectContext(
            project_name="Wedela Recreational Club",
            buildings=["Community Hall", "Ablution Retail Block"],
            free_issue_items=["LED downlight"],
        ),
        spine=PowerSpine(
            distribution_boards=[
                SpineDB(name="DB-CR", main_breaker_a=250, phases=3, voltage_v=400,
                        enclosure_mount="floor_standing",
                        circuits=[]),
                SpineDB(name="DB-AB1", main_breaker_a=60, phases=3, enclosure_mount="surface"),
            ],
            feeders=[
                Feeder(from_source="Mini-Sub", to_db="DB-CR", cable_size_mm2=95, cable_cores=4,
                       earth_size_mm2=70, length_m=35, length_annotated=True, is_underground=True),
                Feeder(from_source="DB-CR", to_db="DB-AB1", cable_size_mm2=50, cable_cores=4,
                       length_annotated=False, is_underground=True),   # length NOT drawn
            ],
            incoming_supply=IncomingSupply(supply_source="mini_sub", kiosk_present=True, meter_count=1),
        ),
        takeoff=LayoutTakeoff(rooms=[
            TakeoffRoom(room_name="Tuck Shop", served_by_db="DB-AB1", ceiling_height_m=3.0,
                        panel_lights=4, downlights=2, double_sockets=6, isolators=1),
        ]),
    )


# ─── Determinism ─────────────────────────────────────────────────────

def test_same_facts_produce_identical_bill():
    facts = _wedela_like_facts()
    a = build_boq_from_facts(facts, project_name="W", run_id="x")
    b = build_boq_from_facts(facts, project_name="W", run_id="x")
    # `generated_at` is a wall-clock provenance stamp, not part of the estimate.
    # Everything the estimator computes must be byte-identical.
    exclude = {"generated_at"}
    assert a.model_dump(exclude=exclude) == b.model_dump(exclude=exclude)


def test_total_is_stable_across_many_runs():
    facts = _wedela_like_facts()
    totals = {build_boq_from_facts(facts).total_incl_vat_zar for _ in range(25)}
    assert len(totals) == 1


# ─── Feeder rule-set ─────────────────────────────────────────────────

def test_annotated_feeder_uses_drawn_length():
    facts = _wedela_like_facts()
    boq = build_boq_from_facts(facts)
    supply = [l for l in boq.line_items
              if l.line_kind == LineKind.SUPPLY and "95mm² x4C SWA feeder" in l.description]
    assert supply and supply[0].qty == 35.0
    assert supply[0].source == ItemConfidence.EXTRACTED


def test_unannotated_feeder_is_assumed_and_flagged():
    facts = _wedela_like_facts()
    boq = build_boq_from_facts(facts)
    # the DB-CR→DB-AB1 feeder had no length → assumed default, and a gap emitted
    assumed = [l for l in boq.line_items
               if "50mm² x4C SWA feeder" in l.description and l.source == ItemConfidence.ASSUMED]
    assert assumed
    assert assumed[0].qty == DEFAULT_CONFIG.assumed_feeder_m
    assert any("length not annotated" in g.description.lower() for g in boq.gaps)
    assert boq.items_assumed >= 1


def test_every_feeder_gets_earth_terminations_and_trench():
    facts = _wedela_like_facts()
    boq = build_boq_from_facts(facts)
    submain = [l for l in boq.line_items if l.section == BQSection.SUBMAIN_CABLES]
    assert any("BCEW earth" in l.description for l in submain)
    terms = [l for l in submain if l.description.startswith("Terminate")]
    assert terms and all(l.qty == 2 for l in terms)          # both ends
    trench = [l for l in boq.line_items if l.section == BQSection.UNDERGROUND
              and l.description.startswith("Trench")]
    assert len(trench) == 2                                   # one per underground feeder


def test_earth_length_matches_feeder_length():
    facts = _wedela_like_facts()
    boq = build_boq_from_facts(facts)
    earth = [l for l in boq.line_items if "70mm² BCEW" in l.description and l.line_kind == LineKind.SUPPLY]
    assert earth and earth[0].qty == 35.0                     # same as its 95mm feeder


# ─── Fittings & free-issue ───────────────────────────────────────────

def test_supply_install_split_present_for_cables():
    boq = build_boq_from_facts(_wedela_like_facts())
    kinds = {l.line_kind for l in boq.line_items if l.section == BQSection.SUBMAIN_CABLES}
    assert LineKind.SUPPLY in kinds and LineKind.INSTALL in kinds


def test_free_issue_downlight_is_install_only():
    boq = build_boq_from_facts(_wedela_like_facts())
    dl = [l for l in boq.line_items if "downlight" in l.description.lower()]
    assert dl and "install only" in dl[0].notes.lower()
    # install-only price is far below a supply+install price
    assert dl[0].unit_price_zar < 200


def test_non_free_issue_fitting_includes_material():
    boq = build_boq_from_facts(_wedela_like_facts())
    panel = [l for l in boq.line_items if "recessed" in l.description.lower()]
    assert panel and panel[0].unit_price_zar > 300         # material + labour + markup


def test_fitting_counts_come_straight_from_takeoff():
    boq = build_boq_from_facts(_wedela_like_facts())
    sockets = [l for l in boq.line_items if "double switched socket" in l.description.lower()]
    assert sockets and sockets[0].qty == 6


# ─── Reticulation (point method) ─────────────────────────────────────

def test_reticulation_wire_added_as_allowance():
    boq = build_boq_from_facts(_wedela_like_facts())
    retic = [l for l in boq.line_items if l.section == BQSection.FINAL_CABLES]
    assert retic
    assert all(l.source == ItemConfidence.ASSUMED for l in retic)
    # 6 power points × 10 m/point = 60 m of 2.5mm²
    power = [l for l in retic if "power reticulation" in l.description.lower()]
    assert power and power[0].qty == 60.0


# ─── Totals ──────────────────────────────────────────────────────────

def test_totals_include_contingency_and_vat():
    boq = build_boq_from_facts(_wedela_like_facts())
    assert boq.subtotal_zar > 0
    assert boq.contingency_zar == pytest.approx(boq.subtotal_zar * 0.05, rel=1e-6)
    assert boq.total_excl_vat_zar == pytest.approx(boq.subtotal_zar + boq.contingency_zar)
    assert boq.vat_zar == pytest.approx(boq.total_excl_vat_zar * 0.15, rel=1e-6)
    assert boq.total_incl_vat_zar == pytest.approx(boq.total_excl_vat_zar * 1.15)


def test_line_numbering_is_per_section():
    boq = build_boq_from_facts(_wedela_like_facts())
    for section_no in {l.section.section_number for l in boq.line_items}:
        nums = [l.item_no for l in boq.line_items if l.section.section_number == section_no]
        assert nums == list(range(1, len(nums) + 1))


def test_empty_facts_yield_empty_priceable_bill():
    boq = build_boq_from_facts(PdfFacts())
    assert boq.line_items == []
    assert boq.total_incl_vat_zar == 0.0


def test_markup_is_declared_as_baked_into_rates():
    """Built-up rates already carry the x1.3 material markup: no second markup (issue 009)."""
    boq = build_boq_from_facts(_wedela_like_facts())
    assert boq.contractor_markup_pct == 0.0 and boq.markup_zar == 0.0


def test_site_lighting_is_billed_without_reticulation_wire():
    """Issue 003: solar post lanterns and high-mast flood posts are billed per unit; they add
    no 1.5 mm2 reticulation (solar = self-powered, high-mast = own feeder)."""
    from agent.pdf_pipeline.passes.facts import parse_layout_takeoff
    from evaluation.taxonomy import classify_item  # scripts/tests may read the ruler

    takeoff = parse_layout_takeoff({"rooms": [{"room_name": "Site", "confidence": 0.9,
                                               "solar_post_lights": 18, "high_mast_poles": 7}]})
    room = takeoff.rooms[0]
    assert (room.solar_post_lights, room.high_mast_poles) == (18, 7)
    assert room.light_points() == 0

    boq = build_boq_from_facts(PdfFacts(takeoff=takeoff))
    fams = {classify_item(l.description, unit=l.unit).family: l for l in boq.line_items}
    assert fams["light_solar_post"].qty == 18 and fams["light_solar_post"].unit_price_zar > 0
    assert fams["light_highmast"].qty == 7 and fams["light_highmast"].unit_price_zar > 0
    assert not any("reticulation" in l.description for l in boq.line_items)


def test_db_line_prices_incomer_breakers_and_protection():
    """Issue 004: a DB line is priced from its SLD contents, far above an empty enclosure."""
    from agent.pdf_pipeline.passes.facts import SpineCircuit
    from core import constants
    db = SpineDB(name="DB-X", main_breaker_a=250, phases=3, enclosure_mount="surface",
                 elcb_present=True, surge_protection=True,
                 circuits=[SpineCircuit(circuit_id=f"L{i}", breaker_a=20) for i in range(18)])
    boq = build_boq_from_facts(PdfFacts(spine=PowerSpine(distribution_boards=[db])))
    line = next(l for l in boq.line_items if l.section == BQSection.DISTRIBUTION)
    assert line.unit_price_zar > 5 * constants.DB_PRICES["db_24way_surface"]


# ─── Findings (ADR-0008): what was read, before any price ───────────

def test_findings_say_who_read_them_and_how():
    from agent.pdf_pipeline.passes.assemble import findings_from_facts
    from agent.shared.findings import Evidence

    f = findings_from_facts(_wedela_like_facts())
    assert {b.name for b in f.boards} == {"DB-CR", "DB-AB1"}
    assert all(x.reader == "pdf" for x in (*f.boards, *f.feeders, *f.items, *f.wires))
    written, assumed = f.feeders
    assert written.evidence == Evidence.SEEN and written.length_m == 35 and written.earth_size_mm2 == 70
    assert assumed.evidence == Evidence.ASSUMED and assumed.length_m == DEFAULT_CONFIG.assumed_feeder_m
    panel = next(i for i in f.items if i.item == "Recessed LED Panel")
    assert panel.qty == 4 and panel.location == "Tuck Shop" and panel.evidence == Evidence.SEEN
    assert all(w.evidence == Evidence.ASSUMED for w in f.wires)      # point-method allowance


# ─── Form boxes added 2026-10-02 (items drawn on real sets that had no box) ──

def test_new_room_boxes_are_read_and_priced():
    from agent.pdf_pipeline.passes.facts import parse_layout_takeoff
    from agent.pdf_pipeline.prompts.pass_schemas import READ_LAYOUT_TAKEOFF_TOOL
    from core import constants

    props = READ_LAYOUT_TAKEOFF_TOOL["input_schema"]["properties"]["rooms"]["items"]["properties"]
    for box in ("fluorescent_battens", "prismatic_lights", "switches_1lever_2way", "master_switches"):
        assert box in props
    takeoff = parse_layout_takeoff({"rooms": [{"room_name": "Hall", "confidence": 0.9, "fluorescent_battens": 23,
                                               "prismatic_lights": 5, "switches_1lever_2way": 2, "master_switches": 1}]})
    facts = PdfFacts(takeoff=takeoff)
    boq = build_boq_from_facts(facts)
    by = {l.description: l for l in boq.line_items}
    batten = next(l for d, l in by.items() if "5ft" in d)
    assert batten.qty == 23 and batten.section == BQSection.LIGHTING
    assert batten.unit_price_zar > constants.LIGHT_PRICES["fluorescent_50w_5ft"]   # material + install
    assert any("prismatic" in d.lower() and l.qty == 5 for d, l in by.items())
    assert any("2-way" in d and l.qty == 2 for d, l in by.items())
    assert any("master switch" in d.lower() and l.qty == 1 for d, l in by.items())
    assert room_points(facts) == 28                     # battens and prismatics are light points


def room_points(facts):
    return facts.takeoff.rooms[0].light_points()


def test_board_motor_starters_and_master_switch_are_read_and_priced():
    from agent.pdf_pipeline.passes.facts import parse_power_spine
    from agent.pdf_pipeline.prompts.pass_schemas import READ_POWER_SPINE_TOOL

    board_props = READ_POWER_SPINE_TOOL["input_schema"]["properties"]["distribution_boards"]["items"]["properties"]
    assert "motor_starters" in board_props and "master_switch" in board_props
    spine = lambda n, ms: parse_power_spine({"distribution_boards": [{  # noqa: E731
        "name": "DB-PPS1", "main_breaker_a": 100, "confidence": 0.9, "motor_starters": n, "master_switch": ms,
        "circuits": [{"circuit_id": f"P{i}", "breaker_a": 32, "breaker_poles": 3} for i in range(4)]}], "feeders": []})
    plain = build_boq_from_facts(PdfFacts(spine=spine(0, False))).line_items[0]
    full = build_boq_from_facts(PdfFacts(spine=spine(4, True))).line_items[0]
    assert full.unit_price_zar > plain.unit_price_zar
    assert "4 motor starters" in full.description and "master switch" in full.description


def test_new_boxes_merge_across_sheets_like_the_others():
    from agent.pdf_pipeline.passes.orchestrator import _merge_takeoff
    from agent.pdf_pipeline.passes.facts import LayoutTakeoff, TakeoffRoom
    dst = LayoutTakeoff()
    _merge_takeoff(dst, LayoutTakeoff(rooms=[TakeoffRoom(room_name="Hall", fluorescent_battens=23)]), page=2)
    _merge_takeoff(dst, LayoutTakeoff(rooms=[TakeoffRoom(room_name="Hall", fluorescent_battens=20)]), page=3)
    assert len(dst.rooms) == 1 and dst.rooms[0].fluorescent_battens == 23


def test_counts_from_the_printed_legend_schedule_are_written_evidence():
    from agent.pdf_pipeline.passes.assemble import findings_from_facts
    from agent.pdf_pipeline.passes.facts import parse_layout_takeoff
    from agent.shared.findings import Evidence
    takeoff = parse_layout_takeoff({"rooms": [
        {"room_name": "Block A", "confidence": 0.9, "vapour_proof": 67, "counts_from_legend_schedule": True},
        {"room_name": "Office", "confidence": 0.9, "downlights": 4}]})
    items = findings_from_facts(PdfFacts(takeoff=takeoff)).items
    assert {i.item: i.evidence for i in items} == {"Vapour Proof Light": Evidence.WRITTEN,
                                                   "LED Downlight": Evidence.SEEN}
