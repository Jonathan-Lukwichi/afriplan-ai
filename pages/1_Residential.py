"""
AfriPlan Electrical - Residential Page
New builds, renovations, solar, security, EV charging
"""

import streamlit as st
from datetime import datetime
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.styles import inject_custom_css
from utils.components import page_header, section_header
from utils.constants import (
    ROOM_ELECTRICAL_REQUIREMENTS,
    ROOM_PRESETS,
    PROJECT_TYPES,
    RESIDENTIAL_SOLAR_SYSTEMS,
    RESIDENTIAL_SECURITY_SYSTEMS,
    RESIDENTIAL_SMART_HOME,
    RESIDENTIAL_EV_CHARGING,
    DEDICATED_CIRCUITS,
    COMPLEXITY_FACTORS,
    PAYMENT_TERMS,
    ELECTRICAL_SAFETY,
)
from utils.calculations import (
    calculate_electrical_requirements,
    calculate_load_and_circuits,
    calculate_electrical_bq,
    calculate_admd,
    calculate_voltage_drop,
    calculate_cable_size,
    calculate_essential_load,
    generate_coc_checklist,
)
from utils.constants import ADMD_VALUES, ESSENTIAL_LOADS
from utils.optimizer import generate_quotation_options
from utils.pdf_generator import generate_electrical_pdf, generate_generic_electrical_pdf
from utils.excel_exporter import export_bq_to_excel
from utils.eskom_forms import generate_eskom_application, generate_application_summary_text

inject_custom_css()

# Header
page_header(
    title="Residential Electrical",
    subtitle="New builds, renovations, solar & backup, COC compliance, smart home, security, EV charging"
)

# Sidebar - Project Type Selection
with st.sidebar:
    st.markdown("### Project Type")

    subtypes = PROJECT_TYPES["residential"]["subtypes"]
    subtype_options = {f"{s['icon']} {s['name']}": s['code'] for s in subtypes}
    selected_subtype_label = st.selectbox(
        "Select Project",
        list(subtype_options.keys()),
    )
    selected_subtype = subtype_options[selected_subtype_label]

    # Show standards
    for s in subtypes:
        if s["code"] == selected_subtype:
            if "standards" in s:
                st.caption(f"Standards: {', '.join(s['standards'])}")
            break

    st.markdown("---")

    # Room presets for new_house and renovation
    if selected_subtype in ["new_house", "renovation", "coc_compliance"]:
        st.markdown("### Quick Presets")
        preset_choice = st.selectbox("House Type", [
            "Custom",
            "2-Bedroom House",
            "3-Bedroom House",
            "4-Bedroom House",
            "5-Bedroom Villa",
        ])

        st.markdown("---")
        st.markdown("### Project Settings")

        # Complexity factor
        complexity_options = {v["name"]: k for k, v in COMPLEXITY_FACTORS.items()}
        complexity_label = st.selectbox(
            "Project Complexity",
            list(complexity_options.keys()),
            help="Affects labour costs based on project difficulty"
        )
        st.session_state.complexity_factor = COMPLEXITY_FACTORS[complexity_options[complexity_label]]["factor"]

        # Markup/margin slider
        st.session_state.markup_percent = st.slider(
            "Profit Margin %",
            min_value=10,
            max_value=50,
            value=25,
            step=5,
            help="Adjust contractor profit margin"
        )

        # Payment terms
        payment_options = {v["name"]: k for k, v in PAYMENT_TERMS.items()}
        payment_label = st.selectbox(
            "Payment Terms",
            list(payment_options.keys()),
            help="Standard SA industry: 40/40/20"
        )
        st.session_state.payment_terms = PAYMENT_TERMS[payment_options[payment_label]]

# Initialize session state
if "residential_rooms" not in st.session_state:
    st.session_state.residential_rooms = []

# AI Pre-fill Integration (v3.0)
# Check if user came from Smart Upload with extracted data
if st.session_state.get("from_smart_upload") and st.session_state.get("extracted_data"):
    extracted = st.session_state.extracted_data

    # Show AI pre-fill banner
    ai_confidence = st.session_state.get("ai_confidence", 0)
    conf_color = "#22C55E" if ai_confidence >= 0.7 else "#F59E0B" if ai_confidence >= 0.4 else "#EF4444"
    conf_level = "HIGH" if ai_confidence >= 0.7 else "MEDIUM" if ai_confidence >= 0.4 else "LOW"

    st.markdown(f"""
    <div style="background: linear-gradient(135deg, rgba(0,212,255,0.1), rgba(139,92,246,0.1));
                border: 1px solid rgba(0,212,255,0.3); border-radius: 12px; padding: 1rem;
                margin-bottom: 1.5rem;">
        <div style="display: flex; align-items: center; justify-content: space-between;">
            <div style="display: flex; align-items: center; gap: 10px;">
                <span style="font-size: 1.5rem;">🤖</span>
                <div>
                    <div style="font-family: 'Rajdhani', sans-serif; font-weight: 600; color: #00D4FF;">
                        AI-Extracted Data Loaded
                    </div>
                    <div style="font-size: 12px; color: #94a3b8;">
                        Review and adjust the pre-populated fields below
                    </div>
                </div>
            </div>
            <span style="background: {conf_color}20; color: {conf_color}; padding: 4px 12px;
                         border-radius: 6px; font-size: 12px; font-weight: 600;">
                {conf_level} ({ai_confidence*100:.0f}%)
            </span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Pre-populate rooms from extracted data
    if "rooms" in extracted and extracted["rooms"] and not st.session_state.residential_rooms:
        prefilled_rooms = []
        for room in extracted["rooms"]:
            area = room.get("area_m2", 16) or 16
            side = area ** 0.5
            prefilled_rooms.append({
                "name": room.get("name", "Room"),
                "type": room.get("type", "Living Room"),
                "w": round(side, 1),
                "h": round(side, 1),
            })
        st.session_state.residential_rooms = prefilled_rooms

    # Pre-populate dedicated circuits from electrical details
    if "electrical_details" in extracted:
        elec = extracted["electrical_details"]
        special_req = elec.get("special_requirements", [])

        # Initialize dedicated circuits state
        if "ai_dedicated_circuits" not in st.session_state:
            st.session_state.ai_dedicated_circuits = {
                "stove": any("stove" in req.lower() for req in special_req),
                "geyser": any("geyser" in req.lower() for req in special_req),
                "pool": any("pool" in req.lower() for req in special_req),
                "aircon": any("aircon" in req.lower() or "air con" in req.lower() for req in special_req),
            }

    # Pre-set complexity if renovation detected
    if "project" in extracted:
        install_type = extracted["project"].get("installation_type", "new")
        if install_type == "renovation":
            st.session_state.complexity_factor = 1.15  # Renovation factor
        elif install_type == "rewire":
            st.session_state.complexity_factor = 1.30  # Rewire factor

    # Show validation warnings if available
    if st.session_state.get("validation_report"):
        val_report = st.session_state.validation_report
        flags = val_report.get("flags", [])
        critical_flags = [f for f in flags if f.get("severity") == "critical"]

        if critical_flags:
            with st.expander(f"SANS 10142 Validation: {len(critical_flags)} issues", expanded=True):
                for flag in critical_flags:
                    st.warning(f"**{flag.get('rule', '')}**: {flag.get('message', '')}")
                    if flag.get("auto_fix"):
                        st.caption(f"Auto-fix applied: {flag.get('auto_fix')}")

    # Clear the flag so it doesn't re-trigger
    st.session_state.from_smart_upload = False

# Main content with tabs
if selected_subtype in ["new_house", "renovation", "coc_compliance"]:
    tab1, tab2, tab3, tab4 = st.tabs(["📐 Configure", "⚡ Electrical", "📊 Quote", "📄 Export"])

    with tab1:
        st.markdown('<p class="section-title">Room Configuration</p>', unsafe_allow_html=True)

        # Quick presets
        if 'preset_choice' in dir() and preset_choice != "Custom":
            if preset_choice == "2-Bedroom House":
                default_rooms = [
                    {"name": "Living Room", "type": "Living Room", "w": 5, "h": 4},
                    {"name": "Bedroom 1", "type": "Bedroom", "w": 4, "h": 3},
                    {"name": "Bedroom 2", "type": "Bedroom", "w": 3.5, "h": 3},
                    {"name": "Kitchen", "type": "Kitchen", "w": 3, "h": 3},
                    {"name": "Bathroom", "type": "Bathroom", "w": 2.5, "h": 2},
                ]
            elif preset_choice == "3-Bedroom House":
                default_rooms = [
                    {"name": "Living Room", "type": "Living Room", "w": 5, "h": 4},
                    {"name": "Main Bedroom", "type": "Main Bedroom", "w": 4.5, "h": 4},
                    {"name": "Bedroom 2", "type": "Bedroom", "w": 4, "h": 3},
                    {"name": "Bedroom 3", "type": "Bedroom", "w": 3.5, "h": 3},
                    {"name": "Kitchen", "type": "Kitchen", "w": 4, "h": 3},
                    {"name": "Bathroom", "type": "Bathroom", "w": 3, "h": 2.5},
                    {"name": "Toilet", "type": "Toilet", "w": 1.5, "h": 1.5},
                ]
            elif preset_choice == "4-Bedroom House":
                default_rooms = [
                    {"name": "Living Room", "type": "Living Room", "w": 6, "h": 5},
                    {"name": "Dining Room", "type": "Dining Room", "w": 4, "h": 3.5},
                    {"name": "Main Bedroom", "type": "Main Bedroom", "w": 5, "h": 4},
                    {"name": "Bedroom 2", "type": "Bedroom", "w": 4, "h": 3.5},
                    {"name": "Bedroom 3", "type": "Bedroom", "w": 4, "h": 3},
                    {"name": "Bedroom 4", "type": "Bedroom", "w": 3.5, "h": 3},
                    {"name": "Kitchen", "type": "Kitchen", "w": 4, "h": 4},
                    {"name": "Bathroom 1", "type": "Bathroom", "w": 3, "h": 2.5},
                    {"name": "Bathroom 2", "type": "Bathroom", "w": 2.5, "h": 2},
                    {"name": "Garage", "type": "Garage", "w": 6, "h": 3},
                ]
            else:  # 5-Bedroom Villa
                default_rooms = [
                    {"name": "Living Room", "type": "Living Room", "w": 7, "h": 5},
                    {"name": "Dining Room", "type": "Dining Room", "w": 5, "h": 4},
                    {"name": "Main Bedroom", "type": "Main Bedroom", "w": 5, "h": 5},
                    {"name": "Bedroom 2", "type": "Bedroom", "w": 4.5, "h": 4},
                    {"name": "Bedroom 3", "type": "Bedroom", "w": 4, "h": 3.5},
                    {"name": "Bedroom 4", "type": "Bedroom", "w": 4, "h": 3.5},
                    {"name": "Bedroom 5", "type": "Bedroom", "w": 4, "h": 3},
                    {"name": "Kitchen", "type": "Kitchen", "w": 5, "h": 4},
                    {"name": "Bathroom 1", "type": "Bathroom", "w": 3.5, "h": 3},
                    {"name": "Bathroom 2", "type": "Bathroom", "w": 3, "h": 2.5},
                    {"name": "Bathroom 3", "type": "Bathroom", "w": 2.5, "h": 2},
                    {"name": "Study", "type": "Study", "w": 3.5, "h": 3},
                    {"name": "Garage", "type": "Garage", "w": 7, "h": 4},
                    {"name": "Pool Area", "type": "Pool Area", "w": 5, "h": 4},
                ]
            st.session_state.residential_rooms = default_rooms
        else:
            default_rooms = st.session_state.residential_rooms

        # Room editor
        col1, col2 = st.columns([2, 1])

        with col1:
            st.markdown("#### Rooms")
            if default_rooms:
                for i, room in enumerate(default_rooms):
                    with st.expander(f"{room['name']} ({room['type']}) - {room['w']*room['h']:.1f}m²"):
                        c1, c2, c3 = st.columns(3)
                        with c1:
                            new_name = st.text_input("Name", room['name'], key=f"name_{i}")
                        with c2:
                            new_w = st.number_input("Width (m)", 1.0, 20.0, float(room['w']), 0.5, key=f"w_{i}")
                        with c3:
                            new_h = st.number_input("Height (m)", 1.0, 20.0, float(room['h']), 0.5, key=f"h_{i}")

                        default_rooms[i]['name'] = new_name
                        default_rooms[i]['w'] = new_w
                        default_rooms[i]['h'] = new_h
            else:
                st.info("Select a preset or add rooms manually")

        with col2:
            st.markdown("#### Add Room")
            room_types = list(ROOM_PRESETS.keys())
            new_room_type = st.selectbox("Room Type", room_types)
            new_room_name = st.text_input("Room Name", new_room_type)

            if st.button("➕ Add Room", use_container_width=True):
                preset = ROOM_PRESETS[new_room_type]
                avg_area = (preset["min_area"] + preset["max_area"]) / 2
                side = avg_area ** 0.5
                st.session_state.residential_rooms.append({
                    "name": new_room_name,
                    "type": new_room_type,
                    "w": round(side, 1),
                    "h": round(side, 1),
                })
                st.rerun()

        st.markdown("---")

        # Dedicated Circuits Section
        st.markdown("### Dedicated Circuits")
        st.caption("Select big-ticket dedicated circuits (auto-populated based on rooms)")

        # Auto-detect from rooms
        has_kitchen = any(r.get("type") == "Kitchen" for r in default_rooms)
        has_laundry = any(r.get("type") == "Laundry" for r in default_rooms)
        has_pool = any("pool" in r.get("type", "").lower() or "pool" in r.get("name", "").lower() for r in default_rooms)
        has_outdoor = any(r.get("type") in ["Patio", "Outdoor", "Garage"] for r in default_rooms)

        ded_col1, ded_col2 = st.columns(2)

        with ded_col1:
            include_stove = st.checkbox("Stove Circuit (3-phase 32A)", value=has_kitchen, help="R3,800 - Dedicated circuit for electric stove")
            include_geyser = st.checkbox("Geyser Circuit + Timer", value=True, help="R2,600 - Includes programmable timer")
            include_aircon = st.checkbox("Aircon Circuits", value=False, help="R2,200 per unit")
            if include_aircon:
                num_aircons = st.number_input("Number of Aircons", 1, 5, 1, key="num_aircons")
            else:
                num_aircons = 0

        with ded_col2:
            include_pool = st.checkbox("Pool Pump Circuit", value=has_pool, help="R2,400 - IP65 rated")
            include_gate = st.checkbox("Gate Motor Circuit", value=has_outdoor, help="R1,800")
            include_dishwasher = st.checkbox("Dishwasher Circuit", value=has_kitchen, help="R1,400")
            include_washer = st.checkbox("Washing Machine Circuit", value=has_laundry, help="R1,400")

        # Safety devices
        st.markdown("### Safety Devices")
        safety_col1, safety_col2 = st.columns(2)
        with safety_col1:
            include_smoke = st.checkbox("Smoke Detectors", value=True, help="SANS 10400 requirement")
            if include_smoke:
                num_smoke = st.number_input("Number of Detectors", 1, 10, max(2, len([r for r in default_rooms if r.get("type") in ["Bedroom", "Main Bedroom", "Passage"]])), key="num_smoke")
            else:
                num_smoke = 0
        with safety_col2:
            include_surge = st.checkbox("Surge Protection (Type 1+2)", value=True, help="R3,200 - Protects against lightning")

        # Store dedicated circuits in session
        st.session_state.dedicated_circuits = {
            "stove": include_stove,
            "geyser": include_geyser,
            "aircon": include_aircon,
            "num_aircons": num_aircons,
            "pool_pump": include_pool,
            "gate_motor": include_gate,
            "dishwasher": include_dishwasher,
            "washing_machine": include_washer,
            "smoke_detectors": include_smoke,
            "num_smoke": num_smoke,
            "surge_protection": include_surge,
        }

        st.markdown("---")

        # Calculate button
        if st.button("🔌 Calculate Electrical Requirements", type="primary", use_container_width=True):
            if default_rooms:
                st.session_state.elec_req = calculate_electrical_requirements(default_rooms)
                st.session_state.circuit_info = calculate_load_and_circuits(st.session_state.elec_req)

                # Add dedicated circuits to BQ
                base_bq = calculate_electrical_bq(st.session_state.elec_req, st.session_state.circuit_info)
                dedicated_bq = []

                ded = st.session_state.dedicated_circuits
                if ded.get("stove"):
                    circuit = DEDICATED_CIRCUITS["stove_circuit_3phase"]
                    dedicated_bq.append({"item": circuit["desc"], "qty": 1, "unit": "each", "rate": circuit["total_cost"], "total": circuit["total_cost"], "category": "Dedicated Circuits"})
                if ded.get("geyser"):
                    circuit = DEDICATED_CIRCUITS["geyser_circuit"]
                    dedicated_bq.append({"item": circuit["desc"], "qty": 1, "unit": "each", "rate": circuit["total_cost"], "total": circuit["total_cost"], "category": "Dedicated Circuits"})
                if ded.get("aircon") and ded.get("num_aircons", 0) > 0:
                    circuit = DEDICATED_CIRCUITS["aircon_circuit"]
                    dedicated_bq.append({"item": circuit["desc"], "qty": ded["num_aircons"], "unit": "each", "rate": circuit["total_cost"], "total": circuit["total_cost"] * ded["num_aircons"], "category": "Dedicated Circuits"})
                if ded.get("pool_pump"):
                    circuit = DEDICATED_CIRCUITS["pool_pump_circuit"]
                    dedicated_bq.append({"item": circuit["desc"], "qty": 1, "unit": "each", "rate": circuit["total_cost"], "total": circuit["total_cost"], "category": "Dedicated Circuits"})
                if ded.get("gate_motor"):
                    circuit = DEDICATED_CIRCUITS["gate_motor_circuit"]
                    dedicated_bq.append({"item": circuit["desc"], "qty": 1, "unit": "each", "rate": circuit["total_cost"], "total": circuit["total_cost"], "category": "Dedicated Circuits"})
                if ded.get("dishwasher"):
                    circuit = DEDICATED_CIRCUITS["dishwasher_circuit"]
                    dedicated_bq.append({"item": circuit["desc"], "qty": 1, "unit": "each", "rate": circuit["total_cost"], "total": circuit["total_cost"], "category": "Dedicated Circuits"})
                if ded.get("washing_machine"):
                    circuit = DEDICATED_CIRCUITS["washing_machine_circuit"]
                    dedicated_bq.append({"item": circuit["desc"], "qty": 1, "unit": "each", "rate": circuit["total_cost"], "total": circuit["total_cost"], "category": "Dedicated Circuits"})
                if ded.get("smoke_detectors") and ded.get("num_smoke", 0) > 0:
                    smoke = ELECTRICAL_SAFETY["smoke_detector_mains"]
                    dedicated_bq.append({"item": smoke["desc"], "qty": ded["num_smoke"], "unit": "each", "rate": smoke["price"], "total": smoke["price"] * ded["num_smoke"], "category": "Safety Devices"})
                if ded.get("surge_protection"):
                    from utils.constants import ELECTRICAL_DB
                    surge = ELECTRICAL_DB["surge_arrester_type1_2"]
                    dedicated_bq.append({"item": surge["desc"], "qty": 1, "unit": "each", "rate": surge["price"], "total": surge["price"], "category": "Safety Devices"})

                st.session_state.bq_items = base_bq + dedicated_bq
                st.success("✅ Electrical requirements calculated! Go to the Electrical tab.")

    with tab2:
        st.markdown('<p class="section-title">Electrical Requirements (SANS 10142)</p>', unsafe_allow_html=True)

        if "elec_req" in st.session_state and st.session_state.elec_req:
            elec_req = st.session_state.elec_req
            circuit_info = st.session_state.circuit_info

            # Metrics
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Light Points", elec_req["total_lights"])
            with col2:
                st.metric("Plug Points", elec_req["total_plugs"])
            with col3:
                st.metric("Total Load", f"{circuit_info['total_load_kva']} kVA")
            with col4:
                st.metric("DB Board", circuit_info["db_size"].replace("_", " "))

            st.markdown("---")

            # Room breakdown
            st.subheader("Room-by-Room Breakdown")
            room_data = []
            for room in elec_req["room_details"]:
                room_data.append({
                    "Room": room["name"],
                    "Type": room["type"],
                    "Area (m²)": room["area"],
                    "Lights": room["lights"],
                    "Plugs": room["plugs"],
                    "Special": ", ".join(room["special"]) if room["special"] else "-"
                })
            st.dataframe(room_data, use_container_width=True)

            st.markdown("---")

            # Circuit design
            st.subheader("Circuit Design")
            col1, col2 = st.columns(2)
            with col1:
                st.info(f"""
                **Distribution Board:** {circuit_info['db_size'].replace('_', ' ')}
                - Main Switch: {circuit_info['main_size']}
                - Earth Leakage: 63A 30mA
                - Surge Protection: Type 2
                """)
            with col2:
                st.info(f"""
                **Circuits (max 10 points each):**
                - Lighting: {circuit_info['lighting_circuits']} circuits
                - Power: {circuit_info['power_circuits']} circuits
                - Dedicated: {circuit_info['dedicated_circuits']} circuits
                """)

            st.markdown("---")

            # ADMD Calculator Section
            st.subheader("📋 ADMD Calculator (Eskom Supply Application)")
            st.markdown("*After Diversity Maximum Demand per NRS 034*")

            admd_col1, admd_col2 = st.columns(2)

            with admd_col1:
                dwelling_options = {v["name"]: k for k, v in ADMD_VALUES.items()}
                selected_dwelling = st.selectbox(
                    "Dwelling Type",
                    list(dwelling_options.keys()),
                    index=1,  # Default to Standard House
                    key="admd_dwelling_type"
                )
                dwelling_code = dwelling_options[selected_dwelling]

                geyser_options = ["electric", "solar", "gas"]
                geyser_type = st.selectbox("Geyser Type", geyser_options, key="admd_geyser")

            with admd_col2:
                has_pool = st.checkbox("Has Pool", key="admd_pool")
                has_aircon = st.checkbox("Has Air Conditioning", key="admd_aircon")
                num_dwellings = st.number_input("Number of Dwellings (for bulk)", 1, 100, 1, key="admd_num")

            if st.button("Calculate ADMD", key="calc_admd"):
                admd_result = calculate_admd(
                    dwelling_code, num_dwellings,
                    geyser_type, has_pool, has_aircon
                )
                st.session_state.admd_result = admd_result

            if "admd_result" in st.session_state:
                admd = st.session_state.admd_result
                admd_cols = st.columns(4)
                with admd_cols[0]:
                    st.metric("Base ADMD", f"{admd['base_admd_kva']} kVA")
                with admd_cols[1]:
                    st.metric("Adjusted ADMD", f"{admd['adjusted_admd_kva']} kVA")
                with admd_cols[2]:
                    st.metric("Recommended Supply", admd['recommended_supply'])
                with admd_cols[3]:
                    st.metric("Supply Type", admd['supply_type'])

                if admd['adjustment_notes']:
                    st.info("**Adjustments:** " + ", ".join(admd['adjustment_notes']))

                st.success(f"**Eskom Application:** {admd['eskom_application_size']}")

            st.markdown("---")

            # Voltage Drop Calculator Section
            st.subheader("⚡ Voltage Drop Calculator (SANS 10142)")
            st.markdown("*Maximum allowed: 5% total (2.5% sub-mains + 2.5% final circuits)*")

            vd_col1, vd_col2, vd_col3 = st.columns(3)

            with vd_col1:
                cable_sizes = ["1.5", "2.5", "4.0", "6.0", "10", "16", "25", "35"]
                selected_cable = st.selectbox("Cable Size (mm²)", cable_sizes, index=1, key="vd_cable")
                vd_length = st.number_input("Cable Length (m)", 1.0, 200.0, 25.0, 1.0, key="vd_length")

            with vd_col2:
                vd_current = st.number_input("Load Current (A)", 1.0, 200.0, 16.0, 1.0, key="vd_current")
                vd_phase = st.selectbox("Phase", ["single", "three"], key="vd_phase")

            with vd_col3:
                if st.button("Calculate Voltage Drop", key="calc_vd", type="primary"):
                    vd_result = calculate_voltage_drop(
                        selected_cable, vd_length, vd_current,
                        voltage=230 if vd_phase == "single" else 400,
                        phase=vd_phase
                    )
                    st.session_state.vd_result = vd_result

            if "vd_result" in st.session_state:
                vd = st.session_state.vd_result
                if "error" not in vd:
                    status_colors = {"green": "🟢", "amber": "🟡", "red": "🔴"}
                    status_icon = status_colors.get(vd['status_color'], "⚪")

                    vd_cols = st.columns(4)
                    with vd_cols[0]:
                        st.metric("Voltage Drop", f"{vd['voltage_drop_v']} V")
                    with vd_cols[1]:
                        st.metric("Drop %", f"{vd['voltage_drop_percent']}%")
                    with vd_cols[2]:
                        st.metric("Voltage at Load", f"{vd['voltage_at_load']} V")
                    with vd_cols[3]:
                        st.metric("Status", f"{status_icon} {vd['status']}")

                    if vd['compliant']:
                        st.success(f"✅ Compliant - Within {vd['max_allowed_percent']}% limit")
                    else:
                        st.error(f"❌ Non-compliant - Exceeds {vd['max_allowed_percent']}% limit. Use larger cable or shorter run.")

            st.markdown("---")

            # Essential Load Calculator for Backup Power
            st.subheader("🔋 Essential Load Calculator (Load Shedding Backup)")
            st.markdown("*Size your inverter and battery for load shedding*")

            with st.expander("Select Essential Loads", expanded=True):
                essential_loads_col1, essential_loads_col2 = st.columns(2)

                # Define load groups
                basic_loads = ["lighting_basic", "fridge", "tv", "wifi_router", "phone_charger", "alarm"]
                comfort_loads = ["lighting_full", "aircon_small", "microwave", "computer", "gate_motor"]

                selected_loads = []

                with essential_loads_col1:
                    st.markdown("**Basic Essentials:**")
                    for load_key in basic_loads:
                        load_data = ESSENTIAL_LOADS.get(load_key, {})
                        if st.checkbox(
                            f"{load_data.get('description', load_key)} ({load_data.get('watts', 0)}W)",
                            key=f"ess_{load_key}"
                        ):
                            selected_loads.append(load_key)

                with essential_loads_col2:
                    st.markdown("**Comfort Loads:**")
                    for load_key in comfort_loads:
                        load_data = ESSENTIAL_LOADS.get(load_key, {})
                        if st.checkbox(
                            f"{load_data.get('description', load_key)} ({load_data.get('watts', 0)}W)",
                            key=f"ess_{load_key}"
                        ):
                            selected_loads.append(load_key)

            runtime_hours = st.slider("Desired Runtime (hours)", 2.0, 10.0, 4.0, 0.5, key="ess_runtime")

            if st.button("Calculate Backup System", key="calc_essential"):
                if selected_loads:
                    essential_result = calculate_essential_load(selected_loads, runtime_hours)
                    st.session_state.essential_result = essential_result
                else:
                    st.warning("Please select at least one load")

            if "essential_result" in st.session_state:
                ess = st.session_state.essential_result
                ess_cols = st.columns(4)
                with ess_cols[0]:
                    st.metric("Total Load", f"{ess['total_load_w']} W")
                with ess_cols[1]:
                    st.metric("Inverter Size", f"{ess['recommended_inverter_va']} VA")
                with ess_cols[2]:
                    st.metric("Battery", f"{ess['battery_capacity_kwh']} kWh")
                with ess_cols[3]:
                    st.metric("Est. Cost", f"R {ess['total_system_cost']:,}")

                st.info(f"**Covers:** {ess['load_shedding_stages_covered']} load shedding")

        else:
            st.info("👆 Configure rooms in the Configure tab first, then calculate electrical requirements.")

    with tab3:
        st.markdown('<p class="section-title">Bill of Quantities & Smart Cost Optimizer</p>', unsafe_allow_html=True)

        if "bq_items" in st.session_state and st.session_state.bq_items:
            bq_items = st.session_state.bq_items
            elec_req = st.session_state.elec_req
            circuit_info = st.session_state.circuit_info

            # Get pricing adjustments from sidebar
            complexity_factor = st.session_state.get("complexity_factor", 1.0)
            markup_percent = st.session_state.get("markup_percent", 25) / 100
            payment_terms = st.session_state.get("payment_terms", PAYMENT_TERMS["standard"])

            # BQ Summary with complexity and markup
            base_subtotal = sum(item["total"] for item in bq_items)
            adjusted_subtotal = base_subtotal * complexity_factor
            markup_amount = adjusted_subtotal * markup_percent
            subtotal_with_markup = adjusted_subtotal + markup_amount
            vat = subtotal_with_markup * 0.15
            total = subtotal_with_markup + vat

            # Show pricing breakdown
            st.markdown("### Pricing Summary")
            price_col1, price_col2 = st.columns(2)

            with price_col1:
                st.markdown(f"""
                | Item | Amount |
                |------|--------|
                | Base Material & Labour | R {base_subtotal:,.0f} |
                | Complexity Factor ({complexity_factor:.0%}) | R {base_subtotal * (complexity_factor - 1):,.0f} |
                | **Adjusted Subtotal** | **R {adjusted_subtotal:,.0f}** |
                | Profit Margin ({markup_percent:.0%}) | R {markup_amount:,.0f} |
                """)

            with price_col2:
                st.markdown(f"""
                | Item | Amount |
                |------|--------|
                | Subtotal (excl VAT) | R {subtotal_with_markup:,.0f} |
                | VAT (15%) | R {vat:,.0f} |
                | **TOTAL (incl VAT)** | **R {total:,.0f}** |
                """)

            # Key metrics
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Base Cost", f"R {base_subtotal:,.0f}")
            with col2:
                st.metric("Your Profit", f"R {markup_amount:,.0f}", delta=f"{markup_percent:.0%}")
            with col3:
                st.metric("TOTAL", f"R {total:,.0f}")
            with col4:
                deposit = total * payment_terms["deposit"]
                st.metric("Deposit Required", f"R {deposit:,.0f}", delta=f"{payment_terms['deposit']:.0%}")

            # Payment terms info
            st.info(f"**Payment Terms:** {payment_terms['description']}")

            st.markdown("---")

            # BQ Table by category
            st.subheader("Bill of Quantities")
            categories = {}
            for item in bq_items:
                cat = item["category"]
                if cat not in categories:
                    categories[cat] = []
                categories[cat].append(item)

            for cat_name, items in categories.items():
                cat_total = sum(i['total'] for i in items)
                with st.expander(f"**{cat_name}** - R {cat_total:,.0f}"):
                    for item in items:
                        st.write(f"- {item['item']}: {item['qty']} {item['unit']} @ R{item['rate']:,} = **R{item['total']:,}**")

            st.markdown("---")

            # Smart Cost Optimizer
            st.subheader("🎯 Smart Cost Optimizer")
            st.markdown("Generate 4 quotation options with different strategies:")

            if st.button("Generate Quotation Options", type="primary"):
                options = generate_quotation_options(bq_items, elec_req, circuit_info)
                st.session_state.quote_options = options

            if "quote_options" in st.session_state and st.session_state.quote_options:
                options = st.session_state.quote_options
                option_icons = ["💰", "⭐", "💎", "🏆"]

                cols = st.columns(4)
                for idx, (col, option) in enumerate(zip(cols, options)):
                    with col:
                        border_color = "#22C55E" if option["recommended"] else option["color"]
                        bg_color = "rgba(34, 197, 94, 0.1)" if option["recommended"] else "rgba(30, 41, 59, 0.5)"
                        rec_badge = '<span style="background: #22C55E; color: white; padding: 2px 8px; border-radius: 4px; font-size: 10px;">RECOMMENDED</span>' if option["recommended"] else ""

                        html_content = f"""<div style="border: 2px solid {border_color}; border-radius: 10px; padding: 15px; background: {bg_color};">
<div style="text-align: center; font-size: 24px;">{option_icons[idx]}</div>
<div style="text-align: center; font-weight: bold; color: {option['color']}; margin: 5px 0;">{option['name']}</div>
<div style="text-align: center; font-size: 11px; color: #94A3B8;">{option['strategy']}</div>
{rec_badge}
<hr style="border-color: #334155; margin: 10px 0;">
<div style="font-size: 20px; font-weight: bold; text-align: center; color: #F59E0B;">R {option['selling_price']:,.0f}</div>
<div style="font-size: 11px; text-align: center; color: #64748B;">Selling Price</div>
<div style="margin-top: 10px; font-size: 12px;">
<div>Base Cost: R {option['base_cost']:,.0f}</div>
<div>Markup: {option['markup_percent']:.0f}%</div>
<div>Profit: R {option['profit']:,.0f}</div>
<div>Margin: {option['profit_margin']:.1f}%</div>
<div>Quality: {'*' * int(option['quality_score'])}</div>
</div>
</div>"""
                        st.markdown(html_content, unsafe_allow_html=True)
        else:
            st.info("👆 Configure rooms and calculate electrical requirements first.")

    with tab4:
        st.markdown('<p class="section-title">Export Quotation</p>', unsafe_allow_html=True)

        if "bq_items" in st.session_state and st.session_state.bq_items:
            st.markdown("### Download Options")

            col1, col2 = st.columns(2)

            with col1:
                if st.button("📄 Generate PDF Quote", type="primary", use_container_width=True):
                    pdf_bytes = generate_electrical_pdf(
                        st.session_state.elec_req,
                        st.session_state.circuit_info,
                        st.session_state.bq_items
                    )
                    st.download_button(
                        label="⬇️ Download PDF",
                        data=pdf_bytes,
                        file_name=f"residential_quote_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf",
                        mime="application/pdf",
                        use_container_width=True
                    )

            with col2:
                if st.button("📊 Generate Excel BQ", type="secondary", use_container_width=True):
                    try:
                        project_info = {
                            "Project Type": "Residential Electrical",
                            "Total Light Points": st.session_state.elec_req["total_lights"],
                            "Total Plug Points": st.session_state.elec_req["total_plugs"],
                            "Total Load (kVA)": st.session_state.circuit_info["total_load_kva"],
                            "DB Board Size": st.session_state.circuit_info["db_size"].replace("_", " "),
                        }
                        excel_bytes = export_bq_to_excel(
                            st.session_state.bq_items,
                            project_info,
                            st.session_state.circuit_info
                        )
                        st.download_button(
                            label="⬇️ Download Excel",
                            data=excel_bytes,
                            file_name=f"residential_bq_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            use_container_width=True
                        )
                    except ImportError:
                        st.error("Excel export requires openpyxl. Install with: pip install openpyxl")

            st.markdown("---")

            # COC Pre-Check Checklist
            st.markdown("### 📋 COC Pre-Inspection Checklist")
            st.markdown("*Verify your installation is ready for COC inspection*")

            if st.button("Generate COC Checklist", key="gen_coc_checklist"):
                # Build installation data from session state
                installation_data = {
                    "earth_installed": True,
                    "total_circuits": st.session_state.circuit_info.get("total_circuits", 0),
                    "earth_loop_compliant": True,
                }
                if "vd_result" in st.session_state:
                    installation_data["max_voltage_drop_percent"] = st.session_state.vd_result.get("voltage_drop_percent", 0)

                coc_result = generate_coc_checklist(installation_data)
                st.session_state.coc_checklist = coc_result

            if "coc_checklist" in st.session_state:
                coc = st.session_state.coc_checklist

                # Summary metrics
                coc_cols = st.columns(4)
                with coc_cols[0]:
                    st.metric("Passed", coc['pass_count'], delta_color="normal")
                with coc_cols[1]:
                    st.metric("Failed", coc['fail_count'], delta_color="inverse" if coc['fail_count'] > 0 else "normal")
                with coc_cols[2]:
                    st.metric("Warnings", coc['warning_count'])
                with coc_cols[3]:
                    ready_color = "🟢" if coc['ready_for_coc'] else "🔴"
                    st.metric("Status", f"{ready_color} {'Ready' if coc['ready_for_coc'] else 'Not Ready'}")

                # Detailed checklist
                for item in coc['checklist']:
                    status_icons = {"pass": "✅", "fail": "❌", "warning": "⚠️"}
                    icon = status_icons.get(item['status'], "⚪")
                    with st.expander(f"{icon} {item['item']}"):
                        st.write(f"**Requirement:** {item['requirement']}")
                        st.write(f"**Notes:** {item['notes']}")

                # Overall recommendation
                if coc['ready_for_coc']:
                    st.success(f"✅ {coc['overall_status']}")
                else:
                    st.error(f"❌ {coc['overall_status']}")

            st.markdown("---")

            # Eskom Application Helper
            st.markdown("### ⚡ Eskom Supply Application Helper")
            st.markdown("*Generate pre-populated Eskom application data*")

            eskom_col1, eskom_col2 = st.columns(2)

            with eskom_col1:
                eskom_app_type = st.selectbox(
                    "Application Type",
                    ["new_connection", "upgrade", "temporary"],
                    format_func=lambda x: x.replace("_", " ").title(),
                    key="eskom_app_type"
                )

            with eskom_col2:
                eskom_province = st.selectbox(
                    "Province",
                    ["Gauteng", "KwaZulu-Natal", "Western Cape", "Eastern Cape",
                     "Mpumalanga", "Limpopo", "North West", "Free State", "Northern Cape"],
                    key="eskom_province"
                )

            if st.button("Generate Eskom Application", key="gen_eskom_app"):
                # Use ADMD data if available, otherwise use circuit info
                if "admd_result" in st.session_state:
                    load_data = st.session_state.admd_result
                else:
                    load_data = {
                        "total_admd_kva": st.session_state.circuit_info["total_load_kva"],
                        "recommended_supply": st.session_state.circuit_info["main_size"],
                        "supply_type": "Single Phase",
                    }

                location = {"province": eskom_province}
                eskom_result = generate_eskom_application(eskom_app_type, load_data, location)
                st.session_state.eskom_result = eskom_result

            if "eskom_result" in st.session_state:
                eskom = st.session_state.eskom_result

                # Display key info
                eskom_cols = st.columns(3)
                with eskom_cols[0]:
                    st.metric("Supply Size", eskom['load_details']['supply_size'])
                with eskom_cols[1]:
                    st.metric("Supply Type", eskom['load_details']['supply_type'])
                with eskom_cols[2]:
                    st.metric("Est. Cost", f"R {eskom['estimated_costs']['estimated_total']:,.0f}")

                with st.expander("Required Documents"):
                    for doc in eskom['required_documents']:
                        st.write(f"- {doc}")

                with st.expander("Cost Breakdown"):
                    for key, value in eskom['estimated_costs'].items():
                        if isinstance(value, (int, float)) and key != "extension_cost_per_meter":
                            st.write(f"- {key.replace('_', ' ').title()}: R {value:,.0f}")

                with st.expander("Timeline"):
                    for key, value in eskom['estimated_timeline'].items():
                        st.write(f"- {key.replace('_', ' ').title()}: {value}")

                # Download summary
                summary_text = generate_application_summary_text(eskom)
                st.download_button(
                    label="⬇️ Download Eskom Application Summary",
                    data=summary_text,
                    file_name=f"eskom_application_{datetime.now().strftime('%Y%m%d_%H%M')}.txt",
                    mime="text/plain",
                )

                st.info(f"**Contact:** {eskom['eskom_contact']['region']} - {eskom['eskom_contact']['phone']}")

        else:
            st.info("👆 Configure rooms and calculate electrical requirements first.")

# Solar & Backup Power
elif selected_subtype == "solar_backup":
    tab1, tab2, tab3 = st.tabs(["⚡ System Selection", "📊 Quote", "📄 Export"])

    with tab1:
        st.markdown('<p class="section-title">Solar & Backup Power Systems</p>', unsafe_allow_html=True)

        solar_options = list(RESIDENTIAL_SOLAR_SYSTEMS.keys())
        solar_labels = {k: v["name"] for k, v in RESIDENTIAL_SOLAR_SYSTEMS.items()}

        selected_system = st.selectbox(
            "Select System Size",
            solar_options,
            format_func=lambda x: solar_labels[x]
        )

        system = RESIDENTIAL_SOLAR_SYSTEMS[selected_system]

        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Inverter", f"{system['inverter_kva']} kVA")
        with col2:
            st.metric("Battery", f"{system['battery_kwh']} kWh")
        with col3:
            st.metric("Solar Panels", f"{system['panels_kw']} kWp")
        with col4:
            st.metric("Autonomy", f"{system['autonomy_hours']} hours")

        st.markdown("---")

        st.subheader("Circuits Covered")
        st.write(", ".join(system["circuits_covered"]))

        st.markdown("---")

        st.subheader("Components")
        for key, comp in system["components"].items():
            st.write(f"- {comp['item']}: {comp['qty']} x R{comp['price']:,} = **R{comp['qty'] * comp['price']:,}**")

        st.markdown("---")

        st.subheader("Labour")
        for key, price in system["labour"].items():
            st.write(f"- {key.replace('_', ' ').title()}: **R{price:,}**")

        # Calculate total
        component_total = sum(c["qty"] * c["price"] for c in system["components"].values())
        labour_total = sum(system["labour"].values())
        total = component_total + labour_total

        st.markdown("---")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Components", f"R {component_total:,.0f}")
        with col2:
            st.metric("Labour", f"R {labour_total:,.0f}")
        with col3:
            st.metric("TOTAL", f"R {total:,.0f}")

# Security Systems
elif selected_subtype == "security":
    st.markdown('<p class="section-title">Security Systems</p>', unsafe_allow_html=True)

    security_options = list(RESIDENTIAL_SECURITY_SYSTEMS.keys())
    security_labels = {k: v["name"] for k, v in RESIDENTIAL_SECURITY_SYSTEMS.items()}

    selected_security = st.selectbox(
        "Select Security Package",
        security_options,
        format_func=lambda x: security_labels[x]
    )

    system = RESIDENTIAL_SECURITY_SYSTEMS[selected_security]

    st.subheader("Components")
    for key, comp in system["components"].items():
        st.write(f"- {comp['item']}: {comp['qty']} x R{comp['price']:,} = **R{comp['qty'] * comp['price']:,}**")

    st.markdown("---")

    st.subheader("Labour")
    for key, price in system["labour"].items():
        st.write(f"- {key.replace('_', ' ').title()}: **R{price:,}**")

    # Calculate total
    component_total = sum(c["qty"] * c["price"] for c in system["components"].values())
    labour_total = sum(system["labour"].values())
    total = component_total + labour_total

    st.markdown("---")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Components", f"R {component_total:,.0f}")
    with col2:
        st.metric("Labour", f"R {labour_total:,.0f}")
    with col3:
        st.metric("TOTAL", f"R {total:,.0f}")

# EV Charging
elif selected_subtype == "ev_charging":
    st.markdown('<p class="section-title">EV Charging Installation</p>', unsafe_allow_html=True)

    ev_options = list(RESIDENTIAL_EV_CHARGING.keys())
    ev_labels = {k: v["name"] for k, v in RESIDENTIAL_EV_CHARGING.items()}

    selected_ev = st.selectbox(
        "Select Charger Type",
        ev_options,
        format_func=lambda x: ev_labels[x]
    )

    system = RESIDENTIAL_EV_CHARGING[selected_ev]

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Power", f"{system['power_kw']} kW")
    with col2:
        st.metric("Voltage", f"{system['voltage']} V")
    with col3:
        st.metric("Current", f"{system['current_a']} A")
    with col4:
        st.metric("Charge Time", system['charge_time_typical'])

    st.markdown("---")

    st.subheader("Components")
    for key, comp in system["components"].items():
        st.write(f"- {comp['item']}: {comp['qty']} x R{comp['price']:,} = **R{comp['qty'] * comp['price']:,}**")

    st.markdown("---")

    st.subheader("Labour")
    for key, price in system["labour"].items():
        st.write(f"- {key.replace('_', ' ').title()}: **R{price:,}**")

    # Calculate total
    component_total = sum(c["qty"] * c["price"] for c in system["components"].values())
    labour_total = sum(system["labour"].values())
    total = component_total + labour_total

    st.markdown("---")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Components", f"R {component_total:,.0f}")
    with col2:
        st.metric("Labour", f"R {labour_total:,.0f}")
    with col3:
        st.metric("TOTAL", f"R {total:,.0f}")

# Smart Home
elif selected_subtype == "smart_home":
    tab1, tab2, tab3 = st.tabs(["🏠 System Selection", "📊 Quote", "📄 Export"])

    with tab1:
        st.markdown('<p class="section-title">Smart Home Automation</p>', unsafe_allow_html=True)

        smart_options = list(RESIDENTIAL_SMART_HOME.keys())
        smart_labels = {k: v["name"] for k, v in RESIDENTIAL_SMART_HOME.items()}

        selected_smart = st.selectbox(
            "Select Smart Home Package",
            smart_options,
            format_func=lambda x: smart_labels[x]
        )

        system = RESIDENTIAL_SMART_HOME[selected_smart]

        st.markdown(f"""
        <div style="background: linear-gradient(135deg, rgba(17,24,39,0.8), rgba(15,23,42,0.6));
                    border: 1px solid rgba(0,212,255,0.1); border-radius: 16px; padding: 1.5rem;">
            <h4 style="color: #00D4FF; margin-bottom: 0.5rem;">{system['name']}</h4>
            <p style="color: #94a3b8;">{system['description']}</p>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("---")

        st.subheader("Components Included")
        component_total = 0
        for key, comp in system["components"].items():
            item_total = comp['qty'] * comp['price']
            component_total += item_total
            st.write(f"- {comp['item']}: {comp['qty']} x R{comp['price']:,} = **R{item_total:,}**")

        st.markdown("---")

        st.subheader("Installation & Setup")
        labour_total = 0
        for key, price in system["labour"].items():
            labour_total += price
            st.write(f"- {key.replace('_', ' ').title()}: **R{price:,}**")

        total = component_total + labour_total

        st.markdown("---")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Components", f"R {component_total:,.0f}")
        with col2:
            st.metric("Installation", f"R {labour_total:,.0f}")
        with col3:
            st.metric("TOTAL", f"R {total:,.0f}")

        # Store for quote tab
        st.session_state.smart_home_system = system
        st.session_state.smart_home_total = total

    with tab2:
        st.markdown('<p class="section-title">Smart Home Quotation</p>', unsafe_allow_html=True)

        if "smart_home_system" in st.session_state:
            system = st.session_state.smart_home_system

            # Generate BQ items
            bq_items = []
            for key, comp in system["components"].items():
                bq_items.append({
                    "category": "Smart Home Equipment",
                    "item": comp['item'],
                    "qty": comp['qty'],
                    "unit": "each",
                    "rate": comp['price'],
                    "total": comp['qty'] * comp['price']
                })

            for key, price in system["labour"].items():
                bq_items.append({
                    "category": "Labour",
                    "item": key.replace('_', ' ').title(),
                    "qty": 1,
                    "unit": "lump sum",
                    "rate": price,
                    "total": price
                })

            subtotal = sum(item["total"] for item in bq_items)
            vat = subtotal * 0.15
            total = subtotal + vat

            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Subtotal (excl VAT)", f"R {subtotal:,.0f}")
            with col2:
                st.metric("VAT (15%)", f"R {vat:,.0f}")
            with col3:
                st.metric("TOTAL (incl VAT)", f"R {total:,.0f}")

            st.markdown("---")

            st.subheader("Bill of Quantities")
            categories = {}
            for item in bq_items:
                cat = item["category"]
                if cat not in categories:
                    categories[cat] = []
                categories[cat].append(item)

            for cat_name, items in categories.items():
                cat_total = sum(i['total'] for i in items)
                with st.expander(f"**{cat_name}** - R {cat_total:,.0f}"):
                    for item in items:
                        st.write(f"- {item['item']}: {item['qty']} {item['unit']} @ R{item['rate']:,} = **R{item['total']:,}**")

            st.session_state.smart_home_bq = bq_items
        else:
            st.info("👆 Select a smart home package first.")

    with tab3:
        st.markdown('<p class="section-title">Export Quotation</p>', unsafe_allow_html=True)

        if "smart_home_bq" in st.session_state:
            if st.button("📄 Generate PDF Quote", type="primary", use_container_width=True):
                summary = {
                    "Package": st.session_state.smart_home_system['name'],
                    "Description": st.session_state.smart_home_system['description'],
                }
                pdf_bytes = generate_generic_electrical_pdf(
                    st.session_state.smart_home_bq,
                    summary,
                    "residential",
                    "smart_home"
                )
                st.download_button(
                    label="⬇️ Download PDF",
                    data=pdf_bytes,
                    file_name=f"smart_home_quote_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf",
                    mime="application/pdf",
                    use_container_width=True
                )
        else:
            st.info("👆 Configure smart home package first.")

else:
    st.info(f"Configuration for {selected_subtype.replace('_', ' ').title()} coming soon!")
