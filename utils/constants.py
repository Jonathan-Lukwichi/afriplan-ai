"""
AfriPlan Electrical - Constants and Material Databases
All SA 2024/2025 electrical pricing and specifications
"""

# ─────────────────────────────────────────────
# SOUTH AFRICAN MATERIAL DATABASE (in ZAR)
# ─────────────────────────────────────────────
SA_MATERIALS = {
    "Cement (50kg bag)": {"unit": "bag", "price_zar": 100.0},
    "Concrete Block (15cm)": {"unit": "block", "price_zar": 15.0},
    "Concrete Block (20cm)": {"unit": "block", "price_zar": 20.0},
    "Rebar (12mm, 12m)": {"unit": "bar", "price_zar": 300.0},
    "Rebar (8mm, 12m)": {"unit": "bar", "price_zar": 160.0},
    "Roof Sheeting (3m)": {"unit": "sheet", "price_zar": 250.0},
    "Sand (7m³ truck)": {"unit": "truck", "price_zar": 1750.0},
    "Stone/Gravel (7m³ truck)": {"unit": "truck", "price_zar": 2300.0},
    "Floor Tiles (m²)": {"unit": "m²", "price_zar": 150.0},
    "Paint (20L bucket)": {"unit": "bucket", "price_zar": 500.0},
    "Structural Timber (6m)": {"unit": "piece", "price_zar": 200.0},
    "Interior Door": {"unit": "set", "price_zar": 800.0},
    "Exterior Door (Steel)": {"unit": "set", "price_zar": 2500.0},
    "Aluminium Window (1.2x1.0m)": {"unit": "set", "price_zar": 1500.0},
    "Plumbing (Basic Bathroom Set)": {"unit": "set", "price_zar": 4500.0},
    "Electrical (per point)": {"unit": "point", "price_zar": 250.0},
    "General Labour (per day)": {"unit": "day", "price_zar": 250.0},
}

# ─────────────────────────────────────────────
# ELECTRICAL MATERIAL DATABASE - SA 2024/2025
# ─────────────────────────────────────────────

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

# ─────────────────────────────────────────────
# ROOM PRESETS
# ─────────────────────────────────────────────
ROOM_PRESETS = {
    "Living Room": {"min_area": 16, "max_area": 30, "color": "#3B82F6", "label": "Living", "windows": 2, "doors": 1},
    "Bedroom": {"min_area": 10, "max_area": 16, "color": "#10B981", "label": "Bed", "windows": 1, "doors": 1},
    "Kitchen": {"min_area": 8, "max_area": 14, "color": "#F59E0B", "label": "Kitchen", "windows": 1, "doors": 1},
    "Bathroom": {"min_area": 4, "max_area": 8, "color": "#06B6D4", "label": "Bath", "windows": 1, "doors": 1},
    "Toilet": {"min_area": 2, "max_area": 4, "color": "#8B5CF6", "label": "WC", "windows": 0, "doors": 1},
    "Passage": {"min_area": 4, "max_area": 10, "color": "#64748B", "label": "Passage", "windows": 0, "doors": 0},
    "Patio": {"min_area": 6, "max_area": 15, "color": "#F97316", "label": "Patio", "windows": 0, "doors": 1},
    "Dining Room": {"min_area": 10, "max_area": 18, "color": "#EC4899", "label": "Dining", "windows": 1, "doors": 1},
    "Study": {"min_area": 8, "max_area": 14, "color": "#14B8A6", "label": "Study", "windows": 1, "doors": 1},
    "Garage": {"min_area": 15, "max_area": 25, "color": "#78716C", "label": "Garage", "windows": 0, "doors": 1},
}

# ─────────────────────────────────────────────
# PROJECT TYPE DEFINITIONS (Multi-Tier)
# ─────────────────────────────────────────────

PROJECT_TYPES = {
    "residential": {
        "name": "Residential",
        "icon": "🏠",
        "subtypes": [
            {"code": "new_house", "name": "New House Construction", "icon": "🏗️", "standards": ["SANS 10142"]},
            {"code": "renovation", "name": "Renovation & Additions", "icon": "🔧", "standards": ["SANS 10142"]},
            {"code": "solar_backup", "name": "Solar & Backup Power", "icon": "☀️", "standards": ["SANS 10142", "NRS 097"]},
            {"code": "coc_compliance", "name": "COC Compliance", "icon": "📋", "standards": ["SANS 10142"]},
            {"code": "smart_home", "name": "Smart Home", "icon": "🏠", "standards": ["SANS 10142"]},
            {"code": "security", "name": "Security Systems", "icon": "🔒", "standards": ["SANS 10142", "PSIRA"]},
            {"code": "ev_charging", "name": "EV Charging", "icon": "🚗", "standards": ["SANS 10142", "IEC 61851"]},
        ]
    },
    "commercial": {
        "name": "Commercial",
        "icon": "🏢",
        "subtypes": [
            {"code": "office", "name": "Office Buildings", "icon": "🏢", "standards": ["SANS 10142", "SANS 10400-XA"]},
            {"code": "retail", "name": "Retail & Shopping", "icon": "🏪", "standards": ["SANS 10142", "SANS 10400"]},
            {"code": "hospitality", "name": "Hotels & Restaurants", "icon": "🏨", "standards": ["SANS 10142", "SANS 10400"]},
            {"code": "healthcare", "name": "Healthcare Facilities", "icon": "🏥", "standards": ["SANS 10142", "SANS 10049"]},
            {"code": "education", "name": "Schools & Educational", "icon": "🏫", "standards": ["SANS 10142", "SANS 10400"]},
        ]
    },
    "industrial": {
        "name": "Industrial",
        "icon": "🏭",
        "subtypes": [
            {"code": "mining_surface", "name": "Mining - Surface", "icon": "⛏️", "standards": ["MHSA", "SANS 10142", "SANS 10108"]},
            {"code": "mining_underground", "name": "Mining - Underground", "icon": "⛏️", "standards": ["MHSA", "SANS 10108", "DMR"]},
            {"code": "manufacturing", "name": "Factory & Manufacturing", "icon": "🏭", "standards": ["SANS 10142", "OHS Act"]},
            {"code": "warehouse", "name": "Warehouse & Distribution", "icon": "📦", "standards": ["SANS 10142"]},
            {"code": "agricultural", "name": "Agricultural & Farms", "icon": "🌾", "standards": ["SANS 10142"]},
            {"code": "substation", "name": "Substations & HV", "icon": "⚡", "standards": ["NRS 034", "Eskom DSS"]},
        ]
    },
    "infrastructure": {
        "name": "Infrastructure",
        "icon": "🌍",
        "subtypes": [
            {"code": "township", "name": "Township Electrification", "icon": "🏘️", "standards": ["NRS 034", "Eskom DSD"]},
            {"code": "rural", "name": "Rural Electrification", "icon": "🌍", "standards": ["NRS 034", "INEP"]},
            {"code": "street_lighting", "name": "Street Lighting", "icon": "🛣️", "standards": ["SANS 10098", "SANS 10089"]},
            {"code": "minigrid", "name": "Mini-Grid & Microgrid", "icon": "📡", "standards": ["NERSA", "NRS 097"]},
            {"code": "utility_solar", "name": "Utility-Scale Solar", "icon": "🔋", "standards": ["NERSA", "Grid Code"]},
        ]
    }
}

# ─────────────────────────────────────────────
# TIER 1: RESIDENTIAL SPECIFICATIONS
# ─────────────────────────────────────────────

RESIDENTIAL_SOLAR_SYSTEMS = {
    "essential": {
        "name": "Essential Backup (3kVA)",
        "inverter_kva": 3,
        "battery_kwh": 5.12,
        "panels_kw": 2.4,
        "circuits_covered": ["lights", "tv", "wifi", "fridge"],
        "autonomy_hours": 4,
        "components": {
            "inverter": {"item": "Hybrid Inverter 3kVA 24V", "qty": 1, "price": 12500},
            "battery": {"item": "Lithium Battery 5.12kWh 48V", "qty": 1, "price": 28000},
            "panels": {"item": "Solar Panel 400W Mono", "qty": 6, "price": 1800},
            "mounting": {"item": "Roof Mount Kit (6 panels)", "qty": 1, "price": 4500},
            "dc_isolator": {"item": "DC Isolator 600V 32A", "qty": 1, "price": 850},
            "ac_isolator": {"item": "AC Isolator 40A", "qty": 2, "price": 350},
            "surge_dc": {"item": "DC Surge Protector", "qty": 1, "price": 1200},
            "cables": {"item": "Solar Cable 6mm 100m", "qty": 1, "price": 2800},
            "changeover": {"item": "Automatic Changeover 40A", "qty": 1, "price": 3500},
        },
        "labour": {"installation": 8500, "commissioning": 1500, "coc": 2200},
    },
    "standard": {
        "name": "Home Backup (5kVA)",
        "inverter_kva": 5,
        "battery_kwh": 10.24,
        "panels_kw": 4.0,
        "circuits_covered": ["lights", "plugs", "tv", "wifi", "fridge", "microwave"],
        "autonomy_hours": 6,
        "components": {
            "inverter": {"item": "Hybrid Inverter 5kVA 48V", "qty": 1, "price": 18500},
            "battery": {"item": "Lithium Battery 5.12kWh 48V", "qty": 2, "price": 28000},
            "panels": {"item": "Solar Panel 400W Mono", "qty": 10, "price": 1800},
            "mounting": {"item": "Roof Mount Kit (10 panels)", "qty": 1, "price": 6500},
            "dc_isolator": {"item": "DC Isolator 600V 32A", "qty": 2, "price": 850},
            "ac_isolator": {"item": "AC Isolator 63A", "qty": 2, "price": 450},
            "surge_dc": {"item": "DC Surge Protector", "qty": 2, "price": 1200},
            "cables": {"item": "Solar Cable 6mm 100m", "qty": 2, "price": 2800},
            "changeover": {"item": "Automatic Changeover 63A", "qty": 1, "price": 4500},
            "db_solar": {"item": "Solar DB 8-way", "qty": 1, "price": 1200},
        },
        "labour": {"installation": 12000, "commissioning": 2000, "coc": 2200},
    },
    "premium": {
        "name": "Full Home (8kVA)",
        "inverter_kva": 8,
        "battery_kwh": 20.48,
        "panels_kw": 6.4,
        "circuits_covered": ["all_circuits", "stove", "geyser_timer"],
        "autonomy_hours": 8,
        "components": {
            "inverter": {"item": "Hybrid Inverter 8kVA 48V", "qty": 1, "price": 32000},
            "battery": {"item": "Lithium Battery 5.12kWh 48V", "qty": 4, "price": 28000},
            "panels": {"item": "Solar Panel 400W Mono", "qty": 16, "price": 1800},
            "mounting": {"item": "Roof Mount Kit (16 panels)", "qty": 1, "price": 9500},
            "dc_isolator": {"item": "DC Isolator 600V 32A", "qty": 3, "price": 850},
            "ac_isolator": {"item": "AC Isolator 80A", "qty": 2, "price": 550},
            "surge_dc": {"item": "DC Surge Protector", "qty": 3, "price": 1200},
            "cables": {"item": "Solar Cable 6mm 100m", "qty": 3, "price": 2800},
            "changeover": {"item": "Automatic Changeover 80A", "qty": 1, "price": 5500},
            "db_solar": {"item": "Solar DB 12-way", "qty": 1, "price": 1800},
            "smart_meter": {"item": "Smart Energy Meter WiFi", "qty": 1, "price": 2500},
        },
        "labour": {"installation": 18000, "commissioning": 3000, "coc": 2200},
    },
}

RESIDENTIAL_SECURITY_SYSTEMS = {
    "basic": {
        "name": "Basic Security",
        "components": {
            "alarm_panel": {"item": "Alarm Panel 8-zone", "qty": 1, "price": 2500},
            "keypad": {"item": "LCD Keypad", "qty": 1, "price": 850},
            "pir_indoor": {"item": "PIR Motion Sensor Indoor", "qty": 4, "price": 350},
            "door_contact": {"item": "Magnetic Door Contact", "qty": 3, "price": 120},
            "siren_indoor": {"item": "Indoor Siren", "qty": 1, "price": 450},
            "siren_outdoor": {"item": "Outdoor Siren Strobe", "qty": 1, "price": 850},
            "battery_backup": {"item": "Backup Battery 7Ah", "qty": 1, "price": 350},
            "cable_alarm": {"item": "Alarm Cable 4-core 100m", "qty": 1, "price": 450},
        },
        "labour": {"installation": 3500, "programming": 500},
    },
    "standard": {
        "name": "Standard Security + CCTV",
        "components": {
            "alarm_panel": {"item": "Alarm Panel 16-zone GSM", "qty": 1, "price": 4500},
            "keypad": {"item": "LCD Keypad", "qty": 2, "price": 850},
            "pir_indoor": {"item": "PIR Motion Sensor Indoor", "qty": 6, "price": 350},
            "pir_outdoor": {"item": "PIR Outdoor Dual-tech", "qty": 2, "price": 850},
            "door_contact": {"item": "Magnetic Door Contact", "qty": 5, "price": 120},
            "siren_indoor": {"item": "Indoor Siren", "qty": 1, "price": 450},
            "siren_outdoor": {"item": "Outdoor Siren Strobe", "qty": 1, "price": 850},
            "battery_backup": {"item": "Backup Battery 18Ah", "qty": 1, "price": 650},
            "nvr": {"item": "NVR 8-Channel 2TB", "qty": 1, "price": 4500},
            "camera_bullet": {"item": "IP Camera Bullet 4MP", "qty": 4, "price": 1800},
            "camera_dome": {"item": "IP Camera Dome 4MP", "qty": 2, "price": 1600},
            "poe_switch": {"item": "PoE Switch 8-port", "qty": 1, "price": 1800},
            "cable_cat6": {"item": "CAT6 Cable 305m", "qty": 1, "price": 2200},
            "monitor": {"item": "Monitor 22-inch", "qty": 1, "price": 2500},
        },
        "labour": {"installation": 8500, "programming": 1500, "cctv_setup": 2500},
    },
}

RESIDENTIAL_EV_CHARGING = {
    "level1": {
        "name": "Level 1 - Basic (3.7kW)",
        "power_kw": 3.7,
        "voltage": 230,
        "current_a": 16,
        "charge_time_typical": "12-18 hours",
        "components": {
            "charger": {"item": "EV Charger 3.7kW Type 2", "qty": 1, "price": 8500},
            "cable_6mm": {"item": "Cable 6mm 3-core 20m", "qty": 1, "price": 1800},
            "isolator": {"item": "Isolator 20A IP65", "qty": 1, "price": 350},
            "rcbo": {"item": "RCBO Type B 20A 30mA", "qty": 1, "price": 1200},
            "conduit": {"item": "Conduit 25mm + fittings", "qty": 1, "price": 650},
        },
        "labour": {"installation": 3500, "coc": 2200},
    },
    "level2": {
        "name": "Level 2 - Standard (7.4kW)",
        "power_kw": 7.4,
        "voltage": 230,
        "current_a": 32,
        "charge_time_typical": "6-9 hours",
        "components": {
            "charger": {"item": "EV Charger 7.4kW Smart", "qty": 1, "price": 14500},
            "cable_10mm": {"item": "Cable 10mm 3-core 20m", "qty": 1, "price": 3200},
            "isolator": {"item": "Isolator 40A IP65", "qty": 1, "price": 450},
            "rcbo": {"item": "RCBO Type B 32A 30mA", "qty": 1, "price": 1500},
            "conduit": {"item": "Conduit 32mm + fittings", "qty": 1, "price": 850},
        },
        "labour": {"installation": 5500, "coc": 2200},
    },
}

# ─────────────────────────────────────────────
# TIER 2: COMMERCIAL SPECIFICATIONS
# ─────────────────────────────────────────────

COMMERCIAL_LOAD_FACTORS = {
    "office": {
        "general_lighting": 12,
        "task_lighting": 5,
        "small_power": 25,
        "hvac": 80,
        "diversity_factor": 0.7,
        "power_factor": 0.9,
    },
    "retail": {
        "general_lighting": 20,
        "accent_lighting": 10,
        "small_power": 15,
        "hvac": 100,
        "refrigeration": 50,
        "diversity_factor": 0.8,
        "power_factor": 0.85,
    },
    "hospitality": {
        "general_lighting": 15,
        "decorative_lighting": 10,
        "small_power": 20,
        "hvac": 120,
        "kitchen": 200,
        "diversity_factor": 0.65,
        "power_factor": 0.85,
    },
    "healthcare": {
        "general_lighting": 15,
        "medical_equipment": 50,
        "small_power": 30,
        "hvac": 150,
        "diversity_factor": 0.75,
        "power_factor": 0.9,
        "emergency_percent": 30,
    },
    "education": {
        "general_lighting": 12,
        "small_power": 15,
        "hvac": 60,
        "computer_lab": 40,
        "diversity_factor": 0.6,
        "power_factor": 0.85,
    },
}

COMMERCIAL_DISTRIBUTION = {
    "small": {
        "main_switch": {"size": "100A", "price": 2500},
        "db_board": {"ways": 24, "price": 4500},
        "submains_cable": "25mm² 4-core",
        "earth_system": "TN-S",
        "metering": "single_tariff",
    },
    "medium": {
        "main_switch": {"size": "250A", "price": 8500},
        "db_board": {"ways": 48, "price": 12000},
        "submains_cable": "70mm² 4-core",
        "earth_system": "TN-S",
        "metering": "tou_tariff",
        "sub_dbs": 4,
    },
    "large": {
        "main_switch": {"size": "630A", "price": 25000},
        "msb": {"type": "Main Switchboard", "price": 85000},
        "submains_cable": "185mm² 4-core",
        "earth_system": "TN-S with isolated earth",
        "metering": "max_demand",
        "sub_dbs": 8,
        "transformer": True,
    },
}

COMMERCIAL_EMERGENCY_POWER = {
    "ups_small": {
        "name": "UPS System 10kVA",
        "capacity_kva": 10,
        "runtime_min": 15,
        "components": {
            "ups": {"item": "Online UPS 10kVA", "qty": 1, "price": 45000},
            "battery_bank": {"item": "Battery Bank 192V", "qty": 1, "price": 35000},
            "bypass_switch": {"item": "Manual Bypass Switch", "qty": 1, "price": 8500},
            "db_critical": {"item": "Critical Load DB", "qty": 1, "price": 5500},
        },
        "labour": 12000,
    },
    "generator_small": {
        "name": "Generator 30kVA",
        "capacity_kva": 30,
        "fuel": "diesel",
        "components": {
            "generator": {"item": "Diesel Generator 30kVA Canopy", "qty": 1, "price": 185000},
            "ats": {"item": "Automatic Transfer Switch 100A", "qty": 1, "price": 35000},
            "fuel_tank": {"item": "Fuel Tank 200L", "qty": 1, "price": 8500},
            "exhaust": {"item": "Exhaust System", "qty": 1, "price": 15000},
            "cables": {"item": "Power Cables 35mm²", "qty": 1, "price": 12000},
        },
        "labour": 35000,
        "civil": 25000,
    },
}

# ─────────────────────────────────────────────
# TIER 3: INDUSTRIAL SPECIFICATIONS
# ─────────────────────────────────────────────

INDUSTRIAL_MOTOR_LOADS = {
    "small": {
        "range_kw": "0.75-7.5kW",
        "voltage": "400V 3-Phase",
        "starter": "DOL",
        "applications": ["Pumps", "Fans", "Conveyors"],
        "typical_motors": [
            {"kw": 0.75, "price": 3500, "starter_price": 2500, "cable": "2.5mm²"},
            {"kw": 1.5, "price": 4200, "starter_price": 2800, "cable": "2.5mm²"},
            {"kw": 4.0, "price": 7500, "starter_price": 4500, "cable": "6mm²"},
            {"kw": 7.5, "price": 11500, "starter_price": 6800, "cable": "10mm²"},
        ],
    },
    "medium": {
        "range_kw": "11-45kW",
        "voltage": "400V 3-Phase",
        "starter": "Star-Delta / Soft Starter",
        "applications": ["Compressors", "Large Pumps", "Crushers"],
        "typical_motors": [
            {"kw": 11, "price": 18500, "starter_price": 12000, "cable": "16mm²"},
            {"kw": 22, "price": 35000, "starter_price": 22000, "cable": "35mm²"},
            {"kw": 37, "price": 55000, "starter_price": 35000, "cable": "70mm²"},
        ],
    },
    "large": {
        "range_kw": "55-200kW",
        "voltage": "400V / 3.3kV / 6.6kV",
        "starter": "VSD / Soft Starter",
        "applications": ["Mills", "Large Compressors", "Winders"],
        "typical_motors": [
            {"kw": 55, "price": 85000, "vsd_price": 65000, "cable": "120mm²"},
            {"kw": 110, "price": 185000, "vsd_price": 135000, "cable": "240mm²"},
            {"kw": 200, "price": 365000, "vsd_price": 245000, "cable": "2x240mm²"},
        ],
    },
}

INDUSTRIAL_MCC = {
    "standard_mcc": {
        "name": "Standard MCC Panel",
        "construction": "Form 3b",
        "ip_rating": "IP42",
        "components": {
            "incomer": {"item": "ACB Incomer 1600A", "price": 125000},
            "bus_bar": {"item": "Copper Busbar per meter", "price": 8500},
            "dol_bucket": {"item": "DOL Starter Bucket (avg)", "price": 12500},
            "sd_bucket": {"item": "Star-Delta Bucket (avg)", "price": 25000},
            "vsd_bucket": {"item": "VSD Bucket (avg)", "price": 85000},
            "pfc": {"item": "PFC Section per 50kVAr", "price": 45000},
        },
        "labour_per_bucket": 3500,
        "testing_commissioning": 25000,
    },
    "mining_mcc": {
        "name": "Mining MCC Panel (Flameproof)",
        "construction": "Form 4b",
        "ip_rating": "IP65",
        "certification": ["SANS 10108", "ATEX"],
        "components": {
            "incomer": {"item": "Flameproof ACB 1000A", "price": 285000},
            "bus_bar": {"item": "Flameproof Busbar per meter", "price": 18500},
            "fp_starter": {"item": "Flameproof DOL Starter (avg)", "price": 85000},
            "fp_vsd": {"item": "Flameproof VSD (avg)", "price": 225000},
        },
        "labour_per_bucket": 8500,
        "testing_commissioning": 65000,
    },
}

INDUSTRIAL_MV_EQUIPMENT = {
    "switchgear_11kv": {
        "name": "11kV Switchgear",
        "components": {
            "vcb_panel": {"item": "11kV VCB Panel", "price": 385000},
            "rmu": {"item": "11kV Ring Main Unit 3-way", "price": 225000},
            "metering_panel": {"item": "11kV Metering Panel", "price": 165000},
            "protection_relay": {"item": "Numerical Protection Relay", "price": 85000},
            "surge_arrester": {"item": "11kV Surge Arrester (set)", "price": 25000},
            "cable_11kv": {"item": "11kV XLPE Cable per meter", "price": 1850},
            "termination": {"item": "11kV Cable Termination (set)", "price": 45000},
        },
    },
    "transformer": {
        "name": "Distribution Transformer",
        "options": [
            {"kva": 100, "type": "11kV/400V", "price": 125000},
            {"kva": 315, "type": "11kV/400V", "price": 245000},
            {"kva": 500, "type": "11kV/400V", "price": 325000},
            {"kva": 1000, "type": "11kV/400V", "price": 545000},
        ],
    },
}

MINING_SPECIFIC = {
    "underground": {
        "flameproof_db": {"item": "Flameproof DB 12-way", "price": 125000},
        "fp_isolator": {"item": "Flameproof Isolator 200A", "price": 45000},
        "trailing_cable": {"item": "Trailing Cable per meter", "price": 450},
        "methane_monitor": {"item": "Methane Monitor", "price": 65000},
    },
    "surface": {
        "dust_proof_db": {"item": "Dust-proof DB IP65", "price": 35000},
        "weatherproof_socket": {"item": "Weatherproof Socket 125A", "price": 8500},
    },
}

# ─────────────────────────────────────────────
# TIER 4: INFRASTRUCTURE SPECIFICATIONS
# ─────────────────────────────────────────────

TOWNSHIP_ELECTRIFICATION = {
    "20A_service": {
        "name": "20A Prepaid Service",
        "connection_size": "20A",
        "admd": 1.5,
        "per_stand_cost": {
            "bulk_supply": 2500,
            "mv_reticulation": 4500,
            "transformer": 3000,
            "lv_reticulation": 5500,
            "service_connection": 2800,
            "metering": 3200,
            "earthing": 800,
            "street_lighting": 1500,
        },
        "total_per_stand": 23800,
    },
    "40A_service": {
        "name": "40A Prepaid Service",
        "connection_size": "40A",
        "admd": 3.5,
        "per_stand_cost": {
            "bulk_supply": 3500,
            "mv_reticulation": 5500,
            "transformer": 4000,
            "lv_reticulation": 6500,
            "service_connection": 3500,
            "metering": 3500,
            "earthing": 1000,
            "street_lighting": 1800,
        },
        "total_per_stand": 29300,
    },
    "60A_service": {
        "name": "60A Conventional Service",
        "connection_size": "60A",
        "admd": 5.0,
        "per_stand_cost": {
            "bulk_supply": 4500,
            "mv_reticulation": 6500,
            "transformer": 5000,
            "lv_reticulation": 7500,
            "service_connection": 4200,
            "metering": 4500,
            "earthing": 1200,
            "street_lighting": 2200,
        },
        "total_per_stand": 35600,
    },
}

RURAL_ELECTRIFICATION = {
    "grid_extension": {
        "mv_line_overhead": {
            "11kV_single": {"item": "11kV Single Phase Line per km", "price": 185000},
            "11kV_three": {"item": "11kV Three Phase Line per km", "price": 285000},
            "22kV_three": {"item": "22kV Three Phase Line per km", "price": 325000},
        },
        "mv_poles": {
            "wood_11m": {"item": "Wood Pole 11m treated", "price": 4500},
            "concrete_11m": {"item": "Concrete Pole 11m", "price": 8500},
        },
        "transformer_pole_mount": {
            "16kva": {"item": "Pole-mount Transformer 16kVA", "price": 45000},
            "50kva": {"item": "Pole-mount Transformer 50kVA", "price": 75000},
            "100kva": {"item": "Pole-mount Transformer 100kVA", "price": 115000},
        },
    },
    "solar_home_system": {
        "basic": {
            "name": "Basic Solar Home (80Wp)",
            "capacity_wp": 80,
            "components": {
                "panel": {"item": "Solar Panel 80W", "qty": 1, "price": 1200},
                "battery": {"item": "Battery 50Ah", "qty": 1, "price": 1500},
                "controller": {"item": "PWM Controller 10A", "qty": 1, "price": 450},
                "lights": {"item": "LED Lights 5W", "qty": 4, "price": 150},
            },
            "labour": 800,
            "total": 5020,
        },
    },
}

STREET_LIGHTING = {
    "luminaires": {
        "led_30w": {"item": "LED Street Light 30W", "price": 2500, "lumens": 3600, "application": "Residential roads"},
        "led_60w": {"item": "LED Street Light 60W", "price": 3800, "lumens": 7200, "application": "Collector roads"},
        "led_90w": {"item": "LED Street Light 90W", "price": 5200, "lumens": 10800, "application": "Arterial roads"},
        "led_120w": {"item": "LED Street Light 120W", "price": 6500, "lumens": 14400, "application": "Major roads"},
        "led_150w": {"item": "LED Street Light 150W", "price": 8200, "lumens": 18000, "application": "Highways"},
    },
    "poles": {
        "galvanized_6m": {"item": "Galvanized Steel Pole 6m", "price": 4500},
        "galvanized_8m": {"item": "Galvanized Steel Pole 8m", "price": 6500},
        "galvanized_10m": {"item": "Galvanized Steel Pole 10m", "price": 8500},
        "galvanized_12m": {"item": "Galvanized Steel Pole 12m", "price": 12000},
        "high_mast_18m": {"item": "High Mast Pole 18m", "price": 85000},
    },
    "installation_per_pole": {
        "excavation": 1500,
        "foundation": 2500,
        "erection": 1800,
        "wiring": 850,
        "testing": 500,
    },
    "spacing_guidelines": {
        "residential": {"pole_height": 6, "spacing": 35, "lumens_required": 3600},
        "collector": {"pole_height": 8, "spacing": 40, "lumens_required": 7200},
        "arterial": {"pole_height": 10, "spacing": 45, "lumens_required": 10800},
        "highway": {"pole_height": 12, "spacing": 50, "lumens_required": 18000},
    },
}

UTILITY_SOLAR = {
    "ground_mount": {
        "1mw": {
            "name": "1MW Ground Mount Solar",
            "capacity_mw": 1,
            "land_required_ha": 2,
            "components": {
                "panels": {"item": "Solar Panels 550W (1820 units)", "price": 4550000},
                "inverters": {"item": "String Inverters 100kW (10)", "price": 1850000},
                "mounting": {"item": "Ground Mount Structure", "price": 1250000},
                "dc_cables": {"item": "DC Cabling System", "price": 450000},
                "transformer": {"item": "Step-up Transformer 1MVA", "price": 650000},
                "switchgear": {"item": "MV Switchgear", "price": 485000},
                "scada": {"item": "SCADA & Monitoring", "price": 285000},
            },
            "civil": 850000,
            "grid_connection": 1250000,
            "epc_margin": 0.12,
        },
    },
}

# ─────────────────────────────────────────────
# SUPPLIER PRICE VARIATIONS (for cost optimizer)
# ─────────────────────────────────────────────

SUPPLIER_PRICES = {
    "budget": {
        "name": "Budget Electrical",
        "markup": 0.0,
        "quality": 3,
        "lead_time": 7,
    },
    "standard": {
        "name": "ACDC Dynamics",
        "markup": 0.10,
        "quality": 4,
        "lead_time": 3,
    },
    "premium": {
        "name": "Schneider Electric",
        "markup": 0.25,
        "quality": 5,
        "lead_time": 5,
    }
}
