"""
AfriPlan Electrical v4.1 — Results Page

Display final BQ and export options.
Dual output: Quantity-only BQ (primary) + Estimated BQ (reference)
"""

import streamlit as st
from datetime import datetime

from agent.models import PricingResult, BQSection, ItemConfidence
from agent.stages.validate import validate
from agent.stages.price import price
from exports.excel_bq import export_quantity_bq, export_estimated_bq
from exports.pdf_summary import generate_pdf_summary

st.set_page_config(
    page_title="Results | AfriPlan",
    page_icon="📊",
    layout="wide",
)


def main():
    st.title("📊 Results & Export")
    st.markdown("Your Bill of Quantities is ready. Download in your preferred format.")

    # Check prerequisites
    if "extraction" not in st.session_state:
        st.warning("No extraction data. Please start from Upload.")
        return

    extraction = st.session_state.extraction
    contractor = st.session_state.get("contractor_profile")
    site = st.session_state.get("site_conditions")

    # Run validation and pricing if not done
    if "pricing" not in st.session_state:
        with st.spinner("Running validation and pricing..."):
            validation, val_result = validate(extraction)
            pricing, price_result = price(extraction, validation, contractor, site)
            st.session_state.validation = validation
            st.session_state.pricing = pricing

    pricing: PricingResult = st.session_state.pricing
    validation = st.session_state.get("validation")

    # Summary cards
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Total BQ Items", pricing.total_items)

    with col2:
        extracted_pct = pricing.items_from_extraction / pricing.total_items * 100 if pricing.total_items > 0 else 0
        st.metric("From Drawings", f"{extracted_pct:.0f}%",
                 help="Items read directly from drawings")

    with col3:
        if validation:
            st.metric("Compliance Score", f"{validation.compliance_score:.0f}%")

    with col4:
        st.metric("Estimated Total", f"R {pricing.estimate_total_incl_vat_zar:,.0f}")

    st.markdown("---")

    # Tabs
    tab1, tab2, tab3, tab4 = st.tabs([
        "📋 Quantity BQ",
        "💰 Estimated BQ",
        "✅ Compliance",
        "📥 Export"
    ])

    with tab1:
        st.subheader("Bill of Quantities — Quantities Only")
        st.info("This is your PRIMARY deliverable. Quantities only — add your own prices.")

        _render_bq_table(pricing.quantity_bq, show_prices=False)

    with tab2:
        st.subheader("Estimated Bill of Quantities")
        st.warning("⚠️ These are ESTIMATE prices only. Use your own supplier prices.")

        _render_bq_table(pricing.estimated_bq, show_prices=True)

        # Totals
        st.markdown("---")
        col1, col2 = st.columns([2, 1])

        with col2:
            st.markdown("**Summary:**")
            st.write(f"Subtotal: R {pricing.estimate_subtotal_zar:,.2f}")
            st.write(f"Contingency (5%): R {pricing.estimate_contingency_zar:,.2f}")
            st.write(f"Margin: R {pricing.estimate_margin_zar:,.2f}")
            st.write(f"Total excl VAT: R {pricing.estimate_total_excl_vat_zar:,.2f}")
            st.write(f"VAT (15%): R {pricing.estimate_vat_zar:,.2f}")
            st.markdown(f"**TOTAL: R {pricing.estimate_total_incl_vat_zar:,.2f}**")

    with tab3:
        st.subheader("Compliance Report")

        if validation:
            # Score gauge
            score = validation.compliance_score
            if score >= 90:
                st.success(f"✅ Compliance Score: {score:.0f}%")
            elif score >= 70:
                st.warning(f"⚠️ Compliance Score: {score:.0f}%")
            else:
                st.error(f"❌ Compliance Score: {score:.0f}%")

            # Stats
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Passed", validation.passed)
            col2.metric("Failed", validation.failed)
            col3.metric("Warnings", validation.warnings)
            col4.metric("Auto-fixed", validation.auto_corrections)

            # Details
            st.markdown("---")
            st.markdown("**Issues:**")

            for flag in validation.flags:
                if flag.passed:
                    continue

                if flag.severity.value == "critical":
                    st.error(f"🔴 {flag.rule_name}: {flag.message}")
                elif flag.severity.value == "warning":
                    st.warning(f"🟡 {flag.rule_name}: {flag.message}")
                else:
                    st.info(f"🔵 {flag.rule_name}: {flag.message}")

                if flag.auto_corrected:
                    st.caption(f"  ↳ Auto-fixed: {flag.corrected_value}")

    with tab4:
        st.subheader("Export Options")

        project_name = extraction.metadata.project_name or "Project"

        col1, col2 = st.columns(2)

        with col1:
            st.markdown("### 📊 Excel Export")

            # Quantity BQ
            st.markdown("**Quantity BQ (Primary)**")
            try:
                qty_excel = export_quantity_bq(pricing, project_name, contractor)
                st.download_button(
                    label="⬇️ Download Quantity BQ (.xlsx)",
                    data=qty_excel,
                    file_name=f"BQ_Quantities_{datetime.now().strftime('%Y%m%d')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True
                )
            except ImportError:
                st.error("openpyxl not installed")

            st.markdown("---")

            # Estimated BQ
            st.markdown("**Estimated BQ (Reference)**")
            try:
                est_excel = export_estimated_bq(pricing, project_name, contractor)
                st.download_button(
                    label="⬇️ Download Estimated BQ (.xlsx)",
                    data=est_excel,
                    file_name=f"BQ_Estimated_{datetime.now().strftime('%Y%m%d')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True
                )
            except ImportError:
                st.error("openpyxl not installed")

        with col2:
            st.markdown("### 📄 PDF Export")

            st.markdown("**Quotation Summary**")
            try:
                tier = st.session_state.get("tier", "commercial")
                pdf_bytes = generate_pdf_summary(
                    pricing=pricing,
                    extraction=extraction,
                    validation=validation,
                    project_name=project_name,
                    contractor=contractor
                )
                st.download_button(
                    label="⬇️ Download PDF Summary",
                    data=pdf_bytes,
                    file_name=f"Quote_{datetime.now().strftime('%Y%m%d')}.pdf",
                    mime="application/pdf",
                    use_container_width=True
                )
            except ImportError:
                st.error("fpdf2 not installed")

            st.markdown("---")

            # JSON Export
            st.markdown("**JSON Data (for integration)**")
            json_data = pricing.model_dump_json(indent=2)
            st.download_button(
                label="⬇️ Download JSON Data",
                data=json_data,
                file_name=f"BQ_Data_{datetime.now().strftime('%Y%m%d')}.json",
                mime="application/json",
                use_container_width=True
            )

    # New project button
    st.markdown("---")

    if st.button("🆕 Start New Project", use_container_width=True):
        # Clear session state
        for key in ["extraction", "validation", "pricing", "review_manager",
                    "site_conditions", "document_set"]:
            if key in st.session_state:
                del st.session_state[key]
        st.switch_page("pages/1_Smart_Upload.py")


def _render_bq_table(items: list, show_prices: bool = False):
    """Render BQ items as a table."""
    import pandas as pd

    current_section = None

    for item in items:
        # Section header
        if item.section != current_section:
            current_section = item.section
            st.markdown(f"#### {item.section.value}")

        # Item row
        cols = st.columns([0.5, 4, 1, 1] + ([1, 1] if show_prices else []))

        conf_color = {
            ItemConfidence.EXTRACTED: "🟢",
            ItemConfidence.INFERRED: "🟡",
            ItemConfidence.ESTIMATED: "🔴",
            ItemConfidence.MANUAL: "🔵",
        }.get(item.source, "⚪")

        cols[0].write(f"{conf_color}")
        cols[1].write(item.description[:60])
        cols[2].write(item.unit)
        cols[3].write(f"{item.qty:.1f}")

        if show_prices:
            cols[4].write(f"R {item.unit_price_zar:,.2f}")
            cols[5].write(f"R {item.total_zar:,.2f}")


if __name__ == "__main__":
    main()
