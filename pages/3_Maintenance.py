"""
AfriPlan Electrical - Maintenance & COC Page

Part 1: COC Inspection Quote (inspection fee + certificate)
Part 2: Remedial Work Quote (defects identified -> repair costs)

This page handles:
- Certificate of Compliance (COC) inspection quotations
- Defect identification and remedial quotations
- DB board upgrade quotations
- Fault finding and repair quotations
"""

import streamlit as st
from datetime import datetime

# Import utilities
try:
    from utils.styles import inject_custom_css
    from utils.components import page_header, section_header, metric_card
    COMPONENTS_AVAILABLE = True
except ImportError:
    COMPONENTS_AVAILABLE = False

try:
    from utils.constants import (
        COC_INSPECTION_FEES,
        COC_DEFECT_PRICING,
        COC_AGE_DEFECT_LIKELIHOOD,
        PAYMENT_TERMS,
    )
    CONSTANTS_AVAILABLE = True
except ImportError:
    CONSTANTS_AVAILABLE = False
    # Fallback constants
    COC_INSPECTION_FEES = {
        "standard": {"name": "Standard House", "base_fee": 1800, "certificate_fee": 450}
    }
    COC_DEFECT_PRICING = {}
    COC_AGE_DEFECT_LIKELIHOOD = {}
    PAYMENT_TERMS = {"standard": {"deposit": 0.5, "completion": 0.5}}

try:
    from utils.pdf_generator import generate_electrical_pdf
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False

try:
    from utils.excel_exporter import export_bq_to_excel
    EXCEL_AVAILABLE = True
except ImportError:
    EXCEL_AVAILABLE = False

# Page config
st.set_page_config(
    page_title="Maintenance & COC - AfriPlan Electrical",
    page_icon="🔧",
    layout="wide"
)

# Inject custom CSS
if COMPONENTS_AVAILABLE:
    inject_custom_css()

# Page header
st.title("🔧 Maintenance & COC")
st.markdown("**Certificate of Compliance inspections and electrical repairs**")
st.markdown("---")

# Initialize session state
if "coc_property_type" not in st.session_state:
    st.session_state.coc_property_type = "standard"
if "coc_defects" not in st.session_state:
    st.session_state.coc_defects = []
if "coc_bq_items" not in st.session_state:
    st.session_state.coc_bq_items = []
if "coc_inspection_fee" not in st.session_state:
    st.session_state.coc_inspection_fee = 0
if "coc_remedial_total" not in st.session_state:
    st.session_state.coc_remedial_total = 0

# Check for AI pre-fill from Smart Upload
if st.session_state.get("from_smart_upload") and st.session_state.get("extracted_data"):
    extracted = st.session_state.extracted_data
    st.info("📤 AI-extracted data loaded from Smart Upload. Review and adjust as needed.")

    # Pre-fill property type
    property_info = extracted.get("property", {})
    if property_info.get("type") in ["flat", "bachelor"]:
        st.session_state.coc_property_type = "basic"
    elif property_info.get("type") in ["townhouse", "complex"]:
        st.session_state.coc_property_type = "complex_unit"
    elif property_info.get("rooms", 0) >= 5 or property_info.get("size_m2", 0) > 200:
        st.session_state.coc_property_type = "large"

    # Pre-fill defects
    defects = extracted.get("defects", [])
    if defects:
        st.session_state.coc_defects = [
            d.get("code") if isinstance(d, dict) else d
            for d in defects
        ]

    st.session_state.from_smart_upload = False

# Sidebar configuration
with st.sidebar:
    st.header("⚙️ Quote Settings")

    work_type = st.selectbox(
        "Work Type",
        options=["COC Inspection", "Remedial Work", "DB Upgrade", "Fault Finding"],
        help="Select the type of work required"
    )

    st.markdown("---")

    # Payment terms
    payment_key = st.selectbox(
        "Payment Terms",
        options=list(PAYMENT_TERMS.keys()),
        format_func=lambda x: PAYMENT_TERMS[x].get("name", x),
        help="Select payment structure"
    )
    payment_terms = PAYMENT_TERMS.get(payment_key, {})

    st.markdown("---")
    st.markdown("### 📊 Quick Stats")

    if st.session_state.coc_inspection_fee > 0:
        st.metric("Inspection Fee", f"R{st.session_state.coc_inspection_fee:,.2f}")

    if st.session_state.coc_remedial_total > 0:
        st.metric("Remedial Total", f"R{st.session_state.coc_remedial_total:,.2f}")

# Main content - Tabs
tab1, tab2, tab3, tab4 = st.tabs([
    "📋 Property Details",
    "⚠️ Defects",
    "💰 Quote",
    "📄 Export"
])

# TAB 1: Property Details / Inspection Configuration
with tab1:
    st.subheader("Property & Inspection Details")

    col1, col2 = st.columns(2)

    with col1:
        # Property type selection
        property_type = st.selectbox(
            "Property Type",
            options=list(COC_INSPECTION_FEES.keys()),
            format_func=lambda x: COC_INSPECTION_FEES[x].get("name", x),
            index=list(COC_INSPECTION_FEES.keys()).index(st.session_state.coc_property_type)
            if st.session_state.coc_property_type in COC_INSPECTION_FEES else 0,
            key="property_type_select"
        )
        st.session_state.coc_property_type = property_type

        # Property details
        property_size = st.number_input(
            "Property Size (m²)",
            min_value=20,
            max_value=1000,
            value=120,
            step=10,
            help="Approximate floor area"
        )

        num_rooms = st.number_input(
            "Number of Rooms",
            min_value=1,
            max_value=20,
            value=6,
            help="Total rooms including bathrooms"
        )

        floors = st.selectbox(
            "Number of Floors",
            options=[1, 2, 3],
            index=0,
            help="Single storey, double storey, etc."
        )

    with col2:
        # Installation age
        installation_age = st.selectbox(
            "Installation Age",
            options=["under_5", "5_to_15", "15_to_30", "over_30"],
            format_func=lambda x: {
                "under_5": "Under 5 years",
                "5_to_15": "5-15 years",
                "15_to_30": "15-30 years",
                "over_30": "Over 30 years"
            }.get(x, x),
            index=1,
            help="Estimated age of electrical installation"
        )

        # Reason for inspection
        reason = st.selectbox(
            "Reason for COC",
            options=[
                "property_sale",
                "new_tenant",
                "insurance",
                "compliance",
                "fault_repair",
                "upgrade"
            ],
            format_func=lambda x: {
                "property_sale": "Property Sale",
                "new_tenant": "New Tenant",
                "insurance": "Insurance Requirement",
                "compliance": "Compliance Check",
                "fault_repair": "Fault Repair",
                "upgrade": "Electrical Upgrade"
            }.get(x, x),
            help="Why is the COC being requested?"
        )

        # Access difficulty
        access_difficulty = st.selectbox(
            "Access Difficulty",
            options=["easy", "moderate", "difficult"],
            format_func=lambda x: {
                "easy": "Easy (ground floor, accessible DB)",
                "moderate": "Moderate (stairs, roof space)",
                "difficult": "Difficult (high ceilings, restricted)"
            }.get(x, x),
            help="How accessible is the installation?"
        )

        # Previous COC
        has_previous_coc = st.checkbox(
            "Previous COC on record",
            value=False,
            help="Does the property have an existing COC?"
        )

    st.markdown("---")

    # Age-based defect prediction
    if installation_age in COC_AGE_DEFECT_LIKELIHOOD:
        age_info = COC_AGE_DEFECT_LIKELIHOOD[installation_age]
        st.info(f"""
        **Expected Outcome ({age_info['description']}):**
        {age_info['expected_outcome']}

        **Pass Probability:** {(1 - age_info['probability']) * 100:.0f}%
        """)

        if age_info.get("likely_defects"):
            with st.expander("🔍 Likely Defects Based on Age"):
                for defect_code in age_info["likely_defects"]:
                    if defect_code in COC_DEFECT_PRICING:
                        defect = COC_DEFECT_PRICING[defect_code]
                        st.markdown(f"- **{defect['desc']}** - R{defect['total']:,.2f}")

    # Calculate inspection fee
    st.markdown("---")
    st.subheader("Inspection Fee Calculation")

    fee_info = COC_INSPECTION_FEES.get(property_type, {})
    base_fee = fee_info.get("base_fee", 1500)
    cert_fee = fee_info.get("certificate_fee", 450)

    # Access difficulty multiplier
    access_multiplier = {"easy": 1.0, "moderate": 1.15, "difficult": 1.30}.get(access_difficulty, 1.0)

    # Floor multiplier
    floor_multiplier = 1.0 + (floors - 1) * 0.1

    adjusted_fee = base_fee * access_multiplier * floor_multiplier
    total_inspection_fee = adjusted_fee + cert_fee

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Base Inspection Fee", f"R{adjusted_fee:,.2f}")
    with col2:
        st.metric("COC Certificate", f"R{cert_fee:,.2f}")
    with col3:
        st.metric("Total Inspection", f"R{total_inspection_fee:,.2f}")

    st.session_state.coc_inspection_fee = total_inspection_fee

# TAB 2: Defects Entry
with tab2:
    st.subheader("⚠️ Defect Identification")

    st.markdown("""
    Select defects found during inspection. This will generate a remedial quotation.
    Defects are categorized by severity:
    - 🔴 **Critical** - Must be fixed for COC to pass
    - 🟠 **High** - Strongly recommended to fix
    - 🟡 **Medium** - Should be fixed
    - 🟢 **Low** - Minor items
    """)

    # Group defects by severity
    critical_defects = {k: v for k, v in COC_DEFECT_PRICING.items() if v.get("severity") == "critical"}
    high_defects = {k: v for k, v in COC_DEFECT_PRICING.items() if v.get("severity") == "high"}
    medium_defects = {k: v for k, v in COC_DEFECT_PRICING.items() if v.get("severity") == "medium"}
    low_defects = {k: v for k, v in COC_DEFECT_PRICING.items() if v.get("severity") == "low"}

    selected_defects = []

    # Critical defects
    st.markdown("### 🔴 Critical Defects")
    cols = st.columns(2)
    for i, (code, defect) in enumerate(critical_defects.items()):
        with cols[i % 2]:
            checked = st.checkbox(
                f"{defect['desc']} - R{defect['total']:,.2f}",
                value=code in st.session_state.coc_defects,
                key=f"defect_{code}"
            )
            if checked:
                qty = st.number_input(
                    f"Qty for {code}",
                    min_value=1,
                    max_value=10,
                    value=1,
                    key=f"qty_{code}",
                    label_visibility="collapsed"
                )
                selected_defects.append({"code": code, "qty": qty})

    # High priority defects
    st.markdown("### 🟠 High Priority Defects")
    cols = st.columns(2)
    for i, (code, defect) in enumerate(high_defects.items()):
        with cols[i % 2]:
            checked = st.checkbox(
                f"{defect['desc']} - R{defect['total']:,.2f}",
                value=code in st.session_state.coc_defects,
                key=f"defect_{code}"
            )
            if checked:
                qty = st.number_input(
                    f"Qty",
                    min_value=1,
                    max_value=10,
                    value=1,
                    key=f"qty_{code}",
                    label_visibility="collapsed"
                )
                selected_defects.append({"code": code, "qty": qty})

    # Medium priority defects
    with st.expander("🟡 Medium Priority Defects"):
        cols = st.columns(2)
        for i, (code, defect) in enumerate(medium_defects.items()):
            with cols[i % 2]:
                checked = st.checkbox(
                    f"{defect['desc']} - R{defect['total']:,.2f}",
                    value=code in st.session_state.coc_defects,
                    key=f"defect_{code}"
                )
                if checked:
                    qty = st.number_input(
                        f"Qty",
                        min_value=1,
                        max_value=10,
                        value=1,
                        key=f"qty_{code}",
                        label_visibility="collapsed"
                    )
                    selected_defects.append({"code": code, "qty": qty})

    # Low priority defects
    with st.expander("🟢 Low Priority Defects"):
        cols = st.columns(2)
        for i, (code, defect) in enumerate(low_defects.items()):
            with cols[i % 2]:
                checked = st.checkbox(
                    f"{defect['desc']} - R{defect['total']:,.2f}",
                    value=code in st.session_state.coc_defects,
                    key=f"defect_{code}"
                )
                if checked:
                    qty = st.number_input(
                        f"Qty",
                        min_value=1,
                        max_value=10,
                        value=1,
                        key=f"qty_{code}",
                        label_visibility="collapsed"
                    )
                    selected_defects.append({"code": code, "qty": qty})

    # Store selected defects
    st.session_state.coc_defects = [d["code"] for d in selected_defects]

    # Summary
    st.markdown("---")
    if selected_defects:
        total_remedial = sum(
            COC_DEFECT_PRICING.get(d["code"], {}).get("total", 0) * d["qty"]
            for d in selected_defects
        )
        st.session_state.coc_remedial_total = total_remedial

        st.success(f"**{len(selected_defects)} defect(s) selected** - Estimated remedial cost: **R{total_remedial:,.2f}**")
    else:
        st.session_state.coc_remedial_total = 0
        st.info("No defects selected. The installation may pass COC inspection.")

# TAB 3: Quote Summary
with tab3:
    st.subheader("💰 Quotation Summary")

    # Build BQ items
    bq_items = []

    # Inspection fee
    if st.session_state.coc_inspection_fee > 0:
        fee_info = COC_INSPECTION_FEES.get(st.session_state.coc_property_type, {})
        bq_items.append({
            "category": "COC Inspection",
            "item": fee_info.get("name", "Inspection Fee"),
            "qty": 1,
            "unit": "each",
            "rate": st.session_state.coc_inspection_fee - fee_info.get("certificate_fee", 450),
            "total": st.session_state.coc_inspection_fee - fee_info.get("certificate_fee", 450),
        })
        bq_items.append({
            "category": "COC Inspection",
            "item": "COC Certificate Issue",
            "qty": 1,
            "unit": "each",
            "rate": fee_info.get("certificate_fee", 450),
            "total": fee_info.get("certificate_fee", 450),
        })

    # Remedial items
    for defect in selected_defects:
        defect_info = COC_DEFECT_PRICING.get(defect["code"], {})
        if defect_info:
            bq_items.append({
                "category": f"Remedial Work ({defect_info.get('severity', 'medium').title()})",
                "item": defect_info.get("desc", defect["code"]),
                "qty": defect["qty"],
                "unit": "each",
                "rate": defect_info.get("total", 0),
                "total": defect_info.get("total", 0) * defect["qty"],
            })

    st.session_state.coc_bq_items = bq_items

    # Display BQ
    if bq_items:
        # Group by category
        categories = {}
        for item in bq_items:
            cat = item["category"]
            if cat not in categories:
                categories[cat] = []
            categories[cat].append(item)

        for cat, items in categories.items():
            st.markdown(f"**{cat}**")
            for item in items:
                col1, col2, col3 = st.columns([4, 1, 1])
                with col1:
                    st.write(f"• {item['item']}")
                with col2:
                    st.write(f"x{item['qty']}")
                with col3:
                    st.write(f"R{item['total']:,.2f}")

        # Totals
        st.markdown("---")
        subtotal = sum(item["total"] for item in bq_items)
        vat = subtotal * 0.15
        total = subtotal + vat

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Subtotal", f"R{subtotal:,.2f}")
        with col2:
            st.metric("VAT (15%)", f"R{vat:,.2f}")
        with col3:
            st.metric("**TOTAL**", f"R{total:,.2f}")

        # Payment breakdown
        st.markdown("---")
        st.subheader("Payment Schedule")

        deposit_pct = payment_terms.get("deposit", 0.5)
        deposit = total * deposit_pct

        st.markdown(f"""
        **{payment_terms.get('name', 'Standard Terms')}:**
        - Deposit: R{deposit:,.2f} ({deposit_pct*100:.0f}%)
        - {payment_terms.get('description', 'As per terms')}
        """)

    else:
        st.info("No items in quotation. Configure inspection and/or select defects.")

# TAB 4: Export
with tab4:
    st.subheader("📄 Export Documents")

    if not st.session_state.coc_bq_items:
        st.warning("No quotation to export. Please complete the configuration first.")
    else:
        col1, col2 = st.columns(2)

        with col1:
            st.markdown("### 📄 PDF Quotation")
            if PDF_AVAILABLE:
                if st.button("Generate PDF Quote", type="primary"):
                    # Generate PDF
                    project_info = {
                        "type": "COC Inspection & Remedial",
                        "property_type": st.session_state.coc_property_type,
                        "date": datetime.now().strftime("%Y-%m-%d"),
                    }

                    try:
                        pdf_bytes = generate_electrical_pdf(
                            elec_req={"work_type": "COC/Maintenance"},
                            circuit_info={"defects_count": len(st.session_state.coc_defects)},
                            bq_items=st.session_state.coc_bq_items,
                        )
                        st.download_button(
                            "⬇️ Download PDF",
                            data=pdf_bytes,
                            file_name=f"COC_Quote_{datetime.now().strftime('%Y%m%d')}.pdf",
                            mime="application/pdf"
                        )
                    except Exception as e:
                        st.error(f"PDF generation error: {e}")
            else:
                st.warning("PDF generation not available")

        with col2:
            st.markdown("### 📊 Excel BQ")
            if EXCEL_AVAILABLE:
                if st.button("Generate Excel BQ", type="secondary"):
                    try:
                        project_info = {
                            "type": "COC Inspection & Remedial",
                            "property_type": st.session_state.coc_property_type,
                            "date": datetime.now().strftime("%Y-%m-%d"),
                        }

                        excel_bytes = export_bq_to_excel(
                            bq_items=st.session_state.coc_bq_items,
                            project_info=project_info,
                        )
                        st.download_button(
                            "⬇️ Download Excel",
                            data=excel_bytes,
                            file_name=f"COC_BQ_{datetime.now().strftime('%Y%m%d')}.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                        )
                    except Exception as e:
                        st.error(f"Excel generation error: {e}")
            else:
                st.warning("Excel export not available (openpyxl not installed)")

        st.markdown("---")

        # COC Checklist summary
        st.markdown("### ✅ COC Checklist Summary")

        critical_count = sum(1 for d in st.session_state.coc_defects if COC_DEFECT_PRICING.get(d, {}).get("severity") == "critical")
        high_count = sum(1 for d in st.session_state.coc_defects if COC_DEFECT_PRICING.get(d, {}).get("severity") == "high")

        if critical_count > 0:
            st.error(f"❌ **COC will FAIL** - {critical_count} critical defect(s) found")
        elif high_count > 0:
            st.warning(f"⚠️ **COC may fail** - {high_count} high priority defect(s) found")
        else:
            st.success("✅ **COC likely to PASS** - No critical defects identified")

        # SANS 10142-1 compliance notes
        st.markdown("""
        **SANS 10142-1 Compliance Requirements:**
        - ✅ Earth leakage protection (30mA ELCB) on all circuits
        - ✅ Adequate earthing system with earth spike
        - ✅ Correct circuit protection (MCB ratings match cable sizes)
        - ✅ No exposed live conductors
        - ✅ Circuit schedule labelled at DB
        - ⭐ Surge protection recommended (not mandatory)
        """)

# Footer
st.markdown("---")
st.caption("AfriPlan Electrical v3.0 | COC Inspections comply with SANS 10142-1:2017 | All prices in ZAR incl. VAT")
