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
from utils.constants import (
    PROJECT_TYPES,
    INDUSTRIAL_MOTOR_LOADS,
    INDUSTRIAL_MCC,
    INDUSTRIAL_MV_EQUIPMENT,
    MINING_SPECIFIC,
)
from utils.pdf_generator import generate_generic_electrical_pdf

st.set_page_config(
    page_title="Industrial - AfriPlan Electrical",
    page_icon="🏭",
    layout="wide",
)

inject_custom_css()

# Header
st.markdown("""
<div class="main-header">
    <h1>🏭 Industrial Electrical</h1>
    <p>Mining, manufacturing, warehouses, substations & HV</p>
</div>
""", unsafe_allow_html=True)

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
    st.markdown('<p class="section-title">Industrial Quotation</p>', unsafe_allow_html=True)

    config = st.session_state.get("industrial_config", {})

    if config:
        # Generate BQ items based on configuration
        bq_items = []

        # MCC
        hazardous = config.get("hazardous_area", False)
        mcc_type = "mining_mcc" if hazardous else "standard_mcc"
        mcc = INDUSTRIAL_MCC[mcc_type]

        bq_items.append({
            "category": "Motor Control Centre",
            "item": mcc["name"],
            "qty": 1,
            "unit": "each",
            "rate": sum(c['price'] for c in mcc["components"].values()),
            "total": sum(c['price'] for c in mcc["components"].values())
        })

        # Motor starters (estimate)
        num_motors = config.get("num_motors", 5)
        starter_price = 25000 if not hazardous else 85000
        bq_items.append({
            "category": "Motor Starters",
            "item": "Motor Starter Buckets",
            "qty": num_motors,
            "unit": "each",
            "rate": starter_price,
            "total": num_motors * starter_price
        })

        # MV Equipment if required
        if config.get("mv_required", False):
            bq_items.append({
                "category": "MV Equipment",
                "item": "11kV VCB Panel",
                "qty": 1,
                "unit": "each",
                "rate": 385000,
                "total": 385000
            })

            # Estimate transformer size
            load_kw = config.get("total_motor_load", 100)
            if load_kw <= 80:
                tx_kva, tx_price = 100, 125000
            elif load_kw <= 250:
                tx_kva, tx_price = 315, 245000
            elif load_kw <= 400:
                tx_kva, tx_price = 500, 325000
            else:
                tx_kva, tx_price = 1000, 545000

            bq_items.append({
                "category": "MV Equipment",
                "item": f"Transformer {tx_kva}kVA 11kV/400V",
                "qty": 1,
                "unit": "each",
                "rate": tx_price,
                "total": tx_price
            })

        # Labour
        bq_items.append({
            "category": "Labour",
            "item": "Installation & Commissioning",
            "qty": 1,
            "unit": "lump sum",
            "rate": mcc["testing_commissioning"] + (num_motors * mcc["labour_per_bucket"]),
            "total": mcc["testing_commissioning"] + (num_motors * mcc["labour_per_bucket"])
        })

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

        st.subheader("Bill of Quantities")
        for item in bq_items:
            st.write(f"- {item['item']}: {item['qty']} {item['unit']} @ R{item['rate']:,} = **R{item['total']:,}**")

        st.markdown("---")

        if st.button("📄 Generate PDF Quote", type="primary", use_container_width=True):
            summary = {
                "Project Type": selected_subtype.replace('_', ' ').title(),
                "Motor Load": f"{config.get('total_motor_load', 0)} kW",
                "Number of Motors": config.get('num_motors', 0),
                "Hazardous Area": "Yes" if hazardous else "No",
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
