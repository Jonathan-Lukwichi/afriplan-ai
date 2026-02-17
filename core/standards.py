"""
AfriPlan Electrical v4.1 — SA Electrical Standards

SANS 10142-1:2017 rules and calculations.
"""

from typing import Dict, Tuple, Optional

# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║  SANS 10142-1:2017 RULES                                                     ║
# ╚══════════════════════════════════════════════════════════════════════════════╝

SANS_10142_RULES = {
    "max_lights_per_circuit": {
        "value": 10,
        "clause": "6.5.1.1",
        "description": "Maximum 10 light points per circuit",
    },
    "max_sockets_per_circuit": {
        "value": 10,
        "clause": "6.5.1.1",
        "description": "Maximum 10 socket outlets per circuit",
    },
    "elcb_required": {
        "value": True,
        "clause": "6.12",
        "description": "Earth leakage protection mandatory",
    },
    "elcb_rating_ma": {
        "value": 30,
        "clause": "6.12.2",
        "description": "Maximum 30mA sensitivity for socket circuits",
    },
    "dedicated_stove_circuit": {
        "value": True,
        "clause": "6.5.4",
        "description": "Stove requires dedicated circuit",
    },
    "dedicated_geyser_circuit": {
        "value": True,
        "clause": "6.5.4",
        "description": "Geyser requires dedicated circuit with timer",
    },
    "max_voltage_drop_pct": {
        "value": 5.0,
        "clause": "Annexure B",
        "description": "Maximum 5% voltage drop (2.5% sub-mains + 2.5% final)",
    },
    "min_spare_ways_pct": {
        "value": 15,
        "clause": "6.2.4",
        "description": "Minimum 15% spare ways for future expansion",
    },
    "lighting_circuit_breaker_max_a": {
        "value": 10,
        "clause": "6.5.1",
        "description": "Maximum 10A breaker for lighting circuits",
    },
    "socket_circuit_breaker_max_a": {
        "value": 20,
        "clause": "6.5.1",
        "description": "Maximum 20A breaker for socket circuits",
    },
}


# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║  LOAD CALCULATIONS                                                           ║
# ╚══════════════════════════════════════════════════════════════════════════════╝

# Load values for points (LED era)
LOAD_VALUES = {
    "light_point_w": 50,              # Average light point load
    "socket_point_w": 250,            # Socket outlet load
    "stove_load_w": 12000,            # Electric stove
    "geyser_load_w": 2000,            # Standard geyser
    "geyser_load_200l_w": 4000,       # Large geyser
    "ac_split_small_w": 1500,         # Small split AC
    "ac_split_medium_w": 2500,        # Medium split AC
    "ac_split_large_w": 4000,         # Large split AC
    "pool_pump_w": 1500,              # Pool pump
    "gate_motor_w": 750,              # Gate motor
}


def validate_circuit_points(
    circuit_type: str,
    num_points: int
) -> Tuple[bool, str]:
    """
    Validate number of points on a circuit.

    Args:
        circuit_type: "lighting" or "power"
        num_points: Number of points on circuit

    Returns:
        Tuple of (is_valid, message)
    """
    if circuit_type == "lighting":
        max_points = SANS_10142_RULES["max_lights_per_circuit"]["value"]
        if num_points > max_points:
            return False, f"Lighting circuit has {num_points} points, max is {max_points}"
    elif circuit_type == "power":
        max_points = SANS_10142_RULES["max_sockets_per_circuit"]["value"]
        if num_points > max_points:
            return False, f"Power circuit has {num_points} points, max is {max_points}"

    return True, "OK"


def calculate_diversity_factor(num_circuits: int) -> float:
    """
    Calculate diversity factor based on number of circuits.
    Based on SANS 10142-1 guidelines for residential installations.

    Args:
        num_circuits: Total number of circuits

    Returns:
        Diversity factor (0.0 to 1.0)
    """
    if num_circuits <= 5:
        return 1.0
    elif num_circuits <= 10:
        return 0.85
    elif num_circuits <= 20:
        return 0.75
    elif num_circuits <= 50:
        return 0.65
    else:
        return 0.55


# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║  VOLTAGE DROP CALCULATION                                                    ║
# ╚══════════════════════════════════════════════════════════════════════════════╝

# mV/A/m values from SANS 10142-1 Annexure B (PVC insulated cables)
CABLE_MV_AM = {
    "1.5": 29.0,
    "2.5": 18.0,
    "4.0": 11.0,
    "6.0": 7.3,
    "10.0": 4.4,
    "16.0": 2.8,
    "25.0": 1.8,
    "35.0": 1.3,
    "50.0": 0.93,
    "70.0": 0.63,
    "95.0": 0.46,
    "120.0": 0.36,
}


def calculate_voltage_drop(
    cable_size_mm2: float,
    length_m: float,
    current_a: float,
    voltage_v: int = 230,
    is_three_phase: bool = False,
) -> Tuple[float, bool, str]:
    """
    Calculate voltage drop for a cable run.

    Args:
        cable_size_mm2: Cable cross-sectional area in mm²
        length_m: Cable length in meters
        current_a: Load current in amps
        voltage_v: Supply voltage (230V single, 400V three-phase)
        is_three_phase: True if 3-phase circuit

    Returns:
        Tuple of (voltage_drop_pct, is_compliant, message)
    """
    # Get mV/A/m value
    cable_key = str(cable_size_mm2)
    if cable_key not in CABLE_MV_AM:
        # Find closest match
        sizes = sorted([float(k) for k in CABLE_MV_AM.keys()])
        for size in sizes:
            if size >= cable_size_mm2:
                cable_key = str(size)
                break
        else:
            cable_key = str(sizes[-1])

    mv_am = CABLE_MV_AM.get(cable_key, 18.0)

    # Calculate voltage drop
    if is_three_phase:
        # 3-phase: VD = √3 × I × L × mV/A/m / 1000
        vd_volts = 1.732 * current_a * length_m * mv_am / 1000
        voltage_v = 400
    else:
        # Single phase: VD = 2 × I × L × mV/A/m / 1000
        vd_volts = 2 * current_a * length_m * mv_am / 1000

    vd_pct = (vd_volts / voltage_v) * 100
    max_vd = SANS_10142_RULES["max_voltage_drop_pct"]["value"]
    is_compliant = vd_pct <= max_vd

    if is_compliant:
        message = f"Voltage drop {vd_pct:.2f}% is within limit ({max_vd}%)"
    else:
        message = f"Voltage drop {vd_pct:.2f}% exceeds limit ({max_vd}%) - increase cable size"

    return round(vd_pct, 2), is_compliant, message


def calculate_cable_size(
    load_current_a: float,
    length_m: float,
    max_vd_pct: float = 2.5,
    is_three_phase: bool = False,
) -> Tuple[float, str]:
    """
    Calculate minimum cable size for a given load and length.

    Args:
        load_current_a: Load current in amps
        length_m: Cable length in meters
        max_vd_pct: Maximum allowable voltage drop percentage
        is_three_phase: True if 3-phase circuit

    Returns:
        Tuple of (cable_size_mm2, cable_description)
    """
    voltage = 400 if is_three_phase else 230
    multiplier = 1.732 if is_three_phase else 2

    # Calculate required mV/A/m
    max_vd_volts = voltage * max_vd_pct / 100
    required_mv_am = (max_vd_volts * 1000) / (multiplier * load_current_a * length_m)

    # Find smallest cable that meets requirement
    for size_str, mv_am in sorted(CABLE_MV_AM.items(), key=lambda x: float(x[0])):
        if mv_am <= required_mv_am:
            size = float(size_str)
            return size, f"{size}mm² cable"

    # Default to largest
    return 120.0, "120mm² cable (maximum standard size)"


# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║  NRS 034 ADMD CALCULATIONS                                                   ║
# ╚══════════════════════════════════════════════════════════════════════════════╝

ADMD_VALUES = {
    "rdp_low_cost": {"kva": 1.5, "supply": "20A 1-phase"},
    "standard_house": {"kva": 3.5, "supply": "60A 1-phase"},
    "medium_house": {"kva": 5.0, "supply": "60A 1-phase"},
    "large_house": {"kva": 8.0, "supply": "80A 1-phase"},
    "luxury_estate": {"kva": 12.0, "supply": "100A 3-phase"},
}


def calculate_admd(
    dwelling_type: str,
    num_dwellings: int = 1,
    has_pool: bool = False,
    has_aircon: bool = False,
    geyser_type: str = "electric",  # electric, solar, gas
) -> Dict[str, any]:
    """
    Calculate After Diversity Maximum Demand per NRS 034.

    Args:
        dwelling_type: Type of dwelling
        num_dwellings: Number of dwelling units
        has_pool: Has pool pump
        has_aircon: Has air conditioning
        geyser_type: Type of geyser (electric, solar, gas)

    Returns:
        Dict with ADMD calculation results
    """
    base = ADMD_VALUES.get(dwelling_type, ADMD_VALUES["standard_house"])
    admd_kva = base["kva"]

    # Adjustments
    if geyser_type in ("solar", "gas"):
        admd_kva -= 0.5  # Reduce for non-electric geyser

    if has_pool:
        admd_kva += 1.0  # Add for pool pump

    if has_aircon:
        admd_kva += 2.0  # Add for AC

    # Multiple dwellings diversity
    if num_dwellings > 1:
        diversity = 1 - (0.05 * min(num_dwellings - 1, 10))
        total_admd = admd_kva * num_dwellings * diversity
    else:
        total_admd = admd_kva

    # Determine supply size
    if total_admd <= 4.6:
        supply = "20A 1-phase"
        supply_kva = 4.6
    elif total_admd <= 13.8:
        supply = "60A 1-phase"
        supply_kva = 13.8
    elif total_admd <= 18.4:
        supply = "80A 1-phase"
        supply_kva = 18.4
    elif total_admd <= 55.4:
        supply = "80A 3-phase"
        supply_kva = 55.4
    elif total_admd <= 110.8:
        supply = "160A 3-phase"
        supply_kva = 110.8
    else:
        supply = "Special application"
        supply_kva = total_admd

    return {
        "dwelling_type": dwelling_type,
        "num_dwellings": num_dwellings,
        "base_admd_kva": base["kva"],
        "adjusted_admd_kva": round(admd_kva, 2),
        "total_admd_kva": round(total_admd, 2),
        "recommended_supply": supply,
        "supply_capacity_kva": supply_kva,
        "headroom_kva": round(supply_kva - total_admd, 2),
    }


# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║  COMMERCIAL LOAD FACTORS                                                     ║
# ╚══════════════════════════════════════════════════════════════════════════════╝

COMMERCIAL_LOAD_FACTORS = {
    # Building type: W/m² (lighting + power + HVAC)
    "office_open_plan": {"lighting": 11, "power": 20, "hvac": 80, "total": 111},
    "office_cellular": {"lighting": 12, "power": 15, "hvac": 70, "total": 97},
    "retail": {"lighting": 20, "power": 30, "hvac": 60, "total": 110},
    "restaurant": {"lighting": 15, "power": 72, "hvac": 60, "total": 147},
    "server_room": {"lighting": 9, "power": 1000, "hvac": 500, "total": 1509},
    "warehouse": {"lighting": 8, "power": 8, "hvac": 15, "total": 31},
    "school_classroom": {"lighting": 12, "power": 10, "hvac": 40, "total": 62},
    "healthcare": {"lighting": 15, "power": 25, "hvac": 80, "total": 120},
}


def calculate_commercial_load(
    area_m2: float,
    building_type: str,
    diversity_factor: float = 0.7,
) -> Dict[str, float]:
    """
    Calculate commercial building load.

    Args:
        area_m2: Floor area in square meters
        building_type: Type of commercial building
        diversity_factor: Diversity factor (default 0.7)

    Returns:
        Dict with load calculation results
    """
    factors = COMMERCIAL_LOAD_FACTORS.get(
        building_type,
        COMMERCIAL_LOAD_FACTORS["office_open_plan"]
    )

    lighting_kw = area_m2 * factors["lighting"] / 1000
    power_kw = area_m2 * factors["power"] / 1000
    hvac_kw = area_m2 * factors["hvac"] / 1000
    total_kw = area_m2 * factors["total"] / 1000

    diversified_kw = total_kw * diversity_factor

    return {
        "area_m2": area_m2,
        "building_type": building_type,
        "lighting_kw": round(lighting_kw, 2),
        "power_kw": round(power_kw, 2),
        "hvac_kw": round(hvac_kw, 2),
        "total_connected_kw": round(total_kw, 2),
        "diversity_factor": diversity_factor,
        "diversified_kw": round(diversified_kw, 2),
        "estimated_kva": round(diversified_kw / 0.85, 2),  # Assuming 0.85 PF
    }
