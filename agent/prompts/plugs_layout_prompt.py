"""
AfriPlan Electrical v4.2 - Plugs/Power Layout Extraction Prompt

Extracts rooms with socket outlets and switches from power layout drawings.
Handles both dedicated power layouts and combined lighting+power drawings.

CRITICAL RULES:
1. READ THE LEGEND FIRST - Every symbol type is defined in the legend
2. COUNT EVERY SYMBOL - Do not estimate, count actual instances
3. DISTINGUISH SOCKET HEIGHTS - 300mm vs 1100mm is critical
4. IDENTIFY WET AREA SOCKETS - IP-rated for bathrooms/kitchens
5. CAPTURE DATA POINTS - CAT6 outlets are common in offices
"""

from typing import List, Optional, TYPE_CHECKING
if TYPE_CHECKING:
    from agent.models import PageInfo, BuildingLegend

from agent.prompts.schemas import PLUGS_LAYOUT_SCHEMA


def get_prompt(
    pages: Optional[List["PageInfo"]] = None,
    building_block: str = "",
    legend: Optional["BuildingLegend"] = None
) -> str:
    """
    Generate the plugs/power layout extraction prompt.

    Args:
        pages: List of power layout page images to analyze
        building_block: Name of the building block these pages belong to
        legend: Pre-extracted legend information (from legend_prompt.py)

    Returns:
        Complete prompt text for Claude
    """
    page_info = ""
    if pages:
        page_info = f"\nAnalyzing {len(pages)} power layout page(s)"
        if building_block:
            page_info += f" for: {building_block}"

    legend_info = ""
    if legend:
        legend_info = f"""
## PRE-EXTRACTED LEGEND

The following legend has been extracted from the drawing. Use these definitions:

### Sockets:
{_format_legend_items(legend.sockets if hasattr(legend, 'sockets') else [])}

### Switches:
{_format_legend_items(legend.switches if hasattr(legend, 'switches') else [])}
"""

    return f"""## TASK: POWER/PLUGS LAYOUT EXTRACTION
{page_info}
{legend_info}

You are analyzing electrical power layout drawings. Extract all rooms with
their socket outlets, switches, data points, and circuit references.

## CRITICAL: READ THE LEGEND FIRST

Before counting fixtures, locate and read the LEGEND/KEY on the drawing.
Different projects use different symbols:

### Common Socket Symbols

| Symbol | Typical Meaning |
|--------|-----------------|
| Double square | 16A Double Switched Socket |
| Single square | 16A Single Switched Socket |
| Square with dot | Unswitched Socket |
| Square with circle | Waterproof Socket (IP55) |
| Square with arrow down | Ceiling Socket |
| Square with "D" or triangle | Data Point (CAT6) |
| Rectangle with "FB" | Floor Box |

### Common Switch Symbols

| Symbol | Typical Meaning |
|--------|-----------------|
| Small rectangle, 1 line | 1-Lever 1-Way Switch |
| Small rectangle, 2 lines | 2-Lever 1-Way Switch |
| Small rectangle, arrow | 2-Way Switch |
| Circle with lines | Dimmer Switch |
| Rectangle "MS" | Master Switch |
| Rectangle "ISO" | Isolator Switch |
| Sun symbol | Day/Night Switch |

**IMPORTANT**: Always use the legend definitions from YOUR drawing, not these defaults.

## SOCKET HEIGHT RULES (SA Standard)

| Height | Application |
|--------|-------------|
| 300mm | General purpose, living areas, bedrooms |
| 450mm | Industrial, workshops |
| 1100mm | Kitchen counter level, above worktops |
| 1200mm | Next to switches (convenience) |
| 1500mm | Bathrooms (above splashback) |

Height affects pricing and is CRITICAL for accurate BQ generation.

## EXTRACTION RULES

### For Each Room:
1. **name**: Exact room name as shown on drawing (e.g., "KITCHEN", "OFFICE 1")
2. **fixtures**: Count of each socket/switch type
3. **circuit_refs**: List of circuit references visible (e.g., ["DB-S1 P1", "DB-S1 P2"])
4. **is_wet_area**: true for bathrooms, kitchens, laundry, scullery
5. **has_ac**: true if AC isolator or unit visible

### Socket Types to Count:

#### Standard Sockets
- **double_socket_300**: 16A Double Switched Socket @300mm
- **single_socket_300**: 16A Single Switched Socket @300mm
- **double_socket_1100**: 16A Double Switched Socket @1100mm (counter level)
- **single_socket_1100**: 16A Single Switched Socket @1100mm

#### Special Sockets
- **double_socket_waterproof**: 16A Double Waterproof Socket (IP55)
- **double_socket_ceiling**: 16A Double Ceiling Socket
- **data_points_cat6**: CAT6 Data Point / Network Outlet
- **floor_box**: Floor Box with Power + Data

### Switch Types to Count:

- **switch_1lever_1way**: 1-Lever 1-Way Switch @1200mm
- **switch_2lever_1way**: 2-Lever 1-Way Switch @1200mm
- **switch_1lever_2way**: 1-Lever 2-Way Switch @1200mm
- **switch_3lever_1way**: 3-Lever 1-Way Switch @1200mm
- **day_night_switch**: Day/Night Switch @2000mm (external)
- **isolator_30a**: 30A Isolator Switch @2000mm
- **isolator_20a**: 20A Isolator Switch @2000mm
- **master_switch**: Master Switch (bedrooms, hotels)

## CIRCUIT REFERENCE FORMATS

Look for circuit references near sockets or in a schedule:
- "DB-S1 P1" = Distribution Board S1, Power circuit 1
- "P2" = Power circuit 2 (DB implied)
- "CKT P3" = Circuit P3
- "DB-KIT P1" = Kitchen board, Power circuit 1

## ROOM MATCHING

Room names must match EXACTLY what's shown on the drawing.
Common room names:
- Reception, Lobby, Foyer
- Office 1, Office 2, Suite A, Open Plan
- Kitchen, Kitchenette, Scullery
- Boardroom, Meeting Room, Conference
- Server Room, Comms Room, IT Room
- Toilet, Bathroom, Ablution, WC, Male/Female
- Store, Storage, Plant Room, Electrical Room
- Corridor, Passage, Circulation
- Workshop, Garage, Carport

## WET AREA IDENTIFICATION

Mark `is_wet_area: true` for:
- Bathroom, Toilet, Ablution, WC
- Kitchen (if sockets near water)
- Scullery, Laundry
- Pool area, Change rooms
- Any room with waterproof sockets

Wet areas require:
- IP55+ rated sockets
- Sockets 600mm from water sources
- No sockets in zones 0/1/2

## CONFIDENCE LEVELS

- **HIGH (extracted)**: Symbol clearly visible with legend match
- **MEDIUM (inferred)**: Symbol identified but count uncertain
- **LOW (estimated)**: Count estimated or symbol unclear

## JSON OUTPUT FORMAT

Respond with ONLY valid JSON matching this schema (no markdown, no explanation):

{PLUGS_LAYOUT_SCHEMA}

## COUNTING RULES

1. **COUNT** visible symbols on the drawing - do NOT estimate
2. If a room shows 6 socket symbols, report qty=6, not an estimate
3. Mark confidence as "extracted" when you physically counted the symbols
4. Mark confidence as "estimated" ONLY if the count is truly unclear

## SOCKET vs SWITCH DISTINCTION

Be careful to distinguish:
- **Sockets** (power outlets): Usually larger, square/rectangular
- **Switches** (light controls): Usually smaller, near doors

Look for height annotations:
- @300mm or @1100mm = Socket
- @1200mm = Switch

## SPECIAL EQUIPMENT INDICATORS

Note rooms that have:
- **AC isolators**: Mark `has_ac: true`
- **Geyser isolators**: Note in circuit_refs
- **Stove isolators**: Note as dedicated circuit

## NEVER FABRICATE

If you cannot clearly count fixtures:
- Use your best count and mark "confidence": "estimated"
- Add a note: "COUNT UNCLEAR - VERIFY ON SITE"
- Do NOT invent fixture quantities

## IMPORTANT REMINDERS

1. Always read the legend FIRST - this defines what symbols mean
2. Count EVERY socket and switch - don't estimate
3. Note the HEIGHT of sockets (300mm vs 1100mm)
4. Capture circuit references where visible
5. Mark wet areas appropriately
6. Include confidence level per room and per fixture type
7. Data points (CAT6) are common in offices - don't miss them
"""


def _format_legend_items(items: list) -> str:
    """Format legend items for inclusion in prompt."""
    if not items:
        return "  (No legend items provided - use drawing legend)"

    lines = []
    for item in items:
        desc = getattr(item, 'description', str(item))
        short = getattr(item, 'short_name', '')
        if short:
            lines.append(f"  - {short}: {desc}")
        else:
            lines.append(f"  - {desc}")
    return "\n".join(lines) if lines else "  (No items)"


def get_plugs_layout_prompt(building_block: str = "") -> str:
    """Simplified accessor for plugs layout prompt."""
    return get_prompt(None, building_block, None)
