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
            if st.button("📄 Generate PDF Quote", type="primary", use_container_width=True):
                summary = {"Solution Type": result["solution_type"]}
                pdf_bytes = generate_generic_electrical_pdf(result["bq_items"], summary, "infrastructure", "rural")
                st.download_button(label="⬇️ Download PDF", data=pdf_bytes, file_name=f"rural_quote_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf", mime="application/pdf", use_container_width=True)
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
            if st.button("📄 Generate PDF Quote", type="primary", use_container_width=True):
                summary = {"Plant Size": result["plant"]["name"], "Capacity": f"{result['plant']['capacity_mw']} MW", "Land Required": f"{result['plant']['land_required_ha']} ha"}
                pdf_bytes = generate_generic_electrical_pdf(result["bq_items"], summary, "infrastructure", "utility_solar")
                st.download_button(label="⬇️ Download PDF", data=pdf_bytes, file_name=f"utility_solar_quote_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf", mime="application/pdf", use_container_width=True)
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
            if st.button("📄 Generate PDF Quote", type="primary", use_container_width=True):
                summary = {"Mini-Grid": result["mg"]["name"], "Capacity": f"{result['mg']['capacity_kw']} kW", "Households Served": result['mg']['households_served']}
                pdf_bytes = generate_generic_electrical_pdf(result["bq_items"], summary, "infrastructure", "minigrid")
                st.download_button(label="⬇️ Download PDF", data=pdf_bytes, file_name=f"minigrid_quote_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf", mime="application/pdf", use_container_width=True)
        else:
            st.info("👆 Configure and generate quote first.")

else:
    st.info(f"Configuration for {selected_subtype.replace('_', ' ').title()} coming soon!")
