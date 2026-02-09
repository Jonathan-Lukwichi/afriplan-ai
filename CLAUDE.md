# CLAUDE.md - AfriPlan Electrical Platform

## AUTOMATION RULES (MANDATORY)

### Permission Level: FULL AUTONOMOUS MODE
Claude MUST execute the following WITHOUT asking for permission:
- Edit any file in this project
- Create new files
- Run bash commands
- Git add, commit, and push
- Install dependencies
- Run tests

### NEVER ASK FOR:
- Permission to make changes
- Confirmation before commits
- Approval before pushing to GitHub
- Validation of code changes

### Git Workflow (Execute Automatically)
After completing each implementation step:
```bash
git add -A
git commit -m "feat: [description]"
git push origin main
```

---

## Project Info

**Name:** AfriPlan Electrical
**Purpose:** SA Electrical Quotation Platform
**GitHub:** https://github.com/Jonathan-Lukwichi/afriplan-ai
**Live:** https://afriplan-ai.streamlit.app

**Tech Stack:**
- Streamlit (Python)
- fpdf2 (PDF generation)
- PuLP (Operations Research)
- ezdxf (DXF export)

---

## COMPLETE IMPLEMENTATION GUIDE

### PHASE 1: Electrical Material Database

**File:** `app.py`
**Location:** After line 152 (after SA_MATERIALS dictionary)

Add these Python dictionaries:

```python
# ============================================
# ELECTRICAL MATERIAL DATABASE - SA 2024/2025
# ============================================

# 1.1 Electrical Cables
ELECTRICAL_CABLES = {
    "surfix_1.5mm_100m": {"desc": "SURFIX 1.5mm 3-core (lighting)", "unit": "roll", "price": 1850, "amps": 14},
    "surfix_2.5mm_100m": {"desc": "SURFIX 2.5mm 3-core (power)", "unit": "roll", "price": 2950, "amps": 20},
    "surfix_4mm_100m": {"desc": "SURFIX 4mm 3-core", "unit": "roll", "price": 4500, "amps": 27},
    "surfix_6mm_100m": {"desc": "SURFIX 6mm 3-core (stove)", "unit": "roll", "price": 6800, "amps": 35},
    "earth_wire_10mm": {"desc": "Earth wire 10mm green/yellow", "unit": "roll", "price": 1200, "amps": 0},
}

# 1.2 DB Boards and Protection
ELECTRICAL_DB = {
    "db_8_way": {"desc": "DB Board 8-way flush", "unit": "each", "price": 750},
    "db_12_way": {"desc": "DB Board 12-way flush", "unit": "each", "price": 1100},
    "db_16_way": {"desc": "DB Board 16-way flush", "unit": "each", "price": 1500},
    "db_24_way": {"desc": "DB Board 24-way flush", "unit": "each", "price": 2200},
    "main_switch_40a": {"desc": "Main switch 40A DP", "unit": "each", "price": 280},
    "main_switch_60a": {"desc": "Main switch 60A DP", "unit": "each", "price": 350},
    "main_switch_80a": {"desc": "Main switch 80A DP", "unit": "each", "price": 450},
    "cb_10a": {"desc": "Circuit breaker 10A SP", "unit": "each", "price": 65},
    "cb_16a": {"desc": "Circuit breaker 16A SP", "unit": "each", "price": 65},
    "cb_20a": {"desc": "Circuit breaker 20A SP", "unit": "each", "price": 70},
    "cb_32a": {"desc": "Circuit breaker 32A SP", "unit": "each", "price": 85},
    "elcb_63a": {"desc": "Earth leakage 63A 30mA", "unit": "each", "price": 950},
    "surge_arrester": {"desc": "Surge arrester Type 2", "unit": "each", "price": 1800},
}

# 1.3 Switches and Sockets
ELECTRICAL_ACCESSORIES = {
    "switch_1_lever": {"desc": "Light switch 1-lever", "unit": "each", "price": 45},
    "switch_2_lever": {"desc": "Light switch 2-lever", "unit": "each", "price": 65},
    "switch_3_lever": {"desc": "Light switch 3-lever", "unit": "each", "price": 85},
    "switch_4_lever": {"desc": "Light switch 4-lever", "unit": "each", "price": 105},
    "switch_2_way": {"desc": "2-way switch", "unit": "each", "price": 55},
    "switch_dimmer": {"desc": "Dimmer switch", "unit": "each", "price": 180},
    "socket_single": {"desc": "Socket outlet single", "unit": "each", "price": 55},
    "socket_double": {"desc": "Socket outlet double", "unit": "each", "price": 75},
    "socket_double_switched": {"desc": "Socket double switched", "unit": "each", "price": 95},
    "socket_usb": {"desc": "Socket with USB ports", "unit": "each", "price": 250},
    "isolator_stove": {"desc": "Stove isolator 45A", "unit": "each", "price": 250},
    "isolator_geyser": {"desc": "Geyser isolator 20A", "unit": "each", "price": 120},
    "isolator_aircon": {"desc": "Aircon isolator 20A", "unit": "each", "price": 150},
}

# 1.4 Light Fittings
ELECTRICAL_LIGHTS = {
    "downlight_led_9w": {"desc": "LED downlight 9W", "unit": "each", "price": 85, "lumens": 800},
    "downlight_led_12w": {"desc": "LED downlight 12W", "unit": "each", "price": 120, "lumens": 1000},
    "downlight_led_15w": {"desc": "LED downlight 15W", "unit": "each", "price": 150, "lumens": 1200},
    "batten_led_18w": {"desc": "LED batten 18W 600mm", "unit": "each", "price": 180, "lumens": 1800},
    "batten_led_36w": {"desc": "LED batten 36W 1200mm", "unit": "each", "price": 280, "lumens": 3600},
    "bulkhead_ip65": {"desc": "LED bulkhead IP65", "unit": "each", "price": 250},
    "floodlight_20w": {"desc": "LED floodlight 20W", "unit": "each", "price": 350},
    "floodlight_50w": {"desc": "LED floodlight 50W", "unit": "each", "price": 550},
    "sensor_pir": {"desc": "PIR motion sensor", "unit": "each", "price": 180},
}

# 1.5 Conduits and Sundries
ELECTRICAL_CONDUIT = {
    "conduit_20mm": {"desc": "PVC conduit 20mm x 4m", "unit": "length", "price": 35},
    "conduit_25mm": {"desc": "PVC conduit 25mm x 4m", "unit": "length", "price": 55},
    "conduit_32mm": {"desc": "PVC conduit 32mm x 4m", "unit": "length", "price": 75},
    "flexi_20mm": {"desc": "Flexible conduit 20mm", "unit": "meter", "price": 25},
    "junction_box": {"desc": "Junction box", "unit": "each", "price": 15},
    "junction_box_ip65": {"desc": "Junction box IP65", "unit": "each", "price": 45},
    "saddle_20mm": {"desc": "Saddle clip 20mm", "unit": "each", "price": 2},
    "saddle_25mm": {"desc": "Saddle clip 25mm", "unit": "each", "price": 3},
    "wall_box": {"desc": "Flush wall box", "unit": "each", "price": 18},
    "ceiling_rose": {"desc": "Ceiling rose DCL", "unit": "each", "price": 35},
    "earth_spike": {"desc": "Earth spike 1.5m copper", "unit": "each", "price": 180},
    "earth_bar": {"desc": "Earth bar 12-way", "unit": "each", "price": 95},
    "cable_tie_100": {"desc": "Cable ties 100mm (100)", "unit": "pack", "price": 25},
    "tape_insulation": {"desc": "Insulation tape", "unit": "roll", "price": 15},
}

# 1.6 Labour Rates (SA 2024/2025)
ELECTRICAL_LABOUR = {
    "light_point": {"desc": "Light point complete", "unit": "point", "price": 280},
    "power_point": {"desc": "Power point complete", "unit": "point", "price": 320},
    "stove_circuit": {"desc": "Stove circuit complete", "unit": "each", "price": 1800},
    "geyser_circuit": {"desc": "Geyser circuit complete", "unit": "each", "price": 1500},
    "aircon_circuit": {"desc": "Aircon circuit complete", "unit": "each", "price": 1200},
    "db_installation": {"desc": "DB board installation", "unit": "each", "price": 1500},
    "earth_installation": {"desc": "Earth system installation", "unit": "each", "price": 800},
    "coc_inspection": {"desc": "COC inspection & certificate", "unit": "each", "price": 2200},
    "fault_finding": {"desc": "Fault finding per hour", "unit": "hour", "price": 450},
    "electrical_rate": {"desc": "Electrician hourly rate", "unit": "hour", "price": 380},
}

# 1.7 Room Electrical Requirements (SANS 10142 Based)
ROOM_ELECTRICAL_REQUIREMENTS = {
    "Living Room": {"lights": 3, "plugs": 6, "special": []},
    "Bedroom": {"lights": 2, "plugs": 4, "special": ["2-way switch"]},
    "Main Bedroom": {"lights": 3, "plugs": 6, "special": ["2-way switch", "aircon prep"]},
    "Kitchen": {"lights": 4, "plugs": 8, "special": ["stove", "extractor"]},
    "Bathroom": {"lights": 2, "plugs": 1, "special": ["extractor", "shaver socket"]},
    "Toilet": {"lights": 1, "plugs": 0, "special": []},
    "Garage": {"lights": 2, "plugs": 4, "special": ["garage door motor"]},
    "Study": {"lights": 2, "plugs": 6, "special": []},
    "Dining Room": {"lights": 2, "plugs": 4, "special": []},
    "Passage": {"lights": 2, "plugs": 1, "special": ["2-way switch"]},
    "Patio": {"lights": 2, "plugs": 2, "special": ["weatherproof", "sensor"]},
    "Laundry": {"lights": 1, "plugs": 3, "special": ["washing machine"]},
    "Store Room": {"lights": 1, "plugs": 1, "special": []},
    "Pool Area": {"lights": 2, "plugs": 1, "special": ["pool pump", "weatherproof"]},
}
```

---

### PHASE 2: Calculation Functions

**File:** `app.py`
**Location:** After the material databases (around line 300)

Add these functions for SANS 10142 compliant calculations:
- `calculate_electrical_requirements(rooms)` - Room-by-room point calculation
- `calculate_load_and_circuits(elec_req)` - Load and circuit sizing
- `calculate_electrical_bq(elec_req, circuit_info)` - Bill of Quantities generation
- `generate_electrical_pdf(elec_req, circuit_info, bq_items)` - PDF export

---

### PHASE 3: Streamlit UI Tab

**File:** `app.py`
**Location:** In the main() function

Modify tabs line and add new Electrical Quote tab with:
- Summary metrics (lights, plugs, load, cost)
- Room-by-room breakdown table
- Circuit design summary
- Expandable BQ categories
- PDF export button

---

### PHASE 4: Update Requirements

**File:** `requirements.txt`
Add:
```
PuLP>=2.7.0
pandas>=2.0.0
```

---

## SA ELECTRICAL STANDARDS REFERENCE

### SANS 10142-1 Key Rules
- Max 10 points per lighting circuit
- Max 10 points per power circuit
- Stove: dedicated 32A circuit
- Geyser: dedicated 20A circuit
- Earth leakage protection mandatory
- Surge protection recommended

### Load Calculation
- Light point: 100W
- Plug point: 250W
- Diversity factor: 50% residential
- Power factor: 0.85

---

## EXECUTION CHECKLIST

1. [ ] Create CLAUDE.md (this file)
2. [ ] Add material databases to app.py
3. [ ] Add calculation functions
4. [ ] Add PDF generation function
5. [ ] Add Electrical Quote tab
6. [ ] Update requirements.txt
7. [ ] Test locally
8. [ ] Commit and push

---

---

## PLATFORM CONTEXT

**Problem:** South Africa needs a comprehensive electrical quotation platform that covers ALL sectors - from residential to mining, from township electrification to industrial manufacturing. Currently, no such integrated solution exists.

**Need:** A platform that serves:
- Homeowners (new builds, renovations, solar)
- Electrical contractors (quotes, BOQs, compliance)
- Developers (township electrification, infrastructure)
- Industrial clients (mining, manufacturing)
- Municipalities (street lighting, rural electrification)

**Outcome:** A complete electrical project quotation platform with:
- Database-driven pricing (not hardcoded)
- API-based architecture for scalability
- Multiple project types (residential → industrial)
- SA regulatory compliance (SANS, MHSA, NERSA)
- Professional PDF/Excel quotations

---

## FULL SCOPE: South African Electrical Market

### TIER 1: Residential
- New house construction
- Renovations & additions
- Solar & backup power
- COC compliance
- Smart home & automation
- Security systems (CCTV, alarm, fence)
- EV charging
- Pool & outdoor

### TIER 2: Commercial
- Office buildings
- Retail & shopping centers
- Restaurants & hospitality
- Healthcare facilities
- Schools & educational
- Hotels & lodges

### TIER 3: Industrial
- Mining operations (surface & underground)
- Factories & manufacturing
- Warehouses & distribution
- Agricultural (farms, irrigation)
- Substations & HV infrastructure
- Motor control & automation

### TIER 4: Infrastructure
- Township/suburb electrification
- Rural electrification (grid extension, mini-grid)
- Street lighting
- Utility-scale solar
- Grid connection & substations

---

## COMPLETE DATABASE SCHEMA

```sql
-- 1. PROJECT TYPES (All sectors)
CREATE TABLE project_types (
    id SERIAL PRIMARY KEY,
    tier VARCHAR(20) NOT NULL,
    code VARCHAR(50) UNIQUE NOT NULL,
    name VARCHAR(100) NOT NULL,
    regulations TEXT[],
    is_active BOOLEAN DEFAULT TRUE
);

-- 2. PRODUCT CATEGORIES (Hierarchical)
CREATE TABLE product_categories (
    id SERIAL PRIMARY KEY,
    parent_id INT REFERENCES product_categories(id),
    code VARCHAR(50) UNIQUE,
    name VARCHAR(100),
    applicable_tiers TEXT[]
);

-- 3. PRODUCTS
CREATE TABLE products (
    id SERIAL PRIMARY KEY,
    category_id INT REFERENCES product_categories(id),
    sku VARCHAR(50) UNIQUE,
    brand VARCHAR(100),
    name VARCHAR(200) NOT NULL,
    specifications JSONB,
    unit VARCHAR(20) NOT NULL,
    voltage_rating VARCHAR(20),
    certifications TEXT[]
);

-- 4. SUPPLIERS (SA suppliers)
CREATE TABLE suppliers (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    code VARCHAR(20) UNIQUE,
    type VARCHAR(20),
    tiers_served TEXT[],
    credit_terms VARCHAR(50)
);

-- 5. PRICES
CREATE TABLE prices (
    id SERIAL PRIMARY KEY,
    product_id INT REFERENCES products(id),
    supplier_id INT REFERENCES suppliers(id),
    price_zar DECIMAL(12,2) NOT NULL,
    effective_date DATE NOT NULL,
    price_type VARCHAR(20)
);

-- 6. ELECTRIFICATION STANDARDS
CREATE TABLE electrification_standards (
    id SERIAL PRIMARY KEY,
    standard_type VARCHAR(50),
    connection_size VARCHAR(20),
    per_stand_allowance JSONB,
    applicable_standards TEXT[]
);

-- 7. INDUSTRIAL STANDARDS (Mining, Manufacturing)
CREATE TABLE industrial_standards (
    id SERIAL PRIMARY KEY,
    industry_type VARCHAR(50),
    equipment_class VARCHAR(50),
    requirements JSONB,
    safety_standards TEXT[]
);

-- 8. LABOUR RATES
CREATE TABLE labour_rates (
    id SERIAL PRIMARY KEY,
    project_type_id INT,
    task_code VARCHAR(50),
    description VARCHAR(200),
    unit VARCHAR(20),
    rate_zar DECIMAL(10,2),
    skill_level VARCHAR(20)
);
```

---

## DATA SOURCES BY SECTOR

### Residential & Commercial
| Data Type | Source |
|-----------|--------|
| LV Materials | Builders Warehouse, Cashbuild |
| Pricing | ACDC Dynamics, Eurolux |
| Solar | Sustainable.co.za, SolarAdvice |
| Standards | SANS 10142 |

### Industrial
| Data Type | Source |
|-----------|--------|
| MV/HV Equipment | ABB, Siemens, Schneider |
| Mining Equipment | Zest WEG |
| Cables | Aberdare, South Ocean |
| Standards | MHSA, SANS 10108 |

### Infrastructure
| Data Type | Source |
|-----------|--------|
| Poles | Rocla |
| Transformers | ABB, Actom, WEG |
| Street Lights | Beka Schreder |
| Metering | Conlog, Landis+Gyr |
| Standards | NRS 034, Eskom DSD |

---

## IMPLEMENTATION ROADMAP

### Phase 1: Foundation (Weeks 1-4)
- Database Setup (Supabase/PostgreSQL)
- FastAPI Backend
- Data Collection Sprint

### Phase 2: Core Calculators (Weeks 5-8)
| Sector | Calculator |
|--------|------------|
| Residential | Room-based electrical |
| Commercial | Area-based electrical |
| Industrial | Equipment-based |
| Infrastructure | Per-stand costing |

### Phase 3: User Interface (Weeks 9-12)
- Project Type Selector
- Dynamic Forms
- Quote Generation

### Phase 4: Data Enrichment (Weeks 13-16)
- Price Update Automation
- Standards Library
- Regional Expansion

### Phase 5: Advanced Features (Weeks 17-24)
- Admin panel
- User accounts
- Contractor marketplace
- API integration
- Mobile app

---

## MVP DELIVERABLES

| Feature | Residential | Commercial | Industrial | Infrastructure |
|---------|-------------|------------|------------|----------------|
| Project creation | ✅ | ✅ | ✅ | ✅ |
| Material BQ | ✅ | ✅ | ✅ | ✅ |
| Labour costing | ✅ | ✅ | ✅ | ✅ |
| PDF export | ✅ | ✅ | ✅ | ✅ |
| Price database | ✅ Basic | ✅ Basic | ⚠️ Limited | ⚠️ Limited |

---

## REVENUE MODEL

| Tier | Target User | Pricing Model | Price Point |
|------|-------------|---------------|-------------|
| Residential | Homeowners | Once-off | R99-R299 |
| Residential Pro | Contractors | Monthly | R499/month |
| Commercial | Contractors | Per project | R999-R2,999 |
| Industrial | Engineering firms | Annual | R29,999/year |
| Infrastructure | Municipalities | Enterprise | Custom |

---

## PHASE 5: SMART COST OPTIMIZER

### The 4 Quotation Options

| Option | Strategy | Margin |
|--------|----------|--------|
| A: Budget | Cheapest supplier per item | 12-15% |
| B: Best Value | Balanced cost/quality | 15-20% |
| C: Premium | Quality brands | 20-25% |
| D: Competitive | Lowest total | 10-12% |

### Algorithm

```python
def generate_quotation_options(requirements: dict, region: str) -> list:
    options = []

    # Option A: Budget
    budget_items = select_by_strategy(all_prices, "cheapest")
    options.append(calculate_option("Budget", budget_items, 0.12))

    # Option B: Best Value
    value_items = select_by_strategy(all_prices, "balanced")
    options.append(calculate_option("Best Value", value_items, 0.18))

    # Option C: Premium
    premium_items = select_by_strategy(all_prices, "premium")
    options.append(calculate_option("Premium", premium_items, 0.22))

    # Option D: Competitive
    competitive_items = optimize_total_cost(all_prices)
    options.append(calculate_option("Competitive", competitive_items, 0.10))

    return options
```

---

## PHASE 6: OPERATIONS RESEARCH OPTIMIZATION

### Mathematical Formulation

```
OBJECTIVE FUNCTIONS:
f1: Minimize Total Cost     = Σ price[i,j] × qty[i] × x[i,j]
f2: Maximize Quality Score  = Σ quality[i,j] × qty[i] × x[i,j]

DECISION VARIABLES:
x[i,j] ∈ {0, 1}  : Select supplier j for item i (binary)

CONSTRAINTS:
1. Σ x[i,j] = 1 for all i    (one supplier per item)
2. Circuit points ≤ 10      (SANS 10142)
3. Quality score ≥ threshold
4. Total cost ≤ budget
```

### PuLP Implementation

```python
from pulp import *

class QuotationOptimizer:
    def optimize(self, requirements: dict, region: str) -> list:
        prob = LpProblem("Quotation", LpMinimize)

        # Decision variables
        x = LpVariable.dicts("select",
            ((i, j) for i in items for j in suppliers),
            cat='Binary')

        # Objective: minimize cost
        prob += lpSum(
            prices.loc[i, j] * requirements[i] * x[i, j]
            for i in items for j in suppliers
        )

        # Constraint: one supplier per item
        for i in items:
            prob += lpSum(x[i, j] for j in suppliers) == 1

        prob.solve(PULP_CBC_CMD(msg=0))
        return self._extract_solution(prob, x)
```

### Value of OR Optimization

| Benefit | Description |
|---------|-------------|
| Proven optimality | Mathematically guaranteed best |
| Constraint handling | Complex constraints handled |
| Multi-objective | Balance cost, quality, time |
| Credibility | Industrial Engineering optimization |
| Differentiation | No SA competitor has this |

---

## PHASE 7: MULTI-TIER EXPANSION

### Commercial Projects
- Office load calculations
- Emergency power sizing
- Fire alarm integration

### Industrial Projects
- Mining (MHSA compliant)
- Factory MCCs/VSDs
- Substation design

### Infrastructure Projects
- Township electrification costing
- Rural grid extension
- Street lighting design
