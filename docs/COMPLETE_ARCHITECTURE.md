# AfriPlan Electrical v5.0 - Complete System Architecture

## Visual Architecture Diagram

```
┌──────────────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                    AFRIPLAN ELECTRICAL v5.0 ARCHITECTURE                                         │
│                                   AI-Powered Quantity Take-Off Platform                                          │
└──────────────────────────────────────────────────────────────────────────────────────────────────────────────────┘

                                              ┌─────────────────┐
                                              │   USER UPLOAD   │
                                              │  (PDF / Image)  │
                                              └────────┬────────┘
                                                       │
                                                       ▼
┌──────────────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                           7-STAGE AI PIPELINE                                                     │
├──────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                                                   │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐  │
│  │   STAGE 1   │    │   STAGE 2   │    │   STAGE 3   │    │   STAGE 4   │    │   STAGE 5   │    │   STAGE 6   │  │
│  │   INGEST    │───▶│  CLASSIFY   │───▶│  DISCOVER   │───▶│   REVIEW    │───▶│  VALIDATE   │───▶│    PRICE    │  │
│  │             │    │             │    │             │    │             │    │             │    │             │  │
│  │  PyMuPDF    │    │  Haiku 4.5  │    │ Sonnet 4.5  │    │   Human     │    │   Python    │    │   Python    │  │
│  │  Pillow     │    │   ~R0.18    │    │   ~R1.80    │    │  Review     │    │    Only     │    │    Only     │  │
│  │   FREE      │    │    FAST     │    │  ACCURATE   │    │    UI       │    │ SANS 10142  │    │ constants   │  │
│  └─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘  │
│         │                  │                  │                  │                  │                  │         │
│         ▼                  ▼                  ▼                  ▼                  ▼                  ▼         │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐  │
│  │DocumentSet  │    │ServiceTier  │    │Extraction   │    │Correction   │    │Validation   │    │PricingResult│  │
│  │  pages[]    │    │  RESID.     │    │  Result     │    │  Log        │    │  Result     │    │  dual BQ    │  │
│  │  images[]   │    │  COMM.      │    │  JSON       │    │  edits[]    │    │  flags[]    │    │  items[]    │  │
│  │  text       │    │  MAINT.     │    │  confidence │    │  accuracy   │    │  auto-fix   │    │  totals     │  │
│  └─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘  │
│                                                                                                                   │
└──────────────────────────────────────────────────────────────────────────────────────────────────────────────────┘
                                                       │
                                                       ▼
                                              ┌─────────────────┐
                                              │    STAGE 7      │
                                              │    OUTPUT       │
                                              │  PDF + Excel    │
                                              └────────┬────────┘
                                                       │
                                    ┌──────────────────┼──────────────────┐
                                    ▼                  ▼                  ▼
                             ┌───────────┐      ┌───────────┐      ┌───────────┐
                             │   PDF     │      │  Excel    │      │   JSON    │
                             │ Quotation │      │    BQ     │      │  Results  │
                             │  fpdf2    │      │ openpyxl  │      │           │
                             └───────────┘      └───────────┘      └───────────┘
```

---

## Detailed Prompt & Code Influence Flow

```
┌──────────────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                               PROMPT ARCHITECTURE & CODE INFLUENCE                                                │
└──────────────────────────────────────────────────────────────────────────────────────────────────────────────────┘

                                    ┌────────────────────────────────────┐
                                    │        SYSTEM PROMPT               │
                                    │   (SA Electrical Domain)           │
                                    │   agent/prompts/system_prompt.py   │
                                    ├────────────────────────────────────┤
                                    │ • SANS 10142-1:2017 rules          │
                                    │ • Max 10 points/circuit            │
                                    │ • ELCB 30mA mandatory              │
                                    │ • NRS 034 ADMD values              │
                                    │ • SA cable conventions             │
                                    │ • Load calculation standards       │
                                    └────────────────┬───────────────────┘
                                                     │
                     ┌───────────────────────────────┼───────────────────────────────┐
                     │                               │                               │
                     ▼                               ▼                               ▼
        ┌────────────────────────┐     ┌────────────────────────┐     ┌────────────────────────┐
        │   RESIDENTIAL PROMPT   │     │   COMMERCIAL PROMPT    │     │   MAINTENANCE PROMPT   │
        │ residential_prompts.py │     │ commercial_prompts.py  │     │ maintenance_prompts.py │
        ├────────────────────────┤     ├────────────────────────┤     ├────────────────────────┤
        │ Room-by-room schema:   │     │ Area-based W/m²:       │     │ COC defect codes:      │
        │ • dwelling_type        │     │ • power_density        │     │ • no_elcb              │
        │ • rooms[].lights       │     │ • three_phase_load     │     │ • exposed_wiring       │
        │ • rooms[].sockets      │     │ • emergency_lighting   │     │ • overloaded_circuit   │
        │ • geyser circuit       │     │ • fire_alarm_zones     │     │ • remedial_items[]     │
        │ • outdoor points       │     │ • NMD calculation      │     │ • defect_severity      │
        └────────────┬───────────┘     └────────────┬───────────┘     └────────────┬───────────┘
                     │                               │                               │
                     └───────────────────────────────┼───────────────────────────────┘
                                                     │
                                                     ▼
                              ┌──────────────────────────────────────────┐
                              │          MULTI-PASS EXTRACTION           │
                              │       (6 Focused AI Passes)              │
                              └──────────────────────┬───────────────────┘
                                                     │
     ┌───────────────┬───────────────┬───────────────┼───────────────┬───────────────┬───────────────┐
     ▼               ▼               ▼               ▼               ▼               ▼               │
┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐              │
│ PASS 1  │    │ PASS 2  │    │ PASS 3  │    │ PASS 4  │    │ PASS 5  │    │ PASS 6  │              │
│ PROJECT │    │   DB    │    │   DB    │    │  ROOM   │    │  ROOM   │    │  CABLE  │              │
│  INFO   │    │DETECTION│    │SCHEDULES│    │DETECTION│    │FIXTURES │    │ ROUTES  │              │
├─────────┤    ├─────────┤    ├─────────┤    ├─────────┤    ├─────────┤    ├─────────┤              │
│Cover Pg │    │SLD Pages│    │Per DB   │    │Layout   │    │Per Room │    │Site Plan│              │
│Metadata │    │DB List  │    │Circuits │    │Room List│    │Fixtures │    │Cables   │              │
└────┬────┘    └────┬────┘    └────┬────┘    └────┬────┘    └────┬────┘    └────┬────┘              │
     │              │              │              │              │              │                   │
     └──────────────┴──────────────┴──────────────┴──────────────┴──────────────┘                   │
                                                     │                                              │
                                                     ▼                                              │
                              ┌──────────────────────────────────────────┐                          │
                              │          EXTRACTION RESULT               │                          │
                              │    (Structured JSON with Confidence)     │                          │
                              ├──────────────────────────────────────────┤                          │
                              │  BuildingBlock[]                         │                          │
                              │  ├─ DistributionBoard[]                  │                          │
                              │  │  └─ Circuit[] (mcb, cable, points)    │                          │
                              │  ├─ Room[]                               │                          │
                              │  │  └─ FixtureCounts (lights, sockets)   │                          │
                              │  └─ HeavyEquipment[] (HVAC, pumps)       │                          │
                              │  SiteCableRun[] (underground, trunking)  │                          │
                              │  Discrepancies[] (SLD vs Layout)         │                          │
                              └──────────────────────┬───────────────────┘                          │
                                                     │                                              │
                                                     ▼                                              │
```

---

## Code Components Influence Flow

```
┌──────────────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                CODE COMPONENTS & DATA TRANSFORMATION                                              │
└──────────────────────────────────────────────────────────────────────────────────────────────────────────────────┘

   PROMPTS (AI Direction)                    CODE (Deterministic Logic)                    OUTPUT (Final Result)
   ─────────────────────                    ─────────────────────────                    ───────────────────────

┌─────────────────────────┐
│ agent/prompts/          │
│ ├─ system_prompt.py     │─────────┐
│ ├─ sld_prompt.py        │         │
│ ├─ lighting_layout.py   │         │
│ ├─ plugs_layout.py      │         │
│ └─ legend_prompt.py     │         │
└─────────────────────────┘         │
            │                       │
            │   Prompts instruct    │
            │   Claude WHAT to      │
            │   extract and HOW     │
            ▼                       │
┌─────────────────────────┐         │
│   CLAUDE AI MODELS      │         │
│   ├─ Haiku (classify)   │         │
│   ├─ Sonnet (extract)   │         │
│   └─ Opus (escalate)    │         │
└───────────┬─────────────┘         │
            │                       │
            │   AI returns JSON     │
            │   with confidence     │
            ▼                       │
┌─────────────────────────┐         │        ┌─────────────────────────┐
│   ExtractionResult      │─────────┼───────▶│   utils/calculations.py │
│   (Raw AI Output)       │         │        │   ├─ calculate_load()   │
│   ├─ circuits[]         │         │        │   ├─ calculate_admd()   │
│   ├─ rooms[]            │         │        │   ├─ voltage_drop()     │
│   ├─ fixtures[]         │         │        │   └─ cable_size()       │
│   └─ confidence scores  │         │        └───────────┬─────────────┘
└─────────────────────────┘         │                    │
                                    │                    │
                                    │                    ▼
                                    │        ┌─────────────────────────┐
                                    │        │ agent/stages/validate.py│
                                    └───────▶│ SANS 10142-1 Rules      │
                                             │ ├─ max 10 pts/circuit   │
                                             │ ├─ ELCB required        │
                                             │ ├─ dedicated circuits   │
                                             │ └─ auto-corrections     │
                                             └───────────┬─────────────┘
                                                         │
                                                         ▼
                                             ┌─────────────────────────┐
                                             │ utils/constants.py      │
                                             │ SA Material Database    │
                                             │ ├─ CABLES (prices)      │
                                             │ ├─ DBs & MCBs           │
                                             │ ├─ LIGHTS (LED)         │
                                             │ ├─ SOCKETS              │
                                             │ ├─ LABOUR RATES         │
                                             │ └─ COC FEES             │
                                             └───────────┬─────────────┘
                                                         │
                                                         ▼
                                             ┌─────────────────────────┐
                                             │ agent/stages/price.py   │
                                             │ BOQ Generation          │
                                             │ ├─ 14 BQ sections       │
                                             │ ├─ item categorization  │
                                             │ └─ dual BQ output       │
                                             └───────────┬─────────────┘
                                                         │
                         ┌───────────────────────────────┼───────────────────────────────┐
                         ▼                               ▼                               ▼
              ┌─────────────────────┐      ┌─────────────────────┐      ┌─────────────────────┐
              │  exports/pdf_       │      │  exports/excel_bq   │      │    JSON Export      │
              │  summary.py         │      │  .py                │      │                     │
              │  (fpdf2)            │      │  (openpyxl)         │      │                     │
              ├─────────────────────┤      ├─────────────────────┤      ├─────────────────────┤
              │ • Cover page        │      │ Sheet 1: Cover      │      │ • Full pipeline     │
              │ • Project summary   │      │ Sheet 2: BOQ        │      │   result            │
              │ • BQ table          │      │ Sheet 3: Summary    │      │ • All stage data    │
              │ • Payment terms     │      │ Sheet 4: Discrep.   │      │ • Confidence scores │
              │ • Notes & validity  │      │ • 14-section layout │      │ • Errors/warnings   │
              └─────────────────────┘      └─────────────────────┘      └─────────────────────┘
```

---

## Component Dependency Map

```
┌──────────────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                      FILE DEPENDENCY ARCHITECTURE                                                 │
└──────────────────────────────────────────────────────────────────────────────────────────────────────────────────┘

                                              ┌───────────────┐
                                              │    app.py     │
                                              │   (Router)    │
                                              └───────┬───────┘
                                                      │
                    ┌─────────────────────────────────┼─────────────────────────────────┐
                    ▼                                 ▼                                 ▼
         ┌──────────────────┐              ┌──────────────────┐              ┌──────────────────┐
         │ 0_Welcome.py     │              │ 1_Smart_Upload   │              │ 6_Guided_Upload  │
         │ (Landing Page)   │              │ (Auto Extract)   │              │ (Step-by-Step)   │
         └──────────────────┘              └────────┬─────────┘              └────────┬─────────┘
                                                    │                                  │
                                                    └──────────────┬───────────────────┘
                                                                   │
                                                                   ▼
                                                    ┌──────────────────────────┐
                                                    │   agent/pipeline.py      │
                                                    │   (7-Stage Orchestrator) │
                                                    └──────────────┬───────────┘
                                                                   │
                    ┌──────────────────────────────────────────────┼──────────────────────────────────────────────┐
                    │                                              │                                              │
                    ▼                                              ▼                                              ▼
         ┌──────────────────┐                           ┌──────────────────┐                           ┌──────────────────┐
         │  agent/stages/   │                           │  agent/prompts/  │                           │  agent/models.py │
         │  ├─ ingest.py    │                           │  ├─ system.py    │                           │  (1880 lines)    │
         │  ├─ classify.py  │◀─────────────────────────▶│  ├─ sld.py       │                           │  • ServiceTier   │
         │  ├─ discover.py  │     PROMPTS FEED INTO     │  ├─ lighting.py  │                           │  • ExtractionRes │
         │  ├─ review.py    │        AI STAGES          │  ├─ plugs.py     │                           │  • PricingResult │
         │  ├─ validate.py  │                           │  └─ legend.py    │                           │  • PipelineResult│
         │  ├─ price.py     │                           └──────────────────┘                           └────────┬─────────┘
         │  └─ output.py    │                                                                                   │
         └────────┬─────────┘                                                                                   │
                  │                                                                                             │
                  │                                                                                             │
                  ▼                                                                                             ▼
         ┌──────────────────┐                                                                        ┌──────────────────┐
         │    utils/        │                                                                        │    exports/      │
         │  ├─ constants.py │◀───────────────────────────────────────────────────────────────────────│  ├─ pdf_summary  │
         │  │  (1650 lines) │        CONSTANTS FEED PRICING                                          │  └─ excel_bq     │
         │  ├─ calculations │        EXPORTS USE MODELS                                              └──────────────────┘
         │  ├─ styles.py    │
         │  └─ components   │
         └──────────────────┘


LEGEND:
─────────▶  Data Flow
◀─────────▶  Bidirectional Dependency
```

---

## Model Selection Strategy

```
┌──────────────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                        LLM MODEL SELECTION STRATEGY                                               │
└──────────────────────────────────────────────────────────────────────────────────────────────────────────────────┘

                              ┌─────────────────────────────────────┐
                              │      CHECK API KEYS AVAILABLE       │
                              └─────────────────┬───────────────────┘
                                                │
                    ┌───────────────────────────┼───────────────────────────┐
                    ▼                           ▼                           ▼
         ┌──────────────────┐        ┌──────────────────┐        ┌──────────────────┐
         │  GROQ_API_KEY    │        │  XAI_API_KEY     │        │ ANTHROPIC_API_KEY│
         │  (100% FREE)     │        │  ($25 free/mo)   │        │    (PAID)        │
         └────────┬─────────┘        └────────┬─────────┘        └────────┬─────────┘
                  │                           │                           │
                  ▼                           ▼                           ▼
         ┌──────────────────┐        ┌──────────────────┐        ┌──────────────────┐
         │ Llama 4 Scout    │        │ Grok-2-Vision    │        │ Claude Models    │
         │ Llama 4 Maverick │        │                  │        │ Haiku/Sonnet/Opus│
         └──────────────────┘        └──────────────────┘        └──────────────────┘
                  │                           │                           │
                  └───────────────────────────┼───────────────────────────┘
                                              │
                                              ▼
                              ┌─────────────────────────────────────┐
                              │    STAGE-BASED MODEL ASSIGNMENT     │
                              └─────────────────┬───────────────────┘
                                                │
         ┌──────────────────────────────────────┼──────────────────────────────────────┐
         ▼                                      ▼                                      ▼
┌─────────────────────┐              ┌─────────────────────┐              ┌─────────────────────┐
│     CLASSIFY        │              │      DISCOVER       │              │     ESCALATION      │
│    (Fast Tier)      │              │   (Multi-Pass)      │              │   (Low Confidence)  │
├─────────────────────┤              ├─────────────────────┤              ├─────────────────────┤
│ • Haiku 4.5 (R0.18) │              │ • Sonnet 4.5 (R1.80)│              │ • Opus 4.6 (R8.50)  │
│ • Grok-2-Vision     │              │ • Llama 4 Maverick  │              │ • Gemini 1.5 Pro    │
│ • Gemini 2.0 Flash  │              │ • Gemini 2.0 Flash  │              │ • Grok-2-Vision     │
│ • Llama 4 Scout     │              │ • Grok-2-Vision     │              │                     │
└─────────────────────┘              └─────────────────────┘              └─────────────────────┘


COST PER DOCUMENT:
─────────────────────────────────────────────────────────────────
│ Provider    │ Classify │ Discover │ Escalate │ Total Est.    │
─────────────────────────────────────────────────────────────────
│ Groq (FREE) │   R0.00  │   R0.00  │   R0.00  │    R0.00     │
│ xAI Grok    │   R0.50  │   R1.00  │   R2.00  │   ~R1.50     │
│ Claude      │   R0.18  │   R1.80  │   R8.50  │   ~R2.00     │
─────────────────────────────────────────────────────────────────
```

---

## Confidence & Accuracy System

```
┌──────────────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                       CONFIDENCE SCORING SYSTEM                                                   │
└──────────────────────────────────────────────────────────────────────────────────────────────────────────────────┘

                              ┌─────────────────────────────────────┐
                              │      PER-ITEM CONFIDENCE            │
                              │      (ItemConfidence Enum)          │
                              └─────────────────────────────────────┘
                                                │
         ┌──────────────────┬───────────────────┼───────────────────┬──────────────────┐
         ▼                  ▼                   ▼                   ▼                  ▼
┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
│   EXTRACTED     │ │    INFERRED     │ │   ESTIMATED     │ │     MANUAL      │
│   ████████████  │ │   ████████████  │ │   ████████████  │ │   ████████████  │
│     GREEN ✓     │ │    YELLOW ⚠     │ │      RED ✗      │ │     BLUE ✓      │
├─────────────────┤ ├─────────────────┤ ├─────────────────┤ ├─────────────────┤
│ Read directly   │ │ Calculated from │ │ Guessed or      │ │ Edited by       │
│ from drawing    │ │ other values    │ │ defaulted       │ │ contractor      │
│                 │ │                 │ │                 │ │                 │
│ Source: SLD     │ │ Source: Formula │ │ Source: Default │ │ Source: Review  │
│ table, layout   │ │ derivation      │ │ assumption      │ │ stage input     │
└─────────────────┘ └─────────────────┘ └─────────────────┘ └─────────────────┘


                              ┌─────────────────────────────────────┐
                              │      OVERALL PIPELINE CONFIDENCE    │
                              │      (Weighted Average)             │
                              └─────────────────┬───────────────────┘
                                                │
┌───────────────────────────────────────────────────────────────────────────────────────────────┐
│                                                                                               │
│   CONFIDENCE = (0.05 × INGEST) + (0.10 × CLASSIFY) + (0.50 × DISCOVER)                       │
│              + (0.10 × REVIEW) + (0.15 × VALIDATE) + (0.10 × PRICE)                          │
│                                                                                               │
│   ┌───────────────────────────────────────────────────────────────────────────┐              │
│   │                                                                           │              │
│   │   INGEST ████                                    5%                       │              │
│   │   CLASSIFY ████████                             10%                       │              │
│   │   DISCOVER █████████████████████████████████████ 50%  ◀── MOST IMPORTANT  │              │
│   │   REVIEW ████████                               10%                       │              │
│   │   VALIDATE ████████████                         15%                       │              │
│   │   PRICE ████████                                10%                       │              │
│   │                                                                           │              │
│   └───────────────────────────────────────────────────────────────────────────┘              │
│                                                                                               │
│   IF CONFIDENCE < 70% → AUTO-ESCALATE TO OPUS 4.6 FOR RE-EXTRACTION                         │
│                                                                                               │
└───────────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## UI Flow Diagram

```
┌──────────────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                          USER INTERFACE FLOW                                                      │
└──────────────────────────────────────────────────────────────────────────────────────────────────────────────────┘

                                         ┌─────────────────────┐
                                         │    0_Welcome.py     │
                                         │   (Landing Page)    │
                                         │   • Tier cards      │
                                         │   • Advantages      │
                                         │   • How it works    │
                                         └──────────┬──────────┘
                                                    │
                         ┌──────────────────────────┼──────────────────────────┐
                         │                          │                          │
                         ▼                          ▼                          ▼
              ┌──────────────────┐      ┌──────────────────┐      ┌──────────────────┐
              │  Smart Upload    │      │  Guided Upload   │      │    Profile       │
              │  (Auto Mode)     │      │  (Step Mode)     │      │   (Settings)     │
              └────────┬─────────┘      └────────┬─────────┘      └──────────────────┘
                       │                         │
                       ▼                         ▼
              ┌──────────────────┐      ┌──────────────────┐
              │  1. Upload PDF   │      │  1. Upload PDF   │
              │  2. Auto Process │      │  2. Categorize   │
              │  3. View Results │      │     Pages        │
              │  4. Export       │      │  3. Run Passes   │
              └────────┬─────────┘      │     One-by-One   │
                       │                │  4. Review Each  │
                       │                │  5. Export       │
                       │                └────────┬─────────┘
                       │                         │
                       └─────────────────────────┘
                                    │
                                    ▼
                       ┌──────────────────────────┐
                       │     EXPORT OPTIONS       │
                       ├──────────────────────────┤
                       │ • PDF Quotation Summary  │
                       │ • Excel BOQ (4 sheets)   │
                       │   - Cover                │
                       │   - Bill of Quantities   │
                       │   - Summary              │
                       │   - Discrepancy Register │
                       │ • JSON Results           │
                       └──────────────────────────┘
```

---

## Data Model Hierarchy

```
┌──────────────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                       DATA MODEL HIERARCHY                                                        │
│                                    (agent/models.py - 1880 lines)                                                │
└──────────────────────────────────────────────────────────────────────────────────────────────────────────────────┘

PipelineResult (Final Output)
├─ stages: Dict[PipelineStage, StageResult]
│   ├─ INGEST → DocumentSet
│   ├─ CLASSIFY → ServiceTier + confidence
│   ├─ DISCOVER → ExtractionResult
│   ├─ REVIEW → CorrectionLog
│   ├─ VALIDATE → ValidationResult
│   ├─ PRICE → PricingResult
│   └─ OUTPUT → exports dict
│
├─ total_cost_zar: float (API cost)
├─ success: bool
└─ errors: List[str]

ExtractionResult (AI Output)
├─ metadata: ProjectMetadata
│   ├─ project_name, client_name, consultant_name
│   ├─ drawing_numbers: List[str]
│   └─ address, site_conditions
│
├─ building_blocks: List[BuildingBlock]
│   └─ BuildingBlock
│       ├─ name: str ("Main Building", "Block A")
│       ├─ distribution_boards: List[DistributionBoard]
│       │   └─ DistributionBoard
│       │       ├─ name: str ("DB-S1")
│       │       ├─ voltage_phase: str ("3PH+N+E")
│       │       ├─ breaker_rating_a: int (100)
│       │       └─ circuits: List[Circuit]
│       │           └─ Circuit
│       │               ├─ name: str ("L1")
│       │               ├─ type: CircuitType (LIGHTING, POWER)
│       │               ├─ mcb_rating_a: int (10)
│       │               ├─ cable_size_mm2: float (2.5)
│       │               ├─ num_points: int (8)
│       │               ├─ total_wattage_w: int (400)
│       │               └─ confidence: ItemConfidence
│       │
│       ├─ rooms: List[Room]
│       │   └─ Room
│       │       ├─ name: str ("Office A")
│       │       ├─ room_type: str ("office")
│       │       ├─ area_m2: float (45.5)
│       │       └─ fixtures: FixtureCounts
│       │           ├─ recessed_led_600x1200: int
│       │           ├─ downlight_led_6w: int
│       │           ├─ double_socket_1100: int
│       │           ├─ single_socket_1100: int
│       │           ├─ switch_1lever_1way: int
│       │           └─ total_points: int
│       │
│       ├─ heavy_equipment: List[HeavyEquipment]
│       │   └─ HeavyEquipment (HVAC, pumps, UPS)
│       │
│       └─ supply_points: List[SupplyPoint]
│
├─ site_cable_runs: List[SiteCableRun]
│   └─ SiteCableRun
│       ├─ from_db, to_location
│       ├─ installation_method (UNDERGROUND, SURFACE)
│       ├─ cable_size_mm2, length_m
│       └─ confidence
│
└─ discrepancies: List[Discrepancy]
    └─ Discrepancy
        ├─ type: str ("point_count_mismatch")
        ├─ severity: str ("critical", "warning")
        ├─ sld_source, layout_source
        └─ recommendation

PricingResult (BOQ Output)
├─ quantity_bq: List[BQLineItem]
│   └─ BQLineItem
│       ├─ item_no: str ("1.1")
│       ├─ section: BQSection (14 sections)
│       ├─ description: str
│       ├─ unit: str ("No", "m", "Set")
│       ├─ qty: float
│       ├─ rate: Optional[float] (None for qty-only)
│       ├─ amount: Optional[float]
│       ├─ source: ItemConfidence
│       └─ drawing_ref: str
│
├─ estimated_bq: List[BQLineItem] (with prices)
├─ section_subtotals: Dict[BQSection, float]
├─ total_vat_amount_zar: float
└─ total_estimate_zar: float
```

---

## Summary

**AfriPlan Electrical v5.0** is an AI-powered quantity take-off platform that:

1. **Ingests** electrical drawings (PDF/images) using PyMuPDF & Pillow
2. **Classifies** project tier using fast AI (Haiku/Groq) with R0.18 cost
3. **Extracts** detailed electrical inventory via multi-pass AI prompts
4. **Reviews** with human-in-the-loop contractor validation
5. **Validates** against SANS 10142-1:2017 South African standards
6. **Prices** deterministically using 1650-line SA material database
7. **Outputs** professional PDF quotations and Excel BOQ (4 sheets)

**Key Architecture Principles:**
- **Prompts direct AI extraction** (what to look for, schema to follow)
- **Code validates and prices** (deterministic, no AI for calculations)
- **Dual BQ output** (quantity-only primary + estimated secondary)
- **Multi-provider support** (100% FREE options via Groq/Grok)
- **75%+ accuracy** with multi-pass extraction + human review

**Golden Rule:** *Claude reads & interprets. Python calculates & prices.*
