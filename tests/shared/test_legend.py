"""
Tests for the shared LDSE spec (agent/shared/legend.py) — the description→BOQ
bridge that turns a drawing's legend text into priced BOQ items.
"""

from __future__ import annotations

import pytest

from agent.shared import BQSection
from agent.shared.legend import (
    Legend,
    LegendEntry,
    build_legend_entry,
    classify_description,
    parse_mounting_mm,
)


@pytest.mark.parametrize("text,item,section", [
    ("16A Double Switched Socket @300mm above FFL.", "16A Double Switched Socket", BQSection.POWER_OUTLETS),
    ("16A Single Switched Socket", "16A Single Switched Socket", BQSection.POWER_OUTLETS),
    ("1lever ,1 Way Switch @ 1200mm above FFL.", "1-Lever Switch", BQSection.LIGHTING),
    ("2 lever,1 Way Switch", "2-Lever Switch", BQSection.LIGHTING),
    ("Day/night switch @ 2000mm", "Day/Night Switch", BQSection.LIGHTING),
    ("30A Isolator Switch", "Isolator Switch", BQSection.POWER_OUTLETS),
    ("600 x 1200 Recessed 3 x 18W LED fluorescent light", "Recessed LED Panel", BQSection.LIGHTING),
    ("30W LED flood light", "LED Floodlight", BQSection.LIGHTING),
    ("18W LED Ceiling light surface mount", "Surface LED Light", BQSection.LIGHTING),
    ("DATA SOCKET OUTLET CAT 6", "Data Socket (CAT6)", BQSection.DATA_COMMS),
    ("Emergency light fitting", "Emergency Light", BQSection.FIRE_SAFETY),
    ("Distribution Board", "Distribution Board", BQSection.DISTRIBUTION),
    ("Solar Photovoltaic Panel", "Solar PV Panel", BQSection.SOLAR_PV),
])
def test_classify_real_legend_descriptions(text, item, section):
    hit = classify_description(text)
    assert hit is not None, text
    assert hit == (item, section)


@pytest.mark.parametrize("header", ["SWITCHES", "POWER SOCKETS", "LIGHTS", "OTHERS", "QTYS", ""])
def test_headers_and_noise_are_not_items(header):
    assert classify_description(header) is None


def test_parse_mounting_height():
    assert parse_mounting_mm("16A Double Switched Socket @300mm above FFL.") == 300
    assert parse_mounting_mm("Switch @ 1200mm") == 1200
    assert parse_mounting_mm("no height here") is None


def test_build_legend_entry_populates_fields():
    e = build_legend_entry("16A Double Switched Socket @300mm above FFL.", symbol_key="DS")
    assert e is not None
    assert e.canonical_item == "16A Double Switched Socket"
    assert e.section == BQSection.POWER_OUTLETS
    assert e.mounting_mm == 300
    assert e.symbol_key == "DS"


def test_build_legend_entry_returns_none_for_header():
    assert build_legend_entry("LIGHTS") is None


def test_legend_by_canonical():
    leg = Legend(entries=[
        build_legend_entry("16A Double Switched Socket"),
        build_legend_entry("30W LED flood light"),
    ])
    grouped = leg.by_canonical()
    assert "16A Double Switched Socket" in grouped
    assert "LED Floodlight" in grouped
