# CLAUDE.md — AfriPlan Electrical v4.1

## What This Tool Actually Is

AfriPlan is a **quantity take-off accelerator** for South African electrical contractors. It reads electrical drawings using AI, extracts a draft Bill of Quantities, and lets the contractor review, correct, and apply their own prices before generating a professional quotation document.

**What the AI does:** Counts fixtures, reads circuit data from SLDs, identifies cable types, and structures the BQ — saving 4-6 hours of manual work per project.

**What the contractor does:** Reviews the AI's counts, corrects errors, fills in their trade prices, adjusts for site conditions, and submits their quotation.

The value is in the quantity take-off, not the pricing. Every contractor buys from different suppliers at different rates. The tool gives them the structure and quantities — they add their numbers.

---

## Rules for Claude Code

1. All prices ZAR. All standards SANS 10142-1. Wire sizes mm². Never AWG.
2. Never hardcode API keys — use `os.environ["ANTHROPIC_API_KEY"]`.
3. Every API call wrapped in try/except with fallback.
4. Pydantic models from `agent/models.py` are SINGLE SOURCE OF TRUTH.
5. JSON parsing: always use `parse_json_safely()` from `agent/utils.py`.
6. Temperature=0 for all extraction calls.
7. Max 30 total pages across all uploaded documents.
8. When uncertain, mark item as `ItemConfidence.ESTIMATED` (shows red in UI) — never guess.
9. Degrade gracefully — partial results with warnings > crash.
10. Test with all 3 Wedela PDFs uploaded simultaneously.
11. The REVIEW stage is the main UI — make editing fast and obvious.

---

## Architecture: 7-Stage Pipeline

```
INGEST (LOCAL) → CLASSIFY (LOCAL+Haiku) → DISCOVER (Sonnet) → REVIEW (UI) → VALIDATE (LOCAL) → PRICE (LOCAL) → OUTPUT (LOCAL)
```

**REVIEW is the new stage.** After AI extraction, the contractor reviews and corrects everything before validation and pricing run. This is where the tool earns trust.

### Model Strategy
- **Haiku 4.5** (`claude-haiku-4-5-20251001`): Classification only — $1/M input
- **Sonnet 4** (`claude-sonnet-4-20250514`): Primary extraction — $3/M input
- **Opus 4** (`claude-opus-4-20250514`): Escalation when confidence < 0.40 — $15/M input
- USD→ZAR: ×18.50

---

## STAGE 1: INGEST (Local, Free)

Same as v4.0. Multi-PDF upload, PyMuPDF conversion, page classification by keyword, building block detection from title blocks and drawing numbers.

Input: Streamlit multi-file upload (accept_multiple_files=True).
Output: `DocumentSet` with typed pages assigned to building blocks.

### Page Classification (keyword heuristics)
```
Drawing number contains "-SLD"           → SLD (0.95)
Drawing number contains "-LIGHTING"      → LAYOUT_LIGHTING (0.95)
Drawing number contains "-PLUG"          → LAYOUT_PLUGS (0.95)
Drawing number contains "-OL-"           → OUTSIDE_LIGHTS (0.90)
Text contains "DRAWING REGISTER"         → REGISTER (0.90)
Text contains "Circuit No" + "Wattage"   → SLD (0.85)
Otherwise                                → UNKNOWN (0.30)
```

### Building Block Detection
```
"WD-AB-" or "ABLUTION RETAIL"  → "Ablution Retail Block"
"WD-ECH-" or "COMMUNITY HALL"  → "Existing Community Hall"
"WD-LGH-" or "LARGE GUARD"     → "Large Guard House"
"WD-SGH-" or "SMALL GUARD"     → "Small Guard House"
"WD-PB-" or "POOL"             → "Pool Block"
"WD-OL-" or "OUTSIDE"          → "Site Infrastructure"
"TJM-" or "NEWMARK"            → "NewMark Office Building"
```

---

## STAGE 2: CLASSIFY (Local + Haiku fallback)

Same as v4.0. Determine ServiceTier and ExtractionMode from page types.

---

## STAGE 3: DISCOVER (Sonnet API)

Same extraction logic as v4.0, but with one critical addition: **every extracted item gets an `ItemConfidence` flag**.

### Confidence Flagging Rules
```
EXTRACTED (green):  Value read directly from drawing text/schedule
                    Examples: circuit wattage from SLD table, cable size from SLD,
                    DB name from label, cable run distance marked on drawing

INFERRED (yellow):  Calculated from related data, not directly on drawing
                    Examples: total wattage = count × per-unit wattage,
                    cable length estimated from room position,
                    fixture type inferred from symbol without legend match

ESTIMATED (red):    Default/guessed, needs contractor review
                    Examples: cable run length when not on drawing (using 8m/12m defaults),
                    room area when not marked, fixture count in crowded area,
                    containment lengths
```

The DISCOVER stage MUST set confidence on every Circuit, DistributionBoard, Room, HeavyEquipment, SiteCableRun, and CableContainment.

### Prompt Design
Same as v4.0 — page-type-specific prompts per building block. See v4.0 CLAUDE.md for SLD prompt, lighting layout prompt, plugs layout prompt, and outside lights prompt.

Addition to each prompt:
```
For each item you extract, indicate your confidence:
- "extracted": you can read this value directly from the drawing
- "inferred": you calculated this from other data on the drawing
- "estimated": you are guessing or using a default value

Be honest about confidence. It is better to mark something "estimated" than to guess wrong.
```

---

## STAGE 4: REVIEW (Streamlit UI — THE MAIN SCREEN)

This is the critical new stage. After DISCOVER completes, the contractor lands on a **full-screen review interface** where every extracted value is editable.

### UI Design

#### Layout: Two-panel
- **Left panel (60%):** Extracted data organized by building block, expandable sections
- **Right panel (40%):** Original drawing page (zoomable image) for reference

#### Confidence colour coding
Every editable field has a background colour:
- 🟢 Green (`EXTRACTED`): AI read this from the drawing — likely correct
- 🟡 Yellow (`INFERRED`): AI calculated this — verify
- 🔴 Red (`ESTIMATED`): AI guessed — contractor must check
- 🔵 Blue (`MANUAL`): Contractor has edited this value

#### Editable sections per building block

**1. Distribution Boards** — shown as expandable cards:
```
📦 DB-PFA (Pool Facility) — 200A, Fed from DB-CR
├── Circuit schedule (st.data_editor — editable table)
│   ID | Type | Description | Wattage | Cable | Breaker | Points | Confidence
│   L1 | lighting | "..." | 384W | 1.5mm² | 10A | 8 | 🟢
│   P1 | power | "..." | 3680W | 2.5mm² | 20A | 10 | 🟢
│   ISO1 | pump | "..." | 5000W | 4mm² | 32A | 1 | 🟡
│
├── Sub-board feeds
│   → DB-PPS1 (Pool Pumps 1): 35mm² 4C, 100A [🟢]
│   → DB-HPS1 (Heat Pumps 1): 50mm² 4C, 150A [🟢]
│
└── Board details: Main=200A, ELCB=63A, Spares=3
```

**2. Rooms** — expandable per room:
```
🏠 Male Changing Room (68m²) — Pool Block
├── Lights: 4× Vapor Proof 2×18W [🟢], 2× Bulkhead 26W [🟡]
├── Sockets: 3× Double @300mm [🟢], 1× Single @1100mm [🟢]
├── Switches: 2× 1-Lever 1-Way [🟢]
├── Equipment: 1× AC Unit [🟢]
└── Circuit refs: DB-PFA L3, DB-PFA P2
```

Each fixture count is a `st.number_input` with +/- buttons. Changing a value:
1. Turns the field blue (MANUAL)
2. Logs a CorrectionEntry (old value, new value, field path)

**3. Heavy Equipment** — editable table:
```
Name | Type | Rating | Cable | VSD? | Fed from | Qty | Confidence
Pool Pump 1 | pool_pump | 5kW | 4mm² SWA | Yes | DB-PPS1 | 1 | 🟢
Heat Pump 3 | heat_pump | 12.5kW | 4mm² SWA | No | DB-HPS1 | 1 | 🟢
```

**4. Site Cable Runs** — editable table:
```
From | To | Cable | Length(m) | Underground? | Confidence
Kiosk | DB-CR | 95mm² 4C SWA | 110 | Yes | 🟢 (marked on drawing)
DB-CR | DB-PFA | 70mm² 4C SWA | 60 | Yes | 🟢
DB-GF | DB-S1 | 16mm² 3C | 15 | No | 🔴 (estimated — no distance on drawing)
```

**5. Add Missing Items** — button at bottom of each section:
"+ Add room", "+ Add DB", "+ Add equipment", "+ Add cable run"

#### Review completion
Bottom of the review screen:
```
[Summary bar]
Total items: 287
AI extracted: 241 (green)
Calculated: 28 (yellow)
Estimated: 18 (red) ← these need your attention
Corrected by you: 5 (blue)

[✅ I've reviewed the extraction — proceed to validation and pricing]
```

The "proceed" button sets `extraction.review_completed = True` and triggers VALIDATE + PRICE.

#### Correction logging
Every edit creates a `CorrectionEntry`:
```python
CorrectionEntry(
    field_path="blocks.Pool Block.rooms.Male Changing.fixtures.vapor_proof_2x18w",
    original_value=3,
    corrected_value=4,
    item_type="fixture_count",
    building_block="Pool Block",
    page_source="WD-PB-01-LIGHTING",
    timestamp="2026-02-16T22:00:00Z"
)
```

After submission, the CorrectionLog shows accuracy:
"AI extracted 241 items. You corrected 5 (97.9% accuracy)."

This data is stored (with contractor consent) to improve future extractions.

---

## STAGE 5: VALIDATE (Local, Free)

Same as v4.0. SANS 10142-1 rules + cross-reference validation.

Runs AFTER the contractor has reviewed and corrected the extraction. This means validation runs on **contractor-approved data**, not raw AI output. Much more reliable.

---

## STAGE 6: PRICE (Local, Free)

### Key Change: DUAL OUTPUT

The pricing stage generates TWO BQs:

#### 1. Quantity BQ (Primary — THE deliverable)
A structured BQ with all items, descriptions, quantities, and units — but **unit_price = 0.0 and total = 0.0** for every line. The contractor opens this in Excel and fills in their own prices.

```
Item | Section | Description | Unit | Qty | Unit Price (R) | Total (R)
1 | E - Light Fittings | 600×1200 Recessed LED 3×18W | each | 47 | | =E1*F1
2 | E - Light Fittings | 2×24W Vapor Proof LED (IP65) | each | 12 | | =E2*F2
3 | F - Sockets | 16A Double Switched @300mm | each | 38 | | =E3*F3
...
```

The Excel file has:
- Column E (Qty) = filled by AI, reviewed by contractor
- Column F (Unit Price) = EMPTY, contractor fills in
- Column G (Total) = FORMULA: =E×F
- Subtotals per section = SUM formulas
- Grand total, contingency, markup, VAT = formulas referencing contractor's input cells

This is how every electrical contractor in SA works. They receive a BQ structure, fill in rates, submit.

#### 2. Estimated BQ (Secondary — ballpark reference)
Same items but with default prices filled in from our pricing tables. Clearly labelled:

```
⚠️ ESTIMATED PRICING — FOR REFERENCE ONLY
These prices are generic estimates. Replace with your actual supplier quotes.
Last updated: February 2026

Item | Description | Qty | Est. Unit Price | Est. Total
...
ESTIMATED TOTAL (incl. VAT): R 847,000
```

Purpose: helps the contractor decide whether to pursue the project before investing time in pricing. If the estimate is R800k but the client's budget is R200k, they know immediately.

### Pricing with Site Conditions

Before generating the estimated BQ, the system applies `SiteConditions` multipliers:

```python
labour_items_total *= site_conditions.labour_multiplier
# e.g. renovation (×1.30) + difficult access (×1.20) + scaffolding (×1.15) = ×1.794

trenching_items_total *= site_conditions.trenching_multiplier
# e.g. hard clay = ×1.40

transport_cost = site_conditions.transport_cost_zar
```

### Pricing with Contractor Profile

If the contractor has a saved profile:
```python
# Use contractor's custom prices where available
for item in bq_items:
    if item.description in contractor_profile.custom_prices:
        item.unit_price_zar = contractor_profile.custom_prices[item.description]
    else:
        item.unit_price_zar = default_price_lookup(item)

# Apply contractor's markup
markup = contractor_profile.markup_pct / 100
```

### Default Pricing Tables

Same as v4.0 (see v4.0 CLAUDE.md for complete fixture, cable, equipment, and labour price tables). These are defaults only — the estimated BQ labels them clearly as estimates.

---

## STAGE 7: OUTPUT (Local, Free)

### Deliverables

#### 1. Excel BQ (Primary — .xlsx)
Professional spreadsheet with:
- Cover sheet (project name, client, contractor details, date)
- Quantity BQ worksheet (items grouped by section A-L, formulas ready)
- Estimated BQ worksheet (with default prices — labelled "ESTIMATE")
- Summary worksheet (per-block subtotals, grand total with formulas)
- Notes worksheet (extraction warnings, assumptions, site conditions applied)

The Excel file uses `openpyxl` with formatting:
- Section headers in bold with background colour
- Confidence column (green/yellow/red cell backgrounds)
- Locked formula cells (contractor can't accidentally break totals)
- Unlocked price cells (contractor fills these in)
- Print area set for A4 portrait

#### 2. PDF Summary (Secondary)
One-page project summary:
- Project name, client, consultant
- Building blocks with DB counts and room counts
- Estimated total range (e.g. "R700k - R950k")
- Confidence score
- Key warnings
- "Full BQ available in Excel workbook"

#### 3. Correction Report (Internal)
If corrections were made:
- Accuracy percentage
- List of corrections by type
- Patterns (e.g. "AI consistently undercounts downlights in ablution areas")

---

## UI Flow: The Complete User Journey

### Step 1: Setup (first time only)
```
[Contractor Profile Setup]
Company name: ____________
ECSA/CIDB number: ____________
Default markup: ____%
Labour rates:
  Electrician daily: R____
  Assistant daily: R____
  Team size: __ electricians + __ assistants
Preferred supplier: [Voltex ▼]
[Save Profile]
```
Stored in Streamlit session state / local JSON.

### Step 2: Upload
```
[Upload Electrical Drawings]
📎 Drag PDFs here or browse
  ✅ NewMark_Offices_Electrical.pdf (7 pages)
  ✅ Wedela_Lighting_Plugs_260525.pdf (10 pages)
  ✅ Wedela_SLD_260525.pdf (8 pages)

[🚀 Extract Quantities]
```

### Step 3: AI Processing (30-60 seconds)
```
[Progress bar: INGEST → CLASSIFY → DISCOVER]
 ████████████░░░░░░░░ DISCOVER: Extracting Pool Block SLD...

 Found: 5 building blocks, 20 distribution boards, 157 circuits
 API cost: R4.20
```

### Step 4: Review (THE MAIN SCREEN — contractor spends 10-30 min here)
```
[Two-panel view: extraction data (left) | drawing page (right)]

🏗️ Wedela Recreational Club — 5 Building Blocks

[Building block tabs: NewMark | Ablution | Community Hall | Guard Houses | Pool]

[Selected: Pool Block]
├── 📦 DB-PFA (200A, 3PH) — 7 lighting, 5 power, 7 isolator circuits
├── 📦 DB-PPS1 (100A) — 4 pool pumps with VSD
├── 📦 DB-PPS2 (100A) — 4 pool pumps with VSD
├── 📦 DB-HPS1 (150A) — 5 heat pumps 12.5kW
├── 📦 DB-HPS2 (100A) — 4 heat pumps 12.5kW
│
├── 🏊 Training Pool Area (710m²) — 4 fixtures [🟢🟢🟡🔴]
├── 🏊 Children's Pool (153m²) — 3 fixtures
├── 🚿 Male Changing (68m²) — 8 fixtures
├── 🚿 Female Changing (67m²) — 8 fixtures
...

[Summary: 287 items | 241 🟢 | 28 🟡 | 18 🔴 | 0 🔵]

[✅ Review Complete — Generate BQ]
```

### Step 5: Site Conditions (quick form — 2 minutes)
```
[Site Conditions]
Project type: ○ New build  ● Renovation  ○ Maintenance
Access: ○ Easy  ● Normal  ○ Difficult  ○ Restricted
Scaffolding needed: ○ Yes  ● No
Soil for trenching: ○ Soft  ● Normal  ○ Hard clay  ○ Rock
Distance from your base: [35] km
Is this a rush job: ○ Yes  ● No

Labour multiplier: ×1.30 (renovation)
Trenching multiplier: ×1.00 (normal soil)
Transport: R5,000

[Apply & Generate BQ]
```

### Step 6: Results
```
[Tabs: Quantity BQ | Estimated BQ | Validation | Export]

[Quantity BQ tab]
Section A - Supply Infrastructure: 3 items
Section B - Distribution Boards: 20 items
Section C - Cables & Wiring: 45 items
...
Total items: 187

[Estimated BQ tab]
⚠️ ESTIMATE ONLY — Replace with your supplier prices
Estimated total (incl. VAT): R 847,000
Range: R 720,000 — R 975,000

[Export tab]
📥 Download Excel BQ (.xlsx) — includes quantity + estimated sheets
📥 Download PDF Summary (.pdf)
📥 Download Full Package (.zip) — Excel + PDF + drawings reference
```

---

## Project Structure

```
afriplan-ai/
├── CLAUDE.md
├── app.py
├── requirements.txt
├── .env.example
│
├── agent/
│   ├── __init__.py
│   ├── models.py                  ★ v4.1 — ContractorProfile, SiteConditions, CorrectionLog, dual BQ
│   ├── pipeline.py                7-stage orchestrator
│   ├── utils.py                   parse_json_safely(), encode_image(), cost tracking
│   ├── stages/
│   │   ├── __init__.py
│   │   ├── ingest.py              PDF → images, page classification
│   │   ├── classify.py            Tier + mode detection
│   │   ├── discover.py            AI extraction (API calls)
│   │   ├── review.py              Review state management (tracks edits)
│   │   ├── validate.py            SANS 10142-1 rules + cross-ref
│   │   ├── price.py               Dual BQ generation
│   │   └── output.py              Excel + PDF assembly
│   └── prompts/
│       ├── system_prompt.py
│       ├── classify_prompt.py
│       ├── register_prompt.py
│       ├── sld_prompt.py          ★ MOST CRITICAL
│       ├── lighting_layout_prompt.py
│       ├── plugs_layout_prompt.py
│       ├── outside_lights_prompt.py
│       ├── residential_prompt.py
│       ├── maintenance_prompt.py
│       └── schemas.py
│
├── core/
│   ├── constants.py               Default pricing tables
│   ├── standards.py               SANS 10142-1 rules
│   └── pricing_engine.py          BQ calculation from extraction
│
├── exports/
│   ├── excel_bq.py                ★ Quantity BQ + Estimated BQ workbook
│   ├── pdf_summary.py             One-page project summary
│   └── eskom_forms.py
│
├── pages/
│   ├── 0_Welcome.py
│   ├── 1_Upload.py                Multi-file upload + pipeline trigger
│   ├── 2_Review.py                ★ THE MAIN SCREEN — full-screen editable extraction
│   ├── 3_Site_Conditions.py       Site conditions form
│   ├── 4_Results.py               BQ display + export
│   └── 5_Profile.py               Contractor profile setup
│
├── utils/
│   ├── styles.py
│   └── components.py              Reusable UI components (confidence badges, etc.)
│
└── tests/
    ├── test_models.py
    ├── test_ingest.py
    ├── test_validation.py
    ├── test_pricing.py
    └── test_corrections.py
```

---

## Error Handling

Same as v4.0. Golden rule: **Never crash. Partial data with warnings > blank screen.**

| Stage | Error | Response |
|-------|-------|----------|
| INGEST | Corrupt PDF | Stop, friendly error |
| INGEST | >30 pages | Stop, ask to split |
| CLASSIFY | Uncertain | Default to COMMERCIAL |
| DISCOVER | API error | Retry once, then show empty form for manual entry |
| DISCOVER | Low confidence | Re-send to Opus, then flag items red |
| REVIEW | No changes | That's fine — proceed with AI extraction as-is |
| VALIDATE | Rule error | Skip rule, warn |
| PRICE | Missing data | Show item as "rate only" in BQ (contractor fills in both qty and rate) |
| OUTPUT | Excel error | Fall back to CSV export |

---

## Test Strategy

### Test 1: Full Wedela (3 PDFs)
Expected: 5 blocks, ≥15 DBs, ≥20 rooms, pool/heat pump equipment, site cable runs with distances. Review screen shows ~280 items with confidence colours. Excel BQ has ~180 line items in sections A-L.

### Test 2: Single PDF
Expected: 1 block, 7 DBs, rooms with fixtures. Simpler review.

### Test 3: Contractor edits
Expected: Change 5 fixture counts in review, verify CorrectionLog captures all edits, accuracy calculation works.

### Test 4: Site conditions impact
Expected: Set renovation + difficult access + hard clay → verify labour ×1.56 and trenching ×1.40 are applied to estimated BQ totals.

### Test 5: Contractor profile
Expected: Save profile with custom prices for 5 items → verify those prices appear in estimated BQ instead of defaults.

### Test 6: Excel output
Expected: Download .xlsx, open in Excel, verify:
- Quantity sheet has empty price column with formulas
- Estimated sheet has default prices (labelled "ESTIMATE")
- Changing a unit price recalculates all totals
- Section subtotals use SUM formulas
- Grand total includes contingency + markup + VAT formulas
