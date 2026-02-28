"""
AfriPlan AI - Improved Extraction Prompts v2.0
===============================================
These prompts are designed based on analysis of real SA electrical plans:
- WEDELA Recreational Club (Commercial/Recreational)
- EUROBATH Yapa Properties (Industrial/Warehouse)
- NewMark Offices (Commercial Office)

Key improvements:
1. Generic DB naming patterns (DB-XX, DBM-XX, DBGF-XX, DB-S1, etc.)
2. Legend-first extraction strategy
3. Circuit cluster counting (not room-based)
4. SA-specific equipment and cable specifications
5. Phase balancing awareness (R/W/B)
"""

# =============================================================================
# SUPPLY POINT EXTRACTION
# =============================================================================

PROMPT_SUPPLY_POINT = """
## TASK: Extract Main Supply Point / Metering Information

Analyze this SLD (Single Line Diagram) and find the incoming electrical supply.

### LOOK FOR:
1. **Main Supply Names:**
   - "Kiosk", "Kiosk Metering", "Metering Box"
   - "MSB", "Main Switch Board", "Main DB"
   - "Existing Mini Sub", "Existing Sub"
   - "Fed from Eskom", "Eskom Metering Box"
   - "LV Cable from transformer"

2. **Supply Specifications:**
   - Voltage: 400V, 230V (for single phase)
   - Main breaker size: 100A, 150A, 200A, 250A, 300A, 400A
   - Fault level: 6kA, 10kA, 15kA, 20kA
   - Phases: 3PH+N+E, 1PH+N+E

3. **Cable from Supply:**
   - Look for cable size: 95mm², 70mm², 50mm², 35mm², etc.
   - Cable type: "PVC SWA PVC", "XLPE", "COPPER", "PVCF Cu"
   - Earth conductor: "BCEW" (Bare Copper Earth Wire)
   - Example: "95mm²x4CORE COPPER PVC SWA PVC"

4. **Solar/Hybrid Systems:**
   - "Solar Panel", "From Solar Panel"
   - "Battery Room", "Inverter"
   - Solar cable specs: "4x10mm PVCF Cu"

### RETURN JSON:
```json
{
  "supply_found": true,
  "supply_type": "eskom" | "solar" | "hybrid" | "generator",
  "name": "Kiosk Metering",
  "location": "External" | "Ground Floor" | "Plant Room",
  "voltage_v": 400,
  "phases": "3PH+N+E",
  "main_breaker_a": 250,
  "fault_level_ka": 15,
  "meter_type": "ct" | "direct" | "prepaid",
  "feeds_to": "DB-GF" | "DB-CR" | "Main DB",
  "incoming_cable": {
    "spec": "95mm²x4C PVC SWA PVC",
    "earth": "25mm² BCEW",
    "length_m": null
  },
  "solar_input": {
    "present": false,
    "cable_spec": null
  },
  "confidence": 0.85
}
```
"""

# =============================================================================
# DISTRIBUTION BOARD DETECTION
# =============================================================================

PROMPT_DB_DETECTION = """
## TASK: Find ALL Distribution Boards on this SLD

Scan the drawing carefully for EVERY distribution board. SA projects use various naming conventions.

### DB NAMING PATTERNS TO DETECT:

1. **Main Boards:**
   - "Main DB", "NEW MAIN DB", "MAIN DB GROUND FLOOR"
   - "MSB", "DB-MAIN", "MDB"
   - "Kiosk" (metering + distribution)

2. **Floor-Based:**
   - DB-GF, DBGF, DB-G/F (Ground Floor)
   - DB-1F, DB-FF, DB-FIRST (First Floor)
   - DB-2F, DB-SF (Second Floor)
   - SUB DB-GF, SUB DB-1F

3. **Area-Based:**
   - DB-CR (Central Reception/Common Room)
   - DB-CA (Common Area)
   - DB-PFA (Pool Facility Area)
   - DB-AB1, DB-AB2 (Ablution Block 1, 2)
   - DB-ST (Stage/Entertainment)

4. **Suite/Unit-Based:**
   - DB-S1, DB-S2, DB-S3, DB-S4 (Suites)
   - DB-SUITE 1, DB-SUITE 2
   - DB-UNIT 1, DB-UNIT 2

5. **Building-Based:**
   - DB-LGH, DB-SGH (Large/Small Guard House)
   - DBM (Mezzanine)
   - DBH (High Bay / Warehouse)

6. **Equipment-Based:**
   - DB-PPS1, DB-PPS2 (Pool Pump Stations)
   - DB-HPS1, DB-HPS2 (Heat Pump Stations)
   - DB-HVAC, DB-LIFT

### FOR EACH DB EXTRACT:
- Name (exactly as shown)
- Location/description
- Fed from (parent DB name)
- Incoming cable spec
- Main breaker rating (A)
- Fault level (kA)
- Phases (3PH+N+E, 1PH+N+E)
- Is main board (true/false)

### RETURN JSON:
```json
{
  "distribution_boards": [
    {
      "name": "DB-GF",
      "location": "Ground Floor",
      "is_main": true,
      "fed_from": "Kiosk Metering",
      "incoming_cable": "14mm x 4C PVC SWA",
      "main_breaker_a": 100,
      "fault_level_ka": 6,
      "phases": "3PH+N+E",
      "feeds_to": ["DB-CA", "DB-S1", "DB-S2", "DB-S3", "DB-S4"]
    },
    {
      "name": "DB-CA",
      "location": "Common Area",
      "is_main": false,
      "fed_from": "DB-GF",
      "incoming_cable": "16mm x 4C PVC SWA PVC",
      "main_breaker_a": 60,
      "fault_level_ka": 6,
      "phases": "3PH+N+E",
      "feeds_to": []
    }
  ],
  "total_count": 6,
  "hierarchy_depth": 2,
  "confidence": 0.90
}
```
"""

# =============================================================================
# CIRCUIT SCHEDULE EXTRACTION
# =============================================================================

PROMPT_CIRCUIT_SCHEDULE = """
## TASK: Extract Circuit Schedule for Distribution Board "{db_name}"

Read the circuit schedule table/diagram for this specific DB. Extract EVERY circuit.

### CIRCUIT TYPES:

1. **Lighting Circuits (L1, L2, L3...):**
   - Circuit ref: L1, L2, L3, etc.
   - Description: "6x48W", "5x54W", "8 lights", etc.
   - Load in Watts
   - Cable size: 1.5mm² (standard for lighting)
   - Number of points/fixtures
   - Phase assignment: R, W, B, or R-PH, W-PH, B-PH

2. **Power Circuits (P1, P2, P3...):**
   - Circuit ref: P1, P2, P3, etc.
   - Load in Watts (e.g., 3680W, 2500W)
   - Cable size: 2.5mm² (standard for power)
   - Number of socket points
   - Phase assignment

3. **Isolator Circuits (ISO1, ISO2...):**
   - Circuit ref: ISO1, ISO2, etc.
   - Rating: 20A, 30A
   - Description: "Isolator", "DOOR", "EF1", "EF2"

4. **Dedicated Circuits:**
   - AC-1, AC1, AC2... (Air Conditioning)
   - HVAC System (load in kW)
   - GEYSER (usually 2kW, 20A circuit)
   - EF1, EF2 (Extractor Fans)
   - Roller Doors

5. **Sub-Board Feeders:**
   - DB-XX fed via cable spec
   - Load in Watts
   - Cable size (varies)

6. **Spare Circuits:**
   - Marked as "SPARE"
   - Count these for DB sizing

### PHASE IDENTIFICATION:
- R, R1, R-PH, R2 = Red phase
- W, W1, W-PH, W2 = White phase
- B, B1, B-PH, B2 = Blue phase

### RETURN JSON:
```json
{
  "db_name": "{db_name}",
  "circuits": {
    "lighting": [
      {
        "ref": "L1",
        "description": "6x48W",
        "load_w": 384,
        "cable_mm2": 1.5,
        "points": 6,
        "phase": "R",
        "breaker_a": 10
      }
    ],
    "power": [
      {
        "ref": "P1",
        "description": "PLUGS",
        "load_w": 3680,
        "cable_mm2": 2.5,
        "points": 4,
        "phase": "R",
        "breaker_a": 20
      }
    ],
    "isolators": [
      {
        "ref": "ISO1",
        "description": "Isolator",
        "rating_a": 30
      }
    ],
    "dedicated": [
      {
        "ref": "AC-1",
        "description": "Air Conditioning",
        "load_w": 1650,
        "cable_mm2": 2.5,
        "breaker_a": 20
      }
    ],
    "sub_boards": [
      {
        "ref": "DB-S1",
        "load_w": 9082,
        "cable_spec": "3Cx6mm²"
      }
    ],
    "spare_count": 2
  },
  "totals": {
    "lighting_circuits": 5,
    "power_circuits": 2,
    "isolators": 8,
    "dedicated": 1,
    "sub_boards": 4,
    "spares": 2,
    "total_ways": 22
  },
  "phase_balance": {
    "R": 12500,
    "W": 11800,
    "B": 10200
  },
  "confidence": 0.88
}
```
"""

# =============================================================================
# CABLE ROUTES EXTRACTION
# =============================================================================

PROMPT_CABLE_ROUTES = """
## TASK: Extract Cable Routes Between Distribution Boards

Find ALL cables connecting distribution boards on this SLD.

### LOOK FOR:
1. **Cable Labels ON Lines:**
   - "95mm²x4C PVC SWA PVC"
   - "4Cx16mm² PVC SWA PVC"
   - "35mm² x 4C"
   - "6mm² x 3C PVC SWA PVC"

2. **Cable Route Indicators:**
   - "DB-XX fed from DB-YY"
   - "Incoming cable from XX"
   - "Fed via XXmm cable"
   - Arrows showing direction

3. **Earth Conductors:**
   - "25mm² BCEW" (Bare Copper Earth Wire)
   - "10Cx16mm BCEW"
   - "4x16mm BCEW"

4. **Underground Indicators:**
   - "Underground"
   - Sleeve sizes: "110mm sleeve", "50mm sleeve", "75mm sleeve"
   - Distances in meters

5. **Cable Lengths:**
   - Distances marked on routes: "35m", "55m", "110m"
   - Or scaled from drawing

### RETURN JSON:
```json
{
  "cable_routes": [
    {
      "from": "Kiosk Metering",
      "to": "DB-GF",
      "cable_spec": "95mm²x4C PVC SWA PVC",
      "earth_spec": "25mm² BCEW",
      "length_m": 35,
      "is_underground": true
    },
    {
      "from": "DB-GF",
      "to": "DB-S1",
      "cable_spec": "6mm² x 3C PVC SWA PVC",
      "length_m": null,
      "is_underground": false
    }
  ],
  "underground_sleeves": [
    {"size_mm": 110, "qty": 2, "purpose": "Main supply sleeves"},
    {"size_mm": 75, "qty": 4, "purpose": "Cable sleeves"},
    {"size_mm": 50, "qty": 3, "purpose": "Solar cables"}
  ],
  "total_cable_length_m": 245,
  "confidence": 0.82
}
```
"""

# =============================================================================
# LEGEND EXTRACTION - LIGHTING
# =============================================================================

PROMPT_LEGEND_LIGHTING = """
## TASK: Extract Lighting Legend from Layout Drawing

Find the LEGEND/KEY on this drawing and extract ALL lighting fixture types.

### COMMON SA LIGHTING FIXTURES:

1. **Downlights:**
   - 6W LED Downlight
   - 8W LED Downlight
   - 12W LED Downlight
   - Circle with rays symbol

2. **LED Panels (Recessed):**
   - 600x600 LED Panel (typically 40W)
   - 600x1200 Recessed 3x18W LED (54W total)
   - Rectangle symbol

3. **Surface Mount:**
   - 18W LED Ceiling Light Surface Mount
   - 36W LED Ceiling Light
   - 2x18W LED Fluorescent

4. **Vapor Proof (Wet Areas):**
   - 2x18W Double Vapor Proof LED
   - 2x24W Double Vapor Proof LED
   - IP65 rated

5. **High Bay (Industrial):**
   - UFO Ring Highbay 250W
   - Type PR48 High Bay 120W LED
   - For warehouse areas

6. **Outdoor/External:**
   - 30W LED Flood Light
   - 50W LED Flood Light
   - 200W LED Flood Light
   - 26W Bulkhead Light Outdoor
   - 60W Pole Light

7. **Emergency:**
   - Emergency Light (3hr)
   - Exit Sign with Battery

### SWITCHES TO DETECT:
- 1-lever 1-way @1200mm (1L1W)
- 2-lever 1-way @1200mm (2L1W)
- 1-lever 2-way @1200mm (1L2W)
- Day/Night switch @2000mm (D/N)
- Master switch (MS)

### RETURN JSON:
```json
{
  "has_legend": true,
  "light_types": [
    {
      "symbol": "rect_1200",
      "name": "600x1200 Recessed 3x18W LED",
      "wattage_w": 54,
      "type": "panel"
    },
    {
      "symbol": "downlight",
      "name": "6W LED Downlight",
      "wattage_w": 6,
      "type": "downlight"
    },
    {
      "symbol": "ufo_highbay",
      "name": "UFO Ring Highbay 250W",
      "wattage_w": 250,
      "type": "highbay"
    }
  ],
  "switch_types": [
    {
      "symbol": "1L1W",
      "name": "1-lever 1-way",
      "height_mm": 1200
    },
    {
      "symbol": "DN",
      "name": "Day/Night switch",
      "height_mm": 2000
    }
  ],
  "emergency_types": [
    {
      "symbol": "EMG",
      "name": "Emergency Light 3hr",
      "wattage_w": 5
    }
  ],
  "confidence": 0.92
}
```
"""

# =============================================================================
# LEGEND EXTRACTION - POWER
# =============================================================================

PROMPT_LEGEND_POWER = """
## TASK: Extract Power/Socket Legend from Layout Drawing

Find the LEGEND/KEY and extract ALL socket and power point types.

### COMMON SA SOCKET TYPES:

1. **Standard Sockets:**
   - 16A Double Switched Socket @300mm (floor level)
   - 16A Double Switched Socket @1100mm (worktop level)
   - 16A Single Switched Socket @300mm
   - 16A Single Switched Socket @1100mm

2. **Waterproof:**
   - 16A Waterproof Socket (IP44/IP65)
   - Outdoor sockets

3. **Special:**
   - Floor Box (recessed floor socket)
   - Ceiling Socket (suspended equipment)
   - Data Socket CAT 6

4. **Isolators:**
   - 20A Isolator Switch @2000mm
   - 30A Isolator Switch @2000mm

5. **Dedicated Equipment:**
   - A/C - Air Conditioning Unit connection
   - Geyser connection (50L, 100L, etc.)

### CONTAINMENT TYPES:
- 2-Compartment Steel Grey Power Skirting
- 200mm Galvanized Cable Tray (Aircon)
- P8000 Trunking
- 150mm Wire Mesh Basket Galvanized
- PVC Conduit (20mm, 25mm)

### RETURN JSON:
```json
{
  "has_legend": true,
  "socket_types": [
    {
      "symbol": "DS300",
      "name": "16A Double Socket @300mm",
      "height_mm": 300,
      "rating_a": 16
    },
    {
      "symbol": "DS1100",
      "name": "16A Double Socket @1100mm",
      "height_mm": 1100,
      "rating_a": 16
    },
    {
      "symbol": "FLOOR_BOX",
      "name": "Floor Box",
      "height_mm": 0,
      "rating_a": 16
    }
  ],
  "data_points": [
    {
      "symbol": "DATA",
      "name": "Data Socket CAT 6",
      "height_mm": 300
    }
  ],
  "isolators": [
    {
      "symbol": "ISO20",
      "name": "20A Isolator Switch",
      "height_mm": 2000,
      "rating_a": 20
    }
  ],
  "equipment": [
    {
      "symbol": "AC",
      "name": "Air Conditioning Unit"
    },
    {
      "symbol": "GEYSER",
      "name": "50L Geyser"
    }
  ],
  "containment": [
    {
      "type": "power_skirting",
      "description": "2-Compartment Steel Grey Power Skirting"
    },
    {
      "type": "cable_tray",
      "description": "200mm Galvanized Cable Tray"
    }
  ],
  "confidence": 0.90
}
```
"""

# =============================================================================
# CIRCUIT CLUSTER EXTRACTION (Layout)
# =============================================================================

PROMPT_CIRCUIT_CLUSTER_LIGHTING = """
## TASK: Count Light Fixtures per Circuit Cluster

Using the legend already extracted, count fixtures in EACH circuit cluster shown on this layout.

### CIRCUIT CLUSTER IDENTIFICATION:
Look for circuit labels on the drawing:
- "DB-CR L1", "DB-CR L2", etc.
- "DB-S1 L1", "DB-S2 L1"
- "DBM-L1", "DBM-L2"
- "DBGF-L1", "DBGF-L2"

### FOR EACH CIRCUIT CLUSTER:
1. Find the circuit label (e.g., "DB-CR L1")
2. Trace the circuit line
3. Count all light fixtures connected to it
4. Identify fixture types using legend

### COUNTING RULES:
- Count ONLY light fixtures (not switches)
- Count individual fixtures (each symbol = 1 fixture)
- Note the fixture type for each

### RETURN JSON:
```json
{
  "circuit_clusters": [
    {
      "circuit_ref": "DB-CR L1",
      "db_name": "DB-CR",
      "circuit_type": "lighting",
      "fixtures": [
        {"type": "600x1200 LED Panel", "qty": 8}
      ],
      "total_fixtures": 8,
      "estimated_load_w": 432,
      "area_served": "Pool Block"
    },
    {
      "circuit_ref": "DB-CR L14",
      "db_name": "DB-CR",
      "circuit_type": "lighting",
      "fixtures": [
        {"type": "30W Flood Light", "qty": 2}
      ],
      "total_fixtures": 2,
      "estimated_load_w": 60,
      "area_served": "External"
    },
    {
      "circuit_ref": "DBM-L1",
      "db_name": "DBM",
      "circuit_type": "lighting",
      "fixtures": [
        {"type": "UFO Highbay 250W", "qty": 8}
      ],
      "total_fixtures": 8,
      "estimated_load_w": 2000,
      "area_served": "Warehouse"
    }
  ],
  "summary": {
    "total_circuits_found": 14,
    "total_fixtures": 95,
    "total_estimated_load_w": 8500
  },
  "confidence": 0.85
}
```
"""

# =============================================================================
# CIRCUIT CLUSTER EXTRACTION - POWER
# =============================================================================

PROMPT_CIRCUIT_CLUSTER_POWER = """
## TASK: Count Socket Points per Circuit Cluster

Using the legend already extracted, count socket points in EACH power circuit cluster.

### CIRCUIT CLUSTER IDENTIFICATION:
- "DB-CR P1", "DB-CR P2"
- "DB-S1 P1", "DB-S2 P1"
- "DB-AB1 P1"
- "DB-GF P1"

### FOR EACH CIRCUIT CLUSTER:
1. Find the power circuit label
2. Trace the circuit
3. Count socket points (EACH double socket = 1 point, NOT 2)
4. Identify socket heights and types

### COUNTING RULES:
- Double socket = 1 point
- Single socket = 1 point
- Floor box = 1 point
- Data point = count separately

### RETURN JSON:
```json
{
  "circuit_clusters": [
    {
      "circuit_ref": "DB-GF P1",
      "db_name": "DB-GF",
      "circuit_type": "power",
      "sockets": [
        {"type": "16A Double @300mm", "qty": 3},
        {"type": "16A Double @1100mm", "qty": 1}
      ],
      "total_points": 4,
      "estimated_load_w": 3680,
      "area_served": "Suite 1"
    },
    {
      "circuit_ref": "DB-CA P1",
      "db_name": "DB-CA",
      "circuit_type": "power",
      "sockets": [
        {"type": "16A Double @300mm", "qty": 4}
      ],
      "data_points": 2,
      "total_points": 4,
      "estimated_load_w": 3680,
      "area_served": "Common Area"
    }
  ],
  "summary": {
    "total_circuits_found": 12,
    "total_socket_points": 45,
    "total_data_points": 15
  },
  "confidence": 0.85
}
```
"""

# =============================================================================
# ROOM DETECTION
# =============================================================================

PROMPT_ROOM_DETECTION = """
## TASK: Detect All Rooms/Areas on this Layout Drawing

Find all rooms and areas with their names and approximate sizes.

### LOOK FOR:
1. Room labels with area: "54 m² Storage", "447 m² Multi Purpose Hall"
2. Room names without area: "SUITE 1", "FOYER", "WC"
3. Area descriptions: "Pool Block", "Ground Floor"

### COMMON SA ROOM TYPES:
- Offices: Office, Suite 1-4, Conference Room, Staff Room
- Ablutions: WC, Male Ablutions, Female Ablutions, Disabled WC
- Storage: Storage, Store, Broom Closet, Refuse
- Kitchen: Kitchen, Kitchenette, Tea Room, Scullery
- Technical: Battery Room, DB Room, Plant Room, Duct
- Common: Foyer, Lobby, Passage, Entrance, Reception
- Industrial: Warehouse, Dispatch Cage, Retail Space
- Recreational: Pool, Gym, Hall, Lounge

### RETURN JSON:
```json
{
  "areas": [
    {
      "name": "Ground Floor",
      "type": "floor",
      "rooms": [
        {"name": "Suite 1", "area_m2": 54.9, "type": "office"},
        {"name": "Foyer", "area_m2": 18.9, "type": "common"},
        {"name": "WC", "area_m2": 4, "type": "ablution"},
        {"name": "Tea Room", "area_m2": 10, "type": "kitchen"}
      ]
    },
    {
      "name": "Warehouse",
      "type": "industrial",
      "rooms": [
        {"name": "High Level Pallet Racking", "area_m2": 1500, "type": "warehouse"},
        {"name": "Dispatch Cage 1", "area_m2": 25, "type": "storage"}
      ]
    }
  ],
  "total_rooms": 15,
  "total_area_m2": 1800,
  "confidence": 0.88
}
```
"""

# =============================================================================
# PROJECT INFO EXTRACTION
# =============================================================================

PROMPT_PROJECT_INFO = """
## TASK: Extract Project Information from Cover Page / Title Block

Find project details from the drawing title block or cover page.

### LOOK FOR:
1. **Project Name:**
   - "THE UPGRADING OF WEDELA RECREATIONAL CLUB"
   - "PROPOSED NEW OFFICES ON ERF1/1"
   - "ERF 470 YAPA PROPERTIES"

2. **Client:**
   - "CLIENT: TJM GREENTECH"
   - Company name in title block

3. **Consultant/Engineer:**
   - "CHONA-MALANGA ENGINEERING"
   - "KABE CONSULTING ENGINEERS"
   - Professional registration numbers (Pr. Eng.)

4. **Drawing Info:**
   - Drawing number: "TJM-SLD-001", "100-TYP-005"
   - Revision: "RA", "Rev 1"
   - Date
   - Scale

5. **Location:**
   - Address or ERF number
   - City/Province

6. **Standards:**
   - "SANS 10142-1"
   - "OHS Act 85 of 1993"

### RETURN JSON:
```json
{
  "project_name": "THE UPGRADING OF WEDELA RECREATIONAL CLUB",
  "client": "KABE CONSULTING ENGINEERS",
  "consultant": "CHONA-MALANGA ENGINEERING",
  "location": {
    "address": null,
    "erf": "ERF 470",
    "city": "Midrand",
    "province": "Gauteng"
  },
  "drawing_info": {
    "number": "TJM-SLD-001",
    "title": "MAIN DB GROUND FLOOR + COMMON AREA",
    "revision": "RA",
    "date": "08/10/2025"
  },
  "standards": ["SANS 10142-1", "OHS Act 85 of 1993"],
  "project_type": "commercial_recreational",
  "confidence": 0.95
}
```
"""

# =============================================================================
# HELPER FUNCTION TO BUILD PROMPTS
# =============================================================================

def get_db_schedule_prompt(db_name: str) -> str:
    """Generate prompt for specific DB schedule extraction."""
    return PROMPT_CIRCUIT_SCHEDULE.replace("{db_name}", db_name)


def get_room_fixtures_prompt(room_name: str, legend_types: dict) -> str:
    """Generate room-specific prompt using extracted legend types."""

    light_list = ", ".join([lt.get("name", "") for lt in legend_types.get("light_types", [])])
    socket_list = ", ".join([st.get("name", "") for st in legend_types.get("socket_types", [])])

    return f"""
## TASK: Count Fixtures in Room "{room_name}"

Using the legend symbols already extracted, count fixtures in THIS room only.

Light types to look for: {light_list}
Socket types to look for: {socket_list}

For EACH fixture type in the legend, count how many appear in "{room_name}".
Note the circuit reference if visible (e.g., "DB-S1 L1", "DB-S2 P2").

### RETURN JSON:
```json
{{
  "room_name": "{room_name}",
  "found_in_drawing": true,
  "lighting": {{
    "6W_downlight": 4,
    "600x1200_panel": 2
  }},
  "sockets": {{
    "double_socket_300": 3,
    "double_socket_1100": 2,
    "data_cat6": 1
  }},
  "switches": {{
    "1lever_switch": 2
  }},
  "circuit_refs": ["DB-S1 L1", "DB-S1 P1"],
  "confidence": 0.85
}}
```
"""


# =============================================================================
# EXTRACTION SEQUENCE
# =============================================================================

EXTRACTION_SEQUENCE = """
## AfriPlan AI Extraction Sequence

### STEP 1: Cover Page
  └─ PROMPT_PROJECT_INFO → project_name, client, consultant

### STEP 2: SLD + Schedules
  ├─ PROMPT_SUPPLY_POINT → kiosk/metering info
  ├─ PROMPT_DB_DETECTION → list of ALL DBs
  ├─ PROMPT_CIRCUIT_SCHEDULE × N → schedule per DB
  └─ PROMPT_CABLE_ROUTES → sub-main cables

### STEP 3: Lighting Layout
  ├─ PROMPT_LEGEND_LIGHTING → fixture types + wattages
  ├─ PROMPT_ROOM_DETECTION → list of rooms
  └─ PROMPT_CIRCUIT_CLUSTER_LIGHTING → fixtures per circuit

### STEP 4: Power Layout
  ├─ PROMPT_LEGEND_POWER → socket types + containment
  └─ PROMPT_CIRCUIT_CLUSTER_POWER → sockets per circuit

### STEP 5: Reconciliation
  Compare SLD circuit points vs Layout circuit points
  Flag mismatches for manual review
"""
