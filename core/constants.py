"""
AfriPlan Electrical v4.1 — Core Constants

Default pricing database for electrical materials and labour.
All prices in South African Rand (ZAR), updated Feb 2026.

Note: These are ESTIMATE prices for ballpark quotations.
Contractors should use their own supplier prices.
"""

from typing import Dict, Optional

# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║  LIGHT FITTINGS                                                              ║
# ╚══════════════════════════════════════════════════════════════════════════════╝

LIGHT_PRICES: Dict[str, float] = {
    # Recessed / Panel Lights
    "recessed_led_600x1200": 650.0,      # 600×1200 Recessed LED 3×18W
    "recessed_led_600x600": 480.0,       # 600×600 Recessed LED 2×18W
    "surface_mount_led_18w": 280.0,      # 18W LED Surface Mount
    "surface_mount_led_36w": 420.0,      # 36W LED Surface Mount

    # Downlights
    "downlight_led_6w": 180.0,           # 6W LED Downlight
    "downlight_led_12w": 220.0,          # 12W LED Downlight
    "downlight_led_18w": 280.0,          # 18W LED Downlight

    # Vapor Proof / Wet Area
    "vapor_proof_2x24w": 850.0,          # 2×24W Vapor Proof LED (IP65)
    "vapor_proof_2x18w": 720.0,          # 2×18W Vapor Proof LED
    "vapor_proof_1x18w": 480.0,          # 1×18W Vapor Proof LED

    # Prismatic / Linear
    "prismatic_2x18w": 580.0,            # 2×18W Prismatic LED
    "prismatic_1x36w": 420.0,            # 1×36W Prismatic LED
    "fluorescent_50w_5ft": 320.0,        # 50W 5ft Fluorescent

    # Bulkheads / Outdoor
    "bulkhead_26w": 380.0,               # 26W Bulkhead Outdoor
    "bulkhead_24w": 350.0,               # 24W Bulkhead Outdoor
    "bulkhead_18w": 280.0,               # 18W Bulkhead Outdoor

    # Flood Lights
    "flood_light_30w": 450.0,            # 30W LED Flood Light
    "flood_light_50w": 650.0,            # 50W LED Flood Light
    "flood_light_100w": 1200.0,          # 100W LED Flood Light
    "flood_light_200w": 2800.0,          # 200W LED Flood Light

    # Pole Lights (complete with pole & base)
    "pole_light_60w": 4500.0,            # Outdoor Pole Light 2300mm 60W
    "pole_light_100w": 5800.0,           # Outdoor Pole Light 3000mm 100W

    # Emergency Lights
    "emergency_light_led": 850.0,        # LED Emergency Light
    "exit_sign_led": 650.0,              # LED Exit Sign
}


# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║  SOCKET OUTLETS                                                              ║
# ╚══════════════════════════════════════════════════════════════════════════════╝

SOCKET_PRICES: Dict[str, float] = {
    # Standard Sockets
    "double_socket_300": 160.0,          # 16A Double Switched Socket @300mm
    "single_socket_300": 120.0,          # 16A Single Switched Socket @300mm
    "double_socket_1100": 180.0,         # 16A Double Switched Socket @1100mm
    "single_socket_1100": 140.0,         # 16A Single Switched Socket @1100mm

    # Specialty Sockets
    "double_socket_waterproof": 280.0,   # 16A Double Waterproof Socket
    "single_socket_waterproof": 220.0,   # 16A Single Waterproof Socket
    "double_socket_ceiling": 200.0,      # 16A Double Ceiling Socket

    # Data Points
    "data_points_cat6": 450.0,           # CAT6 Data Point
    "data_points_cat6a": 580.0,          # CAT6A Data Point
    "floor_box": 1800.0,                 # Floor Box with Power + Data

    # Specialty
    "shaver_socket": 350.0,              # Shaver Socket
    "usb_socket": 320.0,                 # USB Charging Socket
}


# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║  SWITCHES                                                                    ║
# ╚══════════════════════════════════════════════════════════════════════════════╝

SWITCH_PRICES: Dict[str, float] = {
    # Standard Switches
    "switch_1lever_1way": 60.0,          # 1-Lever 1-Way Switch @1200mm
    "switch_2lever_1way": 95.0,          # 2-Lever 1-Way Switch @1200mm
    "switch_3lever_1way": 130.0,         # 3-Lever 1-Way Switch @1200mm
    "switch_4lever_1way": 165.0,         # 4-Lever 1-Way Switch @1200mm
    "switch_1lever_2way": 85.0,          # 1-Lever 2-Way Switch @1200mm
    "switch_2lever_2way": 125.0,         # 2-Lever 2-Way Switch @1200mm

    # Specialty Switches
    "dimmer_switch": 280.0,              # Dimmer Switch
    "day_night_switch": 450.0,           # Day/Night Switch @2000mm
    "motion_sensor": 380.0,              # PIR Motion Sensor
    "timer_switch": 320.0,               # Timer Switch

    # Isolators
    "isolator_20a": 280.0,               # 20A Isolator Switch @2000mm
    "isolator_30a": 320.0,               # 30A Isolator Switch @2000mm
    "isolator_60a": 450.0,               # 60A Isolator Switch @2000mm
    "isolator_100a": 650.0,              # 100A Isolator Switch

    # Special
    "master_switch": 550.0,              # Master Switch
    "key_switch": 480.0,                 # Key Switch
}


# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║  CABLES                                                                      ║
# ╚══════════════════════════════════════════════════════════════════════════════╝

CABLE_PRICES: Dict[str, float] = {
    # GP Wire (per meter)
    "gp_wire_1.5mm2_3c": 18.0,           # 1.5mm² 3C GP Wire
    "gp_wire_2.5mm2_3c": 25.0,           # 2.5mm² 3C GP Wire
    "gp_wire_4mm2_3c": 38.0,             # 4mm² 3C GP Wire
    "gp_wire_6mm2_3c": 55.0,             # 6mm² 3C GP Wire

    # Surfix (per meter)
    "surfix_1.5mm2_3c": 22.0,            # 1.5mm² 3C Surfix
    "surfix_2.5mm2_3c": 32.0,            # 2.5mm² 3C Surfix
    "surfix_4mm2_3c": 48.0,              # 4mm² 3C Surfix
    "surfix_6mm2_3c": 72.0,              # 6mm² 3C Surfix

    # PVC SWA PVC (per meter)
    "swa_4mm2_4c": 85.0,                 # 4mm² 4C PVC SWA PVC
    "swa_6mm2_4c": 120.0,                # 6mm² 4C PVC SWA PVC
    "swa_10mm2_4c": 180.0,               # 10mm² 4C PVC SWA PVC
    "swa_16mm2_4c": 280.0,               # 16mm² 4C PVC SWA PVC
    "swa_25mm2_4c": 420.0,               # 25mm² 4C PVC SWA PVC
    "swa_35mm2_4c": 580.0,               # 35mm² 4C PVC SWA PVC
    "swa_50mm2_4c": 780.0,               # 50mm² 4C PVC SWA PVC
    "swa_70mm2_4c": 1050.0,              # 70mm² 4C PVC SWA PVC
    "swa_95mm2_4c": 1450.0,              # 95mm² 4C PVC SWA PVC
    "swa_120mm2_4c": 1850.0,             # 120mm² 4C PVC SWA PVC

    # Earth Wire (per meter)
    "earth_wire_4mm2": 15.0,             # 4mm² Earth Wire
    "earth_wire_6mm2": 22.0,             # 6mm² Earth Wire
    "earth_wire_10mm2": 35.0,            # 10mm² Earth Wire
    "earth_wire_16mm2": 55.0,            # 16mm² Earth Wire
}


# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║  DISTRIBUTION BOARDS                                                         ║
# ╚══════════════════════════════════════════════════════════════════════════════╝

DB_PRICES: Dict[str, float] = {
    # DB Boards (enclosure only)
    "db_12way_surface": 1200.0,          # 12-way Surface Mount DB
    "db_18way_surface": 1600.0,          # 18-way Surface Mount DB
    "db_24way_surface": 2200.0,          # 24-way Surface Mount DB
    "db_36way_surface": 3200.0,          # 36-way Surface Mount DB
    "db_48way_surface": 4200.0,          # 48-way Surface Mount DB

    # MCBs
    "mcb_6a_1p": 85.0,                   # 6A 1-Pole MCB
    "mcb_10a_1p": 85.0,                  # 10A 1-Pole MCB
    "mcb_16a_1p": 85.0,                  # 16A 1-Pole MCB
    "mcb_20a_1p": 85.0,                  # 20A 1-Pole MCB
    "mcb_32a_1p": 95.0,                  # 32A 1-Pole MCB
    "mcb_40a_1p": 110.0,                 # 40A 1-Pole MCB
    "mcb_63a_1p": 140.0,                 # 63A 1-Pole MCB
    "mcb_20a_3p": 320.0,                 # 20A 3-Pole MCB
    "mcb_32a_3p": 380.0,                 # 32A 3-Pole MCB
    "mcb_40a_3p": 450.0,                 # 40A 3-Pole MCB
    "mcb_63a_3p": 580.0,                 # 63A 3-Pole MCB
    "mcb_100a_3p": 850.0,                # 100A 3-Pole MCB

    # ELCBs / RCDs
    "elcb_40a_30ma_2p": 1100.0,          # 40A 30mA 2-Pole ELCB
    "elcb_63a_30ma_2p": 1250.0,          # 63A 30mA 2-Pole ELCB
    "elcb_63a_30ma_4p": 1850.0,          # 63A 30mA 4-Pole ELCB
    "elcb_100a_30ma_4p": 2400.0,         # 100A 30mA 4-Pole ELCB

    # Surge Protection
    "spd_type2_1p": 650.0,               # Type 2 SPD 1-Phase
    "spd_type2_3p": 1450.0,              # Type 2 SPD 3-Phase

    # Isolators
    "main_switch_63a_2p": 380.0,         # 63A 2-Pole Main Switch
    "main_switch_100a_4p": 680.0,        # 100A 4-Pole Main Switch
    "main_switch_160a_4p": 950.0,        # 160A 4-Pole Main Switch
    "main_switch_250a_4p": 1450.0,       # 250A 4-Pole Main Switch
}


# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║  LABOUR RATES                                                                ║
# ╚══════════════════════════════════════════════════════════════════════════════╝

LABOUR_RATES: Dict[str, float] = {
    # Installation rates
    "per_circuit": 450.0,                # Per circuit installation
    "per_point": 85.0,                   # Per point installation
    "per_db_install": 1500.0,            # Per DB installation + wiring
    "per_db_terminate": 800.0,           # Per DB termination only
    "per_heavy_equipment": 2500.0,       # Per heavy equipment connection

    # Testing & certification
    "testing_per_db": 450.0,             # Testing per DB
    "coc_certificate": 650.0,            # COC Certificate
    "coc_inspection_basic": 1500.0,      # Basic COC inspection
    "coc_inspection_standard": 1800.0,   # Standard COC inspection
    "coc_inspection_large": 2400.0,      # Large property COC inspection

    # Site work
    "trenching_per_m": 180.0,            # Trenching 600mm deep per meter
    "trenching_rock_per_m": 450.0,       # Trenching in rock per meter
    "backfill_per_m": 80.0,              # Backfill per meter
    "cable_laying_per_m": 45.0,          # Cable laying per meter
    "pole_installation": 1800.0,         # Per pole installation

    # Daily rates
    "electrician_daily": 1800.0,         # Qualified electrician daily
    "assistant_daily": 650.0,            # Assistant daily
    "foreman_daily": 2500.0,             # Site foreman daily
}


# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║  SITE WORK & CONTAINMENT                                                     ║
# ╚══════════════════════════════════════════════════════════════════════════════╝

CONTAINMENT_PRICES: Dict[str, float] = {
    # Conduit (per meter)
    "pvc_conduit_20mm": 25.0,            # 20mm PVC Conduit
    "pvc_conduit_25mm": 35.0,            # 25mm PVC Conduit
    "pvc_conduit_32mm": 45.0,            # 32mm PVC Conduit
    "pvc_conduit_40mm": 55.0,            # 40mm PVC Conduit
    "pvc_conduit_50mm": 75.0,            # 50mm PVC Conduit

    # Junction Boxes
    "junction_box_80x80": 35.0,          # 80×80mm Junction Box
    "junction_box_100x100": 55.0,        # 100×100mm Junction Box
    "junction_box_150x150": 85.0,        # 150×150mm Junction Box

    # Cable Tray (per meter)
    "cable_tray_100mm": 120.0,           # 100mm Cable Tray
    "cable_tray_200mm": 180.0,           # 200mm Cable Tray
    "cable_tray_300mm": 250.0,           # 300mm Cable Tray
    "cable_tray_450mm": 350.0,           # 450mm Cable Tray

    # Earth
    "earth_spike_1.2m": 180.0,           # 1.2m Earth Spike
    "earth_spike_1.5m": 250.0,           # 1.5m Earth Spike
    "earth_clamp": 45.0,                 # Earth Clamp
    "earth_bar_4way": 280.0,             # 4-Way Earth Bar
}


def get_default_price(item_type: str, description: str = "") -> float:
    """
    Get default price for an item.

    Args:
        item_type: Type of item (light, socket, switch, cable, db, labour)
        description: Item description for specific lookup

    Returns:
        Default price in ZAR
    """
    price_maps = {
        "light": LIGHT_PRICES,
        "socket": SOCKET_PRICES,
        "switch": SWITCH_PRICES,
        "cable": CABLE_PRICES,
        "db": DB_PRICES,
        "labour": LABOUR_RATES,
        "containment": CONTAINMENT_PRICES,
    }

    price_map = price_maps.get(item_type, {})

    # Try exact key match
    if description in price_map:
        return price_map[description]

    # Try partial match
    description_lower = description.lower()
    for key, price_value in price_map.items():
        if key in description_lower or description_lower in key:
            return price_value

    # Default fallbacks by type
    defaults = {
        "light": 500.0,
        "socket": 150.0,
        "switch": 100.0,
        "cable": 30.0,
        "db": 2500.0,
        "labour": 500.0,
        "containment": 50.0,
    }

    return defaults.get(item_type, 100.0)
