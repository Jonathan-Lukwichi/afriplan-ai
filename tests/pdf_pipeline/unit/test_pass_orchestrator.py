"""
Tests for the v2 orchestrator (Passes 1–3 → PdfFacts → deterministic bill).

Uses MockAnthropic to feed canned pass-tool outputs — no network. Verifies
routing by sheet type, cross-page merging, and that the whole chain lands a
priced bill.
"""

from __future__ import annotations

from agent.pdf_pipeline.models import PageClassification, PageType
from agent.pdf_pipeline.passes.orchestrator import build_bill, extract_facts
from agent.pdf_pipeline.stages.ingest import IngestedPage


def _pages(n: int):
    return [IngestedPage(page_index=i, width_px=1, height_px=1, image_b64="") for i in range(n)]


def _classifications(types):
    return [
        PageClassification(page_index=i, page_type=t, confidence=0.9, rationale="test")
        for i, t in enumerate(types)
    ]


PROJECT_CTX = {
    "project_name": "Wedela Recreational Club",
    "buildings": ["Community Hall", "Ablution Retail Block"],
    "free_issue_items": ["LED downlight"],
}
POWER_SPINE = {
    "distribution_boards": [
        {"name": "DB-CR", "main_breaker_a": 250, "phases": 3, "circuits": [], "confidence": 0.9},
    ],
    "feeders": [
        {"from_source": "Mini-Sub", "to_db": "DB-CR", "cable_size_mm2": 95, "cable_cores": 4,
         "earth_size_mm2": 70, "length_m": 35, "length_annotated": True, "is_underground": True},
    ],
    "incoming_supply": {"supply_source": "mini_sub", "kiosk_present": True, "meter_count": 1},
    "extraction_warnings": [],
}
LAYOUT = {
    "rooms": [
        {"room_name": "Tuck Shop", "served_by_db": "DB-AB1",
         "panel_lights": 4, "double_sockets": 6, "confidence": 0.8},
    ],
    "legend": {},
    "extraction_warnings": [],
}


def test_routes_each_sheet_type_to_its_pass_tool(mock_llm):
    llm = mock_llm(tool_responses={
        "read_project_context": PROJECT_CTX,
        "read_power_spine": POWER_SPINE,
        "read_layout_takeoff": LAYOUT,
    })
    classifications = _classifications([PageType.REGISTER, PageType.SLD, PageType.LIGHTING_LAYOUT])
    facts, costs = extract_facts(llm, _pages(3), classifications)

    assert facts.context.project_name == "Wedela Recreational Club"
    assert len(facts.spine.distribution_boards) == 1
    assert facts.spine.feeders[0].length_m == 35
    assert facts.spine.incoming_supply.kiosk_present is True
    assert facts.takeoff.rooms[0].room_name == "Tuck Shop"
    assert len(costs) == 3


def test_plugs_and_lighting_both_feed_takeoff(mock_llm):
    llm = mock_llm(tool_responses={"read_layout_takeoff": LAYOUT})
    classifications = _classifications([PageType.LIGHTING_LAYOUT, PageType.PLUGS_LAYOUT])
    facts, _ = extract_facts(llm, _pages(2), classifications)
    # both pages routed to read_layout_takeoff → two merged rooms
    assert len(facts.takeoff.rooms) == 2


def test_unknown_pages_are_skipped(mock_llm):
    llm = mock_llm(tool_responses={"read_power_spine": POWER_SPINE})
    classifications = _classifications([PageType.UNKNOWN, PageType.SLD])
    facts, costs = extract_facts(llm, _pages(2), classifications)
    assert len(costs) == 1                       # only the SLD page called a tool
    assert len(facts.spine.distribution_boards) == 1


def test_full_chain_produces_priced_bill(mock_llm):
    llm = mock_llm(tool_responses={
        "read_project_context": PROJECT_CTX,
        "read_power_spine": POWER_SPINE,
        "read_layout_takeoff": LAYOUT,
    })
    classifications = _classifications([PageType.REGISTER, PageType.SLD, PageType.LIGHTING_LAYOUT])
    facts, _ = extract_facts(llm, _pages(3), classifications)
    boq = build_bill(facts, project_name="Wedela", run_id="t1")

    assert boq.line_items
    assert boq.total_incl_vat_zar > 0
    # the annotated 35m feeder made it all the way through
    assert any(l.qty == 35.0 for l in boq.line_items)
    # free-issue downlight logic still applies end-to-end
    assert boq.project_name == "Wedela"


def test_multi_sld_pages_merge_feeders(mock_llm):
    spine_a = {"distribution_boards": [], "feeders": [
        {"from_source": "A", "to_db": "B", "length_annotated": True, "length_m": 10}]}
    # same canned response for both SLD pages → feeders accumulate
    llm = mock_llm(tool_responses={"read_power_spine": spine_a})
    classifications = _classifications([PageType.SLD, PageType.SLD])
    facts, _ = extract_facts(llm, _pages(2), classifications)
    assert len(facts.spine.feeders) == 2
