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
