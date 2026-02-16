# CLAUDE.md - AfriPlan Electrical Platform

## Project Overview

**Name:** AfriPlan Electrical
**Purpose:** SA Electrical Quotation Platform - 3 Service Tiers
**GitHub:** https://github.com/Jonathan-Lukwichi/afriplan-ai
**Live:** https://afriplan-ai.streamlit.app
**Version:** 3.0 (AI Agent Pipeline Edition)

---

## Tech Stack

| Component | Technology |
|-----------|------------|
| Frontend | Streamlit (Python) |
| AI Pipeline | Claude API (Anthropic) |
| PDF Export | fpdf2 |
| Excel Export | openpyxl |
| Optimization | PuLP (Operations Research) |
| CAD Export | ezdxf |
| PDF Processing | PyMuPDF (fitz) |
| Image Processing | Pillow |

### AI Models Used

| Model | Use Case | Cost (ZAR/doc) |
|-------|----------|----------------|
| Haiku 4.5 | Fast classification | ~R0.18 |
| Sonnet 4.5 | Balanced extraction | ~R1.80 |
| Opus 4.6 | Escalation for low confidence | ~R8.50 |

---

## Project Structure

```
afriplan-ai/
├── app.py                          # Main application entry (st.navigation)
├── agent/                          # v3.0 AI Agent Pipeline
│   ├── __init__.py                 # Package exports
│   ├── afriplan_agent.py           # 6-stage pipeline orchestrator
│   ├── classifier.py               # Tier classification logic
│   └── prompts/                    # Tier-specific prompts
│       ├── system_prompt.py        # SA electrical context
│       ├── residential_prompts.py  # Room-based extraction
│       ├── commercial_prompts.py   # Area-based extraction
│       └── maintenance_prompts.py  # COC/defect extraction
├── pages/
│   ├── 0_Welcome.py                # Landing page with tier selection
│   ├── 1_Smart_Upload.py           # AI document analysis (v3.0)
│   ├── 2_Residential.py            # Residential quotations
│   ├── 3_Commercial.py             # Commercial quotations
│   └── 4_Maintenance.py            # Maintenance & COC
├── utils/
│   ├── __init__.py                 # Package initialization
│   ├── calculations.py             # SANS 10142 calculation functions
│   ├── constants.py                # Material databases & pricing
│   ├── validators.py               # SANS 10142-1 hard rule validator
│   ├── pdf_generator.py            # PDF quotation export
│   ├── excel_exporter.py           # Excel BQ export
│   ├── eskom_forms.py              # Eskom application helper
│   ├── components.py               # Reusable UI components
│   ├── optimizer.py                # PuLP cost optimization
│   ├── styles.py                   # Custom CSS styling
│   └── document_analyzer.py        # Legacy Claude Vision integration
├── .streamlit/
│   ├── config.toml                 # Streamlit configuration
│   └── secrets.toml                # API key (ANTHROPIC_API_KEY)
├── requirements.txt                # Python dependencies
├── .gitignore                      # Git ignore rules
├── questions.md                    # Expert validation questions
└── CLAUDE.md                       # This file
```

---

## v3.0 AI Agent Pipeline

### 6-Stage Processing

```
INGEST → CLASSIFY → DISCOVER → VALIDATE → PRICE → OUTPUT
```

| Stage | Description | AI Model | Purpose |
|-------|-------------|----------|---------|
| 1. INGEST | Document processing | None | Convert PDF/image to Claude-ready format |
| 2. CLASSIFY | Tier detection | Haiku 4.5 | Fast routing to residential/commercial/maintenance |
| 3. DISCOVER | JSON extraction | Sonnet 4.5 | Extract rooms, areas, circuits, defects |
| 4. VALIDATE | SANS 10142-1 check | None | Python hard rules + auto-corrections |
| 5. PRICE | Cost calculation | None | Deterministic pricing from constants.py |
| 6. OUTPUT | Quote generation | None | PDF/Excel export |

### Confidence & Escalation

- **High confidence (≥70%)**: Direct processing
- **Medium confidence (40-70%)**: Warning displayed, recommend verification
- **Low confidence (<40%)**: Escalate DISCOVER to Opus 4.6

---

## Service Tiers (v3.0)

### Tier 1: Residential
- Room-by-room configuration
- ADMD calculation (NRS 034)
- Dedicated circuits (stove, geyser, aircon, pool)
- Safety devices (smoke detectors, surge protection)

### Tier 2: Commercial
- Area-based W/m² calculations
- Three-phase load balancing
- Emergency lighting & fire detection
- Building types: office, retail, hospitality, healthcare, education

### Tier 3: Maintenance & COC
- COC inspection quotations
- Fault finding & repairs
- DB board upgrades
- Remedial work from defect lists

**Note:** Industrial and Infrastructure tiers deprecated in v3.0 (scope refocus)

---

## Current Implementation Status

### AI Pipeline - COMPLETE
- [x] 6-stage pipeline orchestration
- [x] Multi-model strategy (Haiku → Sonnet → Opus)
- [x] Confidence scoring and escalation
- [x] JSON extraction with parse error handling
- [x] SANS 10142-1 hard rule validation
- [x] Validation metrics (passed/failed/warnings/score)
- [x] Cost tracking per stage (ZAR)

### Tier 1: Residential - COMPLETE
- [x] Room-based configuration
- [x] SANS 10142 compliant calculations
- [x] ADMD calculator (NRS 034)
- [x] Voltage drop verification
- [x] Cable sizing per Annexure B
- [x] Dedicated circuits section
- [x] Safety devices
- [x] Complexity factors (1.0x - 1.5x)
- [x] Profit margin slider (10-50%)
- [x] Payment terms (40/40/20 standard)
- [x] PDF & Excel export
- [x] COC checklist generator

### Tier 2: Commercial - COMPLETE
- [x] Area-based calculations
- [x] Building type selection
- [x] Three-phase load calculations
- [x] Emergency lighting
- [x] Fire detection zones
- [x] PDF & Excel export

### Tier 3: Maintenance & COC - COMPLETE
- [x] Property type selection
- [x] COC inspection pricing
- [x] Defect detection from photos
- [x] Remedial work quotations
- [x] PDF & Excel export

---

## Key Constants & Databases

### utils/constants.py

| Database | Description | Items |
|----------|-------------|-------|
| ELECTRICAL_CABLES | Surfix cables, earth wire | 5 |
| ELECTRICAL_DB | DB boards, breakers, ELCBs | 20+ |
| ELECTRICAL_SAFETY | Smoke detectors, emergency lights | 7 |
| ELECTRICAL_ACCESSORIES | Switches, sockets, isolators | 23 |
| ELECTRICAL_LIGHTS | LED downlights, battens, floods | 9 |
| ELECTRICAL_CONDUIT | PVC conduit, junction boxes | 14 |
| ELECTRICAL_LABOUR | Labour rates per task | 10 |
| DEDICATED_CIRCUITS | Stove, geyser, aircon, pool, gate | 9 |
| COMPLEXITY_FACTORS | New build, renovation, rewire | 7 |
| PAYMENT_TERMS | 40/40/20, 50/30/20, 30/30/30/10 | 3 |

### Dedicated Circuits (Big-ticket items)

| Circuit | Description | Total Cost |
|---------|-------------|------------|
| stove_circuit_3phase | Stove circuit (3-phase 32A) | R3,800 |
| stove_circuit_single | Stove circuit (single-phase) | R2,800 |
| geyser_circuit | Geyser circuit + timer | R2,600 |
| aircon_circuit | Aircon circuit (20A) | R2,200 |
| pool_pump_circuit | Pool pump (IP65) | R2,400 |
| gate_motor_circuit | Gate motor circuit | R1,800 |
| dishwasher_circuit | Dishwasher (16A) | R1,400 |
| washing_machine_circuit | Washing machine (16A) | R1,400 |

---

## SA Electrical Standards Reference

### SANS 10142-1:2017 Key Rules (Primary SA Wiring Standard)
- Max 10 points per lighting circuit
- Max 10 points per power circuit
- Stove: dedicated 32A circuit (3-phase recommended)
- Geyser: dedicated 20A circuit with timer
- Earth leakage protection mandatory (30mA RCD)
- Surge protection recommended (Type 1+2)
- Voltage drop max 5% (2.5% sub-mains + 2.5% final)
- COC (Certificate of Compliance) required for all installations

### Load Calculation (Updated for LED era)
- Light point: 50W (LED standard)
- Plug point: 250W
- Diversity factor: 50% residential
- Power factor: 0.85

### NRS 034 ADMD Values

| Dwelling Type | ADMD (kVA) | Supply |
|--------------|------------|--------|
| RDP/Low cost | 1.5-2.0 | 20A |
| Standard house | 3.5-4.0 | 60A |
| Medium house | 5.0-6.0 | 60A |
| Large house | 8.0-10.0 | 80A |
| Luxury estate | 12.0-15.0 | 100A |

---

## Payment Terms (SA Industry Standard)

| Option | Structure | Use Case |
|--------|-----------|----------|
| Standard | 40% / 40% / 20% | Most projects |
| Conservative | 50% / 30% / 20% | New clients |
| Progress-Based | 30% / 30% / 30% / 10% | Large projects |

---

## API Configuration

### Claude API (v3.0 Pipeline)

Set API key via:
1. **Environment Variable:** `ANTHROPIC_API_KEY`
2. **Streamlit Secrets:** `.streamlit/secrets.toml`

```toml
# .streamlit/secrets.toml
ANTHROPIC_API_KEY = "sk-ant-api03-your-key-here"
```

### Model IDs

```python
MODEL_HAIKU = "claude-3-5-haiku-20241022"   # Fast classification
MODEL_SONNET = "claude-sonnet-4-20250514"   # Balanced extraction
MODEL_OPUS = "claude-opus-4-20250514"       # Premium escalation
```

---

## Dependencies

```
streamlit>=1.30.0
matplotlib>=3.8.0
numpy>=1.24.0
fpdf2>=2.7.0
Pillow>=10.0.0
plotly>=5.18.0
ezdxf
pandas>=2.0.0
PuLP>=2.7.0
openpyxl>=3.1.0
anthropic>=0.18.0
PyMuPDF>=1.23.0
```

---

## Git Workflow

After completing features:
```bash
git add -A
git commit -m "feat: [description]"
git push origin main
```

Streamlit Cloud auto-deploys from main branch.

---

## Recent Changes (v3.0)

### AI Agent Pipeline
- 6-stage orchestrated processing
- Multi-model strategy (Haiku → Sonnet → Opus escalation)
- Confidence scoring with weighted averages
- Cost tracking per stage in ZAR

### Smart Document Upload
- Full pipeline visualization with progress
- Stage-by-stage confidence display
- Editable extraction results
- SANS 10142-1 validation with passed/failed metrics

### Scope Refocus
- Simplified to 3 tiers: Residential, Commercial, Maintenance
- Industrial and Infrastructure tiers deprecated
- Focused on core SA contractor market

### Validation Improvements
- Hard rule validation (Python, no AI)
- Auto-correction for common issues (ELCB, surge protection)
- Compliance scoring (percentage based)

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

**Issues:** https://github.com/Jonathan-Lukwichi/afriplan-ai/issues
**Live App:** https://afriplan-ai.streamlit.app
