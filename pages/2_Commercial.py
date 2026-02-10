"""
AfriPlan Electrical - Commercial Page
Offices, retail, hospitality, healthcare, education
"""

import streamlit as st
from datetime import datetime
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.styles import inject_custom_css
from utils.components import page_header
from utils.constants import (
    PROJECT_TYPES,
    COMMERCIAL_LOAD_FACTORS,
    COMMERCIAL_DISTRIBUTION,
    COMMERCIAL_EMERGENCY_POWER,
)
from utils.calculations import calculate_commercial_electrical
from utils.optimizer import generate_quotation_options
from utils.pdf_generator import generate_generic_electrical_pdf

inject_custom_css()

# Header
page_header(
    title="Commercial Electrical",
    subtitle="Offices, retail, hospitality, healthcare, education"
)

# Sidebar
with st.sidebar:
    st.markdown("### Project Type")

    subtypes = PROJECT_TYPES["commercial"]["subtypes"]
    subtype_options = {f"{s['icon']} {s['name']}": s['code'] for s in subtypes}
    selected_subtype_label = st.selectbox("Select Project", list(subtype_options.keys()))
    selected_subtype = subtype_options[selected_subtype_label]

    for s in subtypes:
        if s["code"] == selected_subtype:
            if "standards" in s:
                st.caption(f"Standards: {', '.join(s['standards'])}")
            break

    st.markdown("---")

    st.markdown("### Building Parameters")
    area_m2 = st.number_input("Floor Area (m²)", 50, 50000, 500, 50)
    floors = st.number_input("Number of Floors", 1, 50, 1)
    emergency_power = st.checkbox("Emergency Power Required")
    fire_alarm = st.checkbox("Fire Alarm System", value=True)

# Main content with tabs
tab1, tab2, tab3, tab4 = st.tabs(["📐 Configure", "⚡ Load Study", "📊 Quote", "📄 Export"])

with tab1:
    st.markdown('<p class="section-title">Building Configuration</p>', unsafe_allow_html=True)

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### Building Details")
        st.info(f"""
        **Building Type:** {selected_subtype.replace('_', ' ').title()}
        **Floor Area:** {area_m2:,} m²
        **Floors:** {floors}
        **Total Area:** {area_m2 * floors:,} m²
        """)

    with col2:
        st.markdown("### Load Factors (W/m²)")
        if selected_subtype in COMMERCIAL_LOAD_FACTORS:
            lf = COMMERCIAL_LOAD_FACTORS[selected_subtype]
            st.write(f"- General Lighting: {lf.get('general_lighting', 12)} W/m²")
            st.write(f"- Small Power: {lf.get('small_power', 25)} W/m²")
            st.write(f"- HVAC: {lf.get('hvac', 80)} W/m²")
            st.write(f"- Diversity Factor: {lf.get('diversity_factor', 0.7)}")
            st.write(f"- Power Factor: {lf.get('power_factor', 0.9)}")

    if st.button("🔌 Calculate Load & Distribution", type="primary", use_container_width=True):
        result = calculate_commercial_electrical(
            area_m2, selected_subtype, floors, emergency_power, fire_alarm
        )
        st.session_state.commercial_result = result
        st.success("✅ Load calculation complete! Go to the Load Study tab.")

with tab2:
    st.markdown('<p class="section-title">Load Study & Distribution Design</p>', unsafe_allow_html=True)

    if "commercial_result" in st.session_state:
        result = st.session_state.commercial_result

        # Metrics
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total Load", f"{result['total_kva']} kVA")
        with col2:
            st.metric("Lighting", f"{result['lighting_load']} kW")
        with col3:
            st.metric("Small Power", f"{result['power_load']} kW")
        with col4:
            st.metric("HVAC", f"{result['hvac_load']} kW")

        st.markdown("---")

        # Circuit breakdown
        st.subheader("Circuit Requirements")
        col1, col2 = st.columns(2)
        with col1:
            st.info(f"""
            **Building Size:** {result['building_size'].title()}

            **Circuits:**
            - Lighting: {result['lighting_circuits']} circuits
            - Power: {result['power_circuits']} circuits
            - HVAC: {result['hvac_circuits']} circuits
            """)
        with col2:
            dist = COMMERCIAL_DISTRIBUTION.get(result['building_size'], COMMERCIAL_DISTRIBUTION['medium'])
            st.info(f"""
            **Distribution:**
            - Main Switch: {dist['main_switch']['size']}
            - Earth System: {dist['earth_system']}
            - Metering: {dist['metering']}
            """)

        st.markdown("---")

        # Emergency Power Options
        if emergency_power:
            st.subheader("Emergency Power Options")
            for key, ep in COMMERCIAL_EMERGENCY_POWER.items():
                with st.expander(f"{ep['name']} ({ep['capacity_kva']} kVA)"):
                    for comp_key, comp in ep["components"].items():
                        st.write(f"- {comp['item']}: R{comp['price']:,}")
                    st.write(f"- Labour: R{ep.get('labour', 0):,}")
                    total = sum(c['price'] for c in ep["components"].values()) + ep.get('labour', 0) + ep.get('civil', 0)
                    st.write(f"**Total: R{total:,}**")
    else:
        st.info("👆 Configure building parameters and calculate load first.")

with tab3:
    st.markdown('<p class="section-title">Bill of Quantities</p>', unsafe_allow_html=True)

    if "commercial_result" in st.session_state:
        result = st.session_state.commercial_result
        bq_items = result["bq_items"]

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
        for item in bq_items:
            st.write(f"- {item['item']}: {item['qty']} {item['unit']} @ R{item['rate']:,} = **R{item['total']:,}**")
    else:
        st.info("👆 Configure building parameters and calculate load first.")

with tab4:
    st.markdown('<p class="section-title">Export Quotation</p>', unsafe_allow_html=True)

    if "commercial_result" in st.session_state:
        result = st.session_state.commercial_result

        if st.button("📄 Generate PDF Quote", type="primary", use_container_width=True):
            summary = {
                "Building Type": selected_subtype.replace('_', ' ').title(),
                "Floor Area": f"{area_m2:,} m²",
                "Total Load": f"{result['total_kva']} kVA",
            }
            pdf_bytes = generate_generic_electrical_pdf(
                result["bq_items"],
                summary,
                "commercial",
                selected_subtype
            )
            st.download_button(
                label="⬇️ Download PDF",
                data=pdf_bytes,
                file_name=f"commercial_quote_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf",
                mime="application/pdf",
                use_container_width=True
            )
    else:
        st.info("👆 Configure building parameters and calculate load first.")
