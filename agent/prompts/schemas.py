"""
AfriPlan Electrical v4.4 — JSON Schemas for AI Extraction

Contains example JSON structures that guide Claude's structured output.

v4.1 addition: Every extracted value includes a confidence field:
- "extracted": read directly from the drawing
- "inferred": calculated from other values
- "estimated": using a default or guessing

v4.3 additions:
- VSD rating (kW) and starter type for pump/motor circuits
- Day/night switch detection with bypass
- ISO (isolator) circuit type support
- Circuit reference linking to heavy_equipment

v4.4 additions (Layout Drawing Enhancements - Wedela Lighting & Plugs PDF):
- Pool lighting types: pool_flood_light (FL), pool_underwater_light (PS)
- legend_totals section for validation cross-checking
- Room circuit_refs for DB-Room linking
- Waterproof sockets, ceiling sockets, master switch support
"""

# Confidence instruction to add to all prompts
CONFIDENCE_INSTRUCTION = '''
## CONFIDENCE MARKING RULES (CRITICAL FOR ACCURACY)

Mark confidence for each value you extract:

### "extracted" - Use this when:
- You can READ the exact value from a schedule table (e.g., "384W" in circuit schedule)
- You can COUNT items clearly visible (e.g., 8 light symbols counted)
- You can SEE the specification text (e.g., "16mm² 4C PVC SWA PVC")
- The legend identifies the item type clearly

### "inferred" - Use this when:
- You CALCULATED from other values (e.g., 8 lights x 48W = 384W)
- You MATCHED symbols to legend and counted
- You DETERMINED size from breaker/load relationship
- The value follows logically from what you extracted

### "estimated" - ONLY use when:
- The value is NOT VISIBLE and cannot be calculated
- You are GUESSING based on typical installations
- The drawing is unclear/illegible for that specific item
- Cable LENGTH is not marked and you cannot scale it

## IMPORTANT:
- Counting visible symbols = "extracted" (NOT estimated!)
- Reading from schedule table = "extracted"
- Matching symbol to legend = "extracted"
- Calculating wattage from count x watts = "inferred"

AVOID marking as "estimated" when you can actually see and count items.
The goal is accuracy - if you can see it, mark it "extracted".
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

# Schema for title block extraction (from every drawing)
TITLE_BLOCK_SCHEMA = """{
  "drawing_number": "TJM-SLD-001",
  "drawing_number_confidence": "extracted",
  "revision": "RA",
  "revision_confidence": "extracted",
  "description": "PROPOSED NEW OFFICES ON ERF1/1, NEWMARK",
  "description_confidence": "extracted",
  "part": "MAIN SLD DB MAIN + COMMON AREA",
  "consultant": "CHONA-MALANGA ENGINEERING",
  "consultant_confidence": "extracted",
  "client": "TJM GREENTECH",
  "client_confidence": "extracted",
  "drawn_by": "JM",
  "checked_by": "CM",
  "date": "2024-03-15",
  "standard": "SANS 10142-1",
  "sap_project_no": "",
  "network_id_no": ""
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
          "type": "pool_pump",
          "description": "Pool Pump 1 (2.2kW)",
          "wattage_w": 2200,
          "confidence": "extracted",
          "cable_size_mm2": 4,
          "cable_cores": 4,
          "cable_type": "PVC SWA PVC",
          "breaker_a": 32,
          "breaker_poles": 3,
          "has_vsd": true,
          "vsd_rating_kw": 2.2,
          "starter_type": "vsd",
          "has_isolator": true,
          "isolator_rating_a": 30
        },
        {
          "id": "ISO1",
          "type": "isolator",
          "description": "Geyser Isolator (2kW)",
          "wattage_w": 2000,
          "confidence": "extracted",
          "cable_size_mm2": 2.5,
          "cable_cores": 3,
          "cable_type": "GP WIRE",
          "breaker_a": 20,
          "breaker_poles": 2,
          "has_isolator": true,
          "isolator_rating_a": 20,
          "equipment_type": "geyser"
        },
        {
          "id": "L1",
          "type": "lighting",
          "description": "External Lights - Day/Night",
          "wattage_w": 480,
          "wattage_formula": "8x60W",
          "confidence": "extracted",
          "cable_size_mm2": 1.5,
          "cable_cores": 3,
          "cable_type": "GP WIRE",
          "breaker_a": 10,
          "breaker_poles": 1,
          "num_points": 8,
          "has_day_night": true,
          "has_bypass": true,
          "controlled_circuits": ["L1", "L2"]
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
      "vsd_rating_kw": 2.2,
      "starter_type": "vsd",
      "isolator_a": 30,
      "fed_from_db": "DB-PFA",
      "circuit_ref": "PP1",
      "qty": 1
    },
    {
      "name": "Heat Pump 1",
      "type": "heat_pump",
      "rating_kw": 7.5,
      "confidence": "extracted",
      "cable_size_mm2": 6,
      "cable_type": "PVC SWA PVC",
      "breaker_a": 40,
      "has_vsd": true,
      "vsd_rating_kw": 7.5,
      "starter_type": "vsd",
      "isolator_a": 40,
      "fed_from_db": "DB-HPS1",
      "circuit_ref": "HP1",
      "qty": 1
    },
    {
      "name": "HVAC System",
      "type": "hvac",
      "rating_kw": 60,
      "confidence": "extracted",
      "cable_size_mm2": 25,
      "cable_type": "PVC SWA PVC",
      "breaker_a": 100,
      "has_vsd": false,
      "starter_type": "star_delta",
      "isolator_a": 125,
      "fed_from_db": "DB-1",
      "circuit_ref": "HVAC",
      "qty": 1
    }
  ]
}"""

# Schema for lighting layout extraction - rooms with light fixtures
LIGHTING_LAYOUT_SCHEMA = """{
  "building_block": "Pool Block",
  "rooms": [
    {
      "name": "Pool Area",
      "room_number": 1,
      "type": "pool_area",
      "confidence": "extracted",
      "area_m2": 250,
      "floor": "Ground",
      "fixtures": {
        "recessed_led_600x1200": 0,
        "surface_mount_led_18w": 8,
        "surface_mount_led_18w_confidence": "extracted",
        "flood_light_200w": 4,
        "flood_light_200w_confidence": "extracted",
        "pool_flood_light": 6,
        "pool_flood_light_confidence": "extracted",
        "pool_underwater_light": 4,
        "pool_underwater_light_confidence": "extracted"
      },
      "circuit_refs": ["DB-PFA L1", "DB-PFA L2"]
    },
    {
      "name": "Male Changing",
      "room_number": 2,
      "type": "ablution",
      "confidence": "extracted",
      "area_m2": 35,
      "floor": "Ground",
      "is_wet_area": true,
      "fixtures": {
        "vapor_proof_2x24w": 4,
        "vapor_proof_2x24w_confidence": "extracted",
        "bulkhead_24w": 2,
        "bulkhead_24w_confidence": "extracted"
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
    "block_name": "Pool Block",
    "lights": [
      {
        "symbol_id": "FL",
        "category": "light",
        "description": "Pool Flood Light 150W",
        "short_name": "Pool Flood",
        "wattage_w": 150,
        "ip_rating": "IP65"
      },
      {
        "symbol_id": "PS",
        "category": "light",
        "description": "Pool Underwater Light 35W",
        "short_name": "Pool Underwater",
        "wattage_w": 35,
        "ip_rating": "IP68"
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
  },
  "legend_totals": {
    "pool_flood_light": 6,
    "pool_underwater_light": 4,
    "vapor_proof_2x24w": 4,
    "bulkhead_24w": 2,
    "surface_mount_led_18w": 8,
    "flood_light_200w": 4
  }
}"""

# Schema for plugs/power layout extraction - rooms with sockets and switches
PLUGS_LAYOUT_SCHEMA = """{
  "building_block": "Ablution Retail Block",
  "rooms": [
    {
      "name": "Male Changing Room",
      "room_number": 1,
      "confidence": "extracted",
      "is_wet_area": true,
      "fixtures": {
        "double_socket_300": 2,
        "double_socket_300_confidence": "extracted",
        "double_socket_waterproof": 4,
        "double_socket_waterproof_confidence": "extracted",
        "switch_1lever_1way": 2,
        "switch_1lever_1way_confidence": "extracted",
        "master_switch": 1,
        "master_switch_confidence": "extracted"
      },
      "circuit_refs": ["DB-AB1 P1", "DB-AB1 P2"]
    },
    {
      "name": "Kitchen",
      "room_number": 2,
      "confidence": "extracted",
      "fixtures": {
        "double_socket_300": 6,
        "double_socket_300_confidence": "extracted",
        "double_socket_1100": 4,
        "double_socket_1100_confidence": "extracted",
        "double_socket_ceiling": 2,
        "double_socket_ceiling_confidence": "extracted",
        "switch_2lever_1way": 2,
        "switch_2lever_1way_confidence": "extracted"
      },
      "circuit_refs": ["DB-AB1 P3", "DB-AB1 P4"]
    },
    {
      "name": "Server Room",
      "room_number": 3,
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
    "block_name": "Ablution Retail Block",
    "sockets": [
      {
        "symbol_id": "PS-DS300",
        "category": "socket",
        "description": "16A Double Switched Socket @300mm",
        "short_name": "Double Socket @300",
        "mounting_height_mm": 300
      },
      {
        "symbol_id": "PS-WP",
        "category": "socket",
        "description": "16A Double Switched Socket Waterproof @300mm",
        "short_name": "Waterproof Socket",
        "mounting_height_mm": 300,
        "ip_rating": "IP65"
      },
      {
        "symbol_id": "PS-CEIL",
        "category": "socket",
        "description": "16A Double Switched Ceiling Socket",
        "short_name": "Ceiling Socket",
        "mounting_height_mm": 2400
      }
    ],
    "switches": [
      {
        "symbol_id": "SW-1L1W",
        "category": "switch",
        "description": "1-Lever 1-Way Switch @1200mm",
        "short_name": "1L 1W Switch",
        "mounting_height_mm": 1200
      },
      {
        "symbol_id": "MS",
        "category": "switch",
        "description": "Master Switch - Controls All Lights",
        "short_name": "Master Switch",
        "mounting_height_mm": 1200
      }
    ]
  },
  "legend_totals": {
    "double_socket_300": 16,
    "double_socket_1100": 4,
    "double_socket_waterproof": 4,
    "double_socket_ceiling": 2,
    "switch_1lever_1way": 2,
    "switch_2lever_1way": 2,
    "master_switch": 1,
    "isolator_30a": 2
  }
}"""

# Schema for combined layout extraction - pages with BOTH lights AND sockets/switches
# This handles South African drawings where lighting and power layouts are on the same page
COMBINED_LAYOUT_SCHEMA = """{
  "building_block": "Pool Block",
  "rooms": [
    {
      "name": "Pool Area",
      "room_number": 1,
      "type": "pool_area",
      "confidence": "extracted",
      "area_m2": 250,
      "floor": "Ground",
      "is_wet_area": true,
      "fixtures": {
        "recessed_led_600x1200": 0,
        "downlight_led_6w": 0,
        "vapor_proof_2x24w": 0,
        "surface_mount_led_18w": 8,
        "surface_mount_led_18w_confidence": "extracted",
        "bulkhead_24w": 0,
        "pool_flood_light": 6,
        "pool_flood_light_confidence": "extracted",
        "pool_underwater_light": 4,
        "pool_underwater_light_confidence": "extracted",
        "flood_light_200w": 4,
        "flood_light_200w_confidence": "extracted",
        "double_socket_300": 4,
        "double_socket_300_confidence": "extracted",
        "double_socket_1100": 0,
        "single_socket_300": 0,
        "double_socket_waterproof": 6,
        "double_socket_waterproof_confidence": "extracted",
        "double_socket_ceiling": 2,
        "double_socket_ceiling_confidence": "extracted",
        "data_points_cat6": 0,
        "floor_box": 0,
        "switch_1lever_1way": 2,
        "switch_1lever_1way_confidence": "extracted",
        "switch_2lever_1way": 0,
        "switch_1lever_2way": 0,
        "day_night_switch": 1,
        "day_night_switch_confidence": "extracted",
        "master_switch": 1,
        "master_switch_confidence": "extracted",
        "isolator_30a": 2,
        "isolator_30a_confidence": "extracted",
        "isolator_20a": 0
      },
      "circuit_refs": ["DB-PFA L1", "DB-PFA L2", "DB-PFA P1", "DB-PFA P2"]
    },
    {
      "name": "Male Changing",
      "room_number": 2,
      "type": "ablution",
      "confidence": "extracted",
      "area_m2": 35,
      "floor": "Ground",
      "is_wet_area": true,
      "fixtures": {
        "vapor_proof_2x24w": 4,
        "vapor_proof_2x24w_confidence": "extracted",
        "bulkhead_24w": 2,
        "bulkhead_24w_confidence": "extracted",
        "double_socket_waterproof": 2,
        "double_socket_waterproof_confidence": "extracted",
        "switch_1lever_1way": 1,
        "switch_1lever_1way_confidence": "extracted"
      },
      "circuit_refs": ["DB-AB1 L1", "DB-AB1 P1"]
    }
  ],
  "legend": {
    "block_name": "Pool Block",
    "lights": [
      {
        "symbol_id": "FL",
        "category": "light",
        "description": "Pool Flood Light 150W",
        "short_name": "Pool Flood",
        "wattage_w": 150,
        "ip_rating": "IP65"
      },
      {
        "symbol_id": "PS",
        "category": "light",
        "description": "Pool Underwater Light 35W",
        "short_name": "Pool Underwater",
        "wattage_w": 35,
        "ip_rating": "IP68"
      },
      {
        "symbol_id": "LT-VP24",
        "category": "light",
        "description": "2x24W Double Vapor Proof LED",
        "short_name": "Vapor Proof 2x24W",
        "wattage_w": 48,
        "ip_rating": "IP65"
      }
    ],
    "sockets": [
      {
        "symbol_id": "PS-DS300",
        "category": "socket",
        "description": "16A Double Switched Socket @300mm",
        "short_name": "Double Socket @300",
        "mounting_height_mm": 300
      },
      {
        "symbol_id": "PS-WP",
        "category": "socket",
        "description": "16A Double Switched Socket Waterproof @300mm",
        "short_name": "Waterproof Socket",
        "mounting_height_mm": 300,
        "ip_rating": "IP65"
      }
    ],
    "switches": [
      {
        "symbol_id": "SW-1L1W",
        "category": "switch",
        "description": "1-Lever 1-Way Switch @1200mm",
        "short_name": "1L 1W Switch",
        "mounting_height_mm": 1200
      },
      {
        "symbol_id": "MS",
        "category": "switch",
        "description": "Master Switch - Controls All Lights",
        "short_name": "Master Switch",
        "mounting_height_mm": 1200
      }
    ]
  },
  "legend_totals": {
    "surface_mount_led_18w": 8,
    "pool_flood_light": 6,
    "pool_underwater_light": 4,
    "flood_light_200w": 4,
    "vapor_proof_2x24w": 4,
    "bulkhead_24w": 2,
    "double_socket_300": 4,
    "double_socket_waterproof": 8,
    "double_socket_ceiling": 2,
    "switch_1lever_1way": 3,
    "day_night_switch": 1,
    "master_switch": 1,
    "isolator_30a": 2
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

# Schema for heavy equipment extraction from SLDs (v4.3 enhanced)
HEAVY_EQUIPMENT_SCHEMA = """{
  "equipment": [
    {
      "type": "pool_pump",
      "name": "Main Pool Circulation Pump 1",
      "rating_kw": 2.2,
      "confidence": "extracted",
      "has_vsd": true,
      "vsd_rating_kw": 2.2,
      "starter_type": "vsd",
      "isolator_a": 30,
      "circuit_ref": "PP1",
      "fed_from_db": "DB-PPS1",
      "building_block": "Pool Block",
      "cable_size_mm2": 4,
      "cable_type": "PVC SWA PVC",
      "qty": 1
    },
    {
      "type": "heat_pump",
      "name": "Pool Heat Pump 1",
      "rating_kw": 7.5,
      "confidence": "extracted",
      "has_vsd": true,
      "vsd_rating_kw": 7.5,
      "starter_type": "vsd",
      "isolator_a": 40,
      "circuit_ref": "HP1",
      "fed_from_db": "DB-HPS1",
      "building_block": "Pool Block",
      "cable_size_mm2": 6,
      "cable_type": "PVC SWA PVC",
      "qty": 1
    },
    {
      "type": "circulation_pump",
      "name": "Circulation Pump 1",
      "rating_kw": 1.5,
      "confidence": "extracted",
      "has_vsd": true,
      "vsd_rating_kw": 1.5,
      "starter_type": "vsd",
      "isolator_a": 20,
      "circuit_ref": "CP1",
      "fed_from_db": "DB-PFA",
      "building_block": "Pool Block",
      "cable_size_mm2": 2.5,
      "cable_type": "PVC SWA PVC",
      "qty": 1
    },
    {
      "type": "hvac",
      "name": "HVAC System",
      "rating_kw": 60,
      "confidence": "extracted",
      "has_vsd": false,
      "starter_type": "star_delta",
      "isolator_a": 125,
      "circuit_ref": "HVAC",
      "fed_from_db": "DB-1",
      "building_block": "Community Hall",
      "cable_size_mm2": 25,
      "cable_type": "PVC SWA PVC",
      "qty": 1
    },
    {
      "type": "borehole_pump",
      "name": "Borehole Pump",
      "rating_kw": 4.0,
      "confidence": "extracted",
      "has_vsd": false,
      "starter_type": "dol",
      "isolator_a": 32,
      "circuit_ref": "BH1",
      "fed_from_db": "DB-EXT",
      "building_block": "External",
      "cable_size_mm2": 4,
      "cable_type": "PVC SWA PVC",
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
        "LAYOUT_COMBINED": COMBINED_LAYOUT_SCHEMA,
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
    "combined_layout": COMBINED_LAYOUT_SCHEMA,
    "outside_lights": OUTSIDE_LIGHTS_SCHEMA,
    "residential": RESIDENTIAL_SCHEMA,
    "maintenance": MAINTENANCE_SCHEMA,
    "classify": CLASSIFY_SCHEMA,
    "heavy_equipment": HEAVY_EQUIPMENT_SCHEMA,
    "validation": VALIDATION_SCHEMA,
}
