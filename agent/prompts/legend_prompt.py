"""
AfriPlan Electrical v4.2 - Legend Extraction Prompt

Extracts the LEGEND/KEY from electrical drawings BEFORE counting symbols.
This ensures accurate fixture identification by understanding the specific
symbols used on each drawing.

Purpose:
- Pre-pass extraction of legend information
- Symbol → fixture type mapping
- Wattage and specification capture
- Used to improve accuracy of subsequent fixture counting
"""

from typing import List, TYPE_CHECKING
if TYPE_CHECKING:
    from agent.models import PageInfo


# Legend extraction JSON schema
LEGEND_SCHEMA = """{
  "building_block": "NewMark Office Building",
  "has_legend": true,
  "legend_location": "bottom_right",
  "lights": [
    {
      "symbol_id": "LT-01",
      "symbol_description": "Circle with radiating lines",
      "name": "600x1200 Recessed LED Panel",
      "wattage_w": 54,
      "wattage_formula": "3x18W",
      "ip_rating": "IP20",
      "mounting": "recessed",
      "notes": ""
    },
    {
      "symbol_id": "LT-02",
      "symbol_description": "Square with X pattern",
      "name": "2x24W Vapor Proof LED",
      "wattage_w": 48,
      "wattage_formula": "2x24W",
      "ip_rating": "IP65",
      "mounting": "surface",
      "notes": "For wet areas"
    }
  ],
  "sockets": [
    {
      "symbol_id": "PS-01",
      "symbol_description": "Double square",
      "name": "16A Double Switched Socket",
      "mounting_mm": 300,
      "ip_rating": "IP20",
      "notes": "@300mm AFF"
    },
    {
      "symbol_id": "PS-02",
      "symbol_description": "Double square with circle",
      "name": "16A Double Waterproof Socket",
      "mounting_mm": 300,
      "ip_rating": "IP55",
      "notes": "Wet area use"
    }
  ],
  "switches": [
    {
      "symbol_id": "SW-01",
      "symbol_description": "Small rectangle with one line",
      "name": "1-Lever 1-Way Switch",
      "mounting_mm": 1200,
      "notes": "@1200mm AFF"
    },
    {
      "symbol_id": "SW-02",
      "symbol_description": "Small rectangle with two lines",
      "name": "2-Lever 1-Way Switch",
      "mounting_mm": 1200,
      "notes": ""
    }
  ],
  "equipment": [
    {
      "symbol_id": "EQ-01",
      "symbol_description": "AC unit icon",
      "name": "Air Conditioning Unit",
      "rating_kw": 0,
      "notes": "Size varies per schedule"
    }
  ],
  "containment": [
    {
      "symbol_id": "CT-01",
      "symbol_description": "Dashed line with ladder pattern",
      "name": "Cable Ladder 300mm",
      "size_mm": 300,
      "notes": ""
    }
  ],
  "other_symbols": [
    {
      "symbol_id": "OT-01",
      "symbol_description": "Triangle with E",
      "name": "Emergency Light",
      "notes": "Self-contained 3hr"
    }
  ],
  "confidence": 0.85,
  "notes": ["Legend clearly visible", "Some symbols not in legend - using standard assumptions"]
}"""


def get_prompt(building_block: str = "") -> str:
    """
    Generate the legend extraction prompt.

    Args:
        building_block: Name of the building block if known

    Returns:
        Complete prompt text for Claude
    """
    block_info = ""
    if building_block:
        block_info = f"\nBuilding Block: {building_block}"

    return f"""## TASK: LEGEND/KEY EXTRACTION
{block_info}

You are analyzing an electrical drawing. Your task is to extract the LEGEND or KEY
table BEFORE counting any symbols. This ensures accurate fixture identification.

## WHY LEGEND EXTRACTION MATTERS

Different projects use different symbols. The legend tells us:
- What each symbol represents
- Fixture wattages and specifications
- Mounting heights for sockets/switches
- IP ratings for wet areas

## WHERE TO FIND THE LEGEND

Common locations:
1. **Bottom right corner** - Most common position
2. **Bottom left corner** - Alternative position
3. **Right side margin** - On larger drawings
4. **Separate legend sheet** - For large projects

## LEGEND STRUCTURE

Typical legend format:
```
SYMBOL | DESCRIPTION
-----------------------
  [O]  | 600x1200 Recessed LED 3x18W
  [X]  | 2x24W Vapor Proof LED (IP65)
  [==] | 16A Double Socket @300mm
```

## EXTRACTION RULES

### For Lights:
- **symbol_id**: Create a unique ID (LT-01, LT-02, etc.)
- **symbol_description**: Describe the visual appearance
- **name**: Full fixture name from legend
- **wattage_w**: Total wattage (calculate if formula given)
- **wattage_formula**: Original formula (e.g., "3x18W")
- **ip_rating**: IP20 (indoor), IP44 (damp), IP65 (wet)
- **mounting**: "recessed", "surface", "pendant", "pole"

### For Sockets:
- **symbol_id**: Create a unique ID (PS-01, PS-02, etc.)
- **name**: Socket description from legend
- **mounting_mm**: Height in mm (300, 450, 1100, 1500)
- **ip_rating**: IP rating if shown

### For Switches:
- **symbol_id**: Create a unique ID (SW-01, SW-02, etc.)
- **name**: Switch type from legend
- **mounting_mm**: Typically 1200mm or 1500mm

### For Equipment:
- AC units, geysers, pumps, motors
- Include rating if shown

### For Containment:
- Cable trays, ladders, conduit
- Include size if shown

## STANDARD SOUTH AFRICAN FIXTURES

If legend is unclear, use these SA standards:

| Fixture Type | Typical Wattage | Mounting |
|--------------|-----------------|----------|
| 600x1200 LED Panel | 54W (3x18W) | Recessed |
| 600x600 LED Panel | 40W | Recessed |
| Downlight LED | 6W/9W/12W | Recessed |
| Surface LED | 18W/24W | Surface |
| Vapor Proof | 36W/48W (2x18W/2x24W) | Surface |
| Bulkhead | 24W/26W | Surface |
| Flood Light | 30W/50W/100W/200W | External |
| Pole Light | 60W | 2.3m pole |

## SOCKET HEIGHTS (SA Standard)

| Location | Height |
|----------|--------|
| General rooms | 300mm |
| Kitchen counter | 1100mm |
| Bathroom (away from water) | 1500mm |
| Industrial | 450mm |

## JSON OUTPUT FORMAT

Respond with ONLY valid JSON (no markdown, no explanation):

{LEGEND_SCHEMA}

## IMPORTANT RULES

1. **Extract EVERYTHING** from the legend - don't skip items
2. **Calculate wattage** if formula is given (e.g., 3x18W = 54W)
3. **Note confidence** - high if legend is clear, low if guessing
4. **Include notes** for any assumptions made
5. If NO legend found, set "has_legend": false and use standards
6. Create unique symbol_ids even if not shown on drawing
7. Describe symbol appearance to help with later matching
"""


def get_legend_prompt(building_block: str = "") -> str:
    """Simplified accessor for legend extraction prompt."""
    return get_prompt(building_block)
