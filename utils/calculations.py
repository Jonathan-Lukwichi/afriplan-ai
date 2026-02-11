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
    light_load = elec_req["total_lights"] * 100  # 100W per point
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
