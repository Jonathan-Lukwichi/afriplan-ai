"""
AfriPlan Electrical v4.5 - SLD Extraction Prompt

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

v4.5 Enhancements (Universal Electrical Project Schema):
- System parameters extraction (voltage, phases, frequency, fault levels)
- Breaker type distinction (MCB vs MCCB vs ACB vs Fuse)
- Phase designation for load balancing (R1/W1/B1)
- Cable material (copper vs aluminium)
- Installation method for cables
- Overload relay detection for motor circuits
- Expanded equipment types (meter, UPS, generator, solar, EV charger, etc.)
- Power source extraction with kVA ratings
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

## SYSTEM PARAMETERS EXTRACTION (v4.5)

Look for system-level specifications on the drawing title block or notes:

| Parameter | Where to Find | Example |
|-----------|---------------|---------|
| **voltage_v** | Title block, "SYSTEM" note | 400V (3-phase), 230V (single) |
| **phases** | Title block | "3PH+N+E", "1PH+N+E" |
| **frequency_hz** | Title block | 50Hz (always 50Hz in SA) |
| **fault_level_ka** | Near main breaker | 15kA, 6kA |

Extract as `system_parameters` in the output.

## EXTRACTION RULES

### For Each Distribution Board:
1. **name**: Exact DB designation (e.g., "DB-CR", "DB-S3", "DB-PFA")
2. **designation**: Full name/description (e.g., "Main Distribution Board - Community Hall")
3. **building_block**: Which building this DB serves
4. **total_ways**: Total number of ways/positions in the DB
5. **main_breaker_a**: Main breaker rating in Amps
6. **main_breaker_type**: Breaker type (see below)
7. **elcb_present**: Is there an earth leakage device (ELCB/RCD)?
8. **elcb_rating_ma**: If present, the mA rating (typically 30mA)
9. **surge_present**: Is there a surge protection device (SPD)?
10. **surge_type**: "type1", "type2", "type3", or "type1+2"
11. **supply_from**: What supplies this DB (Eskom, Kiosk, another DB)
12. **supply_cable**: Incoming cable specification
13. **supply_cable_material**: "copper" or "aluminium"
14. **fault_level_ka**: Fault level rating of the board
15. **status**: "existing", "new", or "proposed"

### BREAKER TYPE DETECTION (v4.5)

| Rating Range | Typical Type | Symbol/Label |
|--------------|--------------|--------------|
| 6A-63A | **MCB** | Small rectangle, "MCB" |
| 100A-250A | **MCCB** | Larger box, "MCCB", "Q1" |
| 400A-1600A | **MCCB** | Large box with ratings |
| 800A-6300A | **ACB** | Large symbol, "ACB" |
| Any | **Fuse** | Fuse symbol, "HRC" |

**IMPORTANT**: MCCB costs 5-10× more than MCB — accurate detection is critical for pricing!

### For Each Circuit:
1. **circuit_number**: Exact circuit designation (L1, L2, P1, AC1, etc.)
2. **description**: What the circuit feeds
3. **wattage_w**: Total wattage (from schedule table)
4. **breaker_a**: Breaker rating in Amps
5. **breaker_type**: "mcb", "mccb", "rcbo" (see table above)
6. **breaker_poles**: 1, 2, or 3 poles
7. **cable_size_mm2**: Cable size in mm² (from schedule or assume from breaker)
8. **cable_material**: "copper" or "aluminium" (default: copper)
9. **num_points**: Number of points (lights, sockets, etc.)
10. **is_lighting**: True if this is a lighting circuit (L prefix)
11. **is_dedicated**: True if dedicated circuit (stove, geyser, AC, pump)
12. **phase**: Phase designation if visible (R1, W1, B1, R2, W2, B2, etc.)

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
| Circle with K | **Contactor** | Simple contactor (no overload) |

**For each motor/pump circuit, extract:**
- `has_vsd`: true/false (look for VSD symbol)
- `vsd_rating_kw`: Motor kW rating if VSD present
- `starter_type`: "vsd" | "dol" | "star_delta" | "soft_starter" | "contactor" | "direct"
- `isolator_a`: Isolator rating (usually 1.5× motor current)
- `has_overload_relay`: true/false (look for OL symbol or "OL" text)
- `overload_setting_a`: Overload relay setting if shown

## CABLE MATERIAL DETECTION (v4.5)

Cables are usually copper (Cu) unless specified otherwise:

| Label | Material | Notes |
|-------|----------|-------|
| "Cu", "Copper", no label | **copper** | Default for most installations |
| "Al", "Aluminium", "Alu" | **aluminium** | Larger sizes (70mm²+), cheaper but larger |

**Note**: Aluminium cables require 1.6× larger cross-section for same current capacity.

## PHASE BALANCING EXTRACTION (v4.5)

Look for phase designations on circuits:
- **R, W, B** = Red, White, Blue (SA convention)
- **L1, L2, L3** = Alternative phase naming
- **R1, W1, B1, R2, W2, B2** = Circuit allocation pattern

Extract the `phase` field for each circuit to enable load balancing validation.

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

## HEAVY EQUIPMENT IDENTIFICATION (v4.5 Enhanced)

When you see circuits for equipment, extract as `heavy_equipment`:

### Pumps & Motors
| Equipment Type | Look For | type value | Default has_vsd |
|----------------|----------|------------|-----------------|
| Pool Pump | "POOL PUMP", PP1-PP4 | pool_pump | true |
| Heat Pump | "HEAT PUMP", HP1-HP5 | heat_pump | true |
| Circulation Pump | "CIRC PUMP", CP1 | circulation_pump | true |
| Borehole Pump | "BH PUMP", "BOREHOLE" | borehole_pump | false |
| Fire Pump | "FIRE PUMP", FP1 | fire_pump | false |
| Sump Pump | "SUMP", "SUMPPUMP" | sump_pump | false |

### HVAC & Ventilation
| Equipment Type | Look For | type value |
|----------------|----------|------------|
| HVAC System | "HVAC", large kW (>18kW) | hvac |
| Air Conditioning | "A/C", "AC", "AIRCON" | air_con |
| Ventilation Fan | "VENT FAN", "EXTRACTOR" | ventilation_fan |

### Water Heating
| Equipment Type | Look For | type value |
|----------------|----------|------------|
| Geyser | "GEYSER", G1-G5, "50L", "100L" | geyser |
| Solar Geyser | "SOLAR GEYSER" | solar_geyser |
| Heat Pump Geyser | "HP GEYSER" | heat_pump_geyser |

### Power Systems (v4.5 NEW)
| Equipment Type | Look For | type value |
|----------------|----------|------------|
| Generator | "GEN", "GENERATOR", "GENSET" | generator |
| UPS | "UPS", "UNINTERRUPTIBLE" | ups |
| Solar Inverter | "SOLAR INV", "PV INVERTER" | solar_inverter |
| Battery Storage | "BATTERY", "ESS" | battery_storage |

### Metering (v4.5 NEW)
| Equipment Type | Look For | type value |
|----------------|----------|------------|
| Energy Meter | "METER", "kWh METER" | meter |
| Prepaid Meter | "PREPAID" | prepaid_meter |
| CT Meter | "CT METER" | ct_meter |

### Access & Security (v4.5 NEW)
| Equipment Type | Look For | type value |
|----------------|----------|------------|
| Gate Motor | "GATE MOTOR", "GATE" | gate_motor |
| Garage Motor | "GARAGE" | garage_motor |
| Security System | "SECURITY", "ALARM" | security_system |
| CCTV | "CCTV", "CAMERAS" | cctv |

### Fire Systems (v4.5 NEW)
| Equipment Type | Look For | type value |
|----------------|----------|------------|
| Fire Panel | "FIRE PANEL", "FA PANEL" | fire_panel |

### Transport (v4.5 NEW)
| Equipment Type | Look For | type value |
|----------------|----------|------------|
| Lift | "LIFT", "ELEVATOR" | lift |
| Escalator | "ESCALATOR" | escalator |

### EV Charging (v4.5 NEW)
| Equipment Type | Look For | type value |
|----------------|----------|------------|
| EV Charger | "EV CHARGER", "EVSE", "CHARGING" | ev_charger |

**For each heavy equipment item, extract:**
- `name`: Descriptive name (e.g., "Pool Pump 1", "Main Generator")
- `type`: Equipment type from tables above
- `rating_kw`: Power rating in kW
- `rating_kva`: For transformers/UPS/generators - kVA rating
- `has_vsd`: true/false (for pump circuits)
- `starter_type`: "vsd", "dol", "star_delta", "soft_starter", "contactor", "direct"
- `has_overload_relay`: true/false (look for OL symbol)
- `isolator_a`: Isolator rating in Amps
- `breaker_a`: Breaker rating
- `breaker_type`: "mcb", "mccb", "acb"
- `circuit_ref`: Circuit ID (e.g., "PP1", "HP3", "GEN1")
- `fed_from_db`: Parent DB name (e.g., "DB-PPS1")
- `cable_size_mm2`: Cable size
- `cable_type`: Cable type (e.g., "PVC SWA PVC")
- `cable_material`: "copper" or "aluminium"
- `status`: "existing", "new", "proposed"

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

## v4.5 ADDITIONAL REMINDERS

11. **Breaker type**: MCB vs MCCB is CRITICAL for pricing (MCCB costs 5-10× more)
12. **Phase designation**: Extract R1/W1/B1 patterns for load balancing validation
13. **Cable material**: Note if aluminium (Al) - affects sizing and pricing
14. **Overload relays**: Look for "OL" on motor circuits
15. **System parameters**: Extract voltage, phases, frequency, fault level from title block
16. **Equipment status**: Mark "existing" vs "new" vs "proposed"
17. **Power sources**: Extract kVA rating for transformers, generators, UPS
"""


def get_sld_extraction_prompt(building_block: str = "") -> str:
    """Simplified accessor for SLD prompt without page objects."""
    return get_prompt([], building_block)
