"""
Tests for the v2 pass tool schemas (agent/pdf_pipeline/prompts/pass_schemas.py).

Two guarantees:
  1. Every tool is a well-formed Anthropic tool_use schema.
  2. Realistic payloads modelled on the actual Wedela drawings validate
     against the schemas — and payloads that violate the determinism
     contract (missing required length_annotated etc.) are rejected.
"""

from __future__ import annotations

import jsonschema
import pytest

from agent.pdf_pipeline.prompts.pass_prompts import PROMPT_BY_PASS_TOOL
from agent.pdf_pipeline.prompts.pass_schemas import (
    PASS_TOOLS,
    READ_LAYOUT_TAKEOFF_TOOL,
    READ_POWER_SPINE_TOOL,
    READ_PROJECT_CONTEXT_TOOL,
    TOOL_FOR_SHEET_TYPE,
)

ALL_TOOLS = [
    READ_PROJECT_CONTEXT_TOOL,
    READ_POWER_SPINE_TOOL,
    READ_LAYOUT_TAKEOFF_TOOL,
]


# ─── Structural well-formedness ──────────────────────────────────────

@pytest.mark.parametrize("tool", ALL_TOOLS, ids=lambda t: t["name"])
def test_tool_is_well_formed(tool):
    assert set(tool.keys()) == {"name", "description", "input_schema"}
    assert tool["name"] and isinstance(tool["name"], str)
    assert tool["description"] and isinstance(tool["description"], str)
    schema = tool["input_schema"]
    assert schema["type"] == "object"
    assert "properties" in schema
    # required keys must actually be declared properties
    for req in schema.get("required", []):
        assert req in schema["properties"], f"{tool['name']}: required '{req}' not a property"


@pytest.mark.parametrize("tool", ALL_TOOLS, ids=lambda t: t["name"])
def test_input_schema_is_valid_jsonschema(tool):
    # Raises if the schema itself is not a valid Draft-2020-12 schema
    jsonschema.Draft202012Validator.check_schema(tool["input_schema"])


def test_registry_and_prompts_cover_every_tool():
    assert set(PASS_TOOLS) == {t["name"] for t in ALL_TOOLS}
    assert set(PROMPT_BY_PASS_TOOL) == set(PASS_TOOLS)
    for name, prompt in PROMPT_BY_PASS_TOOL.items():
        assert name in prompt or name.replace("_", " ") in prompt or prompt


def test_sheet_type_routing_points_at_real_tools():
    for sheet_type, tool in TOOL_FOR_SHEET_TYPE.items():
        assert tool in ALL_TOOLS, f"{sheet_type} routes to an unknown tool"


# ─── Realistic Wedela-shaped payloads validate ──────────────────────

def _validate(tool, payload):
    jsonschema.validate(payload, tool["input_schema"])


def test_project_context_payload_validates():
    payload = {
        "project_name": "Upgrading of Wedela Recreational Club",
        "client_name": "Kabe Consulting Engineers",
        "consultant_name": "Chona-Malanga Engineering",
        "standard": "SANS 10142-1",
        "revision": "RA",
        "buildings": ["Community Hall", "Swimming Pool", "Kiosk", "Ablution Retail Block"],
        "free_issue_items": ["LED downlights"],
        "drawing_index": [
            {"drawing_no": "WD-KIOSK-01-SLD", "title": "Kiosk SLD", "sheet_type": "sld"},
        ],
        "legend": {"D/N": "Day/night switch @2000mm"},
        "extraction_warnings": [],
    }
    _validate(READ_PROJECT_CONTEXT_TOOL, payload)


def test_power_spine_payload_with_annotated_feeder_validates():
    payload = {
        "distribution_boards": [
            {
                "name": "DB-CR",
                "location": "Kiosk",
                "main_breaker_a": 250,
                "phases": 3,
                "voltage_v": 400,
                "ka_rating": 15,
                "enclosure_mount": "floor_standing",
                "elcb_present": True,
                "surge_protection": True,
                "circuits": [
                    {"circuit_id": "Q5", "breaker_a": 250, "load_type": "other", "is_spare": False},
                    {"circuit_id": "SPARE", "breaker_a": 20, "load_type": "spare", "is_spare": True},
                ],
                "confidence": 0.9,
            }
        ],
        "feeders": [
            {
                "from_source": "Mini-Sub", "to_db": "DB-CR",
                "cable_size_mm2": 95, "cable_cores": 4, "cable_type": "swa_pvc",
                "earth_size_mm2": 70, "length_m": 35, "length_annotated": True,
                "is_underground": True, "confidence": 0.85,
            },
            {   # missing-length feeder: length_annotated FALSE, length 0
                "from_source": "DB-CR", "to_db": "DB1",
                "length_annotated": False, "length_m": 0,
            },
        ],
        "incoming_supply": {
            "supply_source": "mini_sub", "kiosk_present": True, "meter_count": 1,
            "incomer_cable_size_mm2": 95, "incomer_length_m": 0,
            "incomer_length_annotated": False,
        },
        "extraction_warnings": [],
    }
    _validate(READ_POWER_SPINE_TOOL, payload)


def test_power_spine_feeder_requires_length_annotated_flag():
    # Determinism contract: a feeder MUST declare whether its length was drawn
    bad = {
        "distribution_boards": [],
        "feeders": [{"from_source": "DB-CR", "to_db": "DB1"}],  # no length_annotated
    }
    with pytest.raises(jsonschema.ValidationError):
        _validate(READ_POWER_SPINE_TOOL, bad)


def test_layout_takeoff_payload_validates():
    payload = {
        "rooms": [
            {
                "room_name": "Tuck Shop", "room_type": "retail", "area_m2": 52,
                "served_by_db": "DB-AB1", "ceiling_height_m": 3.0,
                "circuit_tags": ["L4", "S6", "S5"],
                "double_sockets": 6, "panel_lights": 4, "isolators": 1,
                "switches_2lever": 1, "confidence": 0.8,
            },
            {"room_name": "Duct", "confidence": 0.4},  # minimal room
        ],
        "legend": {"⊞": "16A Double Switched Socket"},
        "extraction_warnings": ["Storage 03 partially cut off"],
    }
    _validate(READ_LAYOUT_TAKEOFF_TOOL, payload)


def test_layout_takeoff_rejects_negative_counts():
    bad = {"rooms": [{"room_name": "X", "double_sockets": -1, "confidence": 0.5}]}
    with pytest.raises(jsonschema.ValidationError):
        _validate(READ_LAYOUT_TAKEOFF_TOOL, bad)


def test_extra_properties_are_rejected():
    # additionalProperties:False everywhere keeps the LLM from inventing fields
    bad = {"rooms": [{"room_name": "X", "confidence": 0.5, "made_up_field": 3}]}
    with pytest.raises(jsonschema.ValidationError):
        _validate(READ_LAYOUT_TAKEOFF_TOOL, bad)
