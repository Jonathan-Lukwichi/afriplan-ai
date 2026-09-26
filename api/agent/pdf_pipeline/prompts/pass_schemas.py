"""
v2 estimator — strict tool schemas for the 5-pass PDF pipeline.

These are the "eyes" of the pipeline. Each tool lets the vision LLM report
FACTS it can see on the drawing — counts, cable sizes, and lengths exactly as
annotated. The LLM never computes a rate, never derives a quantity, never
estimates a missing length: that is the job of the deterministic brain
(core/rate_model.py) in Passes 4–5.

The determinism contract shows up directly in these schemas as *_annotated
booleans: the LLM must say whether a value was actually drawn, so the brain
knows whether to trust it or flag it ASSUMED. The LLM reports "not shown";
Python decides what to assume.

Passes:
    1  read_project_context   register / title / legend  → project model
    2  read_power_spine       SLD                          → DB tree + feeders
    3  read_layout_takeoff    lighting / plugs layout      → per-room counts
    (4 rule-set and 5 assemble are pure Python — no LLM tool.)

Schema shape matches the Anthropic SDK:
    { "name": str, "description": str, "input_schema": {...} }
Hand-rolled JSON parsing stays banned (blueprint §3.4) — tool_use validates.
"""

from __future__ import annotations

from typing import Any, Dict


# ─── Reusable sub-schemas ─────────────────────────────────────────────

_CONFIDENCE = {
    "type": "number",
    "minimum": 0.0,
    "maximum": 1.0,
    "description": "Confidence in this value, 0.0–1.0 (see system-prompt bands).",
}

_WARNINGS = {
    "type": "array",
    "items": {"type": "string"},
    "description": "Anything illegible, ambiguous, cut off, or continued on another sheet.",
}


# ═══════════════════════════════════════════════════════════════════════
#  PASS 1 — read_project_context
# ═══════════════════════════════════════════════════════════════════════

READ_PROJECT_CONTEXT_TOOL: Dict[str, Any] = {
    "name": "read_project_context",
    "description": (
        "Read the orienting context of the drawing SET from a cover sheet, "
        "drawing register, title block, or legend page. Capture the project "
        "identity, the list of buildings/blocks, the drawing index, the symbol "
        "legend, and any items the notes mark as FREE-ISSUED / supplied by the "
        "client. Report only what is written — do not infer buildings that are "
        "not named."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "project_name":    {"type": "string"},
            "client_name":     {"type": "string"},
            "consultant_name": {"type": "string"},
            "contractor_name": {"type": "string"},
            "site_address":    {"type": "string"},
            "standard":        {"type": "string", "description": "e.g. 'SANS 10142-1'"},
            "revision":        {"type": "string", "description": "Revision as written, e.g. 'Rev01' or 'RA'."},
            "drawing_numbers": {"type": "array", "items": {"type": "string"}},
            "buildings": {
                "type": "array",
                "items": {"type": "string"},
                "description": (
                    "Named buildings / blocks / parts in the set, e.g. "
                    "'Community Hall', 'Swimming Pool', 'Kiosk'. Drives whether "
                    "the bill is one section or per-building."
                ),
            },
            "free_issue_items": {
                "type": "array",
                "items": {"type": "string"},
                "description": (
                    "Items a note marks as free-issued / supplied by client "
                    "(install-only). Quote the item, e.g. 'LED downlights'."
                ),
            },
            "drawing_index": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "drawing_no": {"type": "string"},
                        "title":      {"type": "string"},
                        "sheet_type": {
                            "type": "string",
                            "enum": ["sld", "lighting_layout", "plugs_layout",
                                     "layout", "schedule", "register", "notes", "other"],
                        },
                    },
                    "required": ["drawing_no"],
                    "additionalProperties": False,
                },
            },
            "legend": {
                "type": "object",
                "additionalProperties": {"type": "string"},
                "description": "Symbol → meaning map exactly as printed in the legend.",
            },
            "notes":              {"type": "array", "items": {"type": "string"}},
            "extraction_warnings": _WARNINGS,
        },
        "additionalProperties": False,
    },
}


# ═══════════════════════════════════════════════════════════════════════
#  PASS 2 — read_power_spine  (the deterministic crux: DB tree + feeders)
# ═══════════════════════════════════════════════════════════════════════

_LOAD_TYPE = {
    "type": "string",
    "enum": ["lighting", "socket", "geyser", "aircon", "motor",
             "pool_pump", "heat_pump", "isolator", "spare", "other"],
    "description": "What the circuit feeds. 'spare' for unused ways.",
}

_SPINE_CIRCUIT_ROW = {
    "type": "object",
    "properties": {
        "circuit_id":     {"type": "string", "description": "e.g. 'L1', 'P3', 'ISO-1'"},
        "description":    {"type": "string"},
        "breaker_a":      {"type": "integer", "minimum": 0},
        "breaker_poles":  {"type": "integer", "minimum": 1, "maximum": 4},
        "cable_size_mm2": {"type": "number",  "minimum": 0},
        "cable_cores":    {"type": "integer", "minimum": 0},
        "num_points":     {"type": "integer", "minimum": 0},
        "load_type":      _LOAD_TYPE,
        "is_spare":       {"type": "boolean"},
        "notes":          {"type": "string"},
    },
    "required": ["circuit_id", "breaker_a"],
    "additionalProperties": False,
}

_FEEDER = {
    "type": "object",
    "description": (
        "One sub-main / feeder cable run between two nodes in the SLD. This is "
        "the backbone of Section A/F. Report the length ONLY if a number is "
        "printed on the run; otherwise set length_m=0 and length_annotated=false."
    ),
    "properties": {
        "from_source": {"type": "string", "description": "Origin node, e.g. 'Mini-Sub', 'DB-CR', 'DB1'."},
        "to_db":       {"type": "string", "description": "Destination DB, e.g. 'DB-ST'."},
        "cable_size_mm2": {"type": "number", "minimum": 0},
        "cable_cores":    {"type": "integer", "minimum": 0},
        "cable_type": {
            "type": "string",
            "enum": ["swa_pvc", "abc_xlpe", "pvc", "surfix", "other"],
        },
        "earth_size_mm2": {
            "type": "number", "minimum": 0,
            "description": "BCEW earth size if shown alongside the feeder; 0 if not shown.",
        },
        "length_m": {
            "type": "number", "minimum": 0,
            "description": "Run length in metres EXACTLY as annotated. 0 if none printed.",
        },
        "length_annotated": {
            "type": "boolean",
            "description": "TRUE only if a length was actually printed on this run. Critical.",
        },
        "is_underground": {"type": "boolean"},
        "confidence": _CONFIDENCE,
    },
    "required": ["from_source", "to_db", "length_annotated"],
    "additionalProperties": False,
}

_SPINE_DB = {
    "type": "object",
    "properties": {
        "name":            {"type": "string"},
        "location":        {"type": "string"},
        "main_breaker_a":  {"type": "integer", "minimum": 0},
        "phases":          {"type": "integer", "enum": [1, 3]},
        "voltage_v":       {"type": "integer", "enum": [230, 400]},
        "ka_rating":       {"type": "number", "minimum": 0, "description": "Fault rating in kA if shown."},
        "enclosure_mount": {
            "type": "string",
            "enum": ["surface", "floor_standing", "kiosk", "unknown"],
        },
        "elcb_present":     {"type": "boolean"},
        "surge_protection": {"type": "boolean"},
        "circuits":         {"type": "array", "items": _SPINE_CIRCUIT_ROW},
        "confidence":       _CONFIDENCE,
        "source_snippet": {
            "type": "string",
            "description": (
                "Quote the exact busbar header text you read this board's name "
                "and main_breaker_a from, verbatim, e.g. 'DB-AB1  400V, 100A, "
                "15kA'. Used to catch misreads (e.g. reporting the voltage "
                "figure as the amperage)."
            ),
        },
    },
    "required": ["name", "circuits", "confidence"],
    "additionalProperties": False,
}

READ_POWER_SPINE_TOOL: Dict[str, Any] = {
    "name": "read_power_spine",
    "description": (
        "From a single-line diagram / DB schedule, read the power spine: every "
        "distribution board (with its breakers and circuit rows including "
        "spares) AND every feeder cable run between nodes. For each feeder, "
        "read the run length ONLY if it is printed on the drawing — never "
        "estimate it. Also capture the incoming supply (municipal / mini-sub / "
        "kiosk / generator) and metering. Read every visible schedule row."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "distribution_boards": {"type": "array", "items": _SPINE_DB},
            "feeders":             {"type": "array", "items": _FEEDER},
            "incoming_supply": {
                "type": "object",
                "properties": {
                    "supply_source": {
                        "type": "string",
                        "enum": ["municipal", "mini_sub", "kiosk", "generator", "existing", "unknown"],
                    },
                    "kiosk_present":          {"type": "boolean"},
                    "meter_count":            {"type": "integer", "minimum": 0},
                    "incomer_cable_size_mm2": {"type": "number", "minimum": 0},
                    "incomer_length_m":       {"type": "number", "minimum": 0},
                    "incomer_length_annotated": {"type": "boolean"},
                },
                "additionalProperties": False,
            },
            "extraction_warnings": _WARNINGS,
        },
        "required": ["distribution_boards", "feeders"],
        "additionalProperties": False,
    },
}


# ═══════════════════════════════════════════════════════════════════════
#  PASS 3 — read_layout_takeoff  (per-room counts, tied to a DB)
# ═══════════════════════════════════════════════════════════════════════

_ROOM_FITTINGS = {
    # Lighting
    "downlights":        {"type": "integer", "minimum": 0},
    "panel_lights":      {"type": "integer", "minimum": 0, "description": "600×1200 / 600×600 recessed panels."},
    "bulkheads":         {"type": "integer", "minimum": 0},
    "vapour_proof":      {"type": "integer", "minimum": 0},
    "floodlights":       {"type": "integer", "minimum": 0},
    "emergency_lights":  {"type": "integer", "minimum": 0},
    "pole_lights":       {"type": "integer", "minimum": 0},
    # Site / external lighting (often on a site or external-works layout)
    "solar_post_lights": {"type": "integer", "minimum": 0,
                          "description": "Stand-alone SOLAR-powered LED post / lantern lights (count posts)."},
    "high_mast_poles":   {"type": "integer", "minimum": 0,
                          "description": "High-mast / tall flood-light POSTS (>= 6 m). Count posts, not lamp heads."},
    # Power
    "double_sockets":    {"type": "integer", "minimum": 0},
    "single_sockets":    {"type": "integer", "minimum": 0},
    "waterproof_sockets":{"type": "integer", "minimum": 0},
    "floor_sockets":     {"type": "integer", "minimum": 0},
    "data_outlets":      {"type": "integer", "minimum": 0},
    # Control
    "switches_1lever":   {"type": "integer", "minimum": 0},
    "switches_2lever":   {"type": "integer", "minimum": 0},
    "switches_3lever":   {"type": "integer", "minimum": 0},
    "isolators":         {"type": "integer", "minimum": 0},
    "day_night_switches":{"type": "integer", "minimum": 0},
}

_TAKEOFF_ROOM = {
    "type": "object",
    "properties": {
        "room_name":  {"type": "string"},
        "room_type":  {"type": "string", "description": "office | ablution | kitchen | store | …"},
        "area_m2":    {"type": "number", "minimum": 0, "description": "As labelled on plan; 0 if not shown."},
        "served_by_db": {
            "type": "string",
            "description": "DB tag shown for/near this room, e.g. 'DB-AB1'. Empty if not shown.",
        },
        "ceiling_height_m": {
            "type": "number", "minimum": 0,
            "description": "As noted; 0 if not shown. Used only for routed-length reasoning.",
        },
        "circuit_tags": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Circuit labels visible in the room, e.g. ['L2-1','S4','ISO1'].",
        },
        **_ROOM_FITTINGS,
        "confidence": _CONFIDENCE,
    },
    "required": ["room_name", "confidence"],
    "additionalProperties": False,
}

READ_LAYOUT_TAKEOFF_TOOL: Dict[str, Any] = {
    "name": "read_layout_takeoff",
    "description": (
        "Walk EVERY visible room on this lighting/plugs layout. Using the "
        "page legend as the symbol dictionary, count every fitting, outlet, "
        "switch and isolator symbol exactly once. Tie each room to the DB tag "
        "shown for it and list the circuit labels visible in the room. Count "
        "what you SEE — never infer counts from room area or type."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "rooms": {"type": "array", "items": _TAKEOFF_ROOM},
            "legend": {
                "type": "object",
                "additionalProperties": {"type": "string"},
                "description": "Symbol → fitting-type map from this page's legend.",
            },
            "extraction_warnings": _WARNINGS,
        },
        "required": ["rooms"],
        "additionalProperties": False,
    },
}


# ─── Registry: pass name → tool (used by the v2 orchestrator in Step 3) ──

PASS_TOOLS: Dict[str, Dict[str, Any]] = {
    "read_project_context": READ_PROJECT_CONTEXT_TOOL,
    "read_power_spine":      READ_POWER_SPINE_TOOL,
    "read_layout_takeoff":   READ_LAYOUT_TAKEOFF_TOOL,
}

# Which tool applies to each classified sheet type
TOOL_FOR_SHEET_TYPE: Dict[str, Dict[str, Any]] = {
    "register":         READ_PROJECT_CONTEXT_TOOL,
    "notes":            READ_PROJECT_CONTEXT_TOOL,
    "sld":              READ_POWER_SPINE_TOOL,
    "lighting_layout":  READ_LAYOUT_TAKEOFF_TOOL,
    "plugs_layout":     READ_LAYOUT_TAKEOFF_TOOL,
    "layout":           READ_LAYOUT_TAKEOFF_TOOL,
}
