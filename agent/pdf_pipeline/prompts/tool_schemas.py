"""
Strict JSON schemas for the per-page-type extraction tools.

Per blueprint §3.4 acceptance criterion 4: hand-rolled JSON parsing is
banned anywhere under agent/pdf_pipeline/. We use Anthropic's tool_use
with strict schemas so the SDK validates structure for us — no
markdown-fence stripping, no trailing-comma fixes, no rescue parsers.

Each schema is a dict in the exact shape the Anthropic SDK expects:
    { "name": str, "description": str, "input_schema": {...} }
"""

from __future__ import annotations

from typing import Any, Dict


# ─── Reusable sub-schemas ─────────────────────────────────────────────

_CONFIDENCE = {
    "type": "number",
    "minimum": 0.0,
    "maximum": 1.0,
    "description": "Confidence in this extracted value, 0.0–1.0.",
}


_CIRCUIT_ROW = {
    "type": "object",
    "properties": {
        "circuit_id":    {"type": "string", "description": "e.g. 'L1', 'P3', 'ISO-1'"},
        "description":   {"type": "string"},
        "breaker_a":     {"type": "integer", "minimum": 0},
        "breaker_poles": {"type": "integer", "minimum": 1, "maximum": 4},
        "cable_size_mm2":{"type": "number",  "minimum": 0},
        "cable_cores":   {"type": "integer", "minimum": 0},
        "num_points":    {"type": "integer", "minimum": 0},
        "is_spare":      {"type": "boolean"},
        "notes":         {"type": "string"},
    },
    "required": ["circuit_id", "breaker_a"],
    "additionalProperties": False,
}


# ─── classify_page tool (Haiku) ───────────────────────────────────────

CLASSIFY_PAGE_TOOL: Dict[str, Any] = {
    "name": "classify_page",
    "description": (
        "Classify the role this drawing page plays in an electrical plan set. "
        "Choose ONE page_type that best matches the dominant content."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "page_type": {
                "type": "string",
                "enum": [
                    "register",
                    "sld",
                    "lighting_layout",
                    "plugs_layout",
                    "schedule",
                    "notes",
                    "unknown",
                ],
                "description": (
                    "register = title block / cover sheet. "
                    "sld = single-line diagram (DB schedule + circuit list). "
                    "lighting_layout = floor plan showing light fittings. "
                    "plugs_layout = floor plan showing socket outlets. "
                    "schedule = tabular schedule (lighting/power/cable). "
                    "notes = legend / general notes / specifications. "
                    "unknown = none of the above."
                ),
            },
            "confidence": _CONFIDENCE,
            "rationale": {
                "type": "string",
                "description": "One sentence: which visual cues drove the classification.",
            },
        },
        "required": ["page_type", "confidence", "rationale"],
        "additionalProperties": False,
    },
}


# ─── extract_sld tool ─────────────────────────────────────────────────

EXTRACT_SLD_TOOL: Dict[str, Any] = {
    "name": "extract_sld",
    "description": (
        "Extract distribution boards and their circuits from a single-line "
        "diagram or DB schedule page. Read every visible row of every "
        "schedule. If a value is not legible, set it to 0 / empty string and "
        "flag it via per_field_confidence."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "distribution_boards": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "name":            {"type": "string"},
                        "location":        {"type": "string"},
                        "main_breaker_a":  {"type": "integer", "minimum": 0},
                        "phases":          {"type": "integer", "enum": [1, 3]},
                        "voltage_v":       {"type": "integer", "enum": [230, 400]},
                        "elcb_present":    {"type": "boolean"},
                        "surge_protection":{"type": "boolean"},
                        "circuits":        {"type": "array", "items": _CIRCUIT_ROW},
                        "confidence":      _CONFIDENCE,
                    },
                    "required": ["name", "main_breaker_a", "phases", "circuits", "confidence"],
                    "additionalProperties": False,
                },
            },
            "extraction_warnings": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Anything illegible, ambiguous, or missing.",
            },
        },
        "required": ["distribution_boards"],
        "additionalProperties": False,
    },
}


# ─── extract_lighting_layout tool ─────────────────────────────────────

_FIXTURE_COUNTS_PROPS = {
    "downlights":            {"type": "integer", "minimum": 0},
    "panel_lights":          {"type": "integer", "minimum": 0},
    "bulkheads":             {"type": "integer", "minimum": 0},
    "floodlights":           {"type": "integer", "minimum": 0},
    "emergency_lights":      {"type": "integer", "minimum": 0},
    "exit_signs":            {"type": "integer", "minimum": 0},
    "pool_flood_light":      {"type": "integer", "minimum": 0},
    "pool_underwater_light": {"type": "integer", "minimum": 0},
}

EXTRACT_LIGHTING_TOOL: Dict[str, Any] = {
    "name": "extract_lighting_layout",
    "description": (
        "Walk every visible room on this lighting layout. For each room, "
        "count every fixture symbol exactly once using the page's legend. "
        "Do not invent rooms; do not infer counts from area."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "rooms": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "room_name":  {"type": "string"},
                        "room_type":  {"type": "string", "description": "bedroom | bathroom | kitchen | …"},
                        **_FIXTURE_COUNTS_PROPS,
                        "confidence": _CONFIDENCE,
                    },
                    "required": ["room_name", "confidence"],
                    "additionalProperties": False,
                },
            },
            "legend": {
                "type": "object",
                "additionalProperties": {"type": "string"},
                "description": "Symbol → description map taken from the legend.",
            },
            "extraction_warnings": {"type": "array", "items": {"type": "string"}},
        },
        "required": ["rooms"],
        "additionalProperties": False,
    },
}


# ─── extract_plugs_layout tool ────────────────────────────────────────

_OUTLET_PROPS = {
    "double_sockets":      {"type": "integer", "minimum": 0},
    "single_sockets":      {"type": "integer", "minimum": 0},
    "waterproof_sockets":  {"type": "integer", "minimum": 0},
    "floor_sockets":       {"type": "integer", "minimum": 0},
    "data_outlets":        {"type": "integer", "minimum": 0},
    "switches_1lever":     {"type": "integer", "minimum": 0},
    "switches_2lever":     {"type": "integer", "minimum": 0},
    "switches_3lever":     {"type": "integer", "minimum": 0},
    "isolators":           {"type": "integer", "minimum": 0},
    "day_night_switches":  {"type": "integer", "minimum": 0},
}

EXTRACT_PLUGS_TOOL: Dict[str, Any] = {
    "name": "extract_plugs_layout",
    "description": (
        "Walk every visible room on this plugs/sockets layout. Count every "
        "outlet, switch, and isolator symbol exactly once using the legend."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "rooms": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "room_name":  {"type": "string"},
                        "room_type":  {"type": "string"},
                        **_OUTLET_PROPS,
                        "confidence": _CONFIDENCE,
                    },
                    "required": ["room_name", "confidence"],
                    "additionalProperties": False,
                },
            },
            "extraction_warnings": {"type": "array", "items": {"type": "string"}},
        },
        "required": ["rooms"],
        "additionalProperties": False,
    },
}


# ─── extract_schedule tool ────────────────────────────────────────────

EXTRACT_SCHEDULE_TOOL: Dict[str, Any] = {
    "name": "extract_schedule",
    "description": (
        "Extract a tabular schedule (typically a circuit/cable schedule) "
        "from this page. One row per circuit."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "title": {"type": "string"},
            "rows":  {"type": "array", "items": _CIRCUIT_ROW},
            "extraction_warnings": {"type": "array", "items": {"type": "string"}},
        },
        "required": ["rows"],
        "additionalProperties": False,
    },
}


# ─── extract_notes tool ───────────────────────────────────────────────

EXTRACT_NOTES_TOOL: Dict[str, Any] = {
    "name": "extract_notes",
    "description": (
        "Extract project metadata and general notes from this page (typically "
        "the cover sheet, legend page, or specification page)."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "project_name":     {"type": "string"},
            "client_name":      {"type": "string"},
            "consultant_name":  {"type": "string"},
            "drawing_numbers":  {"type": "array", "items": {"type": "string"}},
            "revision":         {"type": "integer"},
            "site_address":     {"type": "string"},
            "notes":            {"type": "array", "items": {"type": "string"}},
            "legend":           {"type": "object", "additionalProperties": {"type": "string"}},
        },
        "additionalProperties": False,
    },
}


# Registry — used by extract.py to pick the right tool per page_type
TOOLS_BY_PAGE_TYPE: Dict[str, Dict[str, Any]] = {
    "sld":              EXTRACT_SLD_TOOL,
    "lighting_layout":  EXTRACT_LIGHTING_TOOL,
    "plugs_layout":     EXTRACT_PLUGS_TOOL,
    "schedule":         EXTRACT_SCHEDULE_TOOL,
    "notes":            EXTRACT_NOTES_TOOL,
    "register":         EXTRACT_NOTES_TOOL,   # cover sheet → same shape as notes
}
