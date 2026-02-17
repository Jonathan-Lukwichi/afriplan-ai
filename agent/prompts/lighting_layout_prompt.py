"""
AfriPlan Electrical v4.1.1 - Lighting Layout Extraction Prompt

Extracts rooms with light fixtures from lighting layout drawings.

CRITICAL RULES:
1. READ THE LEGEND FIRST - Every symbol type is defined in the legend
2. COUNT EVERY SYMBOL - Do not estimate, count actual instances
3. MATCH CIRCUIT LABELS - Each fixture has a circuit label (e.g., "L2 DB-S3")
4. NEVER FABRICATE - If count is unclear, mark as "estimated"
"""

from typing import List, TYPE_CHECKING
if TYPE_CHECKING:
    from agent.models import PageInfo

from agent.prompts.schemas import LIGHTING_LAYOUT_SCHEMA


def get_prompt(pages: List["PageInfo"], building_block: str = "") -> str:
    """
    Generate the lighting layout extraction prompt.

    Args:
        pages: List of lighting layout page images to analyze
        building_block: Name of the building block these pages belong to

    Returns:
        Complete prompt text for Claude
    """
    page_info = ""
    if pages:
        page_info = f"\nAnalyzing {len(pages)} lighting layout page(s)"
        if building_block:
            page_info += f" for: {building_block}"

    return f"""## TASK: LIGHTING LAYOUT EXTRACTION
{page_info}

You are analyzing electrical lighting layout drawings. Extract all rooms with
their light fixtures, circuit references, and any legend/key information.

## CRITICAL: READ THE LEGEND FIRST

Before counting fixtures, locate and read the LEGEND/KEY on the drawing.
Different building blocks have different fixture types:

### Common Light Fixture Symbols

| Symbol | Typical Meaning |
|--------|-----------------|
| Circle with line | Surface mount light (18W/24W LED) |
| Dotted circle | Recessed downlight (6W/9W LED) |
| Rectangle 600x600 | LED panel (40W) |
| Rectangle 600x1200 | LED panel (3x18W = 54W) |
| Square with X | Vapor proof light (2x18W/2x24W) |
| Square with lines | Prismatic light (2x18W) |
| Triangle | Emergency light |
| Circle with rays | Flood light (30W/50W/200W) |
| Rectangle on pole | Pole light (60W outdoor) |
| Circle marked "B" | Bulkhead light (24W/26W outdoor) |
| Rectangle 5ft | Fluorescent tube (50W) |

**IMPORTANT**: The legend on YOUR drawing may differ. Always use the legend
definitions from the actual drawing, not these defaults.

## EXTRACTION RULES

### For Each Room:
1. **name**: Exact room name as shown on drawing (e.g., "RECEPTION", "OFFICE 1")
2. **area_m2**: Room area if shown (otherwise estimate from scale)
3. **circuit_refs**: List of circuit references visible (e.g., ["DB-S3 L1", "DB-S3 L2"])
4. **fixtures**: Count of each fixture type

### Fixture Types to Count:

#### Panel/Recessed Lights
- **led_panel_3x18w**: 600x1200mm recessed LED panels (54W total)
- **led_panel_40w**: 600x600mm LED panels
- **led_downlight_6w**: Small recessed downlights
- **led_downlight_9w**: Medium recessed downlights

#### Surface Mount Lights
- **led_surface_18w**: 18W LED surface mount
- **led_surface_24w**: 24W LED surface mount

#### Vapor Proof (Wet Areas)
- **vapor_proof_2x18w**: 2x18W vapor proof fitting
- **vapor_proof_2x24w**: 2x24W vapor proof fitting

#### Specialty Lights
- **prismatic_2x18w**: 2x18W prismatic light
- **fluorescent_50w**: 50W fluorescent tube (5ft)
- **emergency_light**: Self-contained emergency light

#### Outdoor Lights
- **flood_30w**: 30W LED flood light
- **flood_50w**: 50W LED flood light
- **flood_200w**: 200W LED flood light
- **bulkhead_24w**: 24W bulkhead outdoor
- **bulkhead_26w**: 26W bulkhead outdoor
- **pole_light_60w**: 60W pole light (2.3m pole)

## CIRCUIT REFERENCE FORMATS

Look for circuit references near lights or in a schedule:
- "DB-S3 L1" = Distribution Board S3, Lighting circuit 1
- "L2" = Lighting circuit 2 (DB implied)
- "CKT L3" = Circuit L3

## ROOM MATCHING

Room names must match EXACTLY what's shown on the drawing.
Common room names:
- Reception, Lobby, Foyer
- Office 1, Office 2, Suite A
- Kitchen, Kitchenette
- Boardroom, Meeting Room
- Toilet, Bathroom, Ablution, WC
- Store, Storage, Plant Room
- Corridor, Passage, Circulation
- Hall, Main Hall, Community Hall
- Pool Deck, Change Room

## CONFIDENCE LEVELS

- **HIGH**: Fixture clearly visible with legend match
- **MEDIUM**: Fixture identified but legend ambiguous
- **LOW**: Fixture count estimated or symbol unclear

## JSON OUTPUT FORMAT

Respond with ONLY valid JSON matching this schema (no markdown, no explanation):

{LIGHTING_LAYOUT_SCHEMA}

## CRITICAL: LEGEND PARSING

Before counting ANY fixtures, locate and parse the LEGEND/KEY on the drawing.
Extract EVERY item from the legend table:

Example legend entries:
```
SYMBOL | DESCRIPTION
  ⬜   | 600 x 1200 Recessed 3 x 18W LED Fluorescent Light
  ○    | 18W LED Ceiling Light Surface Mount
  ◐    | 30W LED Flood Light
```

Every legend item MUST appear in your extraction. Missing legend items = INCOMPLETE extraction.

## COUNTING RULES

1. COUNT visible symbols on the drawing - do NOT estimate
2. If a room shows 8 light symbols, report qty=8, not an estimate
3. Mark confidence as "extracted" when you physically counted the symbols
4. Mark confidence as "estimated" ONLY if the count is truly unclear

## CIRCUIT LABEL MATCHING

Look for circuit labels near fixtures:
- "L2 DB-S3" means Lighting circuit 2 from Distribution Board S3
- Include the full reference (circuit + DB) in your extraction

## NEVER FABRICATE

If you cannot clearly count fixtures:
- Use your best count and mark "confidence": "estimated"
- Add a note: "COUNT UNCLEAR - VERIFY ON SITE"
- Do NOT invent fixture quantities

## IMPORTANT REMINDERS

1. Always read the legend FIRST - this defines what symbols mean
2. Count EVERY light fixture - don't estimate
3. Each room should list ALL its fixtures with circuit refs
4. Capture circuit references where visible (e.g., "L1 DB-CA")
5. Note emergency lights separately
6. Include confidence level per room and per fixture type
7. If same fixture type appears multiple times in legend, use the specific wattage
"""


def get_lighting_layout_prompt(building_block: str = "") -> str:
    """Simplified accessor for lighting layout prompt."""
    return get_prompt([], building_block)
