"""
AfriPlan AI - Residential Discovery Prompt

Specialized prompt for extracting electrical data from residential building plans,
floor plans, and architectural drawings.
"""

from agent.prompts.system_prompt import SA_ELECTRICAL_SYSTEM_PROMPT

DISCOVERY_RESIDENTIAL = SA_ELECTRICAL_SYSTEM_PROMPT + """

## TASK: RESIDENTIAL ELECTRICAL EXTRACTION

Analyse this residential building plan for a complete electrical quotation.

## EXTRACTION ORDER

### 1. PROJECT METADATA
Extract overall project information:
- dwelling_type: freestanding / townhouse / duplex / simplex / cluster / flat / estate
- Estimated total floor area (m²) — calculate from plan dimensions if not stated
- Number of bedrooms, bathrooms, living areas
- Single or double storey
- Supply type: single-phase 60A (default unless specified or total area >250m²)

### 2. ROOM-BY-ROOM INVENTORY
For EACH room visible on the plan, extract:
- room_name: Specific name (e.g., "Main Bedroom", "Kitchen", "Bathroom 1")
- room_type: One of: bedroom / bathroom / kitchen / living / dining / study / garage / laundry / passage / entrance / outdoor / pool_area / guest_wc / scullery / pantry
- estimated_area_m2: Calculate from dimensions if shown
- lights:
  - count: Total light points (ceiling + wall)
  - types: downlight / batten / pendant / wall_mount / bulkhead / LED_strip
  - confidence: HIGH/MEDIUM/LOW
- sockets:
  - singles: Single socket outlets
  - doubles: Double socket outlets
  - usb: USB combo sockets
  - weatherproof: Outdoor/wet area sockets
  - confidence: HIGH/MEDIUM/LOW
- switches:
  - total: Total switch count
  - types: 1-lever / 2-lever / 3-lever / 2-way / dimmer
  - confidence: HIGH/MEDIUM/LOW
- dedicated_circuits: List any required (stove / oven / geyser / aircon / dishwasher / washing_machine / tumble_dryer / pool_pump / gate_motor / EV_charger)
- extras: extractor_fan / heated_towel_rail / underfloor_heating / data_point

### 3. DB BOARD & PROTECTION
Recommend based on extracted data:
- recommended_ways: Count circuits + 20% spare, round to standard size (8/12/16/20/24)
- main_switch_a: 40A/60A/80A based on calculated load
- elcb: true (MANDATORY 63A 30mA)
- surge_protection: true (RECOMMENDED Type 2)
- circuit_schedule: List each circuit with:
  - circuit_name
  - circuit_type (lighting/power/dedicated)
  - mcb_rating (6A/10A/16A/20A/25A/32A)
  - cable_size (1.5mm²/2.5mm²/4mm²/6mm²)

### 4. GEYSER & HOT WATER
- geyser_location: Where visible on plan
- geyser_size_litres: 100L/150L/200L based on house size and bathrooms
- geyser_type: electric / solar / heat_pump / gas
- circuit_required: true (20A dedicated with timer and isolator)

### 5. OUTDOOR & SECURITY
- light_points: Front, rear, driveway lights
- weatherproof_sockets: Outdoor socket count
- gate_motor: true/false
- electric_fence: true/false
- intercom: true/false
- alarm_power: true/false
- pool_equipment: true/false (pump, light, chlorinator)

### 6. CABLE ROUTING ESTIMATE
- avg_run_m: Estimated average cable run from DB to each room
- flag_long_runs: List runs >30m that may need upsized cable for voltage drop

## DEFAULT VALUES (when not visible)

If elements are not clearly visible on the plan, use these SANS 10142-1 minimums:

| Room Type | Lights | Doubles | Singles | Switches |
|-----------|--------|---------|---------|----------|
| Bedroom | 2 | 2 | 0 | 2 |
| Bathroom | 2 | 1 | 0 | 1 |
| Kitchen | 3 | 4 | 0 | 2 |
| Living | 3 | 4 | 0 | 2 |
| Dining | 2 | 2 | 0 | 1 |
| Study | 2 | 3 | 0 | 1 |
| Garage | 2 | 2 | 0 | 1 |
| Laundry | 1 | 2 | 0 | 1 |
| Passage | 1 | 0 | 0 | 2 |
| Entrance | 1 | 1 | 0 | 1 |
| Outdoor | 2 | 1 | 0 | 1 |

Mark these as confidence: LOW

## JSON RESPONSE SCHEMA

Respond with ONLY this JSON structure (no markdown, no explanation):

{
  "project": {
    "dwelling_type": "",
    "floor_area_m2": 0,
    "bedrooms": 0,
    "bathrooms": 0,
    "floors": 1,
    "supply_type": "single_phase",
    "supply_amps": 60,
    "confidence": "HIGH|MEDIUM|LOW"
  },
  "rooms": [
    {
      "room_name": "",
      "room_type": "",
      "area_m2": 0,
      "lights": {
        "count": 0,
        "types": [],
        "confidence": "HIGH|MEDIUM|LOW"
      },
      "sockets": {
        "singles": 0,
        "doubles": 0,
        "usb": 0,
        "weatherproof": 0,
        "confidence": "HIGH|MEDIUM|LOW"
      },
      "switches": {
        "total": 0,
        "types": [],
        "confidence": "HIGH|MEDIUM|LOW"
      },
      "dedicated_circuits": [],
      "extras": [],
      "confidence": "HIGH|MEDIUM|LOW"
    }
  ],
  "db_board": {
    "recommended_ways": 0,
    "main_switch_a": 60,
    "elcb": true,
    "surge_protection": true,
    "circuits": [
      {
        "name": "",
        "type": "",
        "mcb_a": 0,
        "cable_mm2": 0
      }
    ],
    "confidence": "HIGH|MEDIUM|LOW"
  },
  "geyser": {
    "location": "",
    "size_litres": 150,
    "type": "electric",
    "circuit_required": true,
    "confidence": "HIGH|MEDIUM|LOW"
  },
  "outdoor": {
    "light_points": 0,
    "weatherproof_sockets": 0,
    "gate_motor": false,
    "electric_fence": false,
    "intercom": false,
    "alarm": false,
    "pool": false,
    "confidence": "HIGH|MEDIUM|LOW"
  },
  "cable_estimate": {
    "avg_run_m": 0,
    "long_runs_flagged": []
  },
  "dedicated_circuits": [],
  "total_light_points": 0,
  "total_socket_outlets": 0,
  "total_dedicated_circuits": 0,
  "notes": [],
  "warnings": []
}
"""
