# AfriPlan AI - Complete Architecture Diagram

## Overview

This document provides detailed diagrams showing how **AI Prompts** and **Python Code** influence extraction results at each stage.

---

## 1. High-Level Application Flow

```
+==============================================================================+
|                        AFRIPLAN AI v7.0 ARCHITECTURE                          |
+==============================================================================+

 USER UPLOADS                    AI EXTRACTION                    OUTPUT
+-------------+              +------------------+              +-------------+
|             |              |                  |              |             |
|  PDF Files  |  -------->   |  6-Stage AI      |  -------->   |  Excel BOQ  |
|  (1-4 docs) |              |  Pipeline        |              |  PDF Report |
|             |              |                  |              |  Validation |
+-------------+              +------------------+              +-------------+
      |                              |                              |
      v                              v                              v
 +----------+                 +------------+                  +-----------+
 | PyMuPDF  |                 | Claude/    |                  | openpyxl  |
 | Pillow   |                 | Groq/Grok/ |                  | fpdf2     |
 |          |                 | Gemini API |                  |           |
 +----------+                 +------------+                  +-----------+
```

---

## 2. Document Upload Flow (5 Steps)

```
+==============================================================================+
|                         GUIDED UPLOAD FLOW (v7.0)                             |
+==============================================================================+

STEP 1: COVER PAGE                    STEP 2: SLD/SCHEDULES
+------------------------+            +------------------------+
| Upload: Cover_Page.pdf |            | Upload: SLD.pdf        |
| (multi-file support)   |            | (multi-file support)   |
|                        |            |                        |
| [Skip] or [Extract] -->|----------->| [Skip] or [Detect DBs] |
+------------------------+            +------------------------+
         |                                      |
         v                                      v
+------------------------+            +------------------------+
| AI Pass: PROJECT_INFO  |            | AI Passes:             |
| Prompt: Extract project|            |  - DB_DETECTION        |
| name, client, date     |            |  - SUPPLY_POINT        |
|                        |            |  - DB_SCHEDULE (x N)   |
| Output: project_info{} |            |  - CABLE_ROUTES        |
+------------------------+            +------------------------+
                                               |
                                               v
                        +------------------------------------------+
                        | Code: SANS 10142-1 Validation            |
                        | - Max 10 lights/circuit                  |
                        | - Max 10 sockets/circuit                 |
                        | - ELCB mandatory check                   |
                        +------------------------------------------+

STEP 3: LIGHTING LAYOUT               STEP 4: POWER LAYOUT
+------------------------+            +------------------------+
| Upload: Lighting.pdf   |            | Upload: Power.pdf      |
| (multi-file support)   |            | (multi-file support)   |
|                        |            |                        |
| [Skip] or [Extract] -->|----------->| [Skip] or [Extract]    |
+------------------------+            +------------------------+
         |                                      |
         v                                      v
+------------------------+            +------------------------+
| AI Passes:             |            | AI Passes:             |
|  1. LEGEND_LIGHTING    |            |  1. LEGEND_POWER       |
|  2. CIRCUIT_CLUSTERS   |            |  2. CIRCUIT_CLUSTERS   |
|                        |            |                        |
| Output:                |            | Output:                |
|  - lighting_legend{}   |            |  - power_legend{}      |
|  - lighting_clusters[] |            |  - power_clusters[]    |
+------------------------+            +------------------------+
                                               |
                                               v
                                    STEP 5: REVIEW & EXPORT
                                    +------------------------+
                                    | SLD <-> Layout         |
                                    | RECONCILIATION         |
                                    |                        |
                                    | Code: Match Rate Calc  |
                                    | Code: Accuracy Score   |
                                    | Code: Benchmark Valid. |
                                    |                        |
                                    | Output:                |
                                    |  - Excel BOQ           |
                                    |  - PDF Summary         |
                                    +------------------------+
```

---

## 3. AI Pipeline Stages (Detailed)

```
+==============================================================================+
|                    6-STAGE AI PIPELINE (agent/afriplan_agent.py)              |
+==============================================================================+

  STAGE 1          STAGE 2          STAGE 3          STAGE 4
  INGEST           CLASSIFY         DISCOVER         VALIDATE
+----------+     +----------+     +----------+     +----------+
|          |     |          |     |          |     |          |
| PyMuPDF  |---->| Haiku    |---->| Sonnet   |---->| Python   |
| PDF->IMG |     | Fast     |     | Balanced |     | Rules    |
|          |     |          |     |          |     |          |
| NO AI    |     | AI PROMPT|     | AI PROMPT|     | NO AI    |
| Code only|     | R0.18    |     | R1.80    |     | Code only|
+----------+     +----------+     +----------+     +----------+
     |                |                |                |
     v                v                v                v
 +--------+      +--------+      +--------+      +--------+
 | base64 |      | tier:  |      | JSON:  |      | flags: |
 | images |      | resi/  |      | DBs,   |      | pass/  |
 |        |      | comm/  |      | circuits|     | fail   |
 |        |      | maint  |      | cables |      |        |
 +--------+      +--------+      +--------+      +--------+

  STAGE 5          STAGE 6
  PRICE            OUTPUT
+----------+     +----------+
|          |     |          |
| Python   |---->| fpdf2    |
| Calc     |     | openpyxl |
|          |     |          |
| NO AI    |     | NO AI    |
| Code only|     | Code only|
+----------+     +----------+
     |                |
     v                v
 +--------+      +--------+
 | BQ with|      | Excel  |
 | prices |      | PDF    |
 | totals |      | files  |
 +--------+      +--------+
```

---

## 4. Prompt Locations in Code

```
+==============================================================================+
|                     PROMPT FILE LOCATIONS                                     |
+==============================================================================+

agent/stages/multi_pass_discover.py
|
+-- PROMPT_DB_DETECTION (line ~50)
|   "Find ALL Distribution Boards on this SLD drawing..."
|   Used by: run_db_detection_pass()
|
+-- PROMPT_SUPPLY_POINT (line ~120)
|   "Extract Main Supply Point / Metering Information..."
|   Used by: run_supply_point_pass()
|
+-- PROMPT_DB_SCHEDULE (line ~180)
|   "Extract Circuit Schedule for Distribution Board {db_name}..."
|   Used by: run_db_schedule_pass()
|
+-- PROMPT_CABLE_ROUTES (line ~280)
|   "Extract Cable Routes Between Distribution Boards..."
|   Used by: run_cable_routes_pass()
|
+-- PROMPT_LEGEND_LIGHTING (line ~350)
|   "Extract Lighting Legend from Layout Drawing..."
|   Used by: run_lighting_legend_pass()
|
+-- PROMPT_LEGEND_POWER (line ~420)
|   "Extract Power/Socket Legend from Layout Drawing..."
|   Used by: run_power_legend_pass()
|
+-- PROMPT_CIRCUIT_CLUSTERS (line ~580)
|   "Find ALL Circuit Label Clusters on This Floor Plan..."
|   Used by: run_circuit_clusters_pass()
|
+-- COUNTING RULES EMBEDDED IN PROMPTS:
    - Lighting: count LIGHTS only (NOT switches)
    - Power: count SOCKETS only (double = 1 point)
    - Dedicated: always 1 point per circuit

benchmark/improved_prompts.py
|
+-- PROMPT_SUPPLY_POINT (improved version)
+-- PROMPT_DB_DETECTION (improved version)
+-- PROMPT_CIRCUIT_SCHEDULE (improved version)
+-- PROMPT_CABLE_ROUTES (improved version)
+-- PROMPT_LEGEND_LIGHTING (improved version)
+-- PROMPT_LEGEND_POWER (improved version)
```

---

## 5. Code Influence Points

```
+==============================================================================+
|                     PYTHON CODE INFLUENCE POINTS                              |
+==============================================================================+

+--------------------------------+    +--------------------------------+
|   agent/stages/validate.py     |    |   agent/validators.py          |
+--------------------------------+    +--------------------------------+
|                                |    |                                |
| SANS 10142-1 HARD RULES:       |    | SOFT VALIDATION:               |
|                                |    |                                |
| - Max 10 lights per circuit    |    | - Confidence scoring           |
| - Max 10 sockets per circuit   |    | - Warning generation           |
| - ELCB 30mA mandatory          |    | - Auto-correction suggestions  |
| - Dedicated stove circuit      |    |                                |
| - Dedicated geyser circuit     |    | If confidence < 70%:           |
| - Voltage drop < 5%            |    |   -> Escalate to Opus          |
|                                |    |                                |
| CODE ENFORCES COMPLIANCE       |    | CODE ADJUSTS AI BEHAVIOR       |
+--------------------------------+    +--------------------------------+
         |                                      |
         v                                      v
+--------------------------------+    +--------------------------------+
|   utils/calculations.py        |    |   benchmark/validator.py       |
+--------------------------------+    +--------------------------------+
|                                |    |                                |
| ELECTRICAL CALCULATIONS:       |    | ACCURACY MEASUREMENT:          |
|                                |    |                                |
| - ADMD (NRS 034)               |    | - Compare vs ground truth      |
| - Cable sizing                 |    | - Category scoring             |
| - Voltage drop                 |    | - Critical miss detection      |
| - Load diversity (50%)         |    | - Recommendations              |
| - Circuit counting             |    |                                |
|                                |    | CODE MEASURES AI ACCURACY      |
| CODE APPLIES SA STANDARDS      |    |                                |
+--------------------------------+    +--------------------------------+
```

---

## 6. Complete Data Flow Diagram

```
+==============================================================================+
|                         COMPLETE DATA FLOW                                    |
+==============================================================================+

PDF FILE(S)
    |
    v
+-------------------+
| 1. INGEST         |  <-- PyMuPDF (Code)
| PDF -> Images     |
| Base64 encoding   |
+-------------------+
    |
    v
+-------------------+
| 2. CLASSIFY       |  <-- AI PROMPT (Haiku)
| Detect tier:      |      "Analyze this document and classify..."
| - Residential     |
| - Commercial      |  --> Output: ServiceTier enum
| - Maintenance     |
+-------------------+
    |
    v
+-------------------+
| 3. DISCOVER       |  <-- AI PROMPTS (Sonnet) x7
| Multiple passes:  |
|                   |
| Pass 1: DB_DETECT |      "Find ALL Distribution Boards..."
|    |              |      --> detected_dbs: ["DB-GF", "DB-S1"...]
|    v              |
| Pass 2: SUPPLY    |      "Extract Main Supply Point..."
|    |              |      --> supply_point: {voltage, breaker...}
|    v              |
| Pass 3: SCHEDULE  |      "Extract Circuit Schedule for {db}..."
|    | (per DB)     |      --> db_schedules: {circuits, points...}
|    v              |
| Pass 4: CABLES    |      "Extract Cable Routes..."
|    |              |      --> cable_routes: [{from, to, spec}...]
|    v              |
| Pass 5: LEGEND_L  |      "Extract Lighting Legend..."
|    |              |      --> lighting_legend: {light_types...}
|    v              |
| Pass 6: LEGEND_P  |      "Extract Power Legend..."
|    |              |      --> power_legend: {socket_types...}
|    v              |
| Pass 7: CLUSTERS  |      "Find ALL Circuit Label Clusters..."
|                   |      --> circuit_clusters: [{ref, points...}]
+-------------------+
    |
    v
+-------------------+
| 4. VALIDATE       |  <-- Python Code (No AI)
| SANS 10142-1:     |
|                   |
| - Circuit limits  |      if lights > 10: add_circuit()
| - ELCB check      |      if no_elcb: add_warning()
| - Cable sizing    |      if voltage_drop > 5%: flag_error()
|                   |
| Auto-corrections: |      circuits = ceil(points / 10)
+-------------------+
    |
    v
+-------------------+
| 5. RECONCILE      |  <-- Python Code (No AI)
| SLD vs Layout:    |
|                   |
| For each circuit: |      sld_points = db_schedule[circuit].points
|   Compare points  |      layout_points = cluster[circuit].total
|   Calculate match |      match = abs(sld - layout) <= 1
|                   |
| Match rate = %    |      match_rate = matched / total
+-------------------+
    |
    v
+-------------------+
| 6. PRICE          |  <-- Python Code (No AI)
| Apply pricing:    |
|                   |
| - Material costs  |      utils/constants.py (price database)
| - Labour rates    |      R150/point, R250/dedicated
| - Margin %        |      12% budget, 18% standard, 22% premium
| - Complexity      |      1.0 new, 1.15 renovation, 1.3 rewire
+-------------------+
    |
    v
+-------------------+
| 7. OUTPUT         |  <-- Python Code (No AI)
| Generate files:   |
|                   |
| - Excel BOQ       |      exports/excel_bq.py (openpyxl)
| - PDF Summary     |      exports/pdf_summary.py (fpdf2)
|                   |
+-------------------+
    |
    v
FINAL OUTPUT:
- Professional Excel BOQ with categories
- PDF summary with compliance score
- Benchmark accuracy report (if matched)
```

---

## 7. Prompt → Result Mapping

```
+==============================================================================+
|                    PROMPT → RESULT INFLUENCE MAP                              |
+==============================================================================+

PROMPT INSTRUCTION                      →  RESULT IMPACT
--------------------------------------------------------------------------------

"Find ALL Distribution Boards"          →  List of DBs detected
  └─ "Look for: DB-XX, DBM-XX, SUB DB"     Number affects accuracy score
  └─ "Include: DB-GF, DB-CA variants"      Missing DBs = 0 circuits extracted

"Extract Circuit Schedule"              →  Points per circuit
  └─ "For lighting: count LIGHTS only"     Directly affects SLD reconciliation
  └─ "Switches do NOT count as points"     Wrong count = mismatch with layout
  └─ "Double socket = 1 point"             Impacts BOQ material quantities

"Find ALL Circuit Label Clusters"       →  Layout fixture counts
  └─ "Look for: DB-S3 L2, DB-GF P1"        Must match SLD circuit refs
  └─ "Count fixtures per cluster"           Affects match rate calculation
  └─ "evidence_tokens: exact text read"     Helps debug extraction issues

"Extract Legend"                        →  Fixture type identification
  └─ "Symbol → Name → Wattage"             Wrong legend = wrong fixture IDs
  └─ "Include mounting height"              Affects circuit cluster accuracy

--------------------------------------------------------------------------------
CODE VALIDATION                         →  RESULT IMPACT
--------------------------------------------------------------------------------

SANS 10142-1 checks                     →  Compliance score
  └─ Max 10 points/circuit                  Auto-adds circuits if exceeded
  └─ ELCB mandatory                         Warning if missing
  └─ Voltage drop < 5%                      Warning if exceeded

Reconciliation algorithm                →  Match rate %
  └─ Compare SLD points vs Layout           30% weight in accuracy score
  └─ ±1 tolerance for matching              Too strict = low match rate

Benchmark validation                    →  Accuracy measurement
  └─ Compare vs ground truth                Shows actual extraction quality
  └─ Category scoring                       Identifies weak areas
```

---

## 8. Interactive Pipeline Class Diagram

```
+==============================================================================+
|          InteractivePipeline (agent/stages/interactive_passes.py)             |
+==============================================================================+

class InteractivePipeline:
    |
    +-- __init__(client, model, provider)
    |       └── Initializes AI client (Anthropic/Groq/Gemini/Grok)
    |
    +-- STATE (PipelineState dataclass):
    |       ├── project_info: Dict
    |       ├── detected_dbs: List[str]
    |       ├── db_schedules: Dict[str, Dict]
    |       ├── supply_point: Dict
    |       ├── cable_routes: List[Dict]
    |       ├── lighting_legend: Dict
    |       ├── power_legend: Dict
    |       ├── circuit_clusters: List[Dict]  <-- v7.0
    |       ├── total_tokens: int
    |       └── total_cost: float
    |
    +-- EXTRACTION METHODS (AI calls):
    |       |
    |       +-- run_project_info_pass(pages) → InteractivePassResult
    |       |       └── PROMPT: Extract project name, client, date
    |       |
    |       +-- run_db_detection_pass(pages) → InteractivePassResult
    |       |       └── PROMPT: Find all distribution boards
    |       |
    |       +-- run_supply_point_pass(pages) → InteractivePassResult
    |       |       └── PROMPT: Extract main supply point
    |       |
    |       +-- run_db_schedule_pass(pages, db_name) → InteractivePassResult
    |       |       └── PROMPT: Extract circuit schedule for {db_name}
    |       |
    |       +-- run_cable_routes_pass(pages) → InteractivePassResult
    |       |       └── PROMPT: Extract cable routes
    |       |
    |       +-- run_lighting_legend_pass(pages) → InteractivePassResult
    |       |       └── PROMPT: Extract lighting legend
    |       |
    |       +-- run_power_legend_pass(pages) → InteractivePassResult
    |       |       └── PROMPT: Extract power legend
    |       |
    |       +-- run_circuit_clusters_pass(pages, legend) → InteractivePassResult
    |               └── PROMPT: Find circuit label clusters
    |
    +-- APPLY METHODS (Store results):
    |       ├── apply_project_info(info)
    |       ├── apply_detected_dbs(dbs)
    |       ├── apply_db_schedule(db_name, schedule)
    |       └── apply_cable_routes(routes)
    |
    +-- BUILD METHODS (Compile final result):
    |       └── build_final_result() → ExtractionResult
    |               └── Combines all state into ExtractionResult model
    |
    +-- RECONCILIATION (v7.0):
            └── reconcile_sld_with_clusters() → Dict
                    └── Compares SLD circuit points vs layout cluster points
```

---

## 9. Session State Flow (Streamlit)

```
+==============================================================================+
|                    SESSION STATE DATA FLOW                                    |
+==============================================================================+

pages/6_Guided_Upload.py
    |
    +-- init_session_state()
    |       |
    |       +-- guided_step: int (1-5)
    |       +-- max_completed_step: int
    |       +-- step_X_skipped: bool (x4)
    |       |
    |       +-- cover_pages: List[PageInfo]
    |       +-- sld_pages: List[PageInfo]
    |       +-- lighting_pages: List[PageInfo]
    |       +-- power_pages: List[PageInfo]
    |       |
    |       +-- project_info: Dict
    |       +-- supply_point: Dict
    |       +-- detected_dbs: List[str]
    |       +-- db_schedules: Dict[str, Dict]
    |       +-- cable_routes: List[Dict]
    |       |
    |       +-- lighting_legend: Dict
    |       +-- lighting_circuit_clusters: List[Dict]  <-- v7.0
    |       |
    |       +-- power_legend: Dict
    |       +-- power_circuit_clusters: List[Dict]     <-- v7.0
    |       |
    |       +-- final_extraction: ExtractionResult
    |       +-- final_validation: ValidationResult
    |       +-- final_pricing: PricingResult
    |       |
    |       +-- interactive_pipeline: InteractivePipeline
    |
    |
    +-- render_step_1_cover()  ──────────────────────────────────┐
    |       └── AI: PROJECT_INFO prompt                          │
    |       └── Updates: project_info                            │
    |                                                            │
    +-- render_step_2_sld()  ────────────────────────────────────┤
    |       └── AI: DB_DETECTION, SUPPLY_POINT,                  │
    |              DB_SCHEDULE (x N), CABLE_ROUTES               │
    |       └── Updates: detected_dbs, db_schedules,             │
    |              supply_point, cable_routes                    │
    |                                                            │
    +-- render_step_3_lighting()  ───────────────────────────────┤ DATA
    |       └── AI: LEGEND_LIGHTING, CIRCUIT_CLUSTERS            │ FLOW
    |       └── Updates: lighting_legend,                        │
    |              lighting_circuit_clusters                     │
    |                                                            │
    +-- render_step_4_power()  ──────────────────────────────────┤
    |       └── AI: LEGEND_POWER, CIRCUIT_CLUSTERS               │
    |       └── Updates: power_legend,                           │
    |              power_circuit_clusters                        │
    |                                                            │
    +-- render_step_5_review()  ─────────────────────────────────┘
            └── CODE: Reconciliation, Validation, Pricing
            └── CODE: Benchmark comparison (if matched)
            └── OUTPUT: Excel BOQ, PDF Summary
```

---

## 10. Accuracy Scoring Formula

```
+==============================================================================+
|                    ACCURACY CALCULATION (v7.0)                                |
+==============================================================================+

COMPONENT WEIGHTS:
+------------------+--------+--------------------------------------------------+
| Component        | Weight | Calculation                                      |
+------------------+--------+--------------------------------------------------+
| DBs Detected     |  20%   | min(100, (db_count / 10) * 100)                  |
| SLD Circuits     |  15%   | min(100, (circuit_count / 50) * 100)             |
| Layout Clusters  |  20%   | min(100, (cluster_count / 30) * 100)             |
| Cable Routes     |  15%   | min(100, (cable_count / 10) * 100)               |
| Match Rate       |  30%   | (matched_circuits / total_compared) * 100        |
+------------------+--------+--------------------------------------------------+

FINAL ACCURACY = (db_score * 0.20) + (circuit_score * 0.15) +
                 (cluster_score * 0.20) + (cable_score * 0.15) +
                 (match_rate * 0.30)

TARGET: 75%+

COLOR CODING:
  >= 75%  →  GREEN  (Target achieved!)
  >= 60%  →  ORANGE (Below target)
  <  60%  →  RED    (Needs improvement)
```

---

## Summary

| Stage | Technology | Prompt/Code | Key Influence |
|-------|------------|-------------|---------------|
| 1. Ingest | PyMuPDF | Code only | PDF quality → image quality |
| 2. Classify | Haiku | AI Prompt | Tier routing affects all prompts |
| 3. Discover | Sonnet | AI Prompts (x7) | Extraction accuracy |
| 4. Validate | Python | Code only | SANS compliance enforcement |
| 5. Reconcile | Python | Code only | Match rate calculation |
| 6. Price | Python | Code only | Material costs from database |
| 7. Output | fpdf2/openpyxl | Code only | File generation |

**Key Insight:** The **AI Prompts** (Stage 3) determine extraction quality, while **Python Code** (Stages 4-7) enforces compliance, calculates accuracy, and generates output.
