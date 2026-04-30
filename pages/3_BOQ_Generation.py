"""
AfriPlan v6.1 — Step 3: BOQ Generation.

User picks ONE pipeline's BOQ to use as the basis for the tender export,
optionally tweaks contractor pricing inline, then clicks Generate to
produce the SA-compliant Excel and PDF deliverables.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Dict, Optional

import pandas as pd
import streamlit as st

from agent.shared import (
    BillOfQuantities,
    BQLineItem,
    BQSection,
    ContractorProfile,
    ItemConfidence,
    ProjectMetadata,
)
from agent.shared.contractor_io import save_contractor_profile
from exports.excel_boq import export_boq_to_excel
from exports.pdf_boq import export_boq_to_pdf
from ui.components import footer, page_header, rule
from ui.styles import inject_styles


inject_styles()


# ─── Helpers ─────────────────────────────────────────────────────────

def _reprice(boq: BillOfQuantities, markup: float, contingency: float, vat: float) -> BillOfQuantities:
    """Recompute totals on a cloned BOQ with new pricing parameters."""
    cloned_items = [it.model_copy() for it in boq.line_items]
    subtotal = round(sum(it.total_zar for it in cloned_items), 2)
    contingency_zar = round(subtotal * (contingency / 100.0), 2)
    markup_zar = round(subtotal * (markup / 100.0), 2)
    total_excl = round(subtotal + contingency_zar + markup_zar, 2)
    vat_zar = round(total_excl * (vat / 100.0), 2)
    total_incl = round(total_excl + vat_zar, 2)

    return boq.model_copy(update={
        "line_items": cloned_items,
        "contractor_markup_pct": markup,
        "contingency_pct": contingency,
        "vat_pct": vat,
        "subtotal_zar": subtotal,
        "contingency_zar": contingency_zar,
        "markup_zar": markup_zar,
        "total_excl_vat_zar": total_excl,
        "vat_zar": vat_zar,
        "total_incl_vat_zar": total_incl,
    })


def _metric_html(label: str, value: str) -> str:
    return (
        '<div class="afp-metric">'
        f'<span class="afp-metric-label">{label}</span>'
        f'<span class="afp-metric-value">{value}</span>'
        "</div>"
    )


# ─── Page header ─────────────────────────────────────────────────────

page_header(
    step="STEP 3 OF 3",
    title="Generate the tender BOQ",
    subtitle=(
        "Select which pipeline's extraction to base the BOQ on, fine-tune your "
        "pricing, then download the SANS 10142-1 compliant Excel and PDF."
    ),
)


# ─── Guards ──────────────────────────────────────────────────────────

pdf_view: Optional[Dict[str, Any]] = st.session_state.get("pdf_view")
dxf_view: Optional[Dict[str, Any]] = st.session_state.get("dxf_view")
project_meta: Optional[ProjectMetadata] = st.session_state.get("project_meta")
contractor: ContractorProfile = st.session_state.get("contractor_profile") or ContractorProfile()

available = []
if pdf_view and pdf_view.get("state") == "passed" and pdf_view.get("boq") is not None:
    available.append("PDF")
if dxf_view and dxf_view.get("state") == "passed" and dxf_view.get("boq") is not None:
    available.append("DXF")

if not available:
    st.warning(
        "No passing pipeline results found. Go back to **Step 2 — Extraction** "
        "and run the pipelines first."
    )
    if st.button("← Back to Extraction", type="primary"):
        st.switch_page("pages/2_Extraction.py")
    footer()
    st.stop()


# ─── Pipeline picker ─────────────────────────────────────────────────

st.markdown('<div class="afp-eyebrow">CHOOSE A SOURCE</div>', unsafe_allow_html=True)

if len(available) == 1:
    chosen = available[0]
    st.info(
        f"Only **{chosen}** pipeline produced a passing BOQ — using it as the basis."
    )
else:
    chosen = st.radio(
        "Which pipeline's extraction should the BOQ be built from?",
        options=available,
        horizontal=True,
        help=(
            "PDF reads schedules, notes, and multi-DB SLDs. "
            "DXF gives exact counts and cable lengths. "
            "Pick the one that best represents the actual project."
        ),
    )

source_view = pdf_view if chosen == "PDF" else dxf_view
base_boq: BillOfQuantities = source_view["boq"]


# ─── Pricing controls (inline contractor edit) ───────────────────────

st.markdown('<div style="height:8px"></div>', unsafe_allow_html=True)
st.markdown('<div class="afp-eyebrow">PRICING</div>', unsafe_allow_html=True)

with st.expander("Adjust pricing parameters", expanded=True):
    p1, p2, p3 = st.columns(3)
    new_markup = p1.number_input(
        "Markup %", min_value=0.0, max_value=100.0,
        value=float(contractor.markup_pct), step=1.0, key="boq_markup",
    )
    new_contingency = p2.number_input(
        "Contingency %", min_value=0.0, max_value=50.0,
        value=float(contractor.contingency_pct), step=1.0, key="boq_contingency",
    )
    new_vat = p3.number_input(
        "VAT %", min_value=0.0, max_value=25.0,
        value=float(contractor.vat_pct), step=0.5, key="boq_vat",
    )

    s1, s2 = st.columns(2)
    quote_ref = s1.text_input(
        "Quote reference",
        value=f"AFP-{datetime.utcnow():%Y%m%d}-{base_boq.run_id[:6].upper()}",
    )
    validity_days = s2.number_input(
        "Quotation validity (days)", min_value=7, max_value=180, value=30, step=1,
    )

    if st.button("💾  Save pricing to my profile"):
        contractor.markup_pct = new_markup
        contractor.contingency_pct = new_contingency
        contractor.vat_pct = new_vat
        st.session_state.contractor_profile = contractor
        if save_contractor_profile(contractor):
            st.success("Profile saved — these values will pre-fill next time.")


# Apply pricing tweaks to a fresh BOQ
priced_boq = _reprice(base_boq, new_markup, new_contingency, new_vat)
st.session_state.priced_boq = priced_boq


def _section_table(boq: BillOfQuantities) -> pd.DataFrame:
    rows = []
    for it in boq.line_items:
        rows.append({
            "Item":   it.item_number_str,
            "Section": it.section.short_label,
            "Description": it.description,
            "Unit": it.unit,
            "Qty":  it.qty,
            "Rate (R)":  round(it.unit_price_zar, 2),
            "Total (R)": round(it.total_zar, 2),
            "Source": it.source.value,
        })
    return pd.DataFrame(rows)


# ─── BOQ preview ─────────────────────────────────────────────────────

rule()
st.markdown('<div class="afp-eyebrow">PREVIEW</div>', unsafe_allow_html=True)
st.markdown(
    f'<h2 class="afp-h2" style="margin-top:6px;margin-bottom:14px;">'
    f"Bill of Quantities — {priced_boq.total_items} line items"
    "</h2>",
    unsafe_allow_html=True,
)

# Headline totals
m1, m2, m3, m4 = st.columns(4)
m1.markdown(_metric_html("Subtotal",        f"R {priced_boq.subtotal_zar:,.0f}"),         unsafe_allow_html=True)
m2.markdown(_metric_html("Total ex VAT",    f"R {priced_boq.total_excl_vat_zar:,.0f}"),   unsafe_allow_html=True)
m3.markdown(_metric_html("VAT",             f"R {priced_boq.vat_zar:,.0f}"),              unsafe_allow_html=True)
m4.markdown(_metric_html("Total incl VAT",  f"R {priced_boq.total_incl_vat_zar:,.0f}"),   unsafe_allow_html=True)

st.markdown('<div style="height:14px"></div>', unsafe_allow_html=True)

# Section subtotals chart
section_subtotals = priced_boq.section_subtotals_short
if section_subtotals:
    st.markdown("**Section subtotals**")
    st.bar_chart(section_subtotals, height=180)

# Line items table
with st.expander("Show all line items", expanded=False):
    st.dataframe(_section_table(priced_boq), use_container_width=True, hide_index=True)


# ─── Generate downloads ──────────────────────────────────────────────

rule()
st.markdown('<div class="afp-eyebrow">DOWNLOADS</div>', unsafe_allow_html=True)
st.markdown(
    '<h2 class="afp-h2" style="margin-top:6px;margin-bottom:14px;">'
    "Tender-grade deliverables"
    "</h2>",
    unsafe_allow_html=True,
)

dl_cols = st.columns([1, 1, 1])
try:
    xlsx_bytes = export_boq_to_excel(
        priced_boq,
        project=project_meta,
        contractor=contractor,
        quote_ref=quote_ref,
        validity_days=int(validity_days),
    )
    dl_cols[0].download_button(
        label="📊  Excel BOQ (.xlsx)",
        data=xlsx_bytes,
        file_name=f"{quote_ref}_BOQ.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True,
    )
except Exception as e:                  # noqa: BLE001
    dl_cols[0].error(f"Excel export failed: {e}")

try:
    pdf_bytes = export_boq_to_pdf(
        priced_boq,
        project=project_meta,
        contractor=contractor,
        quote_ref=quote_ref,
        validity_days=int(validity_days),
    )
    dl_cols[1].download_button(
        label="📄  PDF BOQ (.pdf)",
        data=pdf_bytes,
        file_name=f"{quote_ref}_BOQ.pdf",
        mime="application/pdf",
        use_container_width=True,
    )
except Exception as e:                  # noqa: BLE001
    dl_cols[1].error(f"PDF export failed: {e}")

# Optional: export the raw BOQ JSON too (useful for downstream / research)
import json
dl_cols[2].download_button(
    label="📋  Raw BOQ (.json)",
    data=priced_boq.model_dump_json(indent=2).encode("utf-8"),
    file_name=f"{quote_ref}_BOQ.json",
    mime="application/json",
    use_container_width=True,
)

st.caption(
    f"Quote reference **{quote_ref}**  ·  valid until "
    f"{(datetime.utcnow() + timedelta(days=int(validity_days))):%Y-%m-%d}  ·  "
    "All deliverables include cover page, executive summary, 14-section schedule, "
    "compliance declaration, and acceptance / signature block."
)


# ─── Bottom navigation ──────────────────────────────────────────────

rule()
nav = st.columns([1, 1, 1])
with nav[0]:
    if st.button("←  Back to Extraction", use_container_width=True):
        st.switch_page("pages/2_Extraction.py")
with nav[2]:
    if st.button("🏠  Start a new project", use_container_width=True, type="primary"):
        for k in (
            "pdf_bytes", "dxf_bytes", "pdf_name", "dxf_name",
            "pdf_view", "dxf_view", "comparison",
            "project_name", "client_name", "consultant", "site_address",
            "project_meta",
        ):
            st.session_state.pop(k, None)
        st.switch_page("pages/0_Welcome.py")


footer()
