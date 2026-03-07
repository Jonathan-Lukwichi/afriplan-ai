# Ground Truth Schema Documentation

## Overview

This document describes the JSON schema used for ground truth files in the evaluation system.
Each test document needs a `ground_truth.json` file with the correct extraction values.

---

## Schema Structure

```
ground_truth.json
├── document_id          # Unique identifier
├── document_type        # "sld", "layout", "combined"
├── project_info         # Project metadata
├── distribution_boards  # List of DBs with circuits
├── fixtures             # Fixture counts (for layouts)
├── cables               # Cable information
└── totals               # Summary totals
```

---

## Complete Schema

```json
{
  "document_id": "doc_001_wedela",
  "document_type": "sld",
  "page_count": 8,

  "project_info": {
    "project_name": "Wedela Recreational Club",
    "client_name": "Client Name",
    "consultant": "KABE Consulting",
    "drawing_number": "WD-KIOSK-01-SLD",
    "revision": "RA",
    "date": "2025-05-26",
    "standard": "SANS 10142-1"
  },

  "distribution_boards": [
    {
      "name": "DB-KIOSK",
      "location": "Kiosk",
      "voltage": "400V",
      "phase": "3PH+N+E",
      "main_breaker_a": 63,
      "total_ways": 24,
      "spare_ways": 4,
      "has_elcb": true,
      "elcb_rating_a": 63,
      "elcb_sensitivity_ma": 30,
      "has_surge_protection": true,

      "circuits": [
        {
          "name": "L1",
          "type": "lighting",
          "mcb_rating_a": 10,
          "cable_size_mm2": 1.5,
          "cable_type": "SURFIX",
          "num_points": 8,
          "description": "Lights - Reception",
          "phase": "R"
        },
        {
          "name": "P1",
          "type": "power",
          "mcb_rating_a": 16,
          "cable_size_mm2": 2.5,
          "cable_type": "SURFIX",
          "num_points": 6,
          "description": "Plugs - Reception",
          "phase": "R"
        },
        {
          "name": "STOVE",
          "type": "dedicated",
          "mcb_rating_a": 32,
          "cable_size_mm2": 6.0,
          "cable_type": "SURFIX",
          "num_points": 1,
          "description": "Stove Circuit",
          "phase": "3PH"
        }
      ]
    }
  ],

  "fixtures": {
    "by_room": [
      {
        "room_name": "Reception",
        "room_type": "office",
        "area_m2": 45.0,
        "lights": {
          "downlight_led": 6,
          "fluorescent_600x1200": 0,
          "bulkhead": 0,
          "total": 6
        },
        "sockets": {
          "single": 2,
          "double": 4,
          "total_points": 10
        },
        "switches": {
          "1_lever": 2,
          "2_lever": 1,
          "total": 3
        }
      }
    ],
    "totals": {
      "total_lights": 24,
      "total_socket_points": 32,
      "total_switches": 14
    }
  },

  "cables": {
    "main_feeds": [
      {
        "from": "MINI SUB",
        "to": "DB-KIOSK",
        "cable_size_mm2": 95,
        "cable_type": "4C+E COPPER PVC SWA",
        "length_m": 50,
        "installation": "underground"
      }
    ],
    "sub_feeds": [
      {
        "from": "DB-KIOSK",
        "to": "DB-CR",
        "cable_size_mm2": 35,
        "cable_type": "4C+E COPPER PVC SWA",
        "length_m": 25,
        "installation": "underground"
      }
    ]
  },

  "totals": {
    "total_dbs": 3,
    "total_circuits": 36,
    "total_lighting_circuits": 12,
    "total_power_circuits": 18,
    "total_dedicated_circuits": 6,
    "total_spare_circuits": 8
  }
}
```

---

## Field Definitions

### document_type
- `"sld"` - Single Line Diagram (circuit schedules)
- `"layout"` - Floor plan with fixtures
- `"combined"` - Has both SLD and layout pages

### circuit.type
- `"lighting"` - Lighting circuit (typically 10A, 1.5mm²)
- `"power"` - Socket/plug circuit (typically 16A, 2.5mm²)
- `"dedicated"` - Dedicated circuit (stove, geyser, aircon, etc.)
- `"spare"` - Unused/spare way
- `"sub_feed"` - Feed to sub-distribution board

### circuit.phase
- `"R"` - Red phase
- `"W"` - White phase
- `"B"` - Blue phase
- `"3PH"` - Three-phase
- `"N/A"` - Not specified

### installation method
- `"underground"` - Underground in trench
- `"surface"` - Surface mounted conduit
- `"concealed"` - Concealed in walls/ceiling
- `"trunking"` - Cable trunking/tray

---

## Scoring Priority

Fields are scored with different weights based on importance:

| Field | Priority | Weight | Why Important |
|-------|----------|--------|---------------|
| circuit_count | Critical | 1.0 | Affects entire BQ |
| mcb_rating_a | Critical | 1.0 | Safety + pricing |
| cable_size_mm2 | Critical | 1.0 | Major cost item |
| num_points | High | 0.8 | Fixture pricing |
| total_lights | High | 0.8 | Direct pricing |
| total_sockets | High | 0.8 | Direct pricing |
| db_name | Medium | 0.5 | Reference |
| description | Low | 0.3 | Documentation |
| project_name | Low | 0.2 | Metadata only |

---

## Creating Ground Truth

### Step 1: Open the PDF
View each page carefully in a PDF reader.

### Step 2: Count Distribution Boards
List all DB names visible on the drawing.

### Step 3: Extract Circuit Details
For each DB, read the circuit schedule table:
- Circuit name (L1, L2, P1, etc.)
- MCB rating (10A, 16A, 20A, 32A)
- Cable size (1.5mm², 2.5mm², 4mm², 6mm²)
- Number of points (if shown)
- Description

### Step 4: Count Fixtures (for layouts)
Count each symbol type:
- Lights (downlights, fluorescents, etc.)
- Sockets (single, double)
- Switches

### Step 5: Note Cables
Record main and sub-feed cables with sizes.

### Step 6: Calculate Totals
Sum up all circuits, fixtures, etc.

---

## Example: Minimal Ground Truth

For quick testing, you can start with just the critical fields:

```json
{
  "document_id": "doc_001_wedela",
  "document_type": "sld",

  "distribution_boards": [
    {
      "name": "DB-KIOSK",
      "main_breaker_a": 63,
      "circuit_count": 24,
      "circuits": [
        {"name": "L1", "type": "lighting", "mcb_rating_a": 10, "cable_size_mm2": 1.5},
        {"name": "P1", "type": "power", "mcb_rating_a": 16, "cable_size_mm2": 2.5}
      ]
    }
  ],

  "totals": {
    "total_dbs": 1,
    "total_circuits": 24
  }
}
```

---

## Tips

1. **Be consistent** - Use the same naming conventions across all documents
2. **Use lowercase** - For circuit types ("lighting" not "Lighting")
3. **Round numbers** - Cable sizes to standard values (1.5, 2.5, 4, 6, 10, 16, 25, 35, 50, 70, 95)
4. **Count carefully** - Double-check fixture counts
5. **Mark unknowns** - Use `null` for values not visible on drawing
