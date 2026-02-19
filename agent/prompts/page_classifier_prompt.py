"""
AfriPlan Electrical v4.2 - Page Classifier Prompt

Fast classification of electrical drawing pages to route them to the correct
extraction pipeline. Uses Haiku for speed and cost efficiency.

Page Types:
- SLD: Single Line Diagram with circuit schedules
- LAYOUT_LIGHTING: Floor plan with light symbols only
- LAYOUT_PLUGS: Floor plan with socket/switch symbols only
- LAYOUT_COMBINED: Floor plan with BOTH lights AND sockets
- OUTSIDE_LIGHTS: Site plan with external lighting
- REGISTER: Drawing list, cover page, transmittal
- SCHEDULE: Standalone schedules (without SLD)
- DETAIL: Construction details, sections
- UNKNOWN: Cannot determine
"""

from typing import List, TYPE_CHECKING
if TYPE_CHECKING:
    from agent.models import PageInfo


# Page classifier JSON schema
PAGE_CLASSIFIER_SCHEMA = """{
  "page_type": "SLD",
  "confidence": 0.92,
  "building_block": "Pool Block",
  "drawing_number": "EL-SLD-003",
  "reasoning": "Contains single line diagram with circuit schedules and breaker ratings"
}"""


def get_prompt(page_number: int = 1) -> str:
    """
    Generate the page classification prompt for Haiku.

    Args:
        page_number: The page number being classified

    Returns:
        Complete prompt text for Claude
    """
    return f"""## TASK: CLASSIFY ELECTRICAL DRAWING PAGE

You are analyzing page {page_number} of an electrical drawing set.
Classify this page into ONE of the following types:

## PAGE TYPES

| Type | Description | Key Indicators |
|------|-------------|----------------|
| **SLD** | Single Line Diagram | Circuit schedules, breaker ratings, DB symbols, power flow |
| **LAYOUT_LIGHTING** | Lighting Floor Plan | Light fixture symbols ONLY, no sockets/switches visible |
| **LAYOUT_PLUGS** | Power Floor Plan | Socket/switch symbols ONLY, no light fixtures visible |
| **LAYOUT_COMBINED** | Combined Layout | BOTH light fixtures AND sockets/switches on same drawing |
| **OUTSIDE_LIGHTS** | Site External Lighting | Pole lights, flood lights, cable runs between buildings |
| **REGISTER** | Drawing Index/Cover | Drawing list, title page, transmittal, revision table |
| **SCHEDULE** | Standalone Schedule | Equipment schedule, load schedule (without SLD) |
| **DETAIL** | Construction Detail | Section views, installation details, mounting details |
| **UNKNOWN** | Cannot Determine | Unclear or non-electrical content |

## CLASSIFICATION RULES

### SLD (Single Line Diagram)
- Shows distribution boards as rectangular boxes
- Contains circuit schedules with: circuit ID, description, wattage, cable, breaker
- Shows power flow from supply → main DB → sub DBs
- May include transformer symbols, metering
- Look for: "DB-", "MCB", "MCCB", "ELCB", "kW", breaker ratings (20A, 32A, etc.)

### LAYOUT_LIGHTING
- Floor plan with room outlines
- Light fixture symbols: circles, rectangles, LED panels
- NO socket or switch symbols visible
- May show circuit references (L1, L2, etc.)
- Look for: light legends, wattage annotations, emergency lights

### LAYOUT_PLUGS
- Floor plan with room outlines
- Socket symbols: double squares, single squares
- Switch symbols: small rectangles with lines
- NO light fixture symbols visible
- May show circuit references (P1, P2, etc.)
- Look for: socket heights (@300, @1100), isolators, data points

### LAYOUT_COMBINED
- Floor plan with BOTH lights AND sockets/switches
- Common in South African drawings (combined services layout)
- Contains multiple symbol types
- Look for: mixed legends (lights + sockets + switches)

### OUTSIDE_LIGHTS
- Site plan or external areas
- Pole lights, flood lights, bollard lights
- Cable routes between buildings
- Underground cable annotations
- Look for: trench routes, external DB locations, site boundaries

### REGISTER
- Drawing list/index
- Cover page or title sheet
- Transmittal documentation
- Revision history table
- No electrical symbols, mostly text

### SCHEDULE
- Equipment schedule (motors, pumps, AC units)
- Load schedule without SLD
- Luminaire schedule standalone
- Cable schedule

### DETAIL
- Construction sections
- Installation details
- Mounting arrangements
- Cable tray sections

## BUILDING BLOCK DETECTION

If you can identify which building/block this drawing belongs to, include it:
- Look in title block for building name
- Look for "Block A", "Building B", "Pool Area", etc.
- Extract the drawing number if visible

## CONFIDENCE SCORING

- **0.9+**: Clear, unambiguous classification
- **0.7-0.9**: Confident but some ambiguity
- **0.5-0.7**: Best guess, multiple types possible
- **<0.5**: Very uncertain, needs human review

## JSON OUTPUT FORMAT

Respond with ONLY valid JSON (no markdown, no explanation):

{PAGE_CLASSIFIER_SCHEMA}

## IMPORTANT

1. Choose ONLY ONE page type
2. Do not guess building blocks if not clearly visible
3. Combined layouts are common - look for BOTH light AND socket symbols
4. SLDs always have circuit schedules or breaker ratings
5. If truly unclear, use "UNKNOWN" with low confidence
"""


def get_page_classifier_prompt(page_number: int = 1) -> str:
    """Simplified accessor for page classifier prompt."""
    return get_prompt(page_number)
