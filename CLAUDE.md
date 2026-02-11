# CLAUDE.md - AfriPlan Electrical Platform

## Project Overview

**Name:** AfriPlan Electrical
**Purpose:** SA Electrical Quotation Platform - All Sectors
**GitHub:** https://github.com/Jonathan-Lukwichi/afriplan-ai
**Live:** https://afriplan-ai.streamlit.app
**Version:** 2.0 (Professional Edition)

---

## Tech Stack

| Component | Technology |
|-----------|------------|
| Frontend | Streamlit (Python) |
| PDF Export | fpdf2 |
| Excel Export | openpyxl |
| Optimization | PuLP (Operations Research) |
| CAD Export | ezdxf |
| AI Analysis | Claude Vision API (Anthropic) |
| PDF Processing | PyMuPDF |

---

## Project Structure

```
afriplan-ai/
├── app.py                          # Main application entry
├── pages/
│   ├── 0_Welcome.py                # Landing page with tier selection
│   ├── 1_Residential.py            # Residential quotations
│   ├── 2_Commercial.py             # Commercial quotations
│   ├── 3_Industrial.py             # Industrial/mining quotations
│   ├── 4_Infrastructure.py         # Township/street lighting
│   └── 5_Smart_Upload.py           # AI document analysis
├── utils/
│   ├── __init__.py                 # Package initialization
│   ├── calculations.py             # SANS 10142 calculation functions
│   ├── constants.py                # Material databases & pricing
│   ├── pdf_generator.py            # PDF quotation export
│   ├── excel_exporter.py           # Excel BQ export
│   ├── eskom_forms.py              # Eskom application helper
│   ├── components.py               # Reusable UI components
│   ├── optimizer.py                # PuLP cost optimization
│   ├── styles.py                   # Custom CSS styling
│   └── document_analyzer.py        # Claude Vision API integration
├── .streamlit/
│   ├── config.toml                 # Streamlit configuration
│   └── secrets.toml.example        # API key template
├── requirements.txt                # Python dependencies
├── .gitignore                      # Git ignore rules
└── CLAUDE.md                       # This file
```

---

## Current Implementation Status

### Tier 1: Residential - COMPLETE
- [x] Room-based configuration
- [x] SANS 10142 compliant calculations
- [x] ADMD calculator (NRS 034)
- [x] Voltage drop verification
- [x] Cable sizing per Annexure B
- [x] Dedicated circuits section (stove, geyser, aircon, pool)
- [x] Safety devices (smoke detectors, surge protection)
- [x] Complexity factors (new build vs renovation)
- [x] Profit margin slider (10-50%)
- [x] Payment terms (40/40/20 standard)
- [x] Solar & backup power
- [x] Smart home automation
- [x] Security systems
- [x] EV charging
- [x] PDF & Excel export
- [x] COC checklist generator

### Tier 2: Commercial - COMPLETE
- [x] Area-based calculations
- [x] Office, retail, hospitality, healthcare, education
- [x] Three-phase load calculations
- [x] Emergency lighting
- [x] Fire detection zones
- [x] PDF & Excel export

### Tier 3: Industrial - COMPLETE
- [x] Motor load calculations
- [x] MCC panel sizing
- [x] MV equipment (mining)
- [x] Hazardous area compliance
- [x] MHSA standards
- [x] PDF & Excel export

### Tier 4: Infrastructure - COMPLETE
- [x] Township electrification (NRS 034)
- [x] Street lighting (SANS 10098)
- [x] Rural electrification
- [x] Utility-scale solar
- [x] Mini-grids
- [x] Municipal submission requirements
- [x] NERSA compliance
- [x] PDF & Excel export

### Smart Features - COMPLETE
- [x] Smart Document Upload (Claude Vision API)
- [x] Automatic project classification
- [x] Data extraction from plans
- [x] Intelligent routing to correct tier

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

### SANS 10142-1 Key Rules
- Max 10 points per lighting circuit
- Max 10 points per power circuit
- Stove: dedicated 32A circuit (3-phase recommended)
- Geyser: dedicated 20A circuit with timer
- Earth leakage protection mandatory (30mA)
- Surge protection recommended (Type 1+2)
- Voltage drop max 5% (2.5% sub-mains + 2.5% final)

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

### Claude Vision API (Smart Upload)

Set API key via:
1. **Environment Variable:** `ANTHROPIC_API_KEY`
2. **Streamlit Secrets:** `.streamlit/secrets.toml`

```toml
# .streamlit/secrets.toml
ANTHROPIC_API_KEY = "sk-ant-api03-your-key-here"
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

## Recent Changes (v2.0)

### Smart Document Upload
- Claude Vision API integration
- Automatic tier classification
- Project data extraction
- Intelligent routing

### Professional Pricing Tools
- Complexity factors (1.0x - 1.5x)
- Profit margin slider (10-50%)
- Payment terms selection
- Deposit calculation

### Dedicated Circuits
- Stove circuit (3-phase 32A)
- Geyser circuit with timer
- Aircon circuits
- Pool pump circuit
- Gate motor circuit
- Safety devices (smoke detectors)

### Updated Standards
- LED load calculation (50W vs 100W)
- 40/40/20 payment terms
- Room-based auto-population

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
