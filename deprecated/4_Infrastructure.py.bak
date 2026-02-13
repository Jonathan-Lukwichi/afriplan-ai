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
    MUNICIPAL_REQUIREMENTS,
    ADMD_VALUES,
)
from utils.calculations import (
    calculate_township_electrification,
    calculate_street_lighting,
    calculate_admd,
    calculate_voltage_drop,
)
from utils.pdf_generator import generate_generic_electrical_pdf
from utils.excel_exporter import export_bq_to_excel

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

            export_col1, export_col2 = st.columns(2)

            with export_col1:
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

            with export_col2:
                if st.button("📊 Generate Excel BQ", type="secondary", use_container_width=True):
                    try:
                        project_info = {
                            "Project Type": "Township Electrification",
                            "Number of Stands": result['num_stands'],
                            "Service Type": result['service_type'],
                            "Connection Size": result['connection_size'],
                            "Total ADMD (kVA)": result['admd'] * result['num_stands'],
                        }
                        excel_bytes = export_bq_to_excel(
                            result["bq_items"],
                            project_info,
                            {"cost_per_stand": result['cost_per_stand'], "total_cost": result['total_cost']}
                        )
                        st.download_button(
                            label="⬇️ Download Excel",
                            data=excel_bytes,
                            file_name=f"township_bq_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            use_container_width=True
                        )
                    except ImportError:
                        st.error("Excel export requires openpyxl. Install with: pip install openpyxl")

            st.markdown("---")

            # Municipal Submission Requirements
            st.markdown("### 🏛️ Municipal Submission Requirements")
            st.markdown("*Select municipality to see submission requirements*")

            municipality = st.selectbox(
                "Select Municipality",
                list(MUNICIPAL_REQUIREMENTS.keys()),
                format_func=lambda x: MUNICIPAL_REQUIREMENTS[x]["name"],
                key="township_municipality"
            )

            muni = MUNICIPAL_REQUIREMENTS[municipality]
            muni_cols = st.columns(3)
            with muni_cols[0]:
                st.metric("Inspection Fee", f"R {muni['inspection_fee']:,}")
            with muni_cols[1]:
                st.metric("Turnaround", f"{muni['turnaround_days']} days")
            with muni_cols[2]:
                st.metric("Forms Required", len(muni['forms']))

            with st.expander("Required Documents"):
                for form in muni['forms']:
                    st.write(f"- {form}")

            st.info(f"**Note:** Township electrification projects require Eskom bulk supply approval and municipal infrastructure sign-off per NRS 034 and SANS 10142.")

            st.markdown("---")

            # Bulk ADMD Calculator for Township
            st.markdown("### 📋 Bulk ADMD Calculator (NRS 034)")
            st.markdown("*Calculate diversity factor for bulk Eskom application*")

            if st.button("Calculate Bulk ADMD with Diversity", key="calc_bulk_admd"):
                # Use ADMD calculator with diversity factors
                dwelling_type = "rdp_low_cost" if "20A" in result['connection_size'] else "standard_house"
                bulk_admd = calculate_admd(dwelling_type, result['num_stands'])
                st.session_state.bulk_admd_result = bulk_admd

            if "bulk_admd_result" in st.session_state:
                bulk = st.session_state.bulk_admd_result
                bulk_cols = st.columns(4)
                with bulk_cols[0]:
                    st.metric("Base ADMD/Stand", f"{bulk['base_admd_kva']} kVA")
                with bulk_cols[1]:
                    st.metric("Diversity Factor", f"{bulk['diversity_factor']:.0%}")
                with bulk_cols[2]:
                    st.metric("Total ADMD", f"{bulk['total_admd_kva']} kVA")
                with bulk_cols[3]:
                    st.metric("Recommended Supply", bulk['eskom_application_size'])

                st.success(f"**Eskom Bulk Application:** {bulk['total_admd_kva']} kVA ({bulk['supply_type']})")

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

            export_col1, export_col2 = st.columns(2)

            with export_col1:
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

            with export_col2:
                if st.button("📊 Generate Excel BQ", type="secondary", use_container_width=True):
                    try:
                        project_info = {
                            "Project Type": "Street Lighting",
                            "Road Length (m)": result['road_length'],
                            "Road Classification": result['road_type'].title(),
                            "Number of Poles": result['num_poles'],
                            "Pole Height (m)": result['pole_height'],
                            "Pole Spacing (m)": result['spacing'],
                        }
                        excel_bytes = export_bq_to_excel(
                            result["bq_items"],
                            project_info,
                            {"cost_per_meter": result['cost_per_meter'], "total_cost": result['total_cost']}
                        )
                        st.download_button(
                            label="⬇️ Download Excel",
                            data=excel_bytes,
                            file_name=f"street_lighting_bq_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            use_container_width=True
                        )
                    except ImportError:
                        st.error("Excel export requires openpyxl. Install with: pip install openpyxl")

            st.markdown("---")

            # SANS 10098 Compliance Checklist
            st.markdown("### ✅ SANS 10098 Compliance Checklist")

            compliance_items = [
                ("Luminance Level", f"{result['road_type'].title()} road classification - compliant spacing"),
                ("Pole Height", f"{result['pole_height']}m poles per SANS 10098 requirements"),
                ("Spacing", f"{result['spacing']}m spacing meets uniformity requirements"),
                ("Light Source", "LED luminaires - energy efficient and compliant"),
                ("Mounting Height Ratio", "Width/Height ratio within specification"),
            ]

            for item, note in compliance_items:
                st.success(f"✅ **{item}:** {note}")

            st.markdown("---")

            # Municipal Requirements
            st.markdown("### 🏛️ Municipal Submission Requirements")

            municipality = st.selectbox(
                "Select Municipality",
                list(MUNICIPAL_REQUIREMENTS.keys()),
                format_func=lambda x: MUNICIPAL_REQUIREMENTS[x]["name"],
                key="street_municipality"
            )

            muni = MUNICIPAL_REQUIREMENTS[municipality]
            st.info(f"""
            **{muni['name']} Requirements:**
            - Inspection Fee: R {muni['inspection_fee']:,}
            - Turnaround: {muni['turnaround_days']} days
            - Required: {', '.join(muni['forms'])}
            """)

            # Voltage drop check for street lighting
            st.markdown("---")
            st.markdown("### ⚡ Feeder Voltage Drop Check")

            vd_col1, vd_col2 = st.columns(2)
            with vd_col1:
                feeder_cable = st.selectbox("Feeder Cable Size (mm²)", ["4.0", "6.0", "10", "16", "25"], index=2, key="street_vd_cable")
            with vd_col2:
                total_load_a = st.number_input("Total Lighting Load (A)", 1.0, 100.0, float(result['num_poles'] * 0.5), key="street_vd_load")

            if st.button("Check Voltage Drop", key="street_vd_check"):
                vd_result = calculate_voltage_drop(
                    feeder_cable,
                    result['road_length'],
                    total_load_a,
                    voltage=230,
                    phase="single"
                )
                if "error" not in vd_result:
                    if vd_result['compliant']:
                        st.success(f"✅ Voltage drop: {vd_result['voltage_drop_percent']:.2f}% - Compliant (max 5%)")
                    else:
                        st.error(f"❌ Voltage drop: {vd_result['voltage_drop_percent']:.2f}% - Exceeds 5% limit. Consider larger cable or split feeders.")
                else:
                    st.error(vd_result['error'])

        else:
            st.info("👆 Configure and calculate first.")

# Rural Electrification
elif selected_subtype == "rural":
    tab1, tab2, tab3 = st.tabs(["📐 Configure", "📊 Cost Breakdown", "📄 Export"])

    with tab1:
        st.markdown('<p class="section-title">Rural Electrification Options</p>', unsafe_allow_html=True)

        col1, col2 = st.columns(2)

        with col1:
            solution_type = st.radio(
                "Electrification Solution",
                ["Grid Extension", "Solar Home System"],
                help="Grid extension for areas near existing grid, Solar Home Systems for remote areas"
            )

        with col2:
            if solution_type == "Grid Extension":
                line_type = st.selectbox("MV Line Type", ["11kV Single Phase", "11kV Three Phase", "22kV Three Phase"])
                line_length = st.number_input("Line Length (km)", 0.5, 100.0, 5.0, 0.5)
                num_transformers = st.number_input("Number of Transformers", 1, 20, 2)
                tx_size = st.selectbox("Transformer Size", ["16kVA", "50kVA", "100kVA"])
            else:
                shs_type = st.selectbox("Solar Home System Type",
                    list(RURAL_ELECTRIFICATION["solar_home_system"].keys()),
                    format_func=lambda x: RURAL_ELECTRIFICATION["solar_home_system"][x]["name"])
                num_households = st.number_input("Number of Households", 10, 1000, 50, 10)

        if st.button("📊 Calculate Project Cost", type="primary", use_container_width=True):
            bq_items = []
            if solution_type == "Grid Extension":
                line_key = "11kV_single" if "Single" in line_type else "11kV_three" if "11kV" in line_type else "22kV_three"
                line_data = RURAL_ELECTRIFICATION["grid_extension"]["mv_line_overhead"][line_key]
                line_total = line_data["price"] * line_length
                bq_items.append({"category": "MV Lines", "item": line_data["item"], "qty": line_length, "unit": "km", "rate": line_data["price"], "total": line_total})

                tx_key = tx_size.lower().replace("kva", "kva")
                tx_data = RURAL_ELECTRIFICATION["grid_extension"]["transformer_pole_mount"][tx_key]
                tx_total = tx_data["price"] * num_transformers
                bq_items.append({"category": "Transformers", "item": tx_data["item"], "qty": num_transformers, "unit": "each", "rate": tx_data["price"], "total": tx_total})

                poles_needed = int(line_length * 15)
                pole_total = 4500 * poles_needed
                bq_items.append({"category": "Poles", "item": "Wood Pole 11m treated", "qty": poles_needed, "unit": "each", "rate": 4500, "total": pole_total})

                labour = line_length * 25000
                bq_items.append({"category": "Labour", "item": "Installation Labour", "qty": line_length, "unit": "km", "rate": 25000, "total": labour})
            else:
                shs_data = RURAL_ELECTRIFICATION["solar_home_system"][shs_type]
                for comp_key, comp in shs_data["components"].items():
                    comp_total = comp["qty"] * comp["price"] * num_households
                    bq_items.append({"category": "SHS Equipment", "item": comp["item"], "qty": comp["qty"] * num_households, "unit": "each", "rate": comp["price"], "total": comp_total})
                labour_total = shs_data["labour"] * num_households
                bq_items.append({"category": "Labour", "item": "Installation Labour", "qty": num_households, "unit": "households", "rate": shs_data["labour"], "total": labour_total})

            st.session_state.rural_result = {"bq_items": bq_items, "solution_type": solution_type}
            st.success("✅ Project cost calculated!")

    with tab2:
        st.markdown('<p class="section-title">Cost Breakdown</p>', unsafe_allow_html=True)

        if "rural_result" in st.session_state:
            result = st.session_state.rural_result
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
            st.info("👆 Configure project parameters and calculate first.")

    with tab3:
        st.markdown('<p class="section-title">Export Quotation</p>', unsafe_allow_html=True)

        if "rural_result" in st.session_state:
            result = st.session_state.rural_result

            export_col1, export_col2 = st.columns(2)

            with export_col1:
                if st.button("📄 Generate PDF Quote", type="primary", use_container_width=True):
                    summary = {"Solution Type": result["solution_type"]}
                    pdf_bytes = generate_generic_electrical_pdf(result["bq_items"], summary, "infrastructure", "rural")
                    st.download_button(label="⬇️ Download PDF", data=pdf_bytes, file_name=f"rural_quote_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf", mime="application/pdf", use_container_width=True)

            with export_col2:
                if st.button("📊 Generate Excel BQ", type="secondary", use_container_width=True):
                    try:
                        project_info = {
                            "Project Type": "Rural Electrification",
                            "Solution Type": result["solution_type"],
                        }
                        subtotal = sum(item["total"] for item in result["bq_items"])
                        excel_bytes = export_bq_to_excel(
                            result["bq_items"],
                            project_info,
                            {"subtotal": subtotal, "total_incl_vat": subtotal * 1.15}
                        )
                        st.download_button(
                            label="⬇️ Download Excel",
                            data=excel_bytes,
                            file_name=f"rural_bq_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            use_container_width=True
                        )
                    except ImportError:
                        st.error("Excel export requires openpyxl. Install with: pip install openpyxl")

            st.markdown("---")

            # INEP/DOE Requirements for Rural Electrification
            st.markdown("### 📋 INEP Programme Requirements")
            st.markdown("*Integrated National Electrification Programme guidelines*")

            st.info("""
            **INEP Submission Requirements:**
            - Detailed project scope and technical specifications
            - Community beneficiary list with GPS coordinates
            - Environmental impact assessment (if required)
            - Landowner consent forms
            - Municipal IDP alignment confirmation
            - Cost-benefit analysis
            """)

            if result["solution_type"] == "Grid Extension":
                st.warning("""
                **Grid Extension Specific:**
                - Eskom network study approval required
                - Wayleave agreements for line routes
                - NERSA licence for distribution (if applicable)
                """)
            else:
                st.warning("""
                **Solar Home System Specific:**
                - Warranty and maintenance plan required
                - User training documentation
                - Spare parts availability plan
                - Battery disposal/recycling plan
                """)
        else:
            st.info("👆 Configure and calculate first.")

# Utility Solar
elif selected_subtype == "utility_solar":
    tab1, tab2, tab3 = st.tabs(["📐 Configure", "📊 Cost Breakdown", "📄 Export"])

    with tab1:
        st.markdown('<p class="section-title">Utility-Scale Solar Plant Design</p>', unsafe_allow_html=True)

        col1, col2 = st.columns(2)

        with col1:
            plant_options = list(UTILITY_SOLAR["ground_mount"].keys())
            plant_labels = {k: UTILITY_SOLAR["ground_mount"][k]["name"] for k in plant_options}
            selected_plant = st.selectbox("Plant Size", plant_options, format_func=lambda x: plant_labels[x])

        plant = UTILITY_SOLAR["ground_mount"][selected_plant]

        with col2:
            st.info(f"""
            **{plant['name']}**
            - Capacity: {plant['capacity_mw']} MW
            - Land Required: {plant['land_required_ha']} ha
            - EPC Margin: {plant['epc_margin']*100:.0f}%
            """)

        st.markdown("---")
        st.subheader("Plant Components")

        component_total = 0
        for key, comp in plant["components"].items():
            component_total += comp["price"]
            st.write(f"- {comp['item']}: **R{comp['price']:,}**")

        st.markdown("---")

        col1, col2 = st.columns(2)
        with col1:
            st.metric("Civil Works", f"R {plant['civil']:,}")
        with col2:
            st.metric("Grid Connection", f"R {plant['grid_connection']:,}")

        if st.button("📊 Generate Detailed Quote", type="primary", use_container_width=True):
            bq_items = []
            for key, comp in plant["components"].items():
                bq_items.append({"category": "Equipment", "item": comp["item"], "qty": 1, "unit": "lot", "rate": comp["price"], "total": comp["price"]})
            bq_items.append({"category": "Civil Works", "item": "Site Preparation & Foundations", "qty": 1, "unit": "lot", "rate": plant["civil"], "total": plant["civil"]})
            bq_items.append({"category": "Grid Connection", "item": "Grid Interconnection", "qty": 1, "unit": "lot", "rate": plant["grid_connection"], "total": plant["grid_connection"]})

            base_total = sum(item["total"] for item in bq_items)
            epc_margin = base_total * plant["epc_margin"]
            bq_items.append({"category": "EPC Margin", "item": f"EPC Margin ({plant['epc_margin']*100:.0f}%)", "qty": 1, "unit": "lot", "rate": epc_margin, "total": epc_margin})

            st.session_state.utility_result = {"bq_items": bq_items, "plant": plant}
            st.success("✅ Quote generated!")

    with tab2:
        st.markdown('<p class="section-title">Cost Breakdown</p>', unsafe_allow_html=True)

        if "utility_result" in st.session_state:
            result = st.session_state.utility_result
            bq_items = result["bq_items"]
            plant = result["plant"]

            subtotal = sum(item["total"] for item in bq_items)
            vat = subtotal * 0.15
            total = subtotal + vat

            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Subtotal", f"R {subtotal:,.0f}")
            with col2:
                st.metric("VAT (15%)", f"R {vat:,.0f}")
            with col3:
                st.metric("TOTAL", f"R {total:,.0f}")
            with col4:
                st.metric("Cost per MW", f"R {total/plant['capacity_mw']:,.0f}")

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
                        st.write(f"- {item['item']}: **R{item['total']:,}**")
        else:
            st.info("👆 Configure plant and generate quote first.")

    with tab3:
        st.markdown('<p class="section-title">Export Quotation</p>', unsafe_allow_html=True)

        if "utility_result" in st.session_state:
            result = st.session_state.utility_result
            plant = result["plant"]

            export_col1, export_col2 = st.columns(2)

            with export_col1:
                if st.button("📄 Generate PDF Quote", type="primary", use_container_width=True):
                    summary = {"Plant Size": plant["name"], "Capacity": f"{plant['capacity_mw']} MW", "Land Required": f"{plant['land_required_ha']} ha"}
                    pdf_bytes = generate_generic_electrical_pdf(result["bq_items"], summary, "infrastructure", "utility_solar")
                    st.download_button(label="⬇️ Download PDF", data=pdf_bytes, file_name=f"utility_solar_quote_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf", mime="application/pdf", use_container_width=True)

            with export_col2:
                if st.button("📊 Generate Excel BQ", type="secondary", use_container_width=True):
                    try:
                        project_info = {
                            "Project Type": "Utility-Scale Solar",
                            "Plant Size": plant["name"],
                            "Capacity (MW)": plant['capacity_mw'],
                            "Land Required (ha)": plant['land_required_ha'],
                        }
                        subtotal = sum(item["total"] for item in result["bq_items"])
                        excel_bytes = export_bq_to_excel(
                            result["bq_items"],
                            project_info,
                            {"subtotal": subtotal, "cost_per_mw": subtotal / plant['capacity_mw']}
                        )
                        st.download_button(
                            label="⬇️ Download Excel",
                            data=excel_bytes,
                            file_name=f"utility_solar_bq_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            use_container_width=True
                        )
                    except ImportError:
                        st.error("Excel export requires openpyxl. Install with: pip install openpyxl")

            st.markdown("---")

            # NERSA Registration Requirements
            st.markdown("### ⚡ NERSA & Grid Connection Requirements")
            st.markdown("*National Energy Regulator of South Africa compliance*")

            capacity_mw = plant['capacity_mw']

            if capacity_mw <= 1:
                nersa_category = "Registration (≤1 MW)"
                nersa_fee = 0
                nersa_notes = "No NERSA licence required - registration only"
            elif capacity_mw <= 10:
                nersa_category = "Licence Exemption (1-10 MW)"
                nersa_fee = 5000
                nersa_notes = "Licence exemption with registration"
            elif capacity_mw <= 100:
                nersa_category = "Generation Licence (10-100 MW)"
                nersa_fee = 50000
                nersa_notes = "Full generation licence required"
            else:
                nersa_category = "Generation Licence (>100 MW)"
                nersa_fee = 100000
                nersa_notes = "Full generation licence + ministerial approval"

            nersa_cols = st.columns(3)
            with nersa_cols[0]:
                st.metric("NERSA Category", nersa_category)
            with nersa_cols[1]:
                st.metric("Application Fee", f"R {nersa_fee:,}")
            with nersa_cols[2]:
                st.metric("Typical Timeline", "6-12 months")

            st.info(f"**Note:** {nersa_notes}")

            st.markdown("---")

            # Grid Connection Checklist
            st.markdown("### 🔌 Eskom Grid Connection Checklist")

            grid_items = [
                ("Budget Quote Application", "Submit to Eskom for connection costs"),
                ("Grid Code Compliance Study", "Demonstrate compliance with SA Grid Code"),
                ("Power Quality Assessment", "Harmonic and flicker analysis"),
                ("Protection Coordination Study", "Relay settings and fault analysis"),
                ("Environmental Authorization", "DEA approval for >1 MW"),
                ("Wheeling Agreement", "If selling to third party"),
                ("PPA / Offtake Agreement", "Power Purchase Agreement with buyer"),
            ]

            for item, desc in grid_items:
                st.write(f"☐ **{item}:** {desc}")

            st.markdown("---")

            # Financial Analysis
            st.markdown("### 💰 High-Level Financial Indicators")

            subtotal = sum(item["total"] for item in result["bq_items"])
            annual_generation = capacity_mw * 1800  # Typical MWh/MW/year in SA
            tariff_estimate = 0.85  # R/kWh average

            fin_cols = st.columns(4)
            with fin_cols[0]:
                st.metric("Capex/MW", f"R {subtotal/capacity_mw:,.0f}")
            with fin_cols[1]:
                st.metric("Est. Annual Gen", f"{annual_generation:,.0f} MWh")
            with fin_cols[2]:
                st.metric("Est. Revenue/yr", f"R {annual_generation * tariff_estimate * 1000:,.0f}")
            with fin_cols[3]:
                simple_payback = subtotal / (annual_generation * tariff_estimate * 1000)
                st.metric("Simple Payback", f"{simple_payback:.1f} years")

        else:
            st.info("👆 Configure and generate quote first.")

# Mini-Grid
elif selected_subtype == "minigrid":
    tab1, tab2, tab3 = st.tabs(["📐 Configure", "📊 Cost Breakdown", "📄 Export"])

    with tab1:
        st.markdown('<p class="section-title">Mini-Grid & Microgrid Design</p>', unsafe_allow_html=True)

        col1, col2 = st.columns(2)

        with col1:
            if "minigrid" in RURAL_ELECTRIFICATION:
                mg_options = list(RURAL_ELECTRIFICATION["minigrid"].keys())
                mg_labels = {k: RURAL_ELECTRIFICATION["minigrid"][k]["name"] for k in mg_options}
                selected_mg = st.selectbox("Mini-Grid Size", mg_options, format_func=lambda x: mg_labels[x])
                mg = RURAL_ELECTRIFICATION["minigrid"][selected_mg]

        with col2:
            if "minigrid" in RURAL_ELECTRIFICATION:
                st.info(f"""
                **{mg['name']}**
                - Capacity: {mg['capacity_kw']} kW
                - Households Served: {mg['households_served']}
                """)

        if "minigrid" in RURAL_ELECTRIFICATION:
            st.markdown("---")
            st.subheader("Generation & Storage Components")
            for key, comp in mg["components"].items():
                total = comp['qty'] * comp['price']
                st.write(f"- {comp['item']}: {comp['qty']} x R{comp['price']:,} = **R{total:,}**")

            st.markdown("---")
            st.subheader("Distribution Network")
            for key, item in mg["distribution"].items():
                total = item['qty'] * item['price']
                st.write(f"- {item['item']}: {item['qty']} x R{item['price']:,} = **R{total:,}**")

            st.markdown("---")
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Civil Works", f"R {mg['civil']:,}")
            with col2:
                st.metric("Commissioning", f"R {mg['commissioning']:,}")

            if st.button("📊 Generate Detailed Quote", type="primary", use_container_width=True):
                bq_items = []
                for key, comp in mg["components"].items():
                    total = comp['qty'] * comp['price']
                    bq_items.append({"category": "Generation & Storage", "item": comp["item"], "qty": comp['qty'], "unit": "each", "rate": comp["price"], "total": total})
                for key, item in mg["distribution"].items():
                    total = item['qty'] * item['price']
                    bq_items.append({"category": "Distribution", "item": item["item"], "qty": item['qty'], "unit": "each" if "pole" in key.lower() else "m", "rate": item["price"], "total": total})
                bq_items.append({"category": "Civil & Installation", "item": "Civil Works", "qty": 1, "unit": "lot", "rate": mg["civil"], "total": mg["civil"]})
                bq_items.append({"category": "Civil & Installation", "item": "Testing & Commissioning", "qty": 1, "unit": "lot", "rate": mg["commissioning"], "total": mg["commissioning"]})

                st.session_state.minigrid_result = {"bq_items": bq_items, "mg": mg}
                st.success("✅ Quote generated!")
        else:
            st.warning("Mini-grid data not available.")

    with tab2:
        st.markdown('<p class="section-title">Cost Breakdown</p>', unsafe_allow_html=True)

        if "minigrid_result" in st.session_state:
            result = st.session_state.minigrid_result
            bq_items = result["bq_items"]
            mg = result["mg"]

            subtotal = sum(item["total"] for item in bq_items)
            vat = subtotal * 0.15
            total = subtotal + vat
            cost_per_hh = total / mg["households_served"]

            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Subtotal", f"R {subtotal:,.0f}")
            with col2:
                st.metric("VAT (15%)", f"R {vat:,.0f}")
            with col3:
                st.metric("TOTAL", f"R {total:,.0f}")
            with col4:
                st.metric("Cost per Household", f"R {cost_per_hh:,.0f}")

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
        else:
            st.info("👆 Configure mini-grid and generate quote first.")

    with tab3:
        st.markdown('<p class="section-title">Export Quotation</p>', unsafe_allow_html=True)

        if "minigrid_result" in st.session_state:
            result = st.session_state.minigrid_result
            mg = result["mg"]

            export_col1, export_col2 = st.columns(2)

            with export_col1:
                if st.button("📄 Generate PDF Quote", type="primary", use_container_width=True):
                    summary = {"Mini-Grid": mg["name"], "Capacity": f"{mg['capacity_kw']} kW", "Households Served": mg['households_served']}
                    pdf_bytes = generate_generic_electrical_pdf(result["bq_items"], summary, "infrastructure", "minigrid")
                    st.download_button(label="⬇️ Download PDF", data=pdf_bytes, file_name=f"minigrid_quote_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf", mime="application/pdf", use_container_width=True)

            with export_col2:
                if st.button("📊 Generate Excel BQ", type="secondary", use_container_width=True):
                    try:
                        project_info = {
                            "Project Type": "Mini-Grid / Microgrid",
                            "System Size": mg["name"],
                            "Capacity (kW)": mg['capacity_kw'],
                            "Households Served": mg['households_served'],
                        }
                        subtotal = sum(item["total"] for item in result["bq_items"])
                        excel_bytes = export_bq_to_excel(
                            result["bq_items"],
                            project_info,
                            {"subtotal": subtotal, "cost_per_household": subtotal / mg['households_served']}
                        )
                        st.download_button(
                            label="⬇️ Download Excel",
                            data=excel_bytes,
                            file_name=f"minigrid_bq_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            use_container_width=True
                        )
                    except ImportError:
                        st.error("Excel export requires openpyxl. Install with: pip install openpyxl")

            st.markdown("---")

            # Mini-Grid Regulatory Requirements
            st.markdown("### 📋 Mini-Grid Regulatory Framework")
            st.markdown("*South African regulatory requirements for isolated grids*")

            capacity_kw = mg['capacity_kw']

            if capacity_kw <= 100:
                reg_category = "SSEG (≤100 kW)"
                reg_notes = "Small Scale Embedded Generation - simplified registration"
            elif capacity_kw <= 1000:
                reg_category = "Distribution Licence Exemption"
                reg_notes = "Licence exemption for isolated systems serving specific community"
            else:
                reg_category = "Distribution Licence Required"
                reg_notes = "Full NERSA distribution licence required"

            reg_cols = st.columns(2)
            with reg_cols[0]:
                st.metric("Regulatory Category", reg_category)
            with reg_cols[1]:
                st.metric("Households Served", mg['households_served'])

            st.info(f"**Note:** {reg_notes}")

            st.markdown("---")

            # Sustainability Checklist
            st.markdown("### ✅ Project Sustainability Checklist")

            sustainability_items = [
                ("Community Engagement", "Local community buy-in and ownership model"),
                ("Tariff Structure", "Affordable tariff with cost recovery"),
                ("O&M Plan", "Operations and maintenance schedule"),
                ("Spare Parts", "Local availability of replacement components"),
                ("Training", "Local technician training programme"),
                ("Metering", "Prepaid or smart metering for revenue collection"),
                ("Battery Management", "Battery replacement fund provision"),
                ("Load Growth", "Provision for future demand increase"),
            ]

            for item, desc in sustainability_items:
                st.write(f"☐ **{item}:** {desc}")

            st.markdown("---")

            # Financial Summary
            st.markdown("### 💰 Financial Indicators")

            subtotal = sum(item["total"] for item in result["bq_items"])
            vat = subtotal * 0.15
            total = subtotal + vat
            cost_per_hh = total / mg['households_served']

            # Estimate revenue
            avg_consumption = 50  # kWh per household per month
            tariff = 2.50  # R/kWh
            monthly_revenue = mg['households_served'] * avg_consumption * tariff
            annual_revenue = monthly_revenue * 12

            fin_cols = st.columns(4)
            with fin_cols[0]:
                st.metric("Total Investment", f"R {total:,.0f}")
            with fin_cols[1]:
                st.metric("Cost/Household", f"R {cost_per_hh:,.0f}")
            with fin_cols[2]:
                st.metric("Est. Monthly Revenue", f"R {monthly_revenue:,.0f}")
            with fin_cols[3]:
                payback = total / annual_revenue if annual_revenue > 0 else 0
                st.metric("Simple Payback", f"{payback:.1f} years")

        else:
            st.info("👆 Configure and generate quote first.")

else:
    st.info(f"Configuration for {selected_subtype.replace('_', ' ').title()} coming soon!")
