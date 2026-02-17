"""
AfriPlan Electrical v4.1 — JSON Schemas for AI Extraction

Contains example JSON structures that guide Claude's structured output.
v4.1 addition: Every extracted value includes a confidence field:
- "extracted": read directly from the drawing
- "inferred": calculated from other values
- "estimated": using a default or guessing
"""

# Confidence instruction to add to all prompts
CONFIDENCE_INSTRUCTION = '''
For each value you extract, set a confidence level:
- "extracted": you read this directly from the drawing
- "inferred": you calculated this from other values
- "estimated": you are using a default or guessing

Example: If you can read "384W" in the circuit schedule → "extracted"
If you count 8 lights at 48W each to get 384W → "inferred"
If you can't clearly read the value → "estimated"

Always include confidence for:
- Circuit wattages and point counts
- Cable lengths (especially important - mark "estimated" if not on drawing)
- Fixture counts per room
- Breaker ratings
- Equipment ratings
'''

# Schema for project metadata extraction from register/transmittal pages
REGISTER_SCHEMA = """{
  "project_name": "Wedela Recreational Club",
  "project_number": "WD-001",
  "client_name": "Wedela Mining",
  "client_contact": "John Smith",
  "client_email": "john@wedela.com",
  "client_phone": "011 234 5678",
  "site_address": "123 Mining Road, Carletonville",
  "engineer_name": "ABC Electrical Engineers",
  "engineer_ref": "ABC/WD/2024",
  "drawing_date": "2024-03-15",
  "revision": "C",
  "notes": ["Phase 1 of 2", "Existing services to remain"]
}"""

# Schema for SLD extraction - distribution boards with circuits
SLD_SCHEMA = """{
  "building_block": "Pool Block",
  "distribution_boards": [
    {
      "name": "DB-PFA",
      "confidence": "extracted",
      "description": "Pool Filter Area Distribution Board",
      "location": "Pool Filter Room",
      "supply_from": "DB-CR",
      "supply_cable": "16mm² 4C PVC SWA PVC",
      "supply_cable_size_mm2": 16,
      "supply_cable_length_m": 45,
      "main_breaker_a": 100,
      "earth_leakage": true,
      "earth_leakage_rating_a": 63,
      "surge_protection": true,
      "phase": "3PH",
      "voltage_v": 400,
      "fault_level_ka": 15,
      "circuits": [
        {
          "id": "L1",
          "type": "lighting",
          "description": "Pool area lighting",
          "wattage_w": 384,
          "wattage_formula": "8x48W",
          "confidence": "extracted",
          "cable_size_mm2": 2.5,
          "cable_cores": 3,
          "cable_type": "GP WIRE",
          "breaker_a": 10,
          "breaker_poles": 1,
          "num_points": 8
        },
        {
          "id": "P1",
          "type": "power",
          "description": "Pool filter area sockets",
          "wattage_w": 3680,
          "confidence": "inferred",
          "cable_size_mm2": 2.5,
          "cable_cores": 3,
          "cable_type": "GP WIRE",
          "breaker_a": 20,
          "breaker_poles": 1,
          "num_points": 4
        },
        {
          "id": "PP1",
          "type": "pump",
          "description": "Pool Pump 1 (2.2kW)",
          "wattage_w": 2200,
          "confidence": "extracted",
          "cable_size_mm2": 4,
          "cable_cores": 4,
          "cable_type": "PVC SWA PVC",
          "breaker_a": 32,
          "breaker_poles": 3,
          "has_vsd": true,
          "has_isolator": true,
          "isolator_rating_a": 30
        },
        {
          "id": "SP1",
          "type": "spare",
          "description": "Spare",
          "is_spare": true,
          "confidence": "extracted"
        }
      ],
      "spare_ways": 4
    }
  ],
  "heavy_equipment": [
    {
      "name": "Pool Pump 1",
      "type": "pool_pump",
      "rating_kw": 2.2,
      "confidence": "extracted",
      "cable_size_mm2": 4,
      "cable_type": "PVC SWA PVC",
      "breaker_a": 32,
      "has_vsd": true,
      "isolator_a": 30,
      "fed_from_db": "DB-PFA",
      "qty": 1
    }
  ]
}"""

# Schema for lighting layout extraction - rooms with light fixtures
LIGHTING_LAYOUT_SCHEMA = """{
  "building_block": "NewMark Office Building",
  "rooms": [
    {
      "name": "Suite 1 - Open Plan",
      "room_number": 1,
      "type": "office_open_plan",
      "confidence": "extracted",
      "area_m2": 120,
      "floor": "Ground",
      "fixtures": {
        "recessed_led_600x1200": 16,
        "recessed_led_600x1200_confidence": "extracted"
      },
      "circuit_refs": ["DB-S1 L1", "DB-S1 L2"]
    },
    {
      "name": "Male Ablution",
      "room_number": 2,
      "type": "ablution",
      "confidence": "extracted",
      "area_m2": 25,
      "floor": "Ground",
      "is_wet_area": true,
      "fixtures": {
        "vapor_proof_2x24w": 4,
        "vapor_proof_2x24w_confidence": "extracted"
      },
      "circuit_refs": ["DB-AB1 L1"]
    },
    {
      "name": "Kitchen",
      "room_number": 3,
      "type": "kitchen",
      "confidence": "inferred",
      "area_m2": 18,
      "floor": "Ground",
      "fixtures": {
        "recessed_led_600x1200": 2,
        "recessed_led_600x1200_confidence": "estimated",
        "downlight_led_6w": 4,
        "downlight_led_6w_confidence": "estimated"
      },
      "circuit_refs": ["DB-S1 L3"],
      "notes": ["Fixture count estimated from room size - not visible on drawing"]
    }
  ],
  "legend": {
    "block_name": "NewMark Office Building",
    "lights": [
      {
        "symbol_id": "LT-REC",
        "category": "light",
        "description": "600x1200 Recessed LED Panel 3x18W",
        "short_name": "600x1200 Recessed LED",
        "wattage_w": 54,
        "ip_rating": "IP20"
      },
      {
        "symbol_id": "LT-VP24",
        "category": "light",
        "description": "2x24W Double Vapor Proof LED",
        "short_name": "Vapor Proof 2x24W",
        "wattage_w": 48,
        "ip_rating": "IP65"
      }
    ]
  }
}"""

# Schema for plugs/power layout extraction - rooms with sockets and switches
PLUGS_LAYOUT_SCHEMA = """{
  "building_block": "NewMark Office Building",
  "rooms": [
    {
      "name": "Suite 1 - Open Plan",
      "room_number": 1,
      "confidence": "extracted",
      "fixtures": {
        "double_socket_300": 12,
        "double_socket_300_confidence": "extracted",
        "double_socket_1100": 4,
        "double_socket_1100_confidence": "extracted",
        "data_points_cat6": 16,
        "data_points_cat6_confidence": "extracted",
        "floor_box": 2,
        "floor_box_confidence": "extracted",
        "switch_1lever_1way": 4,
        "switch_1lever_1way_confidence": "inferred"
      },
      "circuit_refs": ["DB-S1 P1", "DB-S1 P2", "DB-S1 P3"]
    },
    {
      "name": "Server Room",
      "room_number": 5,
      "confidence": "extracted",
      "fixtures": {
        "double_socket_300": 8,
        "double_socket_300_confidence": "extracted",
        "isolator_30a": 2,
        "isolator_30a_confidence": "extracted"
      },
      "has_ac": true,
      "circuit_refs": ["DB-S1 P4", "DB-S1 AC1"]
    }
  ],
  "legend": {
    "block_name": "NewMark Office Building",
    "sockets": [
      {
        "symbol_id": "PS-DS300",
        "category": "socket",
        "description": "16A Double Switched Socket @300mm",
        "short_name": "Double Socket @300",
        "mounting_height_mm": 300
      }
    ],
    "switches": [
      {
        "symbol_id": "SW-1L1W",
        "category": "switch",
        "description": "1-Lever 1-Way Switch @1200mm",
        "short_name": "1L 1W Switch",
        "mounting_height_mm": 1200
      }
    ]
  }
}"""

# Schema for outside lights / site infrastructure extraction
OUTSIDE_LIGHTS_SCHEMA = """{
  "site_cable_runs": [
    {
      "from_point": "Kiosk (Eskom Metering)",
      "to_point": "DB-CR (Control Room)",
      "cable_spec": "95mm² 4C Copper PVC SWA PVC",
      "cable_size_mm2": 95,
      "cable_cores": 4,
      "cable_type": "PVC SWA PVC",
      "length_m": 85,
      "confidence": "extracted",
      "is_underground": true,
      "needs_trenching": true,
      "notes": "Length marked on drawing: 85m"
    },
    {
      "from_point": "DB-CR",
      "to_point": "DB-PFA",
      "cable_spec": "16mm² 4C PVC SWA PVC",
      "cable_size_mm2": 16,
      "cable_cores": 4,
      "cable_type": "PVC SWA PVC",
      "length_m": 45,
      "confidence": "extracted",
      "is_underground": true,
      "needs_trenching": true
    },
    {
      "from_point": "DB-CR",
      "to_point": "DB-GH1",
      "cable_spec": "6mm² 4C PVC SWA PVC",
      "cable_size_mm2": 6,
      "cable_cores": 4,
      "cable_type": "PVC SWA PVC",
      "length_m": 120,
      "confidence": "estimated",
      "is_underground": true,
      "needs_trenching": true,
      "notes": "Length estimated from scale - not marked on drawing"
    }
  ],
  "outside_lights": {
    "pole_light_60w": 24,
    "pole_light_60w_confidence": "extracted",
    "flood_light_200w": 4,
    "flood_light_200w_confidence": "extracted",
    "bulkhead_26w": 8,
    "bulkhead_26w_confidence": "extracted"
  },
  "underground_sleeves": [
    {
      "size_mm": 50,
      "qty": 4,
      "purpose": "Future solar cable provision"
    }
  ]
}"""

# Schema for project classification (used by Haiku)
CLASSIFY_SCHEMA = """{
  "tier": "COMMERCIAL",
  "mode": "AS_BUILT",
  "building_blocks": [
    "NewMark Office Building",
    "Ablution Retail Block",
    "Existing Community Hall",
    "Large Guard House",
    "Small Guard House",
    "Pool Block"
  ],
  "reasoning": "Multiple commercial buildings with full SLD drawings and layout pages",
  "confidence": 0.92
}"""

# Schema for residential estimation (when no SLDs available)
RESIDENTIAL_SCHEMA = """{
  "property_type": "house",
  "size_m2": 180,
  "floors": 2,
  "rooms": [
    {"name": "Master Bedroom", "type": "bedroom", "area_m2": 25, "confidence": "extracted"},
    {"name": "Bedroom 2", "type": "bedroom", "area_m2": 16, "confidence": "extracted"},
    {"name": "Bedroom 3", "type": "bedroom", "area_m2": 14, "confidence": "extracted"},
    {"name": "Main Bathroom", "type": "bathroom", "area_m2": 8, "confidence": "inferred"},
    {"name": "Kitchen", "type": "kitchen", "area_m2": 20, "confidence": "extracted"},
    {"name": "Living Room", "type": "living", "area_m2": 35, "confidence": "extracted"},
    {"name": "Garage", "type": "garage", "area_m2": 36, "confidence": "extracted"}
  ],
  "special_circuits": {
    "stove_3phase": true,
    "geyser_count": 2,
    "ac_count": 3,
    "pool_pump": true,
    "gate_motor": true
  },
  "estimated_db_ways": 24,
  "estimated_supply_a": 80,
  "confidence": "MEDIUM"
}"""

# Schema for maintenance/COC inspection extraction
MAINTENANCE_SCHEMA = """{
  "property_type": "residential_house",
  "installation_age_years": 25,
  "reason_for_coc": "property_sale",
  "defects": [
    {
      "code": "no_elcb",
      "description": "No earth leakage protection device installed",
      "severity": "critical",
      "location": "Main DB",
      "qty": 1,
      "estimated_fix": "Install 63A 30mA ELCB"
    },
    {
      "code": "overloaded_circuit",
      "description": "Kitchen circuit exceeds 10 points",
      "severity": "high",
      "location": "Kitchen area",
      "qty": 1,
      "estimated_fix": "Split into 2 circuits"
    },
    {
      "code": "outdated_db",
      "description": "Old bakelite DB board with rewireable fuses",
      "severity": "medium",
      "location": "Garage",
      "qty": 1,
      "estimated_fix": "Replace with 24-way DIN rail DB"
    }
  ],
  "existing_db": {
    "type": "bakelite_rewireable",
    "ways": 12,
    "main_breaker_a": 60,
    "earth_leakage": false
  }
}"""

# Schema for heavy equipment extraction from SLDs
HEAVY_EQUIPMENT_SCHEMA = """{
  "equipment": [
    {
      "type": "pool_pump",
      "name": "Main Pool Circulation Pump 1",
      "rating_kw": 2.2,
      "confidence": "extracted",
      "has_vsd": true,
      "circuit_ref": "DB-PFA PUMP1",
      "building_block": "Pool Block",
      "qty": 1
    },
    {
      "type": "heat_pump",
      "name": "Pool Heat Pump",
      "rating_kw": 12.5,
      "confidence": "extracted",
      "has_vsd": false,
      "circuit_ref": "DB-PFA HP1",
      "building_block": "Pool Block",
      "qty": 1
    }
  ]
}"""

# Schema for validation result
VALIDATION_SCHEMA = """{
  "compliance_score": 0.85,
  "flags": [
    {
      "rule_name": "ELCB_REQUIRED",
      "severity": "critical",
      "related_board": "DB-Kitchen",
      "message": "No earth leakage protection detected",
      "auto_corrected": true,
      "corrected_value": "Add 63A 30mA ELCB",
      "standard_ref": "SANS 10142-1"
    }
  ],
  "warnings": [
    "Cable size on DB-Kitchen P2 may need verification"
  ]
}"""


def get_schema_for_page_type(page_type: str) -> str:
    """Get the appropriate schema based on page type."""
    schemas = {
        "REGISTER": REGISTER_SCHEMA,
        "SLD": SLD_SCHEMA,
        "LAYOUT_LIGHTING": LIGHTING_LAYOUT_SCHEMA,
        "LAYOUT_PLUGS": PLUGS_LAYOUT_SCHEMA,
        "OUTSIDE_LIGHTS": OUTSIDE_LIGHTS_SCHEMA,
        "RESIDENTIAL": RESIDENTIAL_SCHEMA,
        "MAINTENANCE": MAINTENANCE_SCHEMA,
    }
    return schemas.get(page_type, SLD_SCHEMA)


# All schemas exported for reference
ALL_SCHEMAS = {
    "register": REGISTER_SCHEMA,
    "sld": SLD_SCHEMA,
    "lighting": LIGHTING_LAYOUT_SCHEMA,
    "plugs": PLUGS_LAYOUT_SCHEMA,
    "outside_lights": OUTSIDE_LIGHTS_SCHEMA,
    "residential": RESIDENTIAL_SCHEMA,
    "maintenance": MAINTENANCE_SCHEMA,
    "classify": CLASSIFY_SCHEMA,
    "heavy_equipment": HEAVY_EQUIPMENT_SCHEMA,
    "validation": VALIDATION_SCHEMA,
}
