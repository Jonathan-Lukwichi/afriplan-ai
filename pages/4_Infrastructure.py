"""
AfriPlan Electrical - Infrastructure Page
Township electrification, rural, street lighting, utility solar
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
    TOWNSHIP_ELECTRIFICATION,
    RURAL_ELECTRIFICATION,
    STREET_LIGHTING,
    UTILITY_SOLAR,
)
from utils.calculations import calculate_township_electrification, calculate_street_lighting
from utils.pdf_generator import generate_generic_electrical_pdf

inject_custom_css()

# Header
page_header(
    title="Infrastructure Electrical",
    subtitle="Township electrification, rural, street lighting, mini-grids, utility solar"
)

# Sidebar
with st.sidebar:
    st.markdown("### Project Type")

    subtypes = PROJECT_TYPES["infrastructure"]["subtypes"]
    subtype_options = {f"{s['icon']} {s['name']}": s['code'] for s in subtypes}
    selected_subtype_label = st.selectbox("Select Project", list(subtype_options.keys()))
    selected_subtype = subtype_options[selected_subtype_label]

    for s in subtypes:
        if s["code"] == selected_subtype:
            if "standards" in s:
                st.caption(f"Standards: {', '.join(s['standards'])}")
            break

# Township Electrification
if selected_subtype == "township":
    tab1, tab2, tab3 = st.tabs(["📐 Configure", "📊 Cost Breakdown", "📄 Export"])

    with tab1:
        st.markdown('<p class="section-title">Township Electrification (NRS 034)</p>', unsafe_allow_html=True)

        col1, col2 = st.columns(2)

        with col1:
            num_stands = st.number_input("Number of Stands", 10, 10000, 100, 10)

        with col2:
            service_options = {
                "20A Prepaid (1.5kVA ADMD)": "20A_service",
                "40A Prepaid (3.5kVA ADMD)": "40A_service",
                "60A Conventional (5.0kVA ADMD)": "60A_service",
            }
            service_label = st.selectbox("Service Type", list(service_options.keys()))
            service_type = service_options[service_label]

        if st.button("📊 Calculate Project Cost", type="primary", use_container_width=True):
            result = calculate_township_electrification(num_stands, service_type)
            st.session_state.township_result = result
            st.success("✅ Project cost calculated!")

    with tab2:
        st.markdown('<p class="section-title">Cost Breakdown</p>', unsafe_allow_html=True)

        if "township_result" in st.session_state:
            result = st.session_state.township_result

            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Stands", result["num_stands"])
            with col2:
                st.metric("Service", result["connection_size"])
            with col3:
                st.metric("Cost per Stand", f"R {result['cost_per_stand']:,.0f}")
            with col4:
                st.metric("TOTAL PROJECT", f"R {result['total_cost']:,.0f}")

            st.markdown("---")

            st.subheader("Per-Stand Cost Breakdown")

            service = TOWNSHIP_ELECTRIFICATION[service_type]
            for component, cost in service["per_stand_cost"].items():
                total = cost * num_stands
                st.write(f"- {component.replace('_', ' ').title()}: R{cost:,} x {num_stands} = **R{total:,}**")

            st.markdown("---")

            # Summary
            st.subheader("Project Summary")
            st.info(f"""
            **Total Stands:** {num_stands:,}
            **Service Type:** {result['service_type']}
            **ADMD per Stand:** {result['admd']} kVA
            **Total ADMD:** {result['admd'] * num_stands:.0f} kVA
            **Cost per Stand:** R {result['cost_per_stand']:,}
            **Total Project Cost:** R {result['total_cost']:,}
            """)
        else:
            st.info("👆 Configure project parameters and calculate first.")

    with tab3:
        st.markdown('<p class="section-title">Export Quotation</p>', unsafe_allow_html=True)

        if "township_result" in st.session_state:
            result = st.session_state.township_result

            if st.button("📄 Generate PDF Quote", type="primary", use_container_width=True):
                summary = {
                    "Number of Stands": f"{result['num_stands']:,}",
                    "Service Type": result['service_type'],
                    "Connection Size": result['connection_size'],
                    "Cost per Stand": f"R {result['cost_per_stand']:,}",
                }
                pdf_bytes = generate_generic_electrical_pdf(
                    result["bq_items"],
                    summary,
                    "infrastructure",
                    "township"
                )
                st.download_button(
                    label="⬇️ Download PDF",
                    data=pdf_bytes,
                    file_name=f"township_quote_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf",
                    mime="application/pdf",
                    use_container_width=True
                )
        else:
            st.info("👆 Configure and calculate first.")

# Street Lighting
elif selected_subtype == "street_lighting":
    tab1, tab2, tab3 = st.tabs(["📐 Configure", "📊 Design & Cost", "📄 Export"])

    with tab1:
        st.markdown('<p class="section-title">Street Lighting Design (SANS 10098)</p>', unsafe_allow_html=True)

        col1, col2 = st.columns(2)

        with col1:
            road_length = st.number_input("Road Length (m)", 100, 50000, 1000, 100)

        with col2:
            road_type_options = {
                "Residential Roads": "residential",
                "Collector Roads": "collector",
                "Arterial Roads": "arterial",
                "Highway": "highway",
            }
            road_type_label = st.selectbox("Road Classification", list(road_type_options.keys()))
            road_type = road_type_options[road_type_label]

        # Show spacing guidelines
        st.markdown("---")
        st.subheader("SANS 10098 Spacing Guidelines")
        guidelines = STREET_LIGHTING["spacing_guidelines"]
        for rt, g in guidelines.items():
            st.write(f"- **{rt.title()}:** Pole height {g['pole_height']}m, Spacing {g['spacing']}m, {g['lumens_required']} lumens required")

        if st.button("📊 Calculate Street Lighting", type="primary", use_container_width=True):
            result = calculate_street_lighting(road_length, road_type)
            st.session_state.street_result = result
            st.success("✅ Street lighting calculated!")

    with tab2:
        st.markdown('<p class="section-title">Design & Cost Breakdown</p>', unsafe_allow_html=True)

        if "street_result" in st.session_state:
            result = st.session_state.street_result

            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Road Length", f"{result['road_length']} m")
            with col2:
                st.metric("Number of Poles", result["num_poles"])
            with col3:
                st.metric("Pole Spacing", f"{result['spacing']} m")
            with col4:
                st.metric("Cost per Meter", f"R {result['cost_per_meter']:.0f}")

            st.markdown("---")

            st.subheader("Bill of Quantities")
            for item in result["bq_items"]:
                st.write(f"- {item['item']}: {item['qty']} {item['unit']} @ R{item['rate']:,} = **R{item['total']:,}**")

            st.markdown("---")

            col1, col2 = st.columns(2)
            with col1:
                st.metric("TOTAL PROJECT COST", f"R {result['total_cost']:,.0f}")
            with col2:
                st.metric("Cost per Meter of Road", f"R {result['cost_per_meter']:.0f}")
        else:
            st.info("👆 Configure project parameters and calculate first.")

    with tab3:
        st.markdown('<p class="section-title">Export Quotation</p>', unsafe_allow_html=True)

        if "street_result" in st.session_state:
            result = st.session_state.street_result

            if st.button("📄 Generate PDF Quote", type="primary", use_container_width=True):
                summary = {
                    "Road Length": f"{result['road_length']} m",
                    "Road Type": result['road_type'].title(),
                    "Number of Poles": result['num_poles'],
                    "Pole Height": f"{result['pole_height']} m",
                }
                pdf_bytes = generate_generic_electrical_pdf(
                    result["bq_items"],
                    summary,
                    "infrastructure",
                    "street_lighting"
                )
                st.download_button(
                    label="⬇️ Download PDF",
                    data=pdf_bytes,
                    file_name=f"street_lighting_quote_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf",
                    mime="application/pdf",
                    use_container_width=True
                )
        else:
            st.info("👆 Configure and calculate first.")

# Rural Electrification
elif selected_subtype == "rural":
    st.markdown('<p class="section-title">Rural Electrification</p>', unsafe_allow_html=True)

    st.subheader("Grid Extension Costs")
    for key, line in RURAL_ELECTRIFICATION["grid_extension"]["mv_line_overhead"].items():
        st.write(f"- {line['item']}: R{line['price']:,}")

    st.markdown("---")

    st.subheader("Pole-Mount Transformers")
    for key, tx in RURAL_ELECTRIFICATION["grid_extension"]["transformer_pole_mount"].items():
        st.write(f"- {tx['item']}: R{tx['price']:,}")

    st.markdown("---")

    st.subheader("Solar Home Systems (Off-Grid)")
    for key, shs in RURAL_ELECTRIFICATION["solar_home_system"].items():
        with st.expander(f"{shs['name']} ({shs['capacity_wp']}Wp)"):
            for comp_key, comp in shs["components"].items():
                st.write(f"- {comp['item']}: {comp['qty']} x R{comp['price']:,}")
            st.write(f"- Labour: R{shs['labour']:,}")
            st.write(f"**Total: R{shs['total']:,}**")

# Utility Solar
elif selected_subtype == "utility_solar":
    st.markdown('<p class="section-title">Utility-Scale Solar</p>', unsafe_allow_html=True)

    for size, plant in UTILITY_SOLAR["ground_mount"].items():
        with st.expander(f"**{plant['name']}**"):
            col1, col2 = st.columns(2)
            with col1:
                st.write(f"**Capacity:** {plant['capacity_mw']} MW")
                st.write(f"**Land Required:** {plant['land_required_ha']} ha")
            with col2:
                st.write(f"**Civil Works:** R{plant['civil']:,}")
                st.write(f"**Grid Connection:** R{plant['grid_connection']:,}")

            st.markdown("---")
            st.write("**Components:**")
            component_total = 0
            for key, comp in plant["components"].items():
                st.write(f"- {comp['item']}: R{comp['price']:,}")
                component_total += comp['price']

            total = component_total + plant['civil'] + plant['grid_connection']
            total_with_margin = total * (1 + plant['epc_margin'])

            st.markdown("---")
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Base Cost", f"R {total:,.0f}")
            with col2:
                st.metric(f"With EPC Margin ({plant['epc_margin']*100:.0f}%)", f"R {total_with_margin:,.0f}")

            st.write(f"**Cost per MW:** R {total_with_margin/plant['capacity_mw']:,.0f}")

# Mini-Grid
elif selected_subtype == "minigrid":
    st.markdown('<p class="section-title">Mini-Grid & Microgrid</p>', unsafe_allow_html=True)

    st.info("Mini-grid configuration coming soon. This will include community solar, battery storage, and distribution network design.")

    st.subheader("Typical Mini-Grid Configuration (50kW)")

    if "minigrid" in RURAL_ELECTRIFICATION:
        mg = RURAL_ELECTRIFICATION["minigrid"]["50kw"]
        st.write(f"**{mg['name']}**")
        st.write(f"- Capacity: {mg['capacity_kw']} kW")
        st.write(f"- Households Served: {mg['households_served']}")

        st.markdown("---")
        st.write("**Components:**")
        for key, comp in mg["components"].items():
            total = comp['qty'] * comp['price'] if isinstance(comp['qty'], int) else comp['price']
            st.write(f"- {comp['item']}: R{total:,}")

        st.write(f"- Civil Works: R{mg['civil']:,}")
        st.write(f"- Commissioning: R{mg['commissioning']:,}")

else:
    st.info(f"Configuration for {selected_subtype.replace('_', ' ').title()} coming soon!")
