"""
AfriPlan Electrical v4.0 - SLD Extraction Prompt

THE MOST CRITICAL PROMPT - Extracts distribution boards and circuits from
Single Line Diagram (SLD) pages. This is where all electrical data comes from.
"""

from typing import List, TYPE_CHECKING
if TYPE_CHECKING:
    from agent.models import PageInfo

from agent.prompts.schemas import SLD_SCHEMA


def get_prompt(pages: List["PageInfo"], building_block: str = "") -> str:
    """
    Generate the SLD extraction prompt.

    Args:
        pages: List of SLD page images to analyze
        building_block: Name of the building block these pages belong to

    Returns:
        Complete prompt text for Claude
    """
    page_info = ""
    if pages:
        page_info = f"\nAnalyzing {len(pages)} SLD page(s)"
        if building_block:
            page_info += f" for: {building_block}"

    return f"""## TASK: SINGLE LINE DIAGRAM (SLD) EXTRACTION
{page_info}

You are analyzing electrical Single Line Diagram (SLD) drawings. Your task is to
extract ALL distribution boards and their complete circuit schedules.

## CRITICAL READING INSTRUCTIONS

### Read BOTH the Diagram AND the Schedule Table

Every SLD page typically has:
1. **TOP SECTION**: Single-line diagram showing the breakers, cables, and connections visually
2. **BOTTOM SECTION**: Circuit schedule table with columns like:
   - Circuit No (e.g., L1, L2, P1, P2, AC1)
   - Description (e.g., "Hall Lights", "Kitchen Power")
   - Wattage (in Watts)
   - Wire Size (e.g., 1.5mm², 2.5mm²)
   - No Of Point / Points
   - Breaker Size (in Amps)

**ALWAYS read the schedule table** - it contains exact values that may not be visible in the diagram.

### Multiple DBs Per Page

Some SLD pages contain 2 or more distribution boards. For example:
- WD-PB-01-SLD might show both DB-CR (top) and DB-PFA (bottom)
- Extract ALL distribution boards you see on each page

### Supply Chain Detection

Look for:
- "SUPPLY FROM: ..." text indicating where this DB gets power
- Cable specifications on the incoming supply (e.g., "4Cx16mm² PVC SWA PVC")
- Main breaker/MCCB rating at the top of the DB
- Sub-board feeds showing which other DBs this one supplies

## EXTRACTION RULES

### For Each Distribution Board:
1. **name**: Exact DB designation (e.g., "DB-CR", "DB-S3", "DB-PFA")
2. **designation**: Full name/description (e.g., "Main Distribution Board - Community Hall")
3. **building_block**: Which building this DB serves
4. **total_ways**: Total number of ways/positions in the DB
5. **main_breaker_a**: Main breaker rating in Amps
6. **elcb_present**: Is there an earth leakage device (ELCB/RCD)?
7. **elcb_rating_ma**: If present, the mA rating (typically 30mA)
8. **surge_present**: Is there a surge protection device (SPD)?
9. **supply_from**: What supplies this DB (Eskom, Kiosk, another DB)
10. **supply_cable**: Incoming cable specification

### For Each Circuit:
1. **circuit_number**: Exact circuit designation (L1, L2, P1, AC1, etc.)
2. **description**: What the circuit feeds
3. **wattage_w**: Total wattage (from schedule table)
4. **breaker_a**: Breaker rating in Amps
5. **cable_size_mm2**: Cable size in mm² (from schedule or assume from breaker)
6. **num_points**: Number of points (lights, sockets, etc.)
7. **is_lighting**: True if this is a lighting circuit (L prefix)
8. **is_dedicated**: True if dedicated circuit (stove, geyser, AC, pump)

### For Sub-Board Feeds:
If the SLD shows feeds going to other distribution boards:
1. **name**: "SB to DB-XXX" format
2. **breaker_a**: Breaker rating for the sub-board feed
3. **cable**: Cable specification
4. **destination_db**: Name of the DB being fed

## CIRCUIT TYPE DETECTION

| Pattern | Type | Typical Breaker | Cable |
|---------|------|-----------------|-------|
| L1, L2, L3... | Lighting | 10A-16A | 1.5mm² |
| P1, P2, P3... | Power (sockets) | 16A-20A | 2.5mm² |
| AC1, AC2... | Air conditioning | 20A-32A | 4mm²-6mm² |
| HP1, HP2... | Heat pump | 32A-40A | 6mm²-10mm² |
| PUMP1, PUMP2... | Pool pump | 16A-20A | 2.5mm²-4mm² |
| G1, G2... | Geyser | 20A | 2.5mm² |
| S1, S2... | Stove | 32A | 6mm² |
| SB, SF... | Sub-board feed | 40A-100A | 6mm²-25mm² |

## HEAVY EQUIPMENT IDENTIFICATION

When you see circuits for:
- **Pool pumps** with VSD drives - note as heavy equipment
- **Heat pumps** (12.5kW+) - note as heavy equipment
- **HVAC** (18kW+) - note as heavy equipment
- **Circulation pumps** - note as heavy equipment
- **Geyser banks** (multiple 50L+ units) - note as heavy equipment

## CONFIDENCE LEVELS

- **HIGH**: Data clearly visible in schedule table or diagram
- **MEDIUM**: Data inferred from standard practices
- **LOW**: Assumption based on typical installations

## JSON OUTPUT FORMAT

Respond with ONLY valid JSON matching this schema (no markdown, no explanation):

{SLD_SCHEMA}

## IMPORTANT REMINDERS

1. Extract EVERY circuit from the schedule table - don't skip any
2. If a page has 2 DBs, extract BOTH
3. Note spare ways (empty positions) in the schedule
4. Capture the supply chain (what feeds what)
5. Note any ELCB/RCD or surge protection devices
6. Read cable sizes carefully - they're critical for pricing
7. If wattage shows "---" or is blank, estimate from typical loads
8. Always include confidence level for each DB
"""


def get_sld_extraction_prompt(building_block: str = "") -> str:
    """Simplified accessor for SLD prompt without page objects."""
    return get_prompt([], building_block)
