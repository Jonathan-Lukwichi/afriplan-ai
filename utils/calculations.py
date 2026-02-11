"""
AfriPlan Electrical - Calculation Functions
All electrical calculation functions for SANS 10142 compliance
"""

import math
from .constants import (
    ROOM_ELECTRICAL_REQUIREMENTS,
    COMMERCIAL_LOAD_FACTORS,
    COMMERCIAL_DISTRIBUTION,
    TOWNSHIP_ELECTRIFICATION,
    STREET_LIGHTING,
    ADMD_VALUES,
    SANS_10142_CABLE_RATINGS,
    VOLTAGE_DROP_LIMITS,
    CONDUCTOR_RESISTIVITY,
    ZS_MAX_VALUES,
    DISCRIMINATION_RATIOS,
    DIVERSITY_FACTORS,
    POWER_FACTOR_TARGETS,
    ESSENTIAL_LOADS,
    SANS_10400_XA_LPD,
    FIRE_DETECTION_ZONES,
)


def calculate_electrical_requirements(rooms: list) -> dict:
    """
    Calculate electrical requirements from room list.
    Uses SANS 10142 standards for SA compliance.
    """
    total_lights = 0
    total_plugs = 0
    room_details = []
    dedicated_circuits = []

    for room in rooms:
        room_type = room.get("type", "Living Room")
        room_area = room.get("w", 4) * room.get("h", 4)

        # Get base requirements
        req = ROOM_ELECTRICAL_REQUIREMENTS.get(room_type, {"lights": 2, "plugs": 4, "special": []})

        # Scale for larger rooms (1 extra light per 20m², 2 extra plugs per 20m²)
        area_factor = max(1, room_area / 20)
        lights = max(req["lights"], int(req["lights"] * area_factor))
        plugs = max(req["plugs"], int(req["plugs"] * area_factor))

        total_lights += lights
        total_plugs += plugs

        room_details.append({
            "name": room.get("name", room_type),
            "type": room_type,
            "area": round(room_area, 1),
            "lights": lights,
            "plugs": plugs,
            "special": req["special"],
        })

        # Track dedicated circuits
        if "stove" in req["special"]:
            dedicated_circuits.append("stove")
        if "aircon prep" in req["special"]:
            dedicated_circuits.append("aircon")
        if "pool pump" in req["special"]:
            dedicated_circuits.append("pool_pump")

    # Always add geyser for residential
    dedicated_circuits.append("geyser")

    return {
        "total_lights": total_lights,
        "total_plugs": total_plugs,
        "room_details": room_details,
        "dedicated_circuits": list(set(dedicated_circuits)),
    }


def calculate_load_and_circuits(elec_req: dict) -> dict:
    """
    Calculate load, circuits, and DB sizing per SANS 10142.
    """
    # Load calculation (SANS 10142 diversity factors)
    light_load = elec_req["total_lights"] * 50   # 50W per LED point (modern LED era)
    plug_load = elec_req["total_plugs"] * 250    # 250W per point

    # Apply diversity (50% for residential per SANS)
    diversified_load = (light_load + plug_load) * 0.5

    # Add dedicated loads (full load, no diversity)
    dedicated_load = 0
    if "stove" in elec_req["dedicated_circuits"]:
        dedicated_load += 8000  # 8kW stove
    if "geyser" in elec_req["dedicated_circuits"]:
        dedicated_load += 3000  # 3kW geyser
    if "aircon" in elec_req["dedicated_circuits"]:
        dedicated_load += 2000  # 2kW aircon
    if "pool_pump" in elec_req["dedicated_circuits"]:
        dedicated_load += 1500  # 1.5kW pool pump

    total_load_w = diversified_load + dedicated_load
    total_load_kva = total_load_w / 1000 / 0.85  # Power factor 0.85

    # Circuit calculation (SANS 10142: max 10 points per circuit)
    lighting_circuits = math.ceil(elec_req["total_lights"] / 10)
    power_circuits = math.ceil(elec_req["total_plugs"] / 10)
    dedicated_count = len(elec_req["dedicated_circuits"])

    # Total circuits = lighting + power + dedicated + main + ELCB
    total_circuits = lighting_circuits + power_circuits + dedicated_count + 2

    # DB sizing (allow 20% spare capacity)
    if total_circuits <= 6:
        db_size = "8_way"
        db_price = 750
    elif total_circuits <= 10:
        db_size = "12_way"
        db_price = 1100
    elif total_circuits <= 14:
        db_size = "16_way"
        db_price = 1500
    else:
        db_size = "24_way"
        db_price = 2200

    # Main breaker sizing
    main_current = (total_load_kva * 1000) / 230
    if main_current <= 35:
        main_size = "40A"
        main_price = 280
    elif main_current <= 55:
        main_size = "60A"
        main_price = 350
    else:
        main_size = "80A"
        main_price = 450

    return {
        "total_load_w": round(total_load_w, 0),
        "total_load_kva": round(total_load_kva, 1),
        "lighting_circuits": lighting_circuits,
        "power_circuits": power_circuits,
        "dedicated_circuits": dedicated_count,
        "total_circuits": total_circuits,
        "db_size": db_size,
        "db_price": db_price,
        "main_size": main_size,
        "main_price": main_price,
    }


def calculate_electrical_bq(elec_req: dict, circuit_info: dict) -> list:
    """
    Generate complete electrical Bill of Quantities.
    """
    bq = []

    # 1. DB Board and Protection
    bq.append({"category": "DB Board & Protection", "item": f"DB Board {circuit_info['db_size'].replace('_', ' ')}",
               "qty": 1, "unit": "each", "rate": circuit_info['db_price'],
               "total": circuit_info['db_price']})
    bq.append({"category": "DB Board & Protection", "item": f"Main Switch {circuit_info['main_size']}",
               "qty": 1, "unit": "each", "rate": circuit_info['main_price'],
               "total": circuit_info['main_price']})
    bq.append({"category": "DB Board & Protection", "item": "Earth Leakage 63A 30mA",
               "qty": 1, "unit": "each", "rate": 950, "total": 950})
    bq.append({"category": "DB Board & Protection", "item": "Surge Arrester Type 2",
               "qty": 1, "unit": "each", "rate": 1800, "total": 1800})

    # Circuit breakers
    bq.append({"category": "DB Board & Protection", "item": "Circuit Breaker 10A (lighting)",
               "qty": circuit_info['lighting_circuits'], "unit": "each", "rate": 65,
               "total": circuit_info['lighting_circuits'] * 65})
    bq.append({"category": "DB Board & Protection", "item": "Circuit Breaker 16A (power)",
               "qty": circuit_info['power_circuits'], "unit": "each", "rate": 65,
               "total": circuit_info['power_circuits'] * 65})

    # Dedicated circuit breakers
    if "stove" in elec_req["dedicated_circuits"]:
        bq.append({"category": "DB Board & Protection", "item": "Circuit Breaker 32A (stove)",
                   "qty": 1, "unit": "each", "rate": 85, "total": 85})
    if "geyser" in elec_req["dedicated_circuits"]:
        bq.append({"category": "DB Board & Protection", "item": "Circuit Breaker 20A (geyser)",
                   "qty": 1, "unit": "each", "rate": 70, "total": 70})
    if "aircon" in elec_req["dedicated_circuits"]:
        bq.append({"category": "DB Board & Protection", "item": "Circuit Breaker 20A (aircon)",
                   "qty": 1, "unit": "each", "rate": 70, "total": 70})

    # 2. Cables (estimate 8m per point average)
    lighting_cable_m = elec_req["total_lights"] * 8
    power_cable_m = elec_req["total_plugs"] * 8

    lighting_rolls = max(1, int(lighting_cable_m / 100) + 1)
    power_rolls = max(1, int(power_cable_m / 100) + 1)

    bq.append({"category": "Cables", "item": "SURFIX 1.5mm 3-core (lighting)",
               "qty": lighting_rolls, "unit": "roll 100m", "rate": 1850,
               "total": lighting_rolls * 1850})
    bq.append({"category": "Cables", "item": "SURFIX 2.5mm 3-core (power)",
               "qty": power_rolls, "unit": "roll 100m", "rate": 2950,
               "total": power_rolls * 2950})

    if "stove" in elec_req["dedicated_circuits"]:
        bq.append({"category": "Cables", "item": "SURFIX 6mm 3-core (stove)",
                   "qty": 1, "unit": "roll 100m", "rate": 6800, "total": 6800})

    bq.append({"category": "Cables", "item": "Earth wire 10mm green/yellow",
               "qty": 1, "unit": "roll", "rate": 1200, "total": 1200})

    # 3. Conduit and Sundries
    total_points = elec_req["total_lights"] + elec_req["total_plugs"]
    conduit_lengths = total_points * 2  # 2 x 4m lengths per point

    bq.append({"category": "Conduit & Sundries", "item": "PVC Conduit 20mm x 4m",
               "qty": conduit_lengths, "unit": "length", "rate": 35,
               "total": conduit_lengths * 35})
    bq.append({"category": "Conduit & Sundries", "item": "Junction Boxes",
               "qty": total_points, "unit": "each", "rate": 15,
               "total": total_points * 15})
    bq.append({"category": "Conduit & Sundries", "item": "Saddle Clips 20mm",
               "qty": conduit_lengths * 4, "unit": "each", "rate": 2,
               "total": conduit_lengths * 4 * 2})
    bq.append({"category": "Conduit & Sundries", "item": "Earth Spike 1.5m copper",
               "qty": 1, "unit": "each", "rate": 180, "total": 180})
    bq.append({"category": "Conduit & Sundries", "item": "Earth Bar 12-way",
               "qty": 1, "unit": "each", "rate": 95, "total": 95})

    # 4. Switches and Sockets
    bq.append({"category": "Switches & Sockets", "item": "Light Switch (mixed levers)",
               "qty": elec_req["total_lights"], "unit": "each", "rate": 55,
               "total": elec_req["total_lights"] * 55})
    bq.append({"category": "Switches & Sockets", "item": "Socket Outlet Double Switched",
               "qty": elec_req["total_plugs"], "unit": "each", "rate": 95,
               "total": elec_req["total_plugs"] * 95})
    bq.append({"category": "Switches & Sockets", "item": "Flush Wall Boxes",
               "qty": total_points, "unit": "each", "rate": 18,
               "total": total_points * 18})
    bq.append({"category": "Switches & Sockets", "item": "Ceiling Roses DCL",
               "qty": elec_req["total_lights"], "unit": "each", "rate": 35,
               "total": elec_req["total_lights"] * 35})

    if "stove" in elec_req["dedicated_circuits"]:
        bq.append({"category": "Switches & Sockets", "item": "Stove Isolator 45A + Socket",
                   "qty": 1, "unit": "each", "rate": 400, "total": 400})
    if "geyser" in elec_req["dedicated_circuits"]:
        bq.append({"category": "Switches & Sockets", "item": "Geyser Isolator 20A",
                   "qty": 1, "unit": "each", "rate": 120, "total": 120})

    # 5. Light Fittings
    bq.append({"category": "Light Fittings", "item": "LED Downlight 12W (incl)",
               "qty": elec_req["total_lights"], "unit": "each", "rate": 120,
               "total": elec_req["total_lights"] * 120})

    # 6. Labour
    bq.append({"category": "Labour", "item": "Light Points Installation",
               "qty": elec_req["total_lights"], "unit": "point", "rate": 280,
               "total": elec_req["total_lights"] * 280})
    bq.append({"category": "Labour", "item": "Power Points Installation",
               "qty": elec_req["total_plugs"], "unit": "point", "rate": 320,
               "total": elec_req["total_plugs"] * 320})
    bq.append({"category": "Labour", "item": "DB Board Installation",
               "qty": 1, "unit": "each", "rate": 1500, "total": 1500})
    bq.append({"category": "Labour", "item": "Earth System Installation",
               "qty": 1, "unit": "each", "rate": 800, "total": 800})

    if "stove" in elec_req["dedicated_circuits"]:
        bq.append({"category": "Labour", "item": "Stove Circuit Installation",
                   "qty": 1, "unit": "each", "rate": 1800, "total": 1800})
    if "geyser" in elec_req["dedicated_circuits"]:
        bq.append({"category": "Labour", "item": "Geyser Circuit Installation",
                   "qty": 1, "unit": "each", "rate": 1500, "total": 1500})

    # 7. Compliance
    bq.append({"category": "Compliance", "item": "COC Inspection & Certificate",
               "qty": 1, "unit": "each", "rate": 2200, "total": 2200})

    return bq


def calculate_commercial_electrical(area_m2: float, building_type: str, floors: int = 1,
                                     emergency_power: bool = False, fire_alarm: bool = True) -> dict:
    """
    Calculate commercial electrical requirements based on area and building type.
    Uses SANS 10142 / IEC load densities.
    """
    load_factors = COMMERCIAL_LOAD_FACTORS.get(building_type, COMMERCIAL_LOAD_FACTORS["office"])

    # Calculate connected loads
    lighting_load = area_m2 * (load_factors.get("general_lighting", 12) + load_factors.get("task_lighting", 0))
    power_load = area_m2 * load_factors.get("small_power", 25)
    hvac_load = area_m2 * load_factors.get("hvac", 80)

    # Special loads
    special_load = 0
    if building_type == "retail":
        special_load = area_m2 * load_factors.get("refrigeration", 0) * 0.3
    elif building_type == "hospitality":
        special_load = area_m2 * load_factors.get("kitchen", 0) * 0.1
    elif building_type == "healthcare":
        special_load = area_m2 * load_factors.get("medical_equipment", 0)

    total_connected_load = lighting_load + power_load + hvac_load + special_load

    # Apply diversity
    diversified_load = total_connected_load * load_factors.get("diversity_factor", 0.7)

    # Calculate kVA
    power_factor = load_factors.get("power_factor", 0.9)
    total_kva = diversified_load / 1000 / power_factor

    # Determine distribution requirements
    if area_m2 < 500:
        dist = COMMERCIAL_DISTRIBUTION["small"]
        building_size = "small"
    elif area_m2 < 2000:
        dist = COMMERCIAL_DISTRIBUTION["medium"]
        building_size = "medium"
    else:
        dist = COMMERCIAL_DISTRIBUTION["large"]
        building_size = "large"

    # Circuit calculations
    lighting_circuits = math.ceil((lighting_load / 1000) / 2)
    power_circuits = math.ceil((power_load / 1000) / 3.5)
    hvac_circuits = math.ceil(hvac_load / 1000 / 5)

    # BQ Items
    bq_items = []

    # Main distribution
    bq_items.append({
        "category": "Main Distribution",
        "item": f"Main Switch {dist['main_switch']['size']}",
        "qty": 1, "unit": "each",
        "rate": dist['main_switch']['price'],
        "total": dist['main_switch']['price']
    })

    if building_size == "large" and "msb" in dist:
        bq_items.append({
            "category": "Main Distribution",
            "item": dist['msb']['type'],
            "qty": 1, "unit": "each",
            "rate": dist['msb']['price'],
            "total": dist['msb']['price']
        })
    else:
        bq_items.append({
            "category": "Main Distribution",
            "item": f"DB Board {dist['db_board']['ways']}-way",
            "qty": 1, "unit": "each",
            "rate": dist['db_board']['price'],
            "total": dist['db_board']['price']
        })

    # Sub DBs for larger buildings
    if "sub_dbs" in dist:
        bq_items.append({
            "category": "Distribution",
            "item": "Sub Distribution Boards",
            "qty": dist["sub_dbs"], "unit": "each",
            "rate": 8500,
            "total": dist["sub_dbs"] * 8500
        })

    # Cables
    bq_items.append({
        "category": "Cables",
        "item": f"Submains Cable {dist['submains_cable']}",
        "qty": floors * 25, "unit": "meters",
        "rate": 350,
        "total": floors * 25 * 350
    })

    # Labour
    bq_items.append({
        "category": "Labour",
        "item": "Installation Labour",
        "qty": int(area_m2 / 10), "unit": "hours",
        "rate": 380,
        "total": int(area_m2 / 10) * 380
    })

    # Compliance
    bq_items.append({
        "category": "Compliance",
        "item": "COC Inspection & Certificate",
        "qty": 1, "unit": "each",
        "rate": 4500,
        "total": 4500
    })

    return {
        "total_kva": round(total_kva, 1),
        "lighting_load": round(lighting_load / 1000, 1),
        "power_load": round(power_load / 1000, 1),
        "hvac_load": round(hvac_load / 1000, 1),
        "lighting_circuits": lighting_circuits,
        "power_circuits": power_circuits,
        "hvac_circuits": hvac_circuits,
        "building_size": building_size,
        "bq_items": bq_items,
    }


def calculate_township_electrification(num_stands: int, service_type: str = "20A_service") -> dict:
    """
    Calculate township electrification costs per NRS 034 standards.
    """
    service = TOWNSHIP_ELECTRIFICATION.get(service_type, TOWNSHIP_ELECTRIFICATION["20A_service"])

    bq_items = []

    for component, cost in service["per_stand_cost"].items():
        bq_items.append({
            "category": "Infrastructure",
            "item": component.replace("_", " ").title(),
            "qty": num_stands,
            "unit": "stands",
            "rate": cost,
            "total": cost * num_stands
        })

    total_cost = service["total_per_stand"] * num_stands

    return {
        "num_stands": num_stands,
        "service_type": service["name"],
        "connection_size": service["connection_size"],
        "admd": service["admd"],
        "cost_per_stand": service["total_per_stand"],
        "total_cost": total_cost,
        "bq_items": bq_items,
    }


def calculate_street_lighting(road_length_m: float, road_type: str = "residential") -> dict:
    """
    Calculate street lighting requirements per SANS 10098.
    """
    guidelines = STREET_LIGHTING["spacing_guidelines"].get(road_type, STREET_LIGHTING["spacing_guidelines"]["residential"])

    pole_height = guidelines["pole_height"]
    spacing = guidelines["spacing"]
    lumens_required = guidelines["lumens_required"]

    # Calculate number of poles
    num_poles = math.ceil(road_length_m / spacing) + 1

    # Select appropriate luminaire
    luminaire_key = f"led_{30 if road_type == 'residential' else 60 if road_type == 'collector' else 90}w"
    luminaire = STREET_LIGHTING["luminaires"].get(luminaire_key, STREET_LIGHTING["luminaires"]["led_60w"])

    # Select appropriate pole
    pole_key = f"galvanized_{pole_height}m"
    pole = STREET_LIGHTING["poles"].get(pole_key, STREET_LIGHTING["poles"]["galvanized_8m"])

    # Installation costs per pole
    installation = STREET_LIGHTING["installation_per_pole"]
    install_per_pole = sum(installation.values())

    bq_items = []

    bq_items.append({
        "category": "Luminaires",
        "item": luminaire["item"],
        "qty": num_poles,
        "unit": "each",
        "rate": luminaire["price"],
        "total": num_poles * luminaire["price"]
    })

    bq_items.append({
        "category": "Poles",
        "item": pole["item"],
        "qty": num_poles,
        "unit": "each",
        "rate": pole["price"],
        "total": num_poles * pole["price"]
    })

    bq_items.append({
        "category": "Installation",
        "item": "Complete Pole Installation",
        "qty": num_poles,
        "unit": "each",
        "rate": install_per_pole,
        "total": num_poles * install_per_pole
    })

    # Control system
    bq_items.append({
        "category": "Control",
        "item": "Photocell Controllers",
        "qty": num_poles,
        "unit": "each",
        "rate": 450,
        "total": num_poles * 450
    })

    # Cabling (2m per pole average)
    cable_length = num_poles * 2
    bq_items.append({
        "category": "Cables",
        "item": "Armoured Cable 4mm²",
        "qty": int(road_length_m * 1.1),
        "unit": "meters",
        "rate": 85,
        "total": int(road_length_m * 1.1) * 85
    })

    total_cost = sum(item["total"] for item in bq_items)

    return {
        "road_length": road_length_m,
        "road_type": road_type,
        "num_poles": num_poles,
        "pole_height": pole_height,
        "spacing": spacing,
        "total_cost": total_cost,
        "cost_per_meter": round(total_cost / road_length_m, 2),
        "bq_items": bq_items,
    }


def calculate_industrial_electrical(total_motor_load: float, num_motors: int,
                                     hazardous_area: bool = False, mv_required: bool = False,
                                     project_type: str = "manufacturing") -> dict:
    """
    Calculate industrial electrical requirements for motors, MCC, and distribution.
    """
    from .constants import INDUSTRIAL_MCC, INDUSTRIAL_MV_EQUIPMENT, MINING_SPECIFIC

    bq_items = []

    # Determine MCC type based on hazardous area
    mcc_type = "mining_mcc" if hazardous_area else "standard_mcc"
    mcc = INDUSTRIAL_MCC[mcc_type]

    # MCC Panel base cost
    mcc_base_cost = sum(c['price'] for c in mcc["components"].values())
    bq_items.append({
        "category": "Motor Control Centre",
        "item": mcc["name"],
        "qty": 1,
        "unit": "each",
        "rate": mcc_base_cost,
        "total": mcc_base_cost
    })

    # Motor starters based on configuration
    if hazardous_area:
        # Flameproof starters for hazardous areas
        avg_motor_kw = total_motor_load / num_motors if num_motors > 0 else 10
        if avg_motor_kw <= 7.5:
            starter_price = 85000  # Flameproof DOL
            starter_type = "Flameproof DOL Starter"
        elif avg_motor_kw <= 45:
            starter_price = 125000  # Flameproof Star-Delta
            starter_type = "Flameproof Star-Delta Starter"
        else:
            starter_price = 225000  # Flameproof VSD
            starter_type = "Flameproof VSD Starter"
    else:
        avg_motor_kw = total_motor_load / num_motors if num_motors > 0 else 10
        if avg_motor_kw <= 7.5:
            starter_price = 12500  # DOL
            starter_type = "DOL Starter Bucket"
        elif avg_motor_kw <= 45:
            starter_price = 25000  # Star-Delta
            starter_type = "Star-Delta Starter Bucket"
        else:
            starter_price = 85000  # VSD
            starter_type = "VSD Starter Bucket"

    bq_items.append({
        "category": "Motor Starters",
        "item": starter_type,
        "qty": num_motors,
        "unit": "each",
        "rate": starter_price,
        "total": num_motors * starter_price
    })

    # Cables - estimate based on motor sizes
    avg_motor_kw = total_motor_load / num_motors if num_motors > 0 else 10
    if avg_motor_kw <= 7.5:
        cable_size = "6mm²"
        cable_price_per_m = 85
    elif avg_motor_kw <= 45:
        cable_size = "35mm²"
        cable_price_per_m = 250
    else:
        cable_size = "120mm²"
        cable_price_per_m = 650

    cable_length = num_motors * 30  # Estimate 30m per motor average
    bq_items.append({
        "category": "Cables",
        "item": f"Motor Power Cable {cable_size}",
        "qty": cable_length,
        "unit": "meters",
        "rate": cable_price_per_m,
        "total": cable_length * cable_price_per_m
    })

    # Control cables
    control_cable_length = num_motors * 50
    bq_items.append({
        "category": "Cables",
        "item": "Control Cable 1.5mm² Screened",
        "qty": control_cable_length,
        "unit": "meters",
        "rate": 35,
        "total": control_cable_length * 35
    })

    # MV Equipment if required
    if mv_required:
        # VCB Panel
        bq_items.append({
            "category": "MV Equipment",
            "item": "11kV VCB Panel",
            "qty": 1,
            "unit": "each",
            "rate": 385000,
            "total": 385000
        })

        # Transformer sizing based on load
        load_kva = total_motor_load / 0.85  # Power factor
        if load_kva <= 80:
            tx_kva, tx_price = 100, 125000
        elif load_kva <= 250:
            tx_kva, tx_price = 315, 245000
        elif load_kva <= 400:
            tx_kva, tx_price = 500, 325000
        else:
            tx_kva, tx_price = 1000, 545000

        bq_items.append({
            "category": "MV Equipment",
            "item": f"Transformer {tx_kva}kVA 11kV/400V",
            "qty": 1,
            "unit": "each",
            "rate": tx_price,
            "total": tx_price
        })

        # MV Cables
        bq_items.append({
            "category": "MV Equipment",
            "item": "11kV XLPE Cable",
            "qty": 50,
            "unit": "meters",
            "rate": 1850,
            "total": 50 * 1850
        })

        # Protection relay
        bq_items.append({
            "category": "MV Equipment",
            "item": "Numerical Protection Relay",
            "qty": 1,
            "unit": "each",
            "rate": 85000,
            "total": 85000
        })

    # Mining-specific equipment
    if project_type in ["mining_surface", "mining_underground"]:
        mine_type = "underground" if project_type == "mining_underground" else "surface"
        equipment = MINING_SPECIFIC.get(mine_type, {})
        for key, item in equipment.items():
            bq_items.append({
                "category": "Mining Equipment",
                "item": item['item'],
                "qty": 1,
                "unit": "each",
                "rate": item['price'],
                "total": item['price']
            })

    # Power Factor Correction
    pfc_kvar = total_motor_load * 0.4  # Estimate 0.4 kVAr per kW
    pfc_price = int(pfc_kvar / 50) * 45000  # R45,000 per 50 kVAr
    if pfc_price > 0:
        bq_items.append({
            "category": "Power Factor Correction",
            "item": f"PFC Panel {int(pfc_kvar)} kVAr",
            "qty": 1,
            "unit": "each",
            "rate": pfc_price,
            "total": pfc_price
        })

    # Labour
    labour_cost = mcc["testing_commissioning"] + (num_motors * mcc["labour_per_bucket"])
    bq_items.append({
        "category": "Labour",
        "item": "Installation & Commissioning",
        "qty": 1,
        "unit": "lump sum",
        "rate": labour_cost,
        "total": labour_cost
    })

    # Calculate totals
    subtotal = sum(item["total"] for item in bq_items)

    return {
        "total_motor_load": total_motor_load,
        "num_motors": num_motors,
        "hazardous_area": hazardous_area,
        "mv_required": mv_required,
        "mcc_type": mcc_type,
        "subtotal": subtotal,
        "bq_items": bq_items,
    }


# ─────────────────────────────────────────────
# SANS 10142 COMPLIANCE CALCULATORS
# ─────────────────────────────────────────────

def calculate_admd(dwelling_type: str, num_dwellings: int = 1,
                   geyser_type: str = "electric", has_pool: bool = False,
                   has_aircon: bool = False) -> dict:
    """
    Calculate After Diversity Maximum Demand per NRS 034.
    Used for Eskom supply applications and metering sizing.

    Args:
        dwelling_type: Type of dwelling from ADMD_VALUES
        num_dwellings: Number of dwellings (for bulk applications)
        geyser_type: "electric", "solar", or "gas"
        has_pool: Whether the dwelling has a pool
        has_aircon: Whether the dwelling has air conditioning

    Returns:
        dict with ADMD calculations and recommendations
    """
    base_data = ADMD_VALUES.get(dwelling_type, ADMD_VALUES["standard_house"])
    base_admd = base_data["admd_kva"]

    # Adjustments for specific loads
    adjustment = 0
    adjustment_notes = []

    if geyser_type == "solar":
        adjustment -= 0.5  # Reduced load with solar geyser
        adjustment_notes.append("Solar geyser: -0.5 kVA")
    elif geyser_type == "gas":
        adjustment -= 1.0  # No electric geyser load
        adjustment_notes.append("Gas geyser: -1.0 kVA")

    if has_pool and "pool" not in dwelling_type.lower():
        adjustment += 1.5  # Pool pump addition
        adjustment_notes.append("Pool pump: +1.5 kVA")

    if has_aircon and dwelling_type in ["rdp_low_cost", "standard_house"]:
        adjustment += 1.0  # AC not typically included in base ADMD
        adjustment_notes.append("Air conditioning: +1.0 kVA")

    adjusted_admd = max(1.5, base_admd + adjustment)

    # Calculate for multiple dwellings (diversity factor)
    if num_dwellings > 1:
        # NRS 034 diversity factors for multiple dwellings
        if num_dwellings <= 5:
            diversity = 1.0
        elif num_dwellings <= 10:
            diversity = 0.85
        elif num_dwellings <= 20:
            diversity = 0.75
        elif num_dwellings <= 50:
            diversity = 0.65
        else:
            diversity = 0.55

        total_admd = adjusted_admd * num_dwellings * diversity
    else:
        diversity = 1.0
        total_admd = adjusted_admd

    # Determine recommended supply size
    supply_current = (total_admd * 1000) / 230  # Single phase

    if supply_current <= 20:
        recommended_supply = "20A"
        supply_type = "Single Phase"
    elif supply_current <= 40:
        recommended_supply = "40A"
        supply_type = "Single Phase"
    elif supply_current <= 60:
        recommended_supply = "60A"
        supply_type = "Single Phase"
    elif supply_current <= 80:
        recommended_supply = "80A"
        supply_type = "Single Phase"
    elif supply_current <= 100:
        recommended_supply = "100A"
        supply_type = "Single Phase"
    else:
        # Three phase required
        three_phase_current = (total_admd * 1000) / (400 * math.sqrt(3))
        if three_phase_current <= 60:
            recommended_supply = "60A"
        elif three_phase_current <= 80:
            recommended_supply = "80A"
        else:
            recommended_supply = "100A"
        supply_type = "Three Phase"

    return {
        "dwelling_type": dwelling_type,
        "dwelling_name": base_data["name"],
        "base_admd_kva": base_admd,
        "adjusted_admd_kva": round(adjusted_admd, 2),
        "adjustment_notes": adjustment_notes,
        "num_dwellings": num_dwellings,
        "diversity_factor": diversity,
        "total_admd_kva": round(total_admd, 2),
        "recommended_supply": recommended_supply,
        "supply_type": supply_type,
        "supply_current_a": round(supply_current, 1),
        "eskom_application_size": f"{recommended_supply} {supply_type}",
    }


def calculate_voltage_drop(
    cable_size_mm2: str,
    length_m: float,
    current_a: float,
    voltage: int = 230,
    conductor: str = "copper",
    phase: str = "single"
) -> dict:
    """
    Calculate voltage drop per SANS 10142.
    Maximum allowed: 5% total (2.5% sub-mains + 2.5% final circuits)

    Args:
        cable_size_mm2: Cable size as string (e.g., "2.5", "4.0")
        length_m: Cable length in meters (one-way)
        current_a: Load current in amps
        voltage: System voltage (230 for single phase, 400 for three phase)
        conductor: "copper" or "aluminium"
        phase: "single" or "three"

    Returns:
        dict with voltage drop calculations and compliance status
    """
    cable_data = SANS_10142_CABLE_RATINGS.get(cable_size_mm2)

    if not cable_data:
        return {
            "error": f"Cable size {cable_size_mm2}mm² not found in database",
            "valid": False
        }

    # Get voltage drop in mV/A/m from table (for single phase)
    vd_mv_a_m = cable_data["voltage_drop_mv_a_m"]

    # Calculate voltage drop
    if phase == "single":
        # Single phase: Vd = 2 × L × I × mV/A/m / 1000
        vd_volts = (2 * length_m * current_a * vd_mv_a_m) / 1000
        system_voltage = 230
    else:
        # Three phase: Vd = √3 × L × I × mV/A/m / 1000
        vd_volts = (math.sqrt(3) * length_m * current_a * vd_mv_a_m) / 1000
        system_voltage = 400

    # Calculate percentage
    vd_percent = (vd_volts / system_voltage) * 100

    # Check compliance
    max_allowed = VOLTAGE_DROP_LIMITS["total"]
    compliant = vd_percent <= max_allowed

    # Determine status
    if vd_percent <= 2.5:
        status = "Excellent"
        status_color = "green"
    elif vd_percent <= 4.0:
        status = "Good"
        status_color = "green"
    elif vd_percent <= 5.0:
        status = "Acceptable"
        status_color = "amber"
    else:
        status = "Non-compliant"
        status_color = "red"

    # Calculate voltage at load end
    voltage_at_load = system_voltage - vd_volts

    return {
        "cable_size_mm2": cable_size_mm2,
        "length_m": length_m,
        "current_a": current_a,
        "phase": phase,
        "voltage_drop_v": round(vd_volts, 2),
        "voltage_drop_percent": round(vd_percent, 2),
        "voltage_at_load": round(voltage_at_load, 1),
        "max_allowed_percent": max_allowed,
        "compliant": compliant,
        "status": status,
        "status_color": status_color,
        "typical_use": cable_data["typical_use"],
    }


def calculate_cable_size(
    load_current: float,
    length_m: float,
    max_vd_percent: float = 5.0,
    phase: str = "single",
    installation_method: str = "C"
) -> dict:
    """
    Select appropriate cable size per SANS 10142 Annexure B.
    Considers both current carrying capacity and voltage drop.

    Args:
        load_current: Design current in amps
        length_m: Cable length in meters
        max_vd_percent: Maximum voltage drop percentage allowed
        phase: "single" or "three"
        installation_method: Installation reference method

    Returns:
        dict with recommended cable size and verification
    """
    system_voltage = 230 if phase == "single" else 400

    # Find cable sizes that meet current rating
    suitable_cables = []

    for size, data in SANS_10142_CABLE_RATINGS.items():
        if phase == "single":
            rating = data["current_rating_single"]
        else:
            rating = data["current_rating_three"]

        if rating >= load_current:
            # Calculate voltage drop for this cable
            vd_result = calculate_voltage_drop(
                size, length_m, load_current,
                voltage=system_voltage, phase=phase
            )

            if vd_result.get("valid", True):
                suitable_cables.append({
                    "size": size,
                    "current_rating": rating,
                    "voltage_drop_percent": vd_result["voltage_drop_percent"],
                    "compliant": vd_result["voltage_drop_percent"] <= max_vd_percent,
                    "max_breaker": data["max_breaker"],
                    "typical_use": data["typical_use"],
                })

    # Find smallest cable that meets both criteria
    compliant_cables = [c for c in suitable_cables if c["compliant"]]

    if compliant_cables:
        recommended = compliant_cables[0]  # Smallest compliant cable
        status = "OK"
    elif suitable_cables:
        # Current OK but voltage drop too high - recommend larger
        recommended = suitable_cables[-1]  # Largest available
        status = "Voltage drop exceeds limit - consider shorter run or larger cable"
    else:
        recommended = None
        status = "No suitable cable found - load too high"

    return {
        "load_current": load_current,
        "length_m": length_m,
        "phase": phase,
        "max_vd_percent": max_vd_percent,
        "recommended": recommended,
        "all_options": suitable_cables[:5],  # Top 5 options
        "status": status,
    }


def check_discrimination(upstream_rating: int, downstream_rating: int) -> dict:
    """
    Check discrimination between circuit breakers per SANS 10142.
    Proper discrimination ensures only the faulty circuit trips.

    Args:
        upstream_rating: Upstream breaker rating in amps
        downstream_rating: Downstream breaker rating in amps

    Returns:
        dict with discrimination analysis
    """
    if downstream_rating >= upstream_rating:
        return {
            "discriminates": False,
            "ratio": 0,
            "status": "Invalid - downstream must be smaller than upstream",
            "recommendation": f"Downstream breaker ({downstream_rating}A) must be smaller than upstream ({upstream_rating}A)",
        }

    ratio = upstream_rating / downstream_rating

    min_ratio = DISCRIMINATION_RATIOS["minimum"]
    rec_ratio = DISCRIMINATION_RATIOS["recommended"]

    if ratio >= rec_ratio:
        status = "Good discrimination"
        compliant = True
    elif ratio >= min_ratio:
        status = "Marginal discrimination - acceptable"
        compliant = True
    else:
        status = "Poor discrimination - breakers may trip together"
        compliant = False

    return {
        "upstream_rating": upstream_rating,
        "downstream_rating": downstream_rating,
        "ratio": round(ratio, 2),
        "minimum_ratio": min_ratio,
        "recommended_ratio": rec_ratio,
        "discriminates": compliant,
        "status": status,
        "recommendation": f"For reliable discrimination, use {int(downstream_rating * rec_ratio)}A or larger upstream" if not compliant else "Configuration is acceptable",
    }


def calculate_earth_loop_impedance(
    cable_size_mm2: str,
    length_m: float,
    breaker_rating: int,
    phase: str = "single"
) -> dict:
    """
    Calculate earth fault loop impedance and verify disconnection time.
    Per SANS 10142 requirements for automatic disconnection.

    Args:
        cable_size_mm2: Cable size (same for live and earth assumed)
        length_m: Cable length in meters
        breaker_rating: MCB rating in amps
        phase: "single" or "three"

    Returns:
        dict with earth loop impedance calculations
    """
    # Get cable resistance
    cable_data = SANS_10142_CABLE_RATINGS.get(cable_size_mm2)
    if not cable_data:
        return {
            "error": f"Cable size {cable_size_mm2}mm² not found",
            "valid": False
        }

    # Calculate cable impedance (R only, simplified)
    # Using mV/A/m as proxy for resistance
    resistance_per_m = cable_data["voltage_drop_mv_a_m"] / 1000 / 2  # Per conductor

    # Earth loop = supply + live conductor + earth conductor
    # Assume supply impedance ≈ 0.35 ohms (typical)
    supply_impedance = 0.35

    # Live + Earth conductor resistance
    conductor_impedance = 2 * (resistance_per_m * length_m)

    # Total earth fault loop impedance
    total_zs = supply_impedance + conductor_impedance

    # Get maximum allowed Zs for this breaker rating
    zs_max = ZS_MAX_VALUES.get(breaker_rating)

    if zs_max is None:
        # Interpolate or use nearest
        ratings = sorted(ZS_MAX_VALUES.keys())
        if breaker_rating < ratings[0]:
            zs_max = ZS_MAX_VALUES[ratings[0]]
        elif breaker_rating > ratings[-1]:
            zs_max = ZS_MAX_VALUES[ratings[-1]]
        else:
            # Find nearest
            for i, r in enumerate(ratings):
                if r > breaker_rating:
                    zs_max = ZS_MAX_VALUES[ratings[i-1]]
                    break

    # Check compliance
    compliant = total_zs <= zs_max

    # Calculate prospective fault current
    fault_current = 230 / total_zs if total_zs > 0 else 0

    # Estimate trip time
    if fault_current > breaker_rating * 10:
        trip_time = "< 0.1s (instantaneous)"
    elif fault_current > breaker_rating * 5:
        trip_time = "< 0.4s"
    else:
        trip_time = "> 0.4s (may not trip)"

    return {
        "cable_size_mm2": cable_size_mm2,
        "length_m": length_m,
        "breaker_rating": breaker_rating,
        "calculated_zs": round(total_zs, 3),
        "maximum_zs": zs_max,
        "compliant": compliant,
        "fault_current_a": round(fault_current, 0),
        "estimated_trip_time": trip_time,
        "status": "Compliant - adequate fault protection" if compliant else "Non-compliant - Zs too high",
        "recommendation": "" if compliant else f"Reduce cable length or increase cable size to achieve Zs < {zs_max} ohms",
    }


def calculate_pfc(
    active_power_kw: float,
    current_pf: float,
    target_pf: float = 0.95
) -> dict:
    """
    Calculate power factor correction capacitor bank size.

    Args:
        active_power_kw: Active power in kW
        current_pf: Current power factor (0 to 1)
        target_pf: Target power factor (default 0.95)

    Returns:
        dict with PFC calculations and cost estimates
    """
    if current_pf >= target_pf:
        return {
            "active_power_kw": active_power_kw,
            "current_pf": current_pf,
            "target_pf": target_pf,
            "kvar_required": 0,
            "status": "No correction needed - PF already meets target",
        }

    # Calculate reactive power at current and target PF
    # tan(φ) = Q/P, so Q = P × tan(φ)
    phi_current = math.acos(current_pf)
    phi_target = math.acos(target_pf)

    q_current = active_power_kw * math.tan(phi_current)
    q_target = active_power_kw * math.tan(phi_target)

    # Required capacitor kVAr
    kvar_required = q_current - q_target

    # Round up to standard capacitor bank sizes
    standard_sizes = [5, 10, 15, 20, 25, 30, 40, 50, 75, 100, 150, 200, 300, 400, 500]
    recommended_size = min((s for s in standard_sizes if s >= kvar_required), default=standard_sizes[-1])

    # Cost estimation (approximately R600-900 per kVAr installed)
    estimated_cost = recommended_size * 750

    # Calculate current before and after
    apparent_power_before = active_power_kw / current_pf
    apparent_power_after = active_power_kw / target_pf
    kva_saved = apparent_power_before - apparent_power_after

    # Estimated annual savings (Eskom reactive energy charge ≈ R0.15/kVArh)
    # Assume 8 hours/day, 250 days/year operation
    hours_per_year = 8 * 250
    annual_kvarh_saved = kvar_required * hours_per_year
    annual_savings = annual_kvarh_saved * 0.15

    # Payback period
    payback_months = (estimated_cost / annual_savings * 12) if annual_savings > 0 else float('inf')

    return {
        "active_power_kw": active_power_kw,
        "current_pf": current_pf,
        "target_pf": target_pf,
        "current_kvar": round(q_current, 1),
        "target_kvar": round(q_target, 1),
        "kvar_required": round(kvar_required, 1),
        "recommended_bank_size": recommended_size,
        "kva_reduction": round(kva_saved, 1),
        "estimated_cost": estimated_cost,
        "annual_savings": round(annual_savings, 0),
        "payback_months": round(payback_months, 1) if payback_months != float('inf') else "N/A",
        "status": "Correction recommended" if kvar_required > 0 else "No correction needed",
    }


def calculate_essential_load(
    selected_loads: list,
    runtime_hours: float = 4.0,
    battery_dod: float = 0.5
) -> dict:
    """
    Calculate essential load for backup power sizing.
    SA-specific for load shedding scenarios.

    Args:
        selected_loads: List of load keys from ESSENTIAL_LOADS
        runtime_hours: Desired runtime in hours
        battery_dod: Battery depth of discharge (0.5 = 50%)

    Returns:
        dict with backup power sizing recommendations
    """
    total_watts = 0
    load_breakdown = []

    for load_key in selected_loads:
        load_data = ESSENTIAL_LOADS.get(load_key)
        if load_data:
            total_watts += load_data["watts"]
            load_breakdown.append({
                "load": load_key,
                "description": load_data["description"],
                "watts": load_data["watts"],
            })

    # Add 20% safety margin
    design_load = total_watts * 1.2

    # Calculate inverter size (VA rating, assume PF 0.8)
    inverter_va = design_load / 0.8

    # Standard inverter sizes
    standard_inverters = [800, 1000, 1500, 2000, 3000, 5000, 8000, 10000]
    recommended_inverter = min((s for s in standard_inverters if s >= inverter_va), default=standard_inverters[-1])

    # Calculate battery capacity
    # Wh = W × hours / DoD / efficiency (assume 85%)
    battery_wh = (total_watts * runtime_hours) / battery_dod / 0.85
    battery_kwh = battery_wh / 1000

    # For lead-acid: Ah = Wh / 12V (for 12V battery bank)
    battery_ah_12v = battery_wh / 12

    # Cost estimation
    inverter_cost = recommended_inverter * 3  # ~R3 per VA for pure sine
    battery_cost = battery_kwh * 2500  # ~R2500 per kWh for lithium, R1500 for lead-acid

    return {
        "selected_loads": load_breakdown,
        "total_load_w": total_watts,
        "design_load_w": round(design_load, 0),
        "runtime_hours": runtime_hours,
        "recommended_inverter_va": recommended_inverter,
        "battery_capacity_kwh": round(battery_kwh, 1),
        "battery_capacity_ah_12v": round(battery_ah_12v, 0),
        "estimated_inverter_cost": round(inverter_cost, 0),
        "estimated_battery_cost": round(battery_cost, 0),
        "total_system_cost": round(inverter_cost + battery_cost, 0),
        "load_shedding_stages_covered": "Stage 1-4" if runtime_hours >= 4 else "Stage 1-2",
    }


def calculate_energy_efficiency(
    lighting_load_w: float,
    area_m2: float,
    building_type: str = "office"
) -> dict:
    """
    Calculate lighting power density per SANS 10400-XA.

    Args:
        lighting_load_w: Total installed lighting load in watts
        area_m2: Floor area in square meters
        building_type: Building type for LPD limit lookup

    Returns:
        dict with energy efficiency compliance status
    """
    lpd_actual = lighting_load_w / area_m2 if area_m2 > 0 else 0

    lpd_data = SANS_10400_XA_LPD.get(building_type, SANS_10400_XA_LPD["office"])
    lpd_limit = lpd_data["limit"]

    compliant = lpd_actual <= lpd_limit

    # Calculate efficiency class
    if lpd_actual <= lpd_limit * 0.6:
        efficiency_class = "A"
        status = "Excellent - Well below SANS limit"
    elif lpd_actual <= lpd_limit * 0.8:
        efficiency_class = "B"
        status = "Good - Below SANS limit"
    elif lpd_actual <= lpd_limit:
        efficiency_class = "C"
        status = "Acceptable - Meets SANS limit"
    elif lpd_actual <= lpd_limit * 1.2:
        efficiency_class = "D"
        status = "Poor - Exceeds SANS limit"
    else:
        efficiency_class = "F"
        status = "Fail - Significantly exceeds SANS limit"

    # Calculate potential savings if non-compliant
    if not compliant:
        excess_watts = (lpd_actual - lpd_limit) * area_m2
        # Assume 8 hours/day, 250 days/year, R2.50/kWh
        annual_excess_kwh = excess_watts * 8 * 250 / 1000
        potential_savings = annual_excess_kwh * 2.50
    else:
        excess_watts = 0
        potential_savings = 0

    return {
        "lighting_load_w": lighting_load_w,
        "area_m2": area_m2,
        "building_type": building_type,
        "lpd_actual": round(lpd_actual, 2),
        "lpd_limit": lpd_limit,
        "compliant": compliant,
        "efficiency_class": efficiency_class,
        "status": status,
        "excess_watts": round(excess_watts, 0),
        "potential_annual_savings": round(potential_savings, 0),
    }


def calculate_fire_detection(
    area_m2: float,
    building_type: str,
    num_floors: int = 1,
    detector_type: str = "smoke"
) -> dict:
    """
    Calculate fire detection requirements per SANS 10139.

    Args:
        area_m2: Total floor area in square meters
        building_type: Type of building
        num_floors: Number of floors
        detector_type: "smoke" or "heat"

    Returns:
        dict with fire detection zone calculations and BQ items
    """
    # Get zone parameters
    max_area = FIRE_DETECTION_ZONES["max_area_per_zone"]
    max_detectors = FIRE_DETECTION_ZONES["max_detectors_per_zone"]
    detector_coverage = FIRE_DETECTION_ZONES["detector_coverage"][detector_type]
    detector_spacing = FIRE_DETECTION_ZONES["detector_spacing"][detector_type]

    # Calculate number of zones
    total_area = area_m2 * num_floors
    num_zones = math.ceil(total_area / max_area)

    # Calculate detectors per floor
    detectors_per_floor = math.ceil(area_m2 / detector_coverage)
    total_detectors = detectors_per_floor * num_floors

    # Ensure detectors per zone doesn't exceed max
    detectors_per_zone = math.ceil(total_detectors / num_zones)
    if detectors_per_zone > max_detectors:
        num_zones = math.ceil(total_detectors / max_detectors)
        detectors_per_zone = math.ceil(total_detectors / num_zones)

    # Call points (1 per 45m travel distance or 2 per floor minimum)
    call_points_per_floor = max(2, math.ceil(math.sqrt(area_m2) / 45) * 2)
    total_call_points = call_points_per_floor * num_floors

    # Sounders (1 per 100m² or minimum 1 per floor)
    sounders_per_floor = max(1, math.ceil(area_m2 / 100))
    total_sounders = sounders_per_floor * num_floors

    # Panel sizing
    if num_zones <= 2:
        panel_type = "2-zone conventional"
        panel_price = 3500
    elif num_zones <= 4:
        panel_type = "4-zone conventional"
        panel_price = 5500
    elif num_zones <= 8:
        panel_type = "8-zone conventional"
        panel_price = 8500
    else:
        panel_type = f"Addressable ({num_zones} loops)"
        panel_price = 15000 + (num_zones * 2000)

    # Generate BQ items
    bq_items = []

    bq_items.append({
        "category": "Fire Detection",
        "item": f"Fire Panel {panel_type}",
        "qty": 1, "unit": "each",
        "rate": panel_price,
        "total": panel_price
    })

    detector_price = 350 if detector_type == "smoke" else 280
    bq_items.append({
        "category": "Fire Detection",
        "item": f"{detector_type.title()} Detector",
        "qty": total_detectors, "unit": "each",
        "rate": detector_price,
        "total": total_detectors * detector_price
    })

    bq_items.append({
        "category": "Fire Detection",
        "item": "Manual Call Point",
        "qty": total_call_points, "unit": "each",
        "rate": 450,
        "total": total_call_points * 450
    })

    bq_items.append({
        "category": "Fire Detection",
        "item": "Electronic Sounder",
        "qty": total_sounders, "unit": "each",
        "rate": 380,
        "total": total_sounders * 380
    })

    # Cabling
    cable_length = total_area * 0.5  # Estimate 0.5m cable per m² floor area
    bq_items.append({
        "category": "Fire Detection",
        "item": "Fire Resistant Cable 2-core",
        "qty": int(cable_length), "unit": "meters",
        "rate": 25,
        "total": int(cable_length) * 25
    })

    # Labour
    labour_cost = (total_detectors * 150) + (total_call_points * 100) + 2500  # Installation + commissioning
    bq_items.append({
        "category": "Fire Detection",
        "item": "Installation & Commissioning",
        "qty": 1, "unit": "lump sum",
        "rate": labour_cost,
        "total": labour_cost
    })

    total_cost = sum(item["total"] for item in bq_items)

    return {
        "area_m2": area_m2,
        "num_floors": num_floors,
        "building_type": building_type,
        "detector_type": detector_type,
        "num_zones": num_zones,
        "total_detectors": total_detectors,
        "detectors_per_zone": detectors_per_zone,
        "total_call_points": total_call_points,
        "total_sounders": total_sounders,
        "panel_type": panel_type,
        "total_cost": total_cost,
        "bq_items": bq_items,
    }


def estimate_harmonics(
    vsd_load_kw: float,
    total_load_kw: float,
    vsd_type: str = "6_pulse"
) -> dict:
    """
    Estimate harmonic distortion from VSD/VFD loads.

    Args:
        vsd_load_kw: Total VSD/VFD load in kW
        total_load_kw: Total installation load in kW
        vsd_type: "6_pulse", "12_pulse", or "active_front_end"

    Returns:
        dict with harmonic analysis results
    """
    # VSD percentage of total load
    vsd_percentage = (vsd_load_kw / total_load_kw * 100) if total_load_kw > 0 else 0

    # Typical THDi for different VSD types
    thd_factors = {
        "6_pulse": 80,      # 80% THDi typical for 6-pulse
        "12_pulse": 12,     # 12% THDi for 12-pulse
        "active_front_end": 5,  # 5% THDi for AFE
    }

    base_thdi = thd_factors.get(vsd_type, 80)

    # Estimate system THDv based on VSD loading
    # Simplified: THDv ≈ THDi × VSD% × short circuit ratio factor
    estimated_thdv = base_thdi * (vsd_percentage / 100) * 0.1

    # IEEE 519 limits (simplified)
    thdv_limit = 5.0  # % for general systems
    thdi_limit = 8.0  # % at PCC for typical systems

    # Compliance check
    thdv_compliant = estimated_thdv <= thdv_limit

    # Derating factor for transformers
    if estimated_thdv < 5:
        derating_factor = 1.0
    elif estimated_thdv < 10:
        derating_factor = 0.95
    elif estimated_thdv < 15:
        derating_factor = 0.90
    else:
        derating_factor = 0.85

    # Recommendations
    recommendations = []
    if not thdv_compliant:
        recommendations.append("Consider harmonic filter installation")
    if vsd_percentage > 50:
        recommendations.append("High VSD loading - recommend power quality study")
    if vsd_type == "6_pulse" and vsd_load_kw > 100:
        recommendations.append("Consider 12-pulse or AFE drives for large motors")

    return {
        "vsd_load_kw": vsd_load_kw,
        "total_load_kw": total_load_kw,
        "vsd_percentage": round(vsd_percentage, 1),
        "vsd_type": vsd_type,
        "base_thdi_percent": base_thdi,
        "estimated_thdv_percent": round(estimated_thdv, 2),
        "thdv_limit": thdv_limit,
        "compliant": thdv_compliant,
        "transformer_derating": derating_factor,
        "recommendations": recommendations,
        "filter_recommended": not thdv_compliant,
    }


def generate_coc_checklist(installation_data: dict) -> dict:
    """
    Generate COC compliance checklist based on installation calculations.
    Helps contractors prepare for COC inspection.

    Args:
        installation_data: Dictionary with installation details from calculations

    Returns:
        dict with checklist items and compliance status
    """
    checklist = []
    pass_count = 0
    fail_count = 0
    warning_count = 0

    # Check 1: Earth continuity
    if installation_data.get("earth_installed", True):
        checklist.append({
            "item": "Earth continuity",
            "requirement": "Earth resistance < 10 ohms",
            "status": "pass",
            "notes": "Verify with earth resistance tester"
        })
        pass_count += 1
    else:
        checklist.append({
            "item": "Earth continuity",
            "requirement": "Earth resistance < 10 ohms",
            "status": "fail",
            "notes": "Earth system not specified"
        })
        fail_count += 1

    # Check 2: Earth leakage protection
    checklist.append({
        "item": "Earth leakage protection",
        "requirement": "30mA ELCB installed on all circuits",
        "status": "pass",
        "notes": "Test trip time < 300ms"
    })
    pass_count += 1

    # Check 3: Circuit protection
    total_circuits = installation_data.get("total_circuits", 0)
    if total_circuits > 0:
        checklist.append({
            "item": "Circuit protection",
            "requirement": "All circuits protected by MCBs",
            "status": "pass",
            "notes": f"{total_circuits} circuits identified"
        })
        pass_count += 1

    # Check 4: Cable sizing (if voltage drop data available)
    vd_percent = installation_data.get("max_voltage_drop_percent", 0)
    if vd_percent > 0:
        if vd_percent <= 5:
            checklist.append({
                "item": "Voltage drop",
                "requirement": "≤ 5% total",
                "status": "pass",
                "notes": f"Calculated: {vd_percent}%"
            })
            pass_count += 1
        else:
            checklist.append({
                "item": "Voltage drop",
                "requirement": "≤ 5% total",
                "status": "fail",
                "notes": f"Calculated: {vd_percent}% - EXCEEDS LIMIT"
            })
            fail_count += 1

    # Check 5: Surge protection
    checklist.append({
        "item": "Surge protection",
        "requirement": "Type 2 SPD at main board",
        "status": "pass",
        "notes": "Included in BQ"
    })
    pass_count += 1

    # Check 6: DB board labeling
    checklist.append({
        "item": "DB board labeling",
        "requirement": "All circuits clearly labeled",
        "status": "warning",
        "notes": "Verify labels installed on site"
    })
    warning_count += 1

    # Check 7: Polarity
    checklist.append({
        "item": "Polarity test",
        "requirement": "Correct polarity on all points",
        "status": "warning",
        "notes": "Requires on-site testing"
    })
    warning_count += 1

    # Check 8: Insulation resistance
    checklist.append({
        "item": "Insulation resistance",
        "requirement": "> 1 MΩ between conductors",
        "status": "warning",
        "notes": "Requires on-site testing with megger"
    })
    warning_count += 1

    # Check 9: Loop impedance
    zs_compliant = installation_data.get("earth_loop_compliant", True)
    checklist.append({
        "item": "Earth fault loop impedance",
        "requirement": "Zs within limits for MCB rating",
        "status": "pass" if zs_compliant else "fail",
        "notes": "Verify with loop impedance tester"
    })
    if zs_compliant:
        pass_count += 1
    else:
        fail_count += 1

    # Check 10: Discrimination
    checklist.append({
        "item": "Discrimination",
        "requirement": "Upstream MCB ≥ 1.6× downstream",
        "status": "pass",
        "notes": "Review breaker schedule"
    })
    pass_count += 1

    # Overall status
    if fail_count > 0:
        overall_status = "NOT READY - Address failed items"
    elif warning_count > 3:
        overall_status = "REVIEW REQUIRED - Multiple items need verification"
    else:
        overall_status = "READY FOR INSPECTION"

    return {
        "checklist": checklist,
        "pass_count": pass_count,
        "fail_count": fail_count,
        "warning_count": warning_count,
        "total_items": len(checklist),
        "overall_status": overall_status,
        "ready_for_coc": fail_count == 0,
    }
