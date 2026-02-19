"""
AfriPlan Electrical v4.3 - SLD Extraction Prompt

THE MOST CRITICAL PROMPT - Extracts distribution boards and circuits from
Single Line Diagram (SLD) pages. This is where all electrical data comes from.

CRITICAL: Focus on the SCHEDULE TABLE at the bottom of SLD pages.
The schedule table has rows: Circuit No | Wattage | Wire Size | No Of Point
Each column is one circuit. This is the PRIMARY source of truth.

v4.3 Enhancements:
- Added ISO, PP, HP, CP, HVAC, RWB circuit types
- VSD and starter type detection
- Enhanced wattage formula parsing (e.g., "5x48W = 240W")
- Pump equipment extraction for pool/heat pumps
- Day/night switch detection with bypass
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

## CIRCUIT TYPE DETECTION (v4.3 Enhanced)

| Prefix | Type | Typical Breaker | Cable | Notes |
|--------|------|-----------------|-------|-------|
| L1, L2, L3... | lighting | 10A-16A | 1.5mm² | Count fixtures |
| P1, P2, P3... | power | 16A-20A | 2.5mm² | Socket circuits |
| AC1, AC2... | air_con | 20A-32A | 4mm²-6mm² | Requires isolator |
| HP1, HP2... | heat_pump | 32A-40A | 6mm²-10mm² | Usually has VSD |
| PP1, PP2... | pool_pump | 20A-32A | 4mm²-6mm² | **NEW** Pool pump with VSD |
| CP1, CP2... | circulation_pump | 16A-20A | 2.5mm²-4mm² | **NEW** Circulation pump |
| PUMP1, PUMP2... | pump | 16A-32A | 2.5mm²-6mm² | Generic pump |
| ISO1, ISO2... | isolator | 20A-63A | varies | **NEW** Dedicated isolator circuit |
| G1, G2... | geyser | 20A | 2.5mm² | Geyser circuit |
| S1, S2... | stove | 32A | 6mm² | Stove/hob circuit |
| SB, SF... | sub_board_feed | 40A-100A | 6mm²-25mm² | Feed to sub-DB |
| HVAC | hvac | 63A-100A | 10mm²-25mm² | **NEW** Large HVAC system |
| RWB | rainwater | 16A-20A | 2.5mm² | **NEW** Rainwater pump |
| D/N, W1-W2 | day_night | 10A | 1.5mm² | **NEW** Day/night switch |
| R1, W1, B1 | phase_marker | - | - | Phase indicators (Red/White/Blue) |

**IMPORTANT**: ISO-prefixed circuits (ISO1-ISO9) are ISOLATOR circuits for equipment like
geysers, AC units, and pumps. They are NOT socket or power circuits.

## VSD AND STARTER TYPE DETECTION (v4.3)

For pump and motor circuits, identify the starter type:

| Symbol | Starter Type | Description |
|--------|--------------|-------------|
| Rectangle with sine wave (~) | **VSD** | Variable Speed Drive - most common for pumps |
| Simple contactor symbol | **DOL** | Direct On-Line starter |
| Two contactors with timer | **Star-Delta** | Star-delta starter for large motors |
| Rectangle with soft curve | **Soft Starter** | Soft starter for smooth motor start |

**For each motor/pump circuit, extract:**
- `has_vsd`: true/false (look for VSD symbol)
- `vsd_rating_kw`: Motor kW rating if VSD present
- `starter_type`: "vsd" | "dol" | "star_delta" | "soft_starter"
- `isolator_a`: Isolator rating (usually 1.5× motor current)

## WATTAGE FORMULA PATTERNS (v4.3)

Parse these common formats found in SA SLDs:

| Pattern | Example | Meaning | Extract As |
|---------|---------|---------|------------|
| NxWW | 5x48W | 5 fittings × 48W each | wattage_w: 240, wattage_formula: "5x48W" |
| NxWWW | 3x1200W | 3 heaters × 1200W | wattage_w: 3600, wattage_formula: "3x1200W" |
| NxNW | 13x30W | 13 lights × 30W | wattage_w: 390, wattage_formula: "13x30W" |
| Combined | 5X54W = 270W | Formula with total | wattage_w: 270, wattage_formula: "5x54W" |
| Plain | 3680W | Just wattage | wattage_w: 3680, wattage_formula: "" |

**ALWAYS extract BOTH:**
- `wattage_formula`: Raw string from drawing (e.g., "5x48W")
- `wattage_w`: Calculated total wattage (e.g., 240)

## DAY/NIGHT SWITCH DETECTION (v4.3)

Look for day/night (photocell) switch circuits:
- **Symbol**: Two small circles labeled S1, S2 with dashed connection
- **Label**: "DAY/NIGHT" or "D/N" annotation
- **Bypass**: Often has "W/BYPASS" or "BYPASS" text

**Extract:**
- `has_day_night`: true if day/night switch present
- `has_bypass`: true if bypass switch included
- `controlled_circuits`: List of circuit IDs controlled (e.g., ["L1", "L2"])

## HEAVY EQUIPMENT IDENTIFICATION (v4.3 Enhanced)

When you see circuits for equipment, extract as `heavy_equipment`:

| Equipment Type | Look For | type value | Default has_vsd |
|----------------|----------|------------|-----------------|
| Pool Pump | "POOL PUMP", PP1-PP4, "POOL PUMP1" | pool_pump | true |
| Heat Pump | "HEAT PUMP", HP1-HP5, "HEAT PUMP1" | heat_pump | true |
| Circulation Pump | "CIRC PUMP", CP1, "CIRCULATION" | circulation_pump | true |
| Borehole Pump | "BH PUMP", "BOREHOLE" | borehole_pump | false |
| HVAC System | "HVAC", large kW (>18kW) | hvac | false |
| Geyser | "GEYSER", G1-G5 | geyser | false |

**For pump sub-boards (DB-PPS, DB-HPS, etc.):**
Each breaker feeding a pump should be extracted as a heavy_equipment item with:
- `name`: "Pool Pump 1", "Heat Pump 2", etc.
- `type`: "pool_pump", "heat_pump", etc.
- `rating_kw`: Motor rating
- `has_vsd`: true (for pool/heat pumps)
- `starter_type`: "vsd", "dol", etc.
- `isolator_a`: Isolator rating in Amps
- `circuit_ref`: Circuit ID (e.g., "PP1", "HP3")
- `fed_from_db`: Parent DB name (e.g., "DB-PPS1")
- `cable_size_mm2`: Cable size
- `cable_type`: Cable type (e.g., "PVC SWA PVC")

## CONFIDENCE LEVELS

- **HIGH**: Data clearly visible in schedule table or diagram
- **MEDIUM**: Data inferred from standard practices
- **LOW**: Assumption based on typical installations

## JSON OUTPUT FORMAT

Respond with ONLY valid JSON matching this schema (no markdown, no explanation):

{SLD_SCHEMA}

## CRITICAL: SCHEDULE TABLE PARSING

The schedule table at the BOTTOM of the SLD drawing is the PRIMARY data source.
It typically looks like this:

```
┌────────────┬──────┬──────┬──────┬───────┬──────┬──────┬──────┬───────┐
│ Circuit No │  P1  │  P2  │  P3  │  L1   │  L2  │  L3  │ AC-1 │ SPARE │
├────────────┼──────┼──────┼──────┼───────┼──────┼──────┼──────┼───────┤
│ Wattage    │3680W │3680W │3680W │  30W  │ 198W │  60W │1650W │       │
├────────────┼──────┼──────┼──────┼───────┼──────┼──────┼──────┼───────┤
│ Wire Size  │2.5mm²│2.5mm²│2.5mm²│1.5mm²│1.5mm²│1.5mm²│2.5mm²│       │
├────────────┼──────┼──────┼──────┼───────┼──────┼──────┼──────┼───────┤
│ No Of Point│   4  │   3  │   2  │   6   │   8  │   6  │   1  │       │
└────────────┴──────┴──────┴──────┴───────┴──────┴──────┴──────┴───────┘
```

READ EVERY COLUMN! Each column = one circuit.

## NEVER FABRICATE

If you cannot clearly read a value:
- Mark it as "confidence": "estimated"
- Add note: "VALUE NOT READABLE - VERIFY"
- Do NOT invent values like "60kW HVAC" or fake DB names

## IMPORTANT REMINDERS

1. Extract EVERY circuit from the schedule table - don't skip any
2. If a page has 2 DBs, extract BOTH
3. Note spare ways (empty positions) in the schedule
4. Capture the supply chain (what feeds what)
5. Note any ELCB/RCD or surge protection devices
6. Read cable sizes carefully - they're critical for pricing
7. If wattage shows "---" or is blank, mark as "estimated" with note
8. Always include confidence level for each extracted value
9. DB names MUST match exactly what's on the drawing (e.g., "DB-CA", "DB-S1")
10. Read main breaker rating from the diagram header
"""


def get_sld_extraction_prompt(building_block: str = "") -> str:
    """Simplified accessor for SLD prompt without page objects."""
    return get_prompt([], building_block)
