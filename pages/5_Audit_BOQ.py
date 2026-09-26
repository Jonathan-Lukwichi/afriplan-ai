"""
AfriPlan — Audit a BOQ.

Upload any priced BOQ workbook (a consultant's, a competitor's tender, your own)
and get every defect ranked by rand value at risk: arithmetic errors, priced lines
left out of totals, unpriced lines, duplicates, roll-up and contingency errors,
orphan sheets and feeders missing their companion items.

Consumes the read-only `audit` + `evaluation` layers only — never a pipeline.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pandas as pd
import streamlit as st

from audit.boq_rules import audit_reference
from audit.report import render_findings, summarise_findings
from evaluation.reference import parse_reference_xlsx
from ui.components import footer, page_header, rule
from ui.styles import inject_styles

inject_styles()

page_header(
    step="AUDIT",
    title="Audit a Bill of Quantities",
    subtitle=(
        "Upload a priced BOQ workbook (.xlsx). Every line is checked: arithmetic, "
        "priced lines missing from totals, unpriced items, duplicates, section roll-ups, "
        "contingency, sheets missing from the summary, and feeders without earth or "
        "terminations. Findings are ranked by the money at risk."
    ),
)


def _metric(label: str, value: str) -> str:
    return (f'<div class="afp-metric"><span class="afp-metric-label">{label}</span>'
            f'<span class="afp-metric-value">{value}</span></div>')


upl = st.file_uploader("Priced BOQ workbook", type=["xlsx"], key="audit_xlsx",
                       help="SA bill layout: a Summary sheet plus one sheet per building with "
                            "ITEM NO | DESCRIPTION | UOM | QTY | RATE | SUB TOTAL.")
if upl is None:
    st.info("Upload a BOQ workbook to audit it. Nothing is stored or sent anywhere.")
    footer()
    st.stop()

with tempfile.TemporaryDirectory() as tmp:
    path = Path(tmp) / "boq.xlsx"
    path.write_bytes(upl.getvalue())
    try:
        ref = parse_reference_xlsx(path, project=Path(upl.name).stem)
    except Exception as e:  # noqa: BLE001 — show, don't crash
        st.error(f"Could not read this workbook as a BOQ: {e}")
        footer()
        st.stop()

findings = audit_reference(ref)
summary = summarise_findings(findings)

rule()
m = st.columns(4)
m[0].markdown(_metric("Bills found", str(len(ref.buildings))), unsafe_allow_html=True)
m[1].markdown(_metric("Priced lines", f"{sum(len(b.lines) for b in ref.buildings):,}"), unsafe_allow_html=True)
m[2].markdown(_metric("Findings", f"{summary['count']} ({summary['high']} high)"), unsafe_allow_html=True)
m[3].markdown(_metric("Value at risk", f"R {summary['value_at_risk_zar']:,.0f}"), unsafe_allow_html=True)

if ref.summary_total_excl_vat:
    st.caption(f"Summary sheet total: R {ref.summary_total_excl_vat:,.2f} excl VAT · "
               f"{sum(1 for b in ref.buildings if b.in_summary)} bills rolled into the summary.")

if not findings:
    st.success("No defects found by the audit rules.")
else:
    st.markdown("**By rule**")
    st.dataframe(pd.DataFrame(summary["by_rule"], columns=["Rule", "Findings", "Value at risk (R)"]),
                 hide_index=True, use_container_width=True)
    st.markdown("**All findings** (highest severity and value first)")
    st.dataframe(pd.DataFrame([{
        "Severity": f.severity, "Rule": f.rule, "Bill": f.building, "Location": f.location,
        "Finding": f.message, "Value at risk (R)": round(f.value_at_risk_zar, 2),
        "Action": f.suggested_action,
    } for f in findings]), hide_index=True, use_container_width=True)

with st.expander("Bills read from the workbook"):
    st.dataframe(pd.DataFrame([{
        "Bill": b.name, "In summary": b.in_summary, "Lines": len(b.lines),
        "Stated total (R)": round(b.total_excl_vat, 2), "Sum of lines (R)": round(b.value, 2),
        "Errors": len(b.errors),
    } for b in ref.buildings]), hide_index=True, use_container_width=True)

st.download_button("📄  Download audit report (.md)",
                   data=render_findings(findings, f"BOQ audit — {upl.name}").encode("utf-8"),
                   file_name=f"{Path(upl.name).stem}_audit.md", mime="text/markdown")

footer()
