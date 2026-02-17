# CLAUDE.md - AfriPlan Electrical Platform v3.0

## Project Overview

**Name:** AfriPlan Electrical
**Version:** 3.0 (AI Agent Edition)
**Purpose:** South African Electrical Quotation Platform - AI-Powered Document Analysis & Professional Quotations
**GitHub:** https://github.com/Jonathan-Lukwichi/afriplan-ai
**Live:** https://afriplan-ai.streamlit.app
**Author:** JLWanalytics

---

## Architecture Overview

AfriPlan Electrical v3.0 implements a **6-Stage AI Pipeline** for intelligent document analysis and quotation generation:

```
+--------------------------------------------------------------------------+
|                         6-STAGE AI PIPELINE                               |
+----------+----------+----------+-----------+----------+------------------+
|  INGEST  | CLASSIFY | DISCOVER | VALIDATE  |  PRICE   |     OUTPUT       |
|  PyMuPDF |  Haiku   |  Sonnet  |  Python   |  Python  |  PDF/Excel       |
|  Pillow  |   4.5    |   4.5    |  + Haiku  |   Only   |  fpdf2/openpyxl  |
|          |  R0.18   |  R1.80   |           |          |                  |
+----------+----------+----------+-----------+----------+------------------+
```

### Model Strategy (Cost-Optimized)

| Model | Purpose | Cost/Doc | Use Case |
|-------|---------|----------|----------|
| Haiku 4.5 | Fast classification | ~R0.18 | Tier routing, soft validation |
| Sonnet 4.5 | Balanced extraction | ~R1.80 | JSON extraction with confidence |
| Opus 4.6 | Escalation only | ~R8.50 | Low confidence re-extraction |

### Service Tiers (v3.0 - Simplified)

| Tier | Description | Standards |
|------|-------------|-----------|
| **Residential** | Houses, flats, domestic | SANS 10142-1, NRS 034 |
| **Commercial** | Offices, retail, hospitality | SANS 10142-1, SANS 10400-XA |
| **Maintenance** | COC inspections, repairs | SANS 10142-1:2017 |

*Note: Industrial and Infrastructure tiers deprecated in v3.0 (scope refocus)*

---

## Tech Stack

| Component | Technology | Version |
|-----------|------------|---------|
| **Frontend** | Streamlit | 1.30+ |
| **AI/LLM** | Claude API (Anthropic) | Haiku/Sonnet/Opus |
| **PDF Processing** | PyMuPDF (fitz) | 1.23+ |
| **PDF Export** | fpdf2 | 2.7+ |
| **Excel Export** | openpyxl | 3.1+ |
| **Optimization** | PuLP | 2.7+ |
| **Charts** | Plotly | 5.18+ |
| **CAD Export** | ezdxf | (optional) |

---

## Project Structure

```
afriplan-ai/
|-- app.py                              # Main application entry (58 lines)
|-- CLAUDE.md                           # This documentation file
|-- requirements.txt                    # Python dependencies
|-- questions.md                        # Expert validation questions
|
|-- agent/                              # AI Pipeline Package
|   |-- __init__.py                     # Package exports (v3.0.0)
|   |-- afriplan_agent.py               # 6-Stage Pipeline Orchestrator (~1000 lines)
|   |-- classifier.py                   # Tier Classification (Haiku 4.5)
|   |-- validators.py                   # SANS 10142-1 Hard Rules
|   +-- prompts/                        # AI Extraction Prompts
|       |-- __init__.py
|       |-- system_prompt.py            # SA Electrical Domain Knowledge
|       |-- residential_prompts.py      # Room-by-room extraction
|       |-- commercial_prompts.py       # Area-based W/m2 extraction
|       +-- maintenance_prompts.py      # COC/defect extraction
|
|-- pages/                              # Streamlit Multipage App
|   |-- 0_Welcome.py                    # Landing page with tier selection
|   |-- 1_Smart_Upload.py               # AI Document Analysis UI
|   |-- 2_Residential.py                # Residential quotations (~1200 lines)
|   |-- 3_Commercial.py                 # Commercial quotations (~500 lines)
|   +-- 4_Maintenance.py                # COC & Maintenance (~600 lines)
|
|-- utils/                              # Utility Functions
|   |-- __init__.py                     # Package initialization
|   |-- calculations.py                 # SANS 10142 calculation functions
|   |-- constants.py                    # Material databases (~1650 lines)
|   |-- components.py                   # Reusable UI components
|   |-- styles.py                       # Premium CSS (~1000 lines)
|   |-- pdf_generator.py                # PDF quotation export
|   |-- excel_exporter.py               # Excel BQ export
|   |-- optimizer.py                    # PuLP cost optimization
|   |-- eskom_forms.py                  # Eskom application helper
|   +-- document_analyzer.py            # Claude Vision API integration
|
|-- .streamlit/
|   |-- config.toml                     # Streamlit configuration
|   +-- secrets.toml.example            # API key template
|
|-- diagram1_app_flow.mermaid           # Application flow diagram
|-- diagram2_agent_flow.mermaid         # AI agent pipeline diagram
|-- diagram3_coc_pipeline.mermaid       # COC processing diagram
+-- diagram4_pipeline.mermaid           # Full pipeline diagram
```

---

## Detailed File Descriptions

### Core Application

#### `app.py` (58 lines)

**Role:** Main application entry point using Streamlit's modern navigation API.

**Key Functions:**
- `st.set_page_config()` - Page title, icon, layout settings
- `st.navigation()` - Multi-page routing with sidebar navigation

**Pages Defined:**
```python
welcome = st.Page("pages/0_Welcome.py", title="Welcome", default=True)
smart_upload = st.Page("pages/1_Smart_Upload.py", title="Smart Upload")
residential = st.Page("pages/2_Residential.py", title="Residential")
commercial = st.Page("pages/3_Commercial.py", title="Commercial")
maintenance = st.Page("pages/4_Maintenance.py", title="Maintenance & COC")
```

---

### Agent Package (`agent/`)

#### `agent/__init__.py` (49 lines)

**Role:** Package exports and version declaration (v3.0.0)

**Exports:**
- `AfriPlanAgent` - Main pipeline orchestrator
- `PipelineResult`, `StageResult`, `PipelineStage` - Result containers
- `TierClassifier`, `ClassificationResult`, `ServiceTier` - Classification

---

#### `agent/afriplan_agent.py` (~1000 lines)

**Role:** 6-Stage Pipeline Orchestrator - The brain of the AI system.

**Classes:**

1. **`PipelineStage`** (Enum)
   - `INGEST` - Document preprocessing
   - `CLASSIFY` - Tier routing
   - `DISCOVER` - JSON extraction
   - `VALIDATE` - SANS compliance
   - `PRICE` - Cost calculation
   - `OUTPUT` - PDF/Excel generation

2. **`StageResult`** (Dataclass)
   - `stage`: PipelineStage
   - `data`: Dict[str, Any]
   - `confidence`: float (0.0-1.0)
   - `processing_time_ms`: int
   - `model_used`: Optional[str]
   - `tokens_used`: int
   - `errors`: List[str]

3. **`PipelineResult`** (Dataclass)
   - `stages`: Dict[PipelineStage, StageResult]
   - `final_output`: Dict
   - `total_cost_zar`: float
   - `success`: bool

4. **`AfriPlanAgent`** (Main Class)

   **Methods:**
   - `process_document(file_bytes, file_type, filename)` -> PipelineResult
   - `_stage_ingest(file_bytes, file_type)` - PDF/image to base64
   - `_stage_classify(images, text)` - Haiku 4.5 tier detection
   - `_stage_discover(images, tier)` - Sonnet 4.5 JSON extraction
   - `_stage_validate(extracted_data, tier)` - Hard rules + soft checks
   - `_stage_price(validated_data, tier)` - Cost calculations
   - `_stage_output(priced_data, tier)` - Generate BQ items
   - `_escalate_to_opus(images, tier)` - Re-extract with Opus 4.6
   - `_parse_json_from_response(response)` - Robust JSON parser

**Key Features:**
- Confidence-based model escalation (< 70% -> Opus)
- Trailing comma fix in JSON parsing
- Auto-correction of compliance violations
- Token tracking and cost estimation

---

#### `agent/classifier.py` (~200 lines)

**Role:** Fast tier classification using Haiku 4.5.

**Classes:**

1. **`ServiceTier`** (Enum)
   ```python
   RESIDENTIAL = "residential"
   COMMERCIAL = "commercial"
   MAINTENANCE = "maintenance"
   UNKNOWN = "unknown"
   ```

2. **`ClassificationResult`** (Dataclass)
   - `tier`: ServiceTier
   - `confidence`: float
   - `subtype`: Optional[str]
   - `reasoning`: str

3. **`TierClassifier`**

   **Methods:**
   - `classify(text, images)` -> ClassificationResult
   - `_fallback_keyword_classification(text)` - No-API fallback

**Classification Prompt:** Instructs Haiku to return JSON with tier, confidence, subtype, reasoning.

---

#### `agent/validators.py` (~300 lines)

**Role:** SANS 10142-1:2017 hard rule validation.

**Classes:**

1. **`ValidationResult`** (Dataclass)
   - `rule_name`: str
   - `passed`: bool
   - `severity`: "critical" | "warning" | "info"
   - `message`: str
   - `auto_corrected`: bool
   - `corrected_value`: Any

2. **`SANS10142Validator`**

   **Methods:**
   - `validate_residential(data)` -> List[ValidationResult]
   - `validate_commercial(data)` -> List[ValidationResult]
   - `validate_maintenance(data)` -> List[ValidationResult]

**Hard Rules Enforced:**

| Rule | Requirement | Auto-Fix |
|------|-------------|----------|
| Max 10 lights/circuit | SANS 10142-1 | Add circuits |
| Max 10 plugs/circuit | SANS 10142-1 | Add circuits |
| ELCB mandatory | 63A 30mA required | Add to BQ |
| Dedicated stove circuit | 32A if stove present | Add circuit |
| Dedicated geyser circuit | 20A with timer | Add circuit |
| Voltage drop < 5% | 2.5% sub-mains + 2.5% final | Flag warning |
| Min 15% spare DB ways | Future expansion | Upsize DB |

---

#### `agent/prompts/system_prompt.py` (113 lines)

**Role:** SA Electrical domain knowledge shared across all prompts.

**Content:**
- Primary standards (SANS 10142-1:2017, NRS 034, SANS 10400-XA)
- Key wiring rules (max 10 points/circuit, ELCB mandatory)
- SA-specific knowledge (230V/400V, SURFIX cables, CBI/ABB brands)
- Load calculation standards (50W/light, 250W/plug, 50% diversity)
- ADMD values for residential supply sizing
- Dedicated circuit requirements
- Extraction rules for confidence scoring

---

#### `agent/prompts/residential_prompts.py` (185 lines)

**Role:** Room-by-room extraction prompt for residential plans.

**Extraction Schema:**
```json
{
  "project": { "dwelling_type", "floor_area_m2", "bedrooms", "bathrooms" },
  "rooms": [{ "room_name", "room_type", "area_m2", "lights", "sockets", "switches" }],
  "db_board": { "recommended_ways", "main_switch_a", "elcb", "surge_protection" },
  "geyser": { "location", "size_litres", "type", "circuit_required" },
  "outdoor": { "light_points", "gate_motor", "pool" },
  "cable_estimate": { "avg_run_m", "long_runs_flagged" }
}
```

**Default Values (when not visible):**

| Room Type | Lights | Doubles | Switches |
|-----------|--------|---------|----------|
| Bedroom | 2 | 2 | 2 |
| Bathroom | 2 | 1 | 1 |
| Kitchen | 3 | 4 | 2 |
| Living | 3 | 4 | 2 |

---

#### `agent/prompts/commercial_prompts.py` (208 lines)

**Role:** Area-based W/m2 extraction for commercial buildings.

**Power Density Standards:**

| Area Type | Lighting | Power | HVAC | Total W/m2 |
|-----------|----------|-------|------|------------|
| Open plan office | 11 | 20 | 80 | 111 |
| Server room | 9 | 1000 | 500 | 1509 |
| Retail | 20 | 30 | 60 | 110 |
| Restaurant | 15 | 72 | 60 | 147 |
| Warehouse | 8 | 8 | 15 | 31 |

**Extraction includes:**
- Three-phase distribution (MSB, sub-boards, phase balance)
- Emergency lighting and exit signs
- Fire alarm system (zones, detectors, MCPs, sounders)
- NMD (Notified Maximum Demand) calculation

---

#### `agent/prompts/maintenance_prompts.py` (174 lines)

**Role:** COC inspection and defect extraction.

**Work Types:**
- `coc_inspection` - Full SANS 10142-1 compliance check
- `fault_repair` - Specific fault diagnosis
- `db_upgrade` - DB board replacement
- `circuit_addition` - Adding circuits
- `rewire` - Partial/full rewiring
- `remedial` - Fix non-compliance items

**Defect Codes:**

| Code | Description | Severity |
|------|-------------|----------|
| `no_elcb` | No earth leakage device | critical |
| `no_earth_spike` | No earth spike | critical |
| `exposed_wiring` | Exposed live wiring | critical |
| `overloaded_circuit` | Circuit overloaded | high |
| `diy_work` | Non-compliant DIY work | high |
| `outdated_db` | Old DB board | medium |
| `no_surge` | No surge protection | medium |

---

### Pages (`pages/`)

#### `pages/0_Welcome.py`

**Role:** Landing page with tier selection and app overview.

**Features:**
- Hero section with animated gradient title
- Platform statistics (Standards, Tiers, Exports)
- Tier cards for Residential, Commercial, Maintenance
- "How It Works" timeline (Upload -> Configure -> Export)
- Quick navigation buttons to each tier

**UI Components Used:**
- `hero_section()`, `tier_card()`, `timeline_steps()`, `premium_footer()`

---

#### `pages/1_Smart_Upload.py` (~500 lines)

**Role:** AI-powered document analysis interface.

**Features:**
- File upload (PDF, PNG, JPG) with drag-drop
- Real-time AI processing with progress indicators
- 6-stage pipeline visualization
- Tabbed results view:
  - **Extraction Tab** - Raw JSON from AI
  - **Validation Tab** - SANS compliance flags
  - **Pricing Tab** - BQ preview with totals
- Confidence scoring with color indicators
- "Route to [Tier]" button for pre-filled quotation

**Session State:**
- `extracted_data` - AI extraction results
- `validation_report` - Compliance flags
- `ai_confidence` - Overall confidence score
- `from_smart_upload` - Flag for downstream pages

---

#### `pages/2_Residential.py` (~1200 lines)

**Role:** Comprehensive residential quotation page.

**Tabs:**

1. **Configure Tab**
   - Room editor with presets (2/3/4/5 bedroom)
   - Dedicated circuits section (stove, geyser, aircon, pool, gate)
   - Safety devices (smoke detectors, surge protection)
   - Calculate button

2. **Electrical Tab**
   - Room-by-room breakdown table
   - Circuit design summary
   - ADMD Calculator (Eskom supply sizing)
   - Voltage Drop Calculator
   - Essential Load Calculator (backup power sizing)

3. **Quote Tab**
   - Pricing summary with complexity/margin adjustments
   - BQ items by category
   - Smart Cost Optimizer (4 quotation options)

4. **Export Tab**
   - PDF quotation generation
   - Excel BQ export
   - COC pre-inspection checklist
   - Eskom application helper

**Project Types:**
- `new_house` - New construction
- `renovation` - Alterations/additions
- `solar_backup` - Solar & battery systems
- `smart_home` - Home automation
- `security` - Security systems
- `ev_charging` - EV charger installation
- `coc_compliance` - COC-focused work

---

#### `pages/3_Commercial.py` (~500 lines)

**Role:** Commercial building quotations.

**Sidebar Inputs:**
- Building type (office, retail, hospitality, healthcare, education)
- Floor area (m2)
- Number of floors
- Emergency power required
- Fire alarm system

**Tabs:**
1. **Configure** - Building parameters summary
2. **Load Study** - Load calculations, PFC calculator, energy efficiency
3. **Quote** - BQ with Smart Cost Optimizer
4. **Export** - PDF generation

**Calculations:**
- Power density (W/m2) by building type
- Three-phase load balancing
- Power Factor Correction (kVAr) sizing
- Fire detection zone calculation
- Energy efficiency rating (SANS 10400-XA)

---

#### `pages/4_Maintenance.py` (~600 lines)

**Role:** COC inspections and electrical repairs.

**Tabs:**

1. **Property Details**
   - Property type and size
   - Installation age
   - Reason for COC
   - Access difficulty
   - Age-based defect prediction

2. **Defects**
   - Defect selection by severity (critical/high/medium/low)
   - Quantity inputs per defect
   - Running remedial total

3. **Quote**
   - Inspection fee calculation
   - Remedial work items
   - Payment schedule

4. **Export**
   - PDF quotation
   - Excel BQ
   - COC checklist summary

**Inspection Fee Tiers:**

| Property Type | Base Fee | Certificate |
|---------------|----------|-------------|
| Basic (flat) | R1,500 | R450 |
| Standard | R1,800 | R450 |
| Large | R2,400 | R450 |
| Complex unit | R1,600 | R450 |
| Commercial | R3,500 | R650 |

---

### Utilities (`utils/`)

#### `utils/constants.py` (~1650 lines)

**Role:** Comprehensive database of SA electrical materials, pricing, and standards.

**Major Databases:**

| Database | Description | Items |
|----------|-------------|-------|
| `ELECTRICAL_CABLES` | Surfix cables, earth wire | 5+ |
| `ELECTRICAL_DB` | DB boards, MCBs, ELCBs | 20+ |
| `ELECTRICAL_SAFETY` | Smoke detectors, emergency lights | 7 |
| `ELECTRICAL_ACCESSORIES` | Switches, sockets, isolators | 23 |
| `ELECTRICAL_LIGHTS` | LED downlights, battens, floods | 9 |
| `ELECTRICAL_CONDUIT` | PVC conduit, junction boxes | 14 |
| `ELECTRICAL_LABOUR` | Labour rates per task | 10 |
| `DEDICATED_CIRCUITS` | Stove, geyser, aircon, pool | 9 |
| `COMPLEXITY_FACTORS` | New build, renovation, rewire | 7 |
| `PAYMENT_TERMS` | 40/40/20, 50/30/20, etc. | 3 |
| `COC_INSPECTION_FEES` | Property type fees | 6 |
| `COC_DEFECT_PRICING` | Defect repair costs | 20+ |
| `COC_AGE_DEFECT_LIKELIHOOD` | Age-based failure rates | 4 |
| `COMMERCIAL_LOAD_FACTORS` | W/m2 by building type | 6 |
| `COMMERCIAL_DISTRIBUTION` | MSB/sub-board specs | 3 |
| `COMMERCIAL_EMERGENCY_POWER` | Generator packages | 3 |
| `ADMD_VALUES` | NRS 034 dwelling types | 5 |
| `SANS_10142_CABLE_RATINGS` | Current capacity tables | 8 |
| `VOLTAGE_DROP_LIMITS` | mV/A/m values | 8 |
| `ESSENTIAL_LOADS` | Backup power loads | 12 |

**Dedicated Circuits (Big-Ticket Items):**

| Circuit | Description | Total Cost |
|---------|-------------|------------|
| `stove_circuit_3phase` | Stove (3-phase 32A) | R3,800 |
| `stove_circuit_single` | Stove (single-phase) | R2,800 |
| `geyser_circuit` | Geyser + timer | R2,600 |
| `aircon_circuit` | Aircon (20A) | R2,200 |
| `pool_pump_circuit` | Pool pump (IP65) | R2,400 |
| `gate_motor_circuit` | Gate motor | R1,800 |

---

#### `utils/calculations.py` (~600 lines)

**Role:** SANS 10142 compliant calculation functions.

**Key Functions:**

1. **`calculate_electrical_requirements(rooms)`**
   - Input: List of rooms with type and dimensions
   - Output: Total lights, plugs, room details, dedicated circuits
   - Scales requirements for larger rooms

2. **`calculate_load_and_circuits(elec_req)`**
   - Applies 50% diversity factor
   - Calculates lighting/power circuits (max 10 points each)
   - Sizes DB board and main breaker
   - Returns total load in kVA

3. **`calculate_electrical_bq(elec_req, circuit_info)`**
   - Generates complete Bill of Quantities
   - Categories: DB Board, Cables, Conduit, Switches/Sockets, Lights, Labour, Compliance

4. **`calculate_commercial_electrical(area_m2, building_type, floors, emergency, fire)`**
   - Area-based W/m2 calculations
   - Three-phase load balancing
   - Emergency lighting calculations

5. **`calculate_admd(dwelling_type, num_dwellings, geyser_type, has_pool, has_aircon)`**
   - NRS 034 ADMD calculation
   - Adjustments for solar/gas geyser, pool, aircon
   - Returns recommended supply size

6. **`calculate_voltage_drop(cable_size, length, current, voltage, phase)`**
   - Uses SANS 10142-1 Annexure B values
   - Returns voltage drop %, compliance status

7. **`calculate_cable_size(load_current, length, phase, installation_method)`**
   - Selects appropriate cable size
   - Considers current capacity and voltage drop

8. **`calculate_essential_load(selected_loads, runtime_hours)`**
   - Sizes inverter and battery for backup power
   - Returns system specs and estimated cost

9. **`calculate_pfc(active_kw, current_pf, target_pf)`**
   - Power factor correction sizing
   - Returns kVAr required, bank size, estimated cost, payback

10. **`calculate_energy_efficiency(lighting_w, area_m2, building_type)`**
    - SANS 10400-XA LPD compliance check
    - Returns efficiency class (A-F)

11. **`calculate_fire_detection(area_m2, building_type, floors, detector_type)`**
    - SANS 10139 zone calculation
    - Returns detector counts, panel type, BQ items

12. **`generate_coc_checklist(installation_data)`**
    - Pre-inspection compliance checklist
    - Returns pass/fail/warning items

---

#### `utils/pdf_generator.py` (278 lines)

**Role:** Professional PDF quotation export using fpdf2.

**Functions:**

1. **`generate_electrical_pdf(elec_req, circuit_info, bq_items, admd_data, vd_data)`**
   - Full residential quotation PDF
   - Sections: Project Summary, ADMD, Voltage Drop, BQ Table, Totals, Notes
   - Brand color: #00D4FF (Fluorescent Cyan)

2. **`generate_generic_electrical_pdf(bq_items, summary, tier, subtype)`**
   - Generic PDF for any project type
   - Sections: Project Info, Summary, BQ Table, Totals, Notes

**PDF Features:**
- SANS-compliant branding
- Quote reference number
- 30-day validity
- Payment terms (40/40/20)
- COC inclusion statement

---

#### `utils/excel_exporter.py` (315 lines)

**Role:** Professional Excel BQ export using openpyxl.

**Functions:**

1. **`export_bq_to_excel(bq_items, project_info, calculation_data)`**
   - **Sheet 1: Cover** - Project details and quotation summary
   - **Sheet 2: Bill of Quantities** - Items grouped by category
   - **Sheet 3: Calculations** - Calculation backup (optional)

2. **`export_load_study_to_excel(load_data, project_name)`**
   - Load study calculation export

**Excel Features:**
- Professional styling with brand colors
- Bordered tables with subtotals
- Currency formatting (R #,##0.00)
- Category headers with grouping

---

#### `utils/components.py` (231 lines)

**Role:** Reusable UI components for consistent styling.

**Functions:**

| Function | Purpose |
|----------|---------|
| `hero_section(title, subtitle, badge, stats)` | Animated hero with stats |
| `section_header(title, subtitle)` | Styled section divider |
| `glass_card(content)` | Glassmorphism card wrapper |
| `tier_card(title, description, tags)` | Project tier selection card |
| `metric_card(value, label, color)` | KPI display card |
| `timeline_steps(steps)` | Horizontal timeline |
| `page_header(title, subtitle)` | Inner page header |
| `loading_animation()` | Three-dot pulse animation |
| `premium_footer()` | App footer with branding |

---

#### `utils/styles.py` (~1000 lines)

**Role:** Premium futuristic dark-tech CSS styling.

**Design System:**
- **Fonts:** Orbitron (headings), Rajdhani (labels), Inter (body)
- **Primary Color:** #00D4FF (Fluorescent Cyan)
- **Background:** Animated grid with floating glow orbs
- **Cards:** Glassmorphism with blur effect

**Key CSS Classes:**

| Class | Purpose |
|-------|---------|
| `.hero-title` | Gradient shimmer animation |
| `.glass-card` | Glassmorphism container |
| `.tier-card` | Project tier selection |
| `.metric-card` | KPI display |
| `.bq-table` | Bill of quantities table |
| `.quote-option` | Cost optimizer cards |

**Streamlit Overrides:**
- Tabs with neon glow effect
- Navigation cards with hover animations
- Input fields with focus borders
- Sidebar dark gradient

---

#### `utils/optimizer.py` (206 lines)

**Role:** Smart Cost Optimizer and PuLP OR optimization.

**Functions:**

1. **`generate_quotation_options(bq_items, elec_req, circuit_info)`**

   Returns 4 quotation strategies:

   | Option | Strategy | Markup | Quality |
   |--------|----------|--------|---------|
   | A: Budget | Cheapest suppliers | 12% | 3/5 |
   | B: Best Value | Balanced (RECOMMENDED) | 18% | 4/5 |
   | C: Premium | Top-tier brands | 22% | 5/5 |
   | D: Competitive | Win the job | 10% | 3.5/5 |

2. **`optimize_quotation_or(bq_items, constraints)`**
   - PuLP Integer Linear Programming
   - Minimizes cost while meeting quality constraints
   - Returns optimal supplier selection per category

---

#### `utils/eskom_forms.py` (309 lines)

**Role:** Eskom supply application helper.

**Functions:**

1. **`generate_eskom_application(project_type, load_data, location, applicant_details)`**
   - Generates pre-populated application data
   - Project types: `new_connection`, `upgrade`, `temporary`
   - Returns: load details, required documents, cost estimate, timeline, contact info

2. **`estimate_connection_costs(admd_kva, supply_type, project_type)`**
   - Connection fees by supply size
   - Meter deposits
   - Extension costs

3. **`generate_application_summary_text(application)`**
   - Text summary for display/export

**Eskom Fee Estimates (2025):**

| Supply | Connection Fee | Deposit |
|--------|---------------|---------|
| 20A 1-phase | R3,500 | R500 |
| 60A 1-phase | R5,500 | R750 |
| 80A 1-phase | R7,500 | R1,000 |
| 80A 3-phase | R18,000 | R2,500 |
| 160A 3-phase | R35,000 | R5,000 |

---

#### `utils/document_analyzer.py` (491 lines)

**Role:** Claude Vision API integration for document classification.

**Classes:**

1. **`ProjectTier`** (Enum)
   - RESIDENTIAL, COMMERCIAL, MAINTENANCE, INDUSTRIAL (deprecated), INFRASTRUCTURE (deprecated), UNKNOWN

2. **`AnalysisResult`** (Dataclass)
   - `tier`, `confidence`, `subtype`, `extracted_data`, `reasoning`, `warnings`

3. **`DocumentAnalyzer`**

   **Methods:**
   - `analyze_document(file_bytes, file_type, filename)` -> AnalysisResult
   - `_build_analysis_prompt()` - Vision prompt construction
   - `_call_vision_api(images, media_type, prompt)` - API call
   - `_pdf_to_images(pdf_bytes)` - PDF page rendering
   - `_parse_response(response)` - JSON extraction
   - `_fallback_analysis(filename)` - Keyword-based fallback

**Helper Functions:**
- `get_tier_page_path(tier)` - Page routing
- `get_tier_display_info(tier)` - Icon, name, color

**Classification Criteria:**
- Keywords mapped to each tier
- Subtype detection (new_house, office, coc_inspection, etc.)
- Confidence scoring based on keyword matches

---

## SA Electrical Standards Reference

### SANS 10142-1:2017 Key Rules

| Rule | Requirement |
|------|-------------|
| Max lighting points | 10 per circuit |
| Max power points | 10 per circuit |
| Stove circuit | Dedicated 32A (3-phase recommended) |
| Geyser circuit | Dedicated 20A with timer |
| Earth leakage | 30mA RCD mandatory |
| Surge protection | Type 2 recommended |
| Voltage drop | Max 5% (2.5% sub-mains + 2.5% final) |
| COC | Required for all new/altered installations |

### Load Calculation (LED Era)

| Load | Value |
|------|-------|
| Light point | 50W |
| Plug point | 250W |
| Diversity factor | 50% residential |
| Power factor | 0.85 |

### NRS 034 ADMD Values

| Dwelling Type | ADMD (kVA) | Supply |
|---------------|------------|--------|
| RDP/Low cost | 1.5-2.0 | 20A |
| Standard house | 3.5-4.0 | 60A |
| Medium house | 5.0-6.0 | 60A |
| Large house | 8.0-10.0 | 80A |
| Luxury estate | 12.0-15.0 | 100A |

---

## Configuration

### Environment Variables

```bash
ANTHROPIC_API_KEY=sk-ant-api03-your-key-here
```

### Streamlit Secrets (`.streamlit/secrets.toml`)

```toml
ANTHROPIC_API_KEY = "sk-ant-api03-your-key-here"
```

### Dependencies (`requirements.txt`)

```
streamlit>=1.30.0
matplotlib>=3.8.0
numpy>=1.24.0
fpdf2>=2.7.0
Pillow>=10.0.0
plotly>=5.18.0
pandas>=2.0.0
PuLP>=2.7.0
openpyxl>=3.1.0
anthropic>=0.18.0
PyMuPDF>=1.23.0
```

---

## Git Workflow

```bash
# Commit changes
git add -A
git commit -m "feat: description"
git push origin main

# Streamlit Cloud auto-deploys from main branch
```

---

## Payment Terms (SA Industry Standard)

| Option | Structure | Use Case |
|--------|-----------|----------|
| Standard | 40% / 40% / 20% | Most projects |
| Conservative | 50% / 30% / 20% | New clients |
| Progress-Based | 30% / 30% / 30% / 10% | Large projects |

---

## Color Scheme

```css
:root {
  --primary: #00D4FF;       /* Fluorescent Cyan */
  --primary-dark: #0099FF;  /* Darker Cyan */
  --background: #0a0e1a;    /* Deep Navy */
  --surface: #111827;       /* Dark Surface */
  --text: #f1f5f9;          /* Light Text */
  --text-muted: #94a3b8;    /* Muted Text */
  --success: #22C55E;       /* Green */
  --warning: #F59E0B;       /* Amber */
  --danger: #EF4444;        /* Red */
}
```

---

## Future Roadmap

### Phase 1: User Accounts
- [ ] Authentication
- [ ] Project saving
- [ ] Quote history

### Phase 2: Contractor Marketplace
- [ ] Contractor profiles
- [ ] Customer reviews
- [ ] Job matching

### Phase 3: Mobile App
- [ ] React Native app
- [ ] Offline support
- [ ] Camera scanning

### Phase 4: API Platform
- [ ] REST API
- [ ] Webhook integrations
- [ ] Third-party apps

---

## Support

**Issues:** https://github.com/Jonathan-Lukwicki/afriplan-ai/issues
**Live App:** https://afriplan-ai.streamlit.app

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 3.0.0 | Feb 2026 | AI Agent Pipeline, 6-stage processing, model escalation |
| 2.0.0 | Jan 2026 | Smart Upload, dedicated circuits, complexity factors |
| 1.0.0 | Dec 2025 | Initial release, 4 tiers, basic calculations |
