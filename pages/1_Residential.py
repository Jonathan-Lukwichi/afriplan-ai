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
    RESIDENTIAL_EV_CHARGING,
)
from utils.calculations import (
    calculate_electrical_requirements,
    calculate_load_and_circuits,
    calculate_electrical_bq,
)
from utils.optimizer import generate_quotation_options
from utils.pdf_generator import generate_electrical_pdf

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

# Initialize session state
if "residential_rooms" not in st.session_state:
    st.session_state.residential_rooms = []

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

        # Calculate button
        if st.button("🔌 Calculate Electrical Requirements", type="primary", use_container_width=True):
            if default_rooms:
                st.session_state.elec_req = calculate_electrical_requirements(default_rooms)
                st.session_state.circuit_info = calculate_load_and_circuits(st.session_state.elec_req)
                st.session_state.bq_items = calculate_electrical_bq(st.session_state.elec_req, st.session_state.circuit_info)
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
        else:
            st.info("👆 Configure rooms in the Configure tab first, then calculate electrical requirements.")

    with tab3:
        st.markdown('<p class="section-title">Bill of Quantities & Smart Cost Optimizer</p>', unsafe_allow_html=True)

        if "bq_items" in st.session_state and st.session_state.bq_items:
            bq_items = st.session_state.bq_items
            elec_req = st.session_state.elec_req
            circuit_info = st.session_state.circuit_info

            # BQ Summary
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
                st.info("More export options coming soon: Excel, DXF, JSON")
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

else:
    st.info(f"Configuration for {selected_subtype.replace('_', ' ').title()} coming soon!")
