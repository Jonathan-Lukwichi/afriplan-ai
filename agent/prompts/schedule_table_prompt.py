"""
AfriPlan Electrical v4.10 - Schedule Table Extraction Prompt

CRITICAL: This is a FOCUSED prompt that ONLY extracts circuit schedule data.
The circuit schedule table is the PRIMARY source of truth for:
- Number of circuits
- Point counts per circuit
- Cable sizes
- Breaker ratings
- Wattages

This prompt is used when the SLD has a schedule table at the bottom.
By focusing ONLY on the table (not the whole diagram), we get more accurate extraction.

v4.10 - SLD-First Strategy: Extract schedule tables FIRST, then cross-reference.
"""

SCHEDULE_TABLE_SCHEMA = """{
  "distribution_boards": [
    {
      "name": "DB-S2",
      "main_breaker_a": 63,
      "main_breaker_type": "mccb",
      "location": "Suite 2",
      "supply_from": "DB-GF",
      "supply_cable_size_mm2": 16,
      "supply_cable_cores": 4,
      "circuits": [
        {
          "id": "P1",
          "type": "power",
          "description": "General Power",
          "wattage_w": 3680,
          "wattage_formula": "",
          "cable_size_mm2": 2.5,
          "cable_cores": 3,
          "breaker_a": 20,
          "num_points": 4,
          "is_spare": false,
          "confidence": "extracted"
        }
      ],
      "spare_count": 2,
      "total_ways": 12,
      "confidence": "extracted"
    }
  ],
  "page_has_schedule_table": true,
  "db_count": 1
}"""


def get_schedule_table_prompt() -> str:
    """
    Generate a FOCUSED prompt that extracts ONLY the circuit schedule table.

    This prompt is designed to:
    1. Find the schedule table at the bottom of SLD pages
    2. Read EVERY column (circuit) in the table
    3. Extract precise values for each circuit
    4. Ignore everything else on the page (reduces noise/distraction)

    Returns:
        Complete prompt text for schedule table extraction
    """
    return f"""## TASK: EXTRACT CIRCUIT SCHEDULE TABLE

**CRITICAL INSTRUCTION**: Your ONLY task is to extract data from the CIRCUIT SCHEDULE TABLE.
Do NOT describe the diagram. Do NOT describe the page layout. ONLY extract table data.

## STEP 1: FIND THE SCHEDULE TABLE

Look at the BOTTOM of the image for a rectangular TABLE with grid lines.
This table typically has:
- 4-6 ROWS (Circuit No, Wattage, Wire Size, No Of Point, Breaker, etc.)
- Multiple COLUMNS (one per circuit - could be 6, 8, 12, 18, or 24 columns)

The table looks like this in the drawing:

```
┌────────────┬───────┬───────┬───────┬───────┬───────┬───────┬───────┐
│ CIRCUIT NO │  P1   │  P2   │  P3   │  L1   │  L2   │  AC1  │ SPARE │
├────────────┼───────┼───────┼───────┼───────┼───────┼───────┼───────┤
│  WATTAGE   │ 3680W │ 3680W │ 3680W │ 198W  │  54W  │ 1650W │   -   │
├────────────┼───────┼───────┼───────┼───────┼───────┼───────┼───────┤
│ WIRE SIZE  │ 2.5mm²│ 2.5mm²│ 2.5mm²│ 1.5mm²│ 1.5mm²│ 2.5mm²│   -   │
├────────────┼───────┼───────┼───────┼───────┼───────┼───────┼───────┤
│NO OF POINT │   4   │   3   │   2   │   8   │   6   │   1   │   -   │
├────────────┼───────┼───────┼───────┼───────┼───────┼───────┼───────┤
│  BREAKER   │  20A  │  20A  │  20A  │  10A  │  10A  │  20A  │   -   │
└────────────┴───────┴───────┴───────┴───────┴───────┴───────┴───────┘
```

## STEP 2: FIND THE DB NAME

Look for the DB designation. It's usually found:
- In the title block (bottom right corner)
- Above the schedule table
- In the drawing title (e.g., "DB-S2 SINGLE LINE DIAGRAM")

Common DB name patterns:
- DB-S1, DB-S2, DB-S3, DB-S4 (Suite DBs)
- DB-GF (Ground Floor)
- DB-FF (First Floor)
- DB-CA (Common Area)
- DB-1, DB-2 (Numbered DBs)

## STEP 3: COUNT ALL CIRCUIT COLUMNS

**IMPORTANT**: Count EVERY column in the schedule table.
- A 12-way DB has 12 circuit columns
- A 24-way DB has 24 circuit columns
- Some columns may be marked "SPARE" - include these too!

## STEP 4: READ EACH CELL

For EACH circuit column, read these values:

| Row Label | What to Extract | Example Values |
|-----------|-----------------|----------------|
| CIRCUIT NO | Circuit ID | P1, P2, L1, L2, AC1, SPARE |
| WATTAGE | Power in Watts | 3680W, 198W, 5x48W |
| WIRE SIZE | Cable in mm² | 1.5mm², 2.5mm², 4mm² |
| NO OF POINT | Point count | 4, 8, 10, 1 |
| BREAKER | Rating in Amps | 10A, 16A, 20A, 32A |

## STEP 5: FIND THE MAIN BREAKER

Look at the TOP of the single-line diagram for:
- Main breaker rating (e.g., "100A", "63A", "250A")
- Main breaker type ("MCCB" for 100A+, "MCB" for 63A and below)

## STEP 6: FIND SUPPLY INFO

Look for text near the incoming supply line:
- "SUPPLY FROM: DB-GF" or "FED FROM: MSB"
- Cable specification like "4Cx16mm² PVC SWA PVC"

## MULTIPLE DBs PER PAGE

Some pages show 2 or 3 DBs. If you see MULTIPLE schedule tables:
- Extract EACH DB separately
- Each table belongs to a different DB
- Look for different DB names for each table

## JSON OUTPUT FORMAT

Respond with ONLY valid JSON (no markdown, no explanation):

{SCHEDULE_TABLE_SCHEMA}

## CRITICAL REMINDERS

1. **VISUALLY SCAN** the table image - data is in GRAPHICS, not searchable text
2. **COUNT ALL COLUMNS** - don't skip any circuit columns
3. **INCLUDE SPARE** circuits - they count as spare_count
4. **EXACT DB NAME** - use the exact name from the drawing (e.g., "DB-S2" not "DB S2")
5. **If no schedule table found** - set page_has_schedule_table: false
6. **DO NOT FABRICATE** - if you can't read a value, use "estimated" confidence
7. **The "NO OF POINT" row is CRITICAL** - this is the official fixture count
"""


def get_quick_db_detection_prompt() -> str:
    """
    Generate a quick prompt to detect if a page contains SLD schedule data.
    Used to filter pages before full extraction.

    Returns:
        Quick detection prompt
    """
    return """## QUICK CHECK: Does this page have a circuit schedule table?

Look for a TABLE at the bottom of the page with rows like:
- CIRCUIT NO
- WATTAGE
- WIRE SIZE
- NO OF POINT
- BREAKER

And look for DB designations like:
- DB-S1, DB-S2, DB-S3, DB-S4
- DB-GF, DB-FF
- DB-CA

Respond with ONLY this JSON (no explanation):
{
  "has_schedule_table": true,
  "db_names_found": ["DB-S2", "DB-S3"],
  "confidence": 0.95
}
"""
