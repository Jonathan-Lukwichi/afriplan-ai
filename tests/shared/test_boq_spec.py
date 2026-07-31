"""
Tests for the v2 BOQ spec extensions (supply/install split, gap report,
new confidence tags). All additive — old behaviour must still hold.
"""

from __future__ import annotations

from agent.shared import (
    BillOfQuantities,
    BQLineItem,
    BQSection,
    GapItem,
    ItemConfidence,
    LineKind,
)


def test_new_confidence_tags_exist():
    assert ItemConfidence.ASSUMED.value == "assumed"
    assert ItemConfidence.PROVISIONAL.value == "provisional"
    # legacy tags still present
    assert ItemConfidence.EXTRACTED.value == "extracted"


def test_line_kind_defaults_to_combined():
    item = BQLineItem(description="6W LED downlight", unit="No", qty=75)
    assert item.line_kind == LineKind.COMBINED
    assert item.assumption == ""


def test_supply_install_split_lines():
    supply = BQLineItem(
        section=BQSection.SUBMAIN_CABLES, description="50mm2x4C SWA",
        unit="m", qty=45, line_kind=LineKind.SUPPLY,
    )
    install = BQLineItem(
        section=BQSection.SUBMAIN_CABLES, description="50mm2x4C SWA",
        unit="m", qty=45, line_kind=LineKind.INSTALL,
    )
    assert supply.line_kind == LineKind.SUPPLY
    assert install.line_kind == LineKind.INSTALL


def test_assumed_item_carries_assumption():
    item = BQLineItem(
        description="Feeder DB-CR->DB1",
        unit="m", qty=45,
        source=ItemConfidence.ASSUMED,
        assumption="Length not on SLD; assumed 45m from route.",
    )
    assert item.source == ItemConfidence.ASSUMED
    assert "assumed" in item.assumption.lower()


def test_gap_report_on_boq():
    gap = GapItem(
        section=BQSection.SUBMAIN_CABLES,
        description="Feeder DB-CR->DB1 length not dimensioned",
        assumption="Assumed 45m from routed estimate.",
        suggested_action="Confirm feeder length on SLD.",
        severity="high",
    )
    boq = BillOfQuantities(pipeline="pdf", gaps=[gap], items_assumed=1)
    assert len(boq.gaps) == 1
    assert boq.items_assumed == 1
    assert boq.gaps[0].severity == "high"


def test_boq_still_constructs_with_no_v2_fields():
    # Backward-compat: old construction path unchanged
    boq = BillOfQuantities(pipeline="dxf")
    assert boq.gaps == []
    assert boq.items_assumed == 0
    assert boq.items_provisional == 0


def test_boq_json_roundtrip_includes_gaps():
    gap = GapItem(description="x", assumption="y", suggested_action="z")
    boq = BillOfQuantities(pipeline="pdf", gaps=[gap])
    dumped = boq.model_dump_json()
    restored = BillOfQuantities.model_validate_json(dumped)
    assert restored.gaps[0].description == "x"
