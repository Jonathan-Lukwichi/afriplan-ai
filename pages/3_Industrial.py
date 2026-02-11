"""
AfriPlan Electrical - Industrial Page
Mining, manufacturing, warehouses, substations
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
    INDUSTRIAL_MOTOR_LOADS,
    INDUSTRIAL_MCC,
    INDUSTRIAL_MV_EQUIPMENT,
    MINING_SPECIFIC,
)
from utils.calculations import calculate_industrial_electrical
from utils.optimizer import generate_quotation_options
from utils.pdf_generator import generate_generic_electrical_pdf

inject_custom_css()

# Header
page_header(
    title="Industrial Electrical",
    subtitle="Mining, manufacturing, warehouses, substations & HV"
)

# Sidebar
with st.sidebar:
    st.markdown("### Project Type")

    subtypes = PROJECT_TYPES["industrial"]["subtypes"]
    subtype_options = {f"{s['icon']} {s['name']}": s['code'] for s in subtypes}
    selected_subtype_label = st.selectbox("Select Project", list(subtype_options.keys()))
    selected_subtype = subtype_options[selected_subtype_label]

    for s in subtypes:
        if s["code"] == selected_subtype:
            if "standards" in s:
                st.caption(f"Standards: {', '.join(s['standards'])}")
            break

# Main content with tabs
tab1, tab2, tab3, tab4 = st.tabs(["📐 Configure", "⚡ Motors & MCC", "🔌 MV/HV Equipment", "📊 Quote"])

with tab1:
    st.markdown('<p class="section-title">Industrial Configuration</p>', unsafe_allow_html=True)

    st.subheader("Project Parameters")

    col1, col2 = st.columns(2)
    with col1:
        total_motor_load = st.number_input("Total Motor Load (kW)", 0, 10000, 100, 10)
        num_motors = st.number_input("Number of Motors", 1, 100, 5)

    with col2:
        if selected_subtype in ["mining_surface", "mining_underground"]:
            hazardous_area = st.checkbox("Hazardous Area (Flameproof Required)", value=True)
        else:
            hazardous_area = st.checkbox("Hazardous Area Classification")

        mv_required = st.checkbox("MV Supply Required (11kV/22kV)")

    st.session_state.industrial_config = {
        "total_motor_load": total_motor_load,
        "num_motors": num_motors,
        "hazardous_area": hazardous_area,
        "mv_required": mv_required,
    }

with tab2:
    st.markdown('<p class="section-title">Motors & Motor Control Centres</p>', unsafe_allow_html=True)

    st.subheader("Motor Load Categories")

    for size, data in INDUSTRIAL_MOTOR_LOADS.items():
        with st.expander(f"**{size.title()} Motors ({data['range_kw']})**"):
            st.write(f"**Voltage:** {data['voltage']}")
            st.write(f"**Starter Type:** {data['starter']}")
            st.write(f"**Applications:** {', '.join(data['applications'])}")

            st.markdown("---")
            st.write("**Typical Motor Sizes:**")
            for motor in data['typical_motors']:
                cable = motor.get('cable', 'N/A')
                price = motor.get('price', motor.get('motor_price', 0))
                starter = motor.get('starter_price', motor.get('vsd_price', 0))
                st.write(f"- {motor['kw']}kW: Motor R{price:,} | Starter/VSD R{starter:,} | Cable {cable}")

    st.markdown("---")

    st.subheader("MCC Specifications")

    config = st.session_state.get("industrial_config", {})
    hazardous = config.get("hazardous_area", False)

    mcc_type = "mining_mcc" if hazardous else "standard_mcc"
    mcc = INDUSTRIAL_MCC[mcc_type]

    st.info(f"""
    **{mcc['name']}**
    - Construction: {mcc['construction']}
    - IP Rating: {mcc['ip_rating']}
    """)

    st.write("**MCC Components:**")
    for key, comp in mcc["components"].items():
        st.write(f"- {comp['item']}: R{comp['price']:,}")

    st.write(f"- Labour per bucket: R{mcc['labour_per_bucket']:,}")
    st.write(f"- Testing & Commissioning: R{mcc['testing_commissioning']:,}")

with tab3:
    st.markdown('<p class="section-title">MV/HV Equipment</p>', unsafe_allow_html=True)

    config = st.session_state.get("industrial_config", {})

    if config.get("mv_required", False):
        st.subheader("11kV Switchgear")

        sg = INDUSTRIAL_MV_EQUIPMENT["switchgear_11kv"]
        for key, comp in sg["components"].items():
            st.write(f"- {comp['item']}: R{comp['price']:,}")

        st.markdown("---")

        st.subheader("Distribution Transformers")

        tx = INDUSTRIAL_MV_EQUIPMENT["transformer"]
        for option in tx["options"]:
            st.write(f"- {option['kva']} kVA ({option['type']}): R{option['price']:,}")
    else:
        st.info("MV supply not selected. Enable in Configure tab if required.")

    if selected_subtype in ["mining_surface", "mining_underground"]:
        st.markdown("---")
        st.subheader("Mining-Specific Equipment")

        mine_type = "underground" if selected_subtype == "mining_underground" else "surface"
        equipment = MINING_SPECIFIC.get(mine_type, {})

        for key, item in equipment.items():
            st.write(f"- {item['item']}: R{item['price']:,}")

with tab4:
    st.markdown('<p class="section-title">Industrial Quotation & Smart Cost Optimizer</p>', unsafe_allow_html=True)

    config = st.session_state.get("industrial_config", {})

    if config:
        # Use the proper calculation function
        hazardous = config.get("hazardous_area", False)
        result = calculate_industrial_electrical(
            config.get("total_motor_load", 100),
            config.get("num_motors", 5),
            hazardous,
            config.get("mv_required", False),
            selected_subtype
        )
        bq_items = result["bq_items"]
        st.session_state.industrial_result = result
        st.session_state.industrial_bq = bq_items

        # Display totals
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

        # BQ by category
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
            st.session_state.industrial_quote_options = options

        if "industrial_quote_options" in st.session_state and st.session_state.industrial_quote_options:
            options = st.session_state.industrial_quote_options
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

        st.markdown("---")

        if st.button("📄 Generate PDF Quote", type="primary", use_container_width=True, key="pdf_btn"):
            summary = {
                "Project Type": selected_subtype.replace('_', ' ').title(),
                "Motor Load": f"{config.get('total_motor_load', 0)} kW",
                "Number of Motors": config.get('num_motors', 0),
                "Hazardous Area": "Yes" if hazardous else "No",
                "MV Required": "Yes" if config.get('mv_required', False) else "No",
            }
            pdf_bytes = generate_generic_electrical_pdf(
                bq_items,
                summary,
                "industrial",
                selected_subtype
            )
            st.download_button(
                label="⬇️ Download PDF",
                data=pdf_bytes,
                file_name=f"industrial_quote_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf",
                mime="application/pdf",
                use_container_width=True
            )
    else:
        st.info("👆 Configure project parameters first.")
