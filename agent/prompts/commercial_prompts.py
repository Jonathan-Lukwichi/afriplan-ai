"""
AfriPlan AI - Commercial Discovery Prompt

Specialized prompt for extracting electrical data from commercial building plans,
office layouts, retail spaces, and business premises.
"""

from agent.prompts.system_prompt import SA_ELECTRICAL_SYSTEM_PROMPT

DISCOVERY_COMMERCIAL = SA_ELECTRICAL_SYSTEM_PROMPT + """

## TASK: COMMERCIAL ELECTRICAL EXTRACTION

Analyse this commercial building plan for a complete electrical quotation.

## EXTRACTION ORDER

### 1. PROJECT METADATA
Extract overall project information:
- building_type: office / retail / restaurant / warehouse / workshop / medical / education / hospitality / mixed_use
- gfa_m2: Total gross floor area in m²
- floors: Number of floors
- supply_phases: 3 (three-phase default for commercial)
- main_breaker_a: Main breaker rating (100A/160A/200A/250A/400A)
- installation_type: new / fitout / renovation
- confidence: HIGH/MEDIUM/LOW

### 2. AREA-BY-AREA INVENTORY
For EACH identifiable zone/area, extract:
- area_name: Descriptive name
- area_type: One of below categories
- area_m2: Floor area
- Apply power density standard (W/m²):

| Area Type | Lighting W/m² | Power W/m² | HVAC W/m² | Total W/m² |
|-----------|--------------|------------|-----------|------------|
| Open plan office | 11 | 20 | 80 | 111 |
| Private office | 11 | 18 | 70 | 99 |
| Boardroom | 12 | 17 | 80 | 109 |
| Reception | 15 | 10 | 60 | 85 |
| Server/comms room | 9 | 1000 | 500 | 1509 |
| Kitchen/canteen | 13 | 83 | 80 | 176 |
| Retail | 20 | 30 | 60 | 110 |
| Restaurant | 15 | 72 | 60 | 147 |
| Warehouse | 8 | 8 | 15 | 31 |
| Workshop | 12 | 46 | 50 | 108 |
| Corridor/circulation | 8 | 6 | 20 | 34 |
| Parking | 5 | 6 | 5 | 16 |
| Toilet block | 10 | 10 | 30 | 50 |
| Plant room | 5 | 20 | 0 | 25 |
| Storage | 8 | 5 | 10 | 23 |

For each area also extract:
- lights:
  - type: LED_panel_600x600 / downlight / high_bay / linear / track
  - count: Number of fittings
  - wattage: Watts per fitting
  - confidence: HIGH/MEDIUM/LOW
- sockets:
  - standard_doubles: Count
  - floor_boxes: Count
  - dedicated: Count (for equipment)
  - confidence: HIGH/MEDIUM/LOW
- data_points:
  - count: Cat6/Cat6A points
  - confidence: HIGH/MEDIUM/LOW
- hvac:
  - type: split / cassette / ducted / VRF
  - kw_rating: Total kW for area
  - phase: single / three
  - confidence: HIGH/MEDIUM/LOW

### 3. THREE-PHASE DISTRIBUTION
- msb: Main Switchboard
  - location: Where on plan
  - rating_a: Main breaker rating
- sub_boards: List of sub-distribution boards
  - name: Board designation (e.g., "DB-GF-01")
  - location: Where on plan
  - ways: Number of ways
  - serves: What area it serves
- phase_balance:
  - L1_kw: Load on Phase 1
  - L2_kw: Load on Phase 2
  - L3_kw: Load on Phase 3
  - Note: Target no phase >40% of total
- nmd_kva: Notified Maximum Demand calculation

### 4. EMERGENCY & LIFE SAFETY
- emergency_lights:
  - count: Total (1 per 15m² in passages, every exit, stairwells)
  - type: maintained / non_maintained / self_test
- exit_signs:
  - count: Illuminated exit signs
  - type: LED / maintained
- fire_alarm:
  - panel_type: conventional / addressable
  - zones: Number of zones
  - detectors: Total smoke/heat detectors (1 per 30m² office, 1 per 15m² retail)
  - mcps: Manual call points (every exit door)
  - sounders: Alarm sounders/bells
- generator_provision: true/false
- ups_provision: true/false
- confidence: HIGH/MEDIUM/LOW

### 5. COMPLIANCE FLAGS
List any compliance requirements detected:
- SANS_10400_T: Fire requirements if occupancy >100 persons
- SANS_10400_XA: Energy efficiency requirements
- OHS_signage: Required labelling and safety signage
- as_built: As-built drawings requirement
- phase_balance: Three-phase balance verification
- emergency_duration: 3-hour emergency lighting requirement

## JSON RESPONSE SCHEMA

Respond with ONLY this JSON structure (no markdown, no explanation):

{
  "project": {
    "building_type": "",
    "gfa_m2": 0,
    "floors": 0,
    "supply_phases": 3,
    "main_breaker_a": 0,
    "installation_type": "new",
    "confidence": "HIGH|MEDIUM|LOW"
  },
  "areas": [
    {
      "name": "",
      "type": "",
      "area_m2": 0,
      "power_density_wm2": 0,
      "total_load_kw": 0,
      "lights": {
        "type": "",
        "count": 0,
        "wattage": 0,
        "confidence": "HIGH|MEDIUM|LOW"
      },
      "sockets": {
        "doubles": 0,
        "floor_boxes": 0,
        "dedicated": 0,
        "confidence": "HIGH|MEDIUM|LOW"
      },
      "data_points": {
        "count": 0,
        "confidence": "HIGH|MEDIUM|LOW"
      },
      "hvac": {
        "type": "",
        "kw": 0,
        "phase": "",
        "confidence": "HIGH|MEDIUM|LOW"
      },
      "confidence": "HIGH|MEDIUM|LOW"
    }
  ],
  "distribution": {
    "msb": {
      "location": "",
      "rating_a": 0
    },
    "sub_boards": [
      {
        "name": "",
        "location": "",
        "ways": 0,
        "serves": ""
      }
    ],
    "phase_balance": {
      "L1_kw": 0,
      "L2_kw": 0,
      "L3_kw": 0,
      "balanced": true
    },
    "nmd_kva": 0,
    "confidence": "HIGH|MEDIUM|LOW"
  },
  "emergency": {
    "emergency_lights": 0,
    "emergency_light_type": "non_maintained",
    "exit_signs": 0,
    "fire_alarm": {
      "panel_type": "addressable",
      "zones": 0,
      "detectors": 0,
      "mcps": 0,
      "sounders": 0
    },
    "generator_provision": false,
    "ups_provision": false,
    "confidence": "HIGH|MEDIUM|LOW"
  },
  "compliance_flags": [],
  "gfa_m2": 0,
  "building_type": "",
  "total_load_kva": 0,
  "emergency_power": false,
  "fire_alarm": true,
  "notes": [],
  "warnings": []
}
"""
