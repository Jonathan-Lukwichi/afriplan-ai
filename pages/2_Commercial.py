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
from utils.calculations import (
    calculate_commercial_electrical,
    calculate_pfc,
    calculate_energy_efficiency,
    calculate_fire_detection,
    check_discrimination,
)
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

        st.markdown("---")

        # Power Factor Correction Calculator
        st.subheader("⚡ Power Factor Correction (Eskom Compliance)")
        st.markdown("*Avoid Eskom penalties - maintain PF ≥ 0.90*")

        pfc_col1, pfc_col2 = st.columns(2)

        with pfc_col1:
            pfc_active_kw = st.number_input(
                "Active Power (kW)",
                10.0, 5000.0,
                float(result['total_kva'] * 0.85),  # Estimate from kVA
                10.0,
                key="pfc_kw"
            )
            pfc_current = st.slider("Current Power Factor", 0.50, 0.95, 0.75, 0.01, key="pfc_current")

        with pfc_col2:
            pfc_target = st.slider("Target Power Factor", 0.90, 0.98, 0.95, 0.01, key="pfc_target")

            if st.button("Calculate PFC Bank", key="calc_pfc", type="primary"):
                pfc_result = calculate_pfc(pfc_active_kw, pfc_current, pfc_target)
                st.session_state.pfc_result = pfc_result

        if "pfc_result" in st.session_state:
            pfc = st.session_state.pfc_result
            if pfc.get("kvar_required", 0) > 0:
                pfc_cols = st.columns(4)
                with pfc_cols[0]:
                    st.metric("kVAr Required", f"{pfc['kvar_required']} kVAr")
                with pfc_cols[1]:
                    st.metric("Bank Size", f"{pfc['recommended_bank_size']} kVAr")
                with pfc_cols[2]:
                    st.metric("Est. Cost", f"R {pfc['estimated_cost']:,}")
                with pfc_cols[3]:
                    st.metric("Annual Savings", f"R {pfc['annual_savings']:,}")

                st.info(f"**Payback Period:** {pfc['payback_months']} months | **kVA Reduction:** {pfc['kva_reduction']} kVA")
            else:
                st.success("✅ Power factor already meets target - no correction needed")

        st.markdown("---")

        # Energy Efficiency Rating
        st.subheader("💡 Energy Efficiency Rating (SANS 10400-XA)")
        st.markdown("*Lighting Power Density compliance check*")

        ee_col1, ee_col2 = st.columns(2)

        with ee_col1:
            ee_lighting_kw = st.number_input(
                "Installed Lighting Load (kW)",
                0.5, 500.0,
                float(result['lighting_load']),
                0.5,
                key="ee_lighting"
            )

        with ee_col2:
            ee_area = st.number_input(
                "Floor Area (m²)",
                50, 50000,
                area_m2,
                50,
                key="ee_area"
            )

        if st.button("Check Energy Efficiency", key="calc_ee"):
            ee_result = calculate_energy_efficiency(
                ee_lighting_kw * 1000,  # Convert to watts
                ee_area,
                selected_subtype
            )
            st.session_state.ee_result = ee_result

        if "ee_result" in st.session_state:
            ee = st.session_state.ee_result
            status_colors = {"A": "🟢", "B": "🟢", "C": "🟡", "D": "🟠", "F": "🔴"}

            ee_cols = st.columns(4)
            with ee_cols[0]:
                st.metric("LPD Actual", f"{ee['lpd_actual']} W/m²")
            with ee_cols[1]:
                st.metric("LPD Limit", f"{ee['lpd_limit']} W/m²")
            with ee_cols[2]:
                st.metric("Class", f"{status_colors.get(ee['efficiency_class'], '⚪')} {ee['efficiency_class']}")
            with ee_cols[3]:
                st.metric("Compliant", "✅ Yes" if ee['compliant'] else "❌ No")

            if ee['compliant']:
                st.success(f"✅ {ee['status']}")
            else:
                st.error(f"❌ {ee['status']} - Potential annual savings: R{ee['potential_annual_savings']:,}")

        st.markdown("---")

        # Fire Detection Calculator
        if fire_alarm:
            st.subheader("🔥 Fire Detection System (SANS 10139)")
            st.markdown("*Zone calculation and equipment sizing*")

            fd_col1, fd_col2 = st.columns(2)

            with fd_col1:
                fd_detector_type = st.selectbox("Detector Type", ["smoke", "heat"], key="fd_type")

            with fd_col2:
                if st.button("Calculate Fire System", key="calc_fd", type="primary"):
                    fd_result = calculate_fire_detection(
                        area_m2,
                        selected_subtype,
                        floors,
                        fd_detector_type
                    )
                    st.session_state.fd_result = fd_result

            if "fd_result" in st.session_state:
                fd = st.session_state.fd_result

                fd_cols = st.columns(4)
                with fd_cols[0]:
                    st.metric("Zones", fd['num_zones'])
                with fd_cols[1]:
                    st.metric("Detectors", fd['total_detectors'])
                with fd_cols[2]:
                    st.metric("Call Points", fd['total_call_points'])
                with fd_cols[3]:
                    st.metric("Total Cost", f"R {fd['total_cost']:,}")

                st.info(f"**Panel Type:** {fd['panel_type']} | **Sounders:** {fd['total_sounders']}")

                with st.expander("Fire Detection BQ Items"):
                    for item in fd['bq_items']:
                        st.write(f"- {item['item']}: {item['qty']} {item['unit']} @ R{item['rate']:,} = **R{item['total']:,}**")

    else:
        st.info("👆 Configure building parameters and calculate load first.")

with tab3:
    st.markdown('<p class="section-title">Bill of Quantities & Smart Cost Optimizer</p>', unsafe_allow_html=True)

    if "commercial_result" in st.session_state:
        result = st.session_state.commercial_result
        bq_items = result["bq_items"]

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
            options = generate_quotation_options(bq_items, result, result)
            st.session_state.commercial_quote_options = options

        if "commercial_quote_options" in st.session_state and st.session_state.commercial_quote_options:
            options = st.session_state.commercial_quote_options
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
<div style="font-size: 20px; font-weight: bold; text-align: center; color: #00D4FF;">R {option['selling_price']:,.0f}</div>
<div style="font-size: 11px; text-align: center; color: #64748B;">Selling Price</div>
<div style="margin-top: 10px; font-size: 12px;">
<div>Base Cost: R {option['base_cost']:,.0f}</div>
<div>Markup: {option['markup_percent']:.0f}%</div>
<div>Profit: R {option['profit']:,.0f}</div>
<div>Margin: {option['profit_margin']:.1f}%</div>
<div>Quality: {'⭐' * int(option['quality_score'])}</div>
</div>
</div>"""
                    st.markdown(html_content, unsafe_allow_html=True)
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
