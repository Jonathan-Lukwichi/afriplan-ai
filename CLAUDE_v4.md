# CLAUDE.md — AfriPlan Electrical v4.0

## Rules for Claude Code

1. All prices ZAR. All standards SANS 10142-1. Wire sizes mm². Never AWG.
2. Never hardcode API keys — use `os.environ["ANTHROPIC_API_KEY"]`.
3. Every Anthropic API call wrapped in try/except with fallback.
4. Pydantic models from `agent/models.py` are SINGLE SOURCE OF TRUTH — never define data shapes inline.
5. JSON parsing: always use `parse_json_safely()` from `agent/utils.py` (strips backticks, handles trailing commas).
6. Temperature=0 for all extraction/classification calls.
7. Max 30 total pages across all uploaded documents.
8. When uncertain, add to warnings list — never guess or hallucinate data.
9. Degrade gracefully — never crash. Partial results with warnings > crash.
10. Test with all 3 Wedela PDFs uploaded simultaneously.
11. Follow existing code style. Type hints on all functions.

---

## Core Objective

Upload one or more electrical drawing PDFs → AI extracts all data per building block → validate against SANS 10142-1 → generate professional Bill of Quantities → export quotation.

**Key v4.0 change:** The system handles **multi-document, multi-building projects**. The Wedela Recreational Club has 3 PDFs, 5 building blocks, 20 distribution boards, 2 separate Eskom supplies. AfriPlan v4.0 must handle this natively.

---

## Architecture: 6-Stage Hybrid Pipeline

```
INGEST (LOCAL) → CLASSIFY (LOCAL+Haiku) → DISCOVER (Sonnet) → VALIDATE (LOCAL) → PRICE (LOCAL) → OUTPUT (LOCAL)
```

Only DISCOVER uses the Anthropic API. Everything else runs locally.

### Model Strategy
- **Haiku 4.5** (`claude-haiku-4-5-20251001`): Classification only — $1/M input
- **Sonnet 4** (`claude-sonnet-4-20250514`): Primary extraction — $3/M input
- **Opus 4** (`claude-opus-4-20250514`): Escalation when confidence < 0.40 — $15/M input
- USD→ZAR conversion: ×18.50

---

## STAGE 1: INGEST (Local, Free)

### Input
One or more PDF files uploaded by user (Streamlit file_uploader with accept_multiple_files=True).

### Process
1. For each PDF:
   a. Open with PyMuPDF (`fitz`), limit 10 pages per PDF, 30 pages total across all PDFs.
   b. Convert each page to PNG at 200 DPI.
   c. Extract embedded text via `page.get_text()`.
   d. Read title block: drawing number, title, building block name.

2. **Page-type classification (keyword heuristics — no API)**:
   ```
   Text contains "DRAWING REGISTER" or "TRANSMITTAL" → REGISTER
   Text contains "Circuit No" + "Wattage" + "Wire Size"  → SLD
   Drawing number contains "-SLD" or "-SLD-"               → SLD
   Drawing number contains "-LIGHTING" or text "LIGHTS LAYOUT" → LAYOUT_LIGHTING
   Drawing number contains "-PLUG" or text "PLUGS LAYOUT"     → LAYOUT_PLUGS
   Drawing number contains "-OL-" or text "OUTSIDE LIGHTS"    → OUTSIDE_LIGHTS
   Text contains visible defects / damage descriptions         → PHOTO
   Otherwise                                                   → UNKNOWN
   ```

3. **Building block detection (from title block and drawing content)**:
   ```
   Title contains "ABLUTION RETAIL" or drawing "WD-AB-"      → "Ablution Retail Block"
   Title contains "COMMUNITY HALL" or drawing "WD-ECH-"      → "Existing Community Hall"
   Title contains "LARGE GUARD" or drawing "WD-LGH-"         → "Large Guard House"
   Title contains "SMALL GUARD" or drawing "WD-SGH-"         → "Small Guard House"
   Title contains "POOL" or drawing "WD-PB-"                 → "Pool Block"
   Title contains "KIOSK" or drawing "WD-KIOSK-"             → "Site Infrastructure"
   Title contains "OUTSIDE" or drawing "WD-OL-"              → "Site Infrastructure"
   Drawing "TJM-" prefix or "NEWMARK" in text                → "NewMark Office Building"
   Otherwise                                                  → "Unclassified"
   ```

4. Build `DocumentSet` with all pages typed and assigned to blocks.

### Output
`DocumentSet` with typed pages, each assigned to a building block.

---

## STAGE 2: CLASSIFY (Local + Haiku fallback)

### Process
1. Look at aggregated page types and building blocks:
   ```
   Has SLD pages?           → extraction_mode = AS_BUILT
   Has only layout pages?   → extraction_mode = ESTIMATION
   Has only photos?         → extraction_mode = INSPECTION
   Has SLDs for some blocks but not others? → extraction_mode = HYBRID
   ```

2. Determine tier from content:
   ```
   Multiple building blocks detected?          → MIXED
   Text contains "bedroom", "bathroom", "house" → RESIDENTIAL
   Text contains "office", "suite", "commercial" → COMMERCIAL
   Text contains "pool", "pump", "hall"          → COMMERCIAL or MIXED
   Text contains "COC", "defect", "inspection"   → MAINTENANCE
   ```

3. If confidence < 0.60, send first 2 pages to Haiku for classification.

### Output
`ServiceTier`, `ExtractionMode`, list of building blocks with their page assignments.

---

## STAGE 3: DISCOVER (Sonnet API — the expensive stage)

This is where data extraction happens. The key design decision: **send page-type-specific prompts per building block**.

### Process

#### Step 1: Group pages
```python
page_groups = {}
for page in document_set.all_pages:
    key = (page.building_block, page.page_type)
    page_groups.setdefault(key, []).append(page)
```

#### Step 2: Send targeted API calls

Each call gets a specialized prompt + the relevant page images + the JSON schema to fill.

| Page Type | Prompt | Schema Output |
|-----------|--------|---------------|
| REGISTER | `register_prompt` | `ProjectMetadata` |
| SLD | `sld_prompt` | `List[DistributionBoard]` with full circuit schedules |
| LAYOUT_LIGHTING | `lighting_layout_prompt` | `List[Room]` with light fixtures + circuit refs |
| LAYOUT_PLUGS | `plugs_layout_prompt` | `List[Room]` with sockets/switches + circuit refs |
| OUTSIDE_LIGHTS | `outside_lights_prompt` | `List[SiteCableRun]` + `FixtureCounts` + cable distances |

**CRITICAL: SLD extraction prompt must instruct Claude to read BOTH:**
1. The circuit **diagram** (single-line drawing showing breakers, cables, connections)
2. The circuit **schedule table** at the bottom (Circuit No, Wattage, Wire Size, No Of Point)

If there are multiple DBs on one SLD page (e.g. WD-PB-01-SLD has DB-CR top and DB-PFA bottom), extract ALL of them.

**CRITICAL: Layout extraction must capture the LEGEND first**, then use it to identify fixtures. Each building block may have different legend items. For example:
- NewMark: has data points, floor boxes, power skirting (others don't)
- Ablution: has vapor proof lights, geyser isolators (offices don't)
- Pool Block: has 200W flood lights, pole lights (others don't)
- Community Hall: has 50W fluorescent, master switches, waterproof sockets (others don't)

#### Step 3: Merge per-block results

For each building block:
1. Merge SLD extraction → `block.distribution_boards`
2. Merge lighting layout → rooms with light fixtures
3. Merge plugs layout → add socket/switch counts to same rooms
4. If a room appears on both lighting AND plugs pages, merge fixtures (don't duplicate)

Room matching logic:
```python
# Match by room name (case-insensitive, stripped)
lighting_rooms = {r.name.strip().lower(): r for r in lighting_extraction}
for plug_room in plugs_extraction:
    key = plug_room.name.strip().lower()
    if key in lighting_rooms:
        # Merge: add socket/switch counts to existing room
        existing = lighting_rooms[key]
        existing.fixtures.double_socket_300 += plug_room.fixtures.double_socket_300
        # ... etc for all socket/switch fields
        existing.circuit_refs.extend(plug_room.circuit_refs)
    else:
        # New room only on plugs layout
        block.rooms.append(plug_room)
```

#### Step 4: Build supply hierarchy

From SLD pages + outside lights drawing, reconstruct:
```
Supply Point (Eskom) → Kiosk → DB-CR → sub-boards → sub-sub-boards
```

Read `supply_from` on each DB and build the tree. Extract cable run lengths from the outside lights drawing where marked (e.g. "110m", "35m", "50m").

#### Step 5: Extract heavy equipment

From SLD pages, identify:
- Pool pumps (circuits with "PUMP" label, VSD drives)
- Heat pumps (circuits with "HEAT PUMP" label)
- HVAC systems (large wattage dedicated circuits, e.g. "60KW HVAC")
- Circulation pumps
- Geyser banks (multiple 50L isolator circuits)

Create `HeavyEquipment` objects for each.

#### Step 6: Calculate confidence

```python
confidence = 0.0
# JSON parsed successfully for all calls?
if all_json_parsed: confidence += 0.25
# Data completeness (non-null fields / expected fields)
confidence += 0.30 * completeness_ratio
# Cross-page consistency (circuit refs match between SLD and layouts)
confidence += 0.25 * cross_ref_score
# Multiple building blocks extracted?
confidence += 0.20 * min(1.0, blocks_with_data / blocks_detected)
```

If confidence < 0.40 for any building block, re-send that block's pages to Opus.

### Output
`ExtractionResult` with building blocks, supply hierarchy, site cable runs, all fixtures.

---

## STAGE 4: VALIDATE (Local Python, Free)

### SANS 10142-1 Rules

#### Hard Rules (auto-enforced)
| Rule | Check | Auto-Fix |
|------|-------|----------|
| Max lighting points | ≤10 per circuit | Split circuit, add breaker |
| Max power points | ≤10 per circuit | Split circuit, add breaker |
| Cable capacity | Cable ampacity ≥ breaker rating | Flag mismatch |
| ELCB mandatory | Every DB must have earth leakage | Add ELCB to BQ |
| Surge protection | Recommended on main DB | Add SPD to BQ |
| Spare ways | Min 15% spare on each DB | Suggest larger DB |
| Dedicated circuits | Stove=32A, Geyser=20A+timer, AC=20A+isolator | Flag if missing |
| Voltage drop | Max 5% total (2.5% sub-mains + 2.5% final) | Warning only |

#### Cable Capacity Table (for validation)
| Cable mm² | Max Amps (Enclosed) |
|-----------|---------------------|
| 1.5 | 14.5A |
| 2.5 | 20A |
| 4 | 27A |
| 6 | 35A |
| 10 | 48A |
| 16 | 64A |
| 25 | 84A |
| 35 | 104A |
| 50 | 126A |
| 70 | 159A |
| 95 | 193A |

#### Cross-Page Validation (v4.0 key feature)
For each building block:
1. For every circuit ref on a layout (e.g. "DB-S3 L1"), check it exists in the SLD extraction.
2. Compare point counts: SLD says "No Of Point = 8", layout shows 8 fixtures → MATCH.
3. Compare wattages: SLD says "384W", layout has 8×48W = 384W → MATCH.
4. Flag conflicts and unmatched refs.
5. Build `CrossReferenceResult`.

#### Cross-Block Validation
1. Every sub-board feed in a parent DB must have a corresponding child DB extracted.
2. Cable sizes on sub-board feeds must match the incoming cable on the child DB.
3. Total wattage downstream of a breaker should not exceed breaker capacity.

### Output
`ValidationResult` with flags, cross-references, compliance score.

---

## STAGE 5: PRICE (Local Python, Free)

### Pricing Logic

The pricing engine operates per building block, then aggregates.

#### A — Supply Infrastructure
For each `SupplyPoint`:
- Kiosk metering panel
- Main breaker (MCCB if ≥100A)
- Cable from supply to first DB (use actual length from `site_cable_runs`)

#### B — Distribution Boards
For each `DistributionBoard`:
- DB enclosure (sized by total_ways: 4-way, 8-way, 12-way, 18-way, 24-way, 36-way)
- Main breaker/MCCB
- Earth leakage device (if present or auto-added)
- Surge protection device (if present or auto-added)
- DIN rail, busbar, neutral bar, earth bar
- DB label and circuit chart

#### C — Cables & Wiring
For each `Circuit`:
- Cable: size × cores × estimated length
- Cable length estimation (when not on drawing):
  ```
  Main DB → Sub DB (same floor): 15m
  Main DB → Sub DB (different floor): 25m
  DB → Furthest point in room: 12m
  DB → Average circuit: 8m
  Kiosk → Main DB: use actual distance from site_cable_runs
  ```
- **KEY RULE:** If SLD specifies cable size (e.g. "4Cx4mm² PVC SWA PVC"), price THAT cable. Don't re-estimate.

For each `SiteCableRun`:
- Price exact cable spec × exact length from drawing
- Add trenching cost per meter if underground

#### D — Cable Containment
For each `CableContainment`:
- Trunking / cable tray / wire mesh at estimated length × unit rate
- Fittings (bends, tees, risers) at 20% of straight run cost

#### E — Light Fittings
For each room's fixture counts, price per type:
| Fixture | Unit Price (ZAR) |
|---------|------------------|
| 600×1200 Recessed LED 3×18W | R650 |
| 18W LED Surface Mount | R280 |
| 30W LED Flood Light | R450 |
| 200W LED Flood Light | R2,800 |
| 6W LED Downlight | R180 |
| 2×24W Vapor Proof LED | R580 |
| 2×18W Vapor Proof | R480 |
| 2×18W Prismatic LED | R420 |
| 26W Bulkhead Outdoor | R350 |
| 24W Bulkhead Outdoor | R320 |
| 50W 5ft Fluorescent | R280 |
| Outdoor Pole Light 2300mm 60W | R4,500 (incl. pole + base) |

#### F — Sockets & Switches
| Item | Unit Price (ZAR) |
|------|------------------|
| 16A Double Socket @300mm | R160 |
| 16A Single Socket @300mm | R120 |
| 16A Double Socket @1100mm | R185 |
| 16A Single Socket @1100mm | R145 |
| 16A Double Waterproof | R280 |
| 16A Double Ceiling Socket | R220 |
| CAT 6 Data Point | R170 |
| Floor Box (complete) | R850 |
| 1-Lever 1-Way Switch | R60 |
| 2-Lever 1-Way Switch | R95 |
| 1-Lever 2-Way Switch | R75 |
| Day/Night Switch | R350 |
| 30A Isolator Switch | R280 |
| 20A Isolator Switch | R185 |
| Master Switch | R450 |

#### G — Heavy Equipment
For each `HeavyEquipment`:
| Equipment | Unit Price (ZAR) |
|-----------|------------------|
| Pool Pump + VSD | R12,500 |
| Pool Pump (DOL) | R6,800 |
| Heat Pump 12.5kW | R18,000 |
| Circulation Pump | R4,500 |
| HVAC connection (per kW) | R650 |
| 50L Geyser (supply + install) | R3,200 |
| 100L Geyser | R4,500 |
| 150L Geyser | R6,800 |
| 200L Geyser | R8,500 |
| AC Unit connection (isolator + cable) | R2,200 |

#### H — Dedicated Circuits
Price any dedicated circuit not already covered by equipment:
- Stove 3-phase: R3,800
- Stove single-phase: R2,800
- Geyser (20A + timer): R2,600
- Gate motor: R1,800
- Pool pump circuit (cable only): R2,400

#### I — Compliance Additions
Items added by validation auto-corrections:
- ELCB addition: R1,450
- SPD addition: R850
- DB upsizing: price difference between current and recommended size
- Missing earth: R1,200 per DB

#### J — Site Works & Trenching
For each underground `SiteCableRun`:
- Trenching: R180/m (600mm deep, backfill, compaction)
- Sand bed: R45/m
- Warning tape: R15/m
- Cable markers: R120 each (every 25m)

For `UndergroundSleeve`:
- 50mm sleeve: R85/m
- 75mm sleeve: R120/m
- 110mm sleeve: R165/m

Pole light foundations: R2,800 each.

#### K — Labour
| Item | Rate (ZAR) |
|------|-----------|
| Per circuit installed | R450 |
| Per point (socket/switch/light) | R85 |
| Per DB installed and wired | R1,500 |
| Per heavy equipment connection | R2,500 |
| Per site cable run (per 10m) | R650 |
| Testing and commissioning (per DB) | R800 |
| COC certification (per supply) | R3,500 |

#### L — Provisional Sums
- Sundries (cable clips, screws, consumables): 5% of materials
- Transport: R5,000 (within 50km), R8,000 (50-100km)
- Builder's work (chasing, making good): 3% of materials

#### Final Calculations
```
Subtotal = Sum(A through L)
Contingency = Subtotal × contingency_pct (default 5%)
Margin = (Subtotal + Contingency) × margin_pct (default 20%)
Total Excl VAT = Subtotal + Contingency + Margin
VAT = Total Excl VAT × 15%
Total Incl VAT = Total Excl VAT + VAT
```

Payment schedule:
- Standard: 40% / 40% / 20%
- Conservative: 50% / 30% / 20%
- Progress: 30% / 30% / 30% / 10%

### Output
`PricingResult` with line items grouped by `BQSection`, block summaries, totals.

---

## STAGE 6: OUTPUT (Local, Free)

### Process
1. Assemble `PipelineResult` from all stage outputs.
2. Calculate overall confidence (weighted average):
   ```
   CLASSIFY: 10% weight
   DISCOVER: 50% weight
   VALIDATE: 25% weight
   PRICE: 15% weight
   ```
3. Sum tokens and cost across all API calls.
4. Compile all warnings and errors.

### Output
Complete `PipelineResult` ready for UI display and export.

---

## Error Handling Strategy

| Stage | Error | Response |
|-------|-------|----------|
| INGEST | Corrupt PDF | Stop pipeline, friendly error: "Could not read PDF. Please check the file." |
| INGEST | Too many pages | Stop: "Maximum 30 pages. Please split into smaller documents." |
| CLASSIFY | API timeout | Fall back to keyword heuristics, default COMMERCIAL if ambiguous |
| DISCOVER | API error | Retry once with backoff. If fails, show empty extraction form for manual entry |
| DISCOVER | Low confidence on block | Re-send that block only to Opus. If still low, show with warnings |
| DISCOVER | JSON parse failure | Use `parse_json_safely()` which handles backticks, trailing commas. If still fails, return empty extraction with error |
| VALIDATE | Rule error | Skip that rule, warn "validation rule X unavailable" |
| PRICE | Missing data for item | Price what we have, flag missing items as "TBD — awaiting data" |
| OUTPUT | Export error | Show data in-app, offer copy-to-clipboard |

**Golden rule: Never crash. Partial data with warnings is always better than a blank screen.**

---

## Project Structure

```
afriplan-ai/
├── CLAUDE.md                           # This blueprint
├── app.py                              # Streamlit entry point
├── requirements.txt
├── .env.example                        # ANTHROPIC_API_KEY=sk-ant-...
│
├── agent/                              # AI Pipeline Package
│   ├── __init__.py                     # Exports: AfriPlanAgent, all models
│   ├── models.py                       # ★ Pydantic data contract (v4.0)
│   ├── pipeline.py                     # 6-stage orchestrator
│   ├── utils.py                        # parse_json_safely(), encode_image(), track_cost()
│   ├── stages/
│   │   ├── __init__.py
│   │   ├── ingest.py                   # PDF→images, page classification, block detection
│   │   ├── classify.py                 # Tier + mode detection
│   │   ├── discover.py                 # Data extraction (API calls)
│   │   ├── validate.py                 # SANS 10142-1 rules + cross-ref
│   │   ├── price.py                    # BQ generation
│   │   └── output.py                   # Final assembly
│   └── prompts/
│       ├── __init__.py
│       ├── system_prompt.py            # SA electrical domain context
│       ├── classify_prompt.py
│       ├── register_prompt.py
│       ├── sld_prompt.py               # ★ MOST CRITICAL — reads DBs + circuit schedules
│       ├── lighting_layout_prompt.py
│       ├── plugs_layout_prompt.py
│       ├── outside_lights_prompt.py
│       ├── residential_prompt.py
│       ├── maintenance_prompt.py
│       └── schemas.py                  # JSON schema strings matching models.py
│
├── core/                               # Business Logic (no AI, no UI)
│   ├── __init__.py
│   ├── constants.py                    # Material databases & pricing
│   ├── calculations.py                 # Existing calc functions
│   ├── standards.py                    # SANS 10142-1 rule definitions
│   └── pricing_engine.py              # BQ calculation from extraction
│
├── exports/
│   ├── pdf_generator.py
│   ├── excel_exporter.py
│   └── eskom_forms.py
│
├── pages/
│   ├── 0_Welcome.py
│   ├── 1_Smart_Upload.py              # ★ Multi-file upload + pipeline UI
│   ├── 2_Residential.py
│   ├── 3_Commercial.py
│   └── 4_Maintenance.py
│
├── utils/
│   ├── styles.py
│   ├── components.py
│   └── optimizer.py
│
└── tests/
    ├── test_models.py
    ├── test_ingest.py
    ├── test_validation.py
    └── test_pricing.py
```

---

## Prompt Design: SLD Extraction (Most Critical)

The SLD prompt must handle these real-world variations:

### Single DB per page (e.g. WD-LGH-01-SLD)
Simple: one DB with circuit schedule at bottom.

### Multiple DBs per page (e.g. TJM-SLD-002 has DB-S1, DB-S2, DB-S3, DB-S4)
The prompt must say: "This page may contain MULTIPLE distribution boards. Extract ALL of them."

### Cascaded DBs with different levels (e.g. WD-PB-01-SLD page 3)
DB-CR (top) feeds DB-PFA (bottom) which feeds pump stations. Different schedule tables for each.

### Pump/heat pump station SLDs (e.g. WD-PB-01-SLD page 4)
Pool pumps and heat pumps with VSDs, DOL starters, specific cable types. Not standard circuit patterns.

### SLD prompt structure:
```
You are analyzing a Single Line Diagram (SLD) for a South African electrical installation.

STEP 1: Identify how many distribution boards appear on this page.
Look for:
- Board labels like "DB-xxx" followed by ratings (e.g. "400V, 200A, 15kA, 50Hz, 3PH+N+E")
- Circuit schedule tables (columns: Circuit No, Wattage, Wire Size, No Of Point)
- Each schedule table belongs to one DB

STEP 2: For EACH distribution board, extract:
- Board name, supply source (look for "Fed from..." labels)
- Incoming cable (look for "incoming main cable Xmm²" or cable annotations)
- Main breaker rating
- Earth leakage presence and rating
- All circuits from the schedule table
- Spare ways count

STEP 3: For each circuit in the schedule:
- Circuit ID (P1, L2, AC1, ISO3, etc.)
- Wattage (e.g. "3680W") and wattage formula if shown (e.g. "8x48W")
- Wire size (e.g. "2.5mm²", "1.5mm²")
- Number of points
- Type: classify based on ID prefix:
  P = power, L = lighting, AC = ac, ISO = isolator,
  DB-xx = sub_board_feed, SPARE = spare,
  PUMP = pump, HVAC = hvac

STEP 4: For sub-board feeds (circuits that feed other boards):
- Note which board they feed (from the label)
- Record the cable size and length if marked

STEP 5: For equipment feeds (pumps, heat pumps, HVAC):
- Extract equipment type, rating (kW), VSD presence
- Cable specification

Return ONLY valid JSON matching the schema below. No markdown, no backticks, no explanation.
```

---

## Prompt Design: Layout Extraction

### Lighting layout prompt:
```
You are analyzing a LIGHTING LAYOUT drawing for a South African electrical installation.

STEP 1: Read the LEGEND at the top of the drawing. It shows the symbol-to-fixture mapping.
Map each symbol to its description: recessed LED, surface mount, flood light, downlight,
vapor proof, prismatic, bulkhead, etc.

STEP 2: Identify each room/area on the drawing:
- Room name (written on drawing)
- Room number if shown
- Area in m² if shown
- Building block name (from title block, e.g. "ABLUTION RETAIL BLOCK")

STEP 3: For EACH room, count the light fixtures by type:
- Use the legend to identify what each symbol represents
- Count each type separately
- Record circuit reference labels (e.g. "DB-S3 L1", "DB-CA L3")

STEP 4: Identify distribution board locations marked on the layout.

STEP 5: Note any special items:
- Day/night switches (for external lighting)
- Fire hydrant positions
- Solar panel provisions

Return ONLY valid JSON. No markdown, no backticks, no explanation.
```

### Plugs layout prompt:
Similar structure but focused on sockets, switches, data points, isolators, AC positions.

### Outside lights prompt:
```
You are analyzing an OUTSIDE LIGHTS / SITE LAYOUT drawing.

STEP 1: Identify ALL cable runs between buildings/DBs.
Look for lines with distances marked (e.g. "110m", "35m", "50m").
Record: from → to, distance, cable specification if shown.

STEP 2: Identify all distribution board positions on the site plan.
Record: DB name, which building it's in, what feeds it.

STEP 3: Count external lighting fixtures:
- Pole lights (with height)
- Flood lights
- Landing lights
- Pathway lights

STEP 4: Note infrastructure items:
- Gates
- Fire hydrant positions
- Kiosk/mini-sub locations

Return ONLY valid JSON. No markdown, no backticks, no explanation.
```

---

## UI Design: Smart Upload Page

### Multi-file upload
```python
uploaded_files = st.file_uploader(
    "Upload electrical drawings (PDF)",
    type=["pdf"],
    accept_multiple_files=True,
    help="Upload one or more PDF files. SLDs, layouts, schedules."
)
```

### Pipeline progress
Show 6 stages as a horizontal progress bar. Each stage turns green on success, yellow on warning, red on failure.

### Results tabs (after pipeline completes)
1. **Overview** — Project name, building blocks detected, confidence, API cost
2. **Building Blocks** — Expandable sections per block:
   - Distribution boards with circuit tables
   - Rooms with fixture counts
   - Heavy equipment
3. **Validation** — Compliance flags, cross-reference results
4. **Bill of Quantities** — Grouped by BQ section, per-block subtotals, project totals
5. **Export** — PDF quotation, Excel BQ, Continue to detailed page

### Editable extraction
Every extracted value should be editable before pricing:
- Circuit wattages, cable sizes, breaker ratings
- Room fixture counts
- Cable run lengths
- Equipment quantities

This allows contractors to correct AI errors before generating the quotation.

---

## SA Electrical Reference Data

### Cable Types
| Type | Usage |
|------|-------|
| GP Wire (PVC/PVC) | Internal wiring in conduit |
| Surfix (flat twin + earth) | Surface wiring, residential |
| PVC SWA PVC | Underground/external armoured cable |
| XLPE SWA | High temperature applications |

### NRS 034 ADMD Values
| Dwelling Type | ADMD (kVA) | Supply (A) |
|---------------|------------|------------|
| RDP/Low cost | 1.5-2.0 | 20 |
| Standard house | 3.5-4.0 | 60 |
| Medium house | 5.0-6.0 | 60 |
| Large house | 8.0-10.0 | 80 |
| Luxury estate | 12.0-15.0 | 100 |

### Load Calculation (LED Era)
- Light point: 50W
- Plug point: 250W
- Diversity: 50% residential, 40% commercial
- Power factor: 0.85
- Supply: 230V (1Ø), 400V (3Ø)

---

## Test Strategy

### Test 1: Full Wedela Project (3 PDFs)
Upload all 3 PDFs simultaneously.
**Expected:**
- 5 building blocks detected
- ≥15 distribution boards extracted
- ≥30 rooms with fixtures
- Site cable runs with actual distances
- Heavy equipment (8 pool pumps, 9 heat pumps, HVAC)
- Cross-reference validation between SLD and layout pages
- Complete BQ with sections A-L

### Test 2: Single NewMark Office PDF
Upload just the NewMark PDF (7 pages).
**Expected:**
- 1 building block: "NewMark Office Building"
- 7 DBs (DB-GF, DB-CA, DB-S1-S4 + Kiosk)
- Rooms: Suites 1-4, Lounge, Foyer, Conference Room, Office
- Data points and floor boxes extracted

### Test 3: Residential floor plan (no SLD)
Upload a simple house floor plan.
**Expected:**
- Mode: ESTIMATION
- Rooms estimated from floor plan
- Fixtures estimated from room types
- DB sized from room count

### Test 4: Corrupt/empty file
Upload an invalid file.
**Expected:**
- Friendly error at INGEST stage
- No crash
