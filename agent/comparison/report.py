"""
Render a PipelineComparison in two ways:

  - render_comparison_panel(cmp)   → Streamlit UI (called by pages/1_Upload.py)
  - export_comparison_to_pdf(cmp)  → bytes (.pdf)

Both are read-only.
"""

from __future__ import annotations

from io import BytesIO

from fpdf import FPDF

from agent.comparison.models import PipelineComparison


# ─── Streamlit panel ──────────────────────────────────────────────────

def render_comparison_panel(cmp: PipelineComparison) -> None:
    import streamlit as st

    st.markdown('<div class="afp-comparison">', unsafe_allow_html=True)

    cols = st.columns(4)
    cols[0].metric(
        "Total difference",
        f"{(cmp.total_difference_pct or 0)*100:.1f}%" if cmp.total_difference_pct is not None else "—",
    )
    cols[1].metric("Agreement score", f"{cmp.agreement_score*100:.0f}%")

    if cmp.winner_vs_baseline and cmp.winner_vs_baseline != "no_baseline":
        winner = cmp.winner_vs_baseline.upper()
        if cmp.winner_vs_baseline == "pdf" and cmp.pdf_vs_baseline_mape is not None:
            cols[2].metric("Winner vs baseline", winner, f"MAPE {cmp.pdf_vs_baseline_mape*100:.1f}%")
        elif cmp.winner_vs_baseline == "dxf" and cmp.dxf_vs_baseline_mape is not None:
            cols[2].metric("Winner vs baseline", winner, f"MAPE {cmp.dxf_vs_baseline_mape*100:.1f}%")
        else:
            cols[2].metric("Winner vs baseline", winner)
    cols[3].metric("PDF cost", f"R {cmp.pdf_cost_zar:.2f}")

    st.markdown(
        f"**PDF total ex VAT:** R {cmp.pdf_total_excl_vat:,.2f}  &nbsp;|&nbsp;  "
        f"**DXF total ex VAT:** R {cmp.dxf_total_excl_vat:,.2f}",
        unsafe_allow_html=True,
    )

    with st.expander("📊 Section-by-section breakdown", expanded=True):
        rows = []
        for section, agg in sorted(cmp.section_agreements.items()):
            delta_pct = f"{agg.delta_pct*100:+.1f}%" if agg.delta_pct is not None else "—"
            rows.append(
                {
                    "Section": section,
                    "PDF (R)": round(agg.pdf_subtotal, 2),
                    "DXF (R)": round(agg.dxf_subtotal, 2),
                    "Δ (R)":   round(agg.delta_zar, 2),
                    "Δ %":     delta_pct,
                    "Both":    agg.items_in_both,
                    "PDF only": len(agg.items_only_in_pdf),
                    "DXF only": len(agg.items_only_in_dxf),
                }
            )
        if rows:
            st.dataframe(rows, use_container_width=True)
        else:
            st.info("No overlapping sections.")

    pdf_only_items = [
        f"{s}: {it}"
        for s, agg in cmp.section_agreements.items()
        for it in agg.items_only_in_pdf
    ]
    dxf_only_items = [
        f"{s}: {it}"
        for s, agg in cmp.section_agreements.items()
        for it in agg.items_only_in_dxf
    ]

    if pdf_only_items or dxf_only_items:
        with st.expander("🔍 Items only in one pipeline"):
            cols = st.columns(2)
            with cols[0]:
                st.markdown(f"**Only in PDF ({len(pdf_only_items)})**")
                for it in pdf_only_items[:50]:
                    st.write(f"• {it}")
                if len(pdf_only_items) > 50:
                    st.caption(f"… {len(pdf_only_items) - 50} more")
            with cols[1]:
                st.markdown(f"**Only in DXF ({len(dxf_only_items)})**")
                for it in dxf_only_items[:50]:
                    st.write(f"• {it}")
                if len(dxf_only_items) > 50:
                    st.caption(f"… {len(dxf_only_items) - 50} more")

    # Download buttons
    cols = st.columns(2)
    cols[0].download_button(
        label="📥 Comparison JSON",
        data=cmp.model_dump_json(indent=2).encode("utf-8"),
        file_name="comparison.json",
        mime="application/json",
    )
    try:
        pdf_bytes = export_comparison_to_pdf(cmp)
        cols[1].download_button(
            label="📥 Comparison Report (PDF)",
            data=pdf_bytes,
            file_name="comparison_report.pdf",
            mime="application/pdf",
        )
    except Exception as e:                  # noqa: BLE001
        cols[1].caption(f"PDF export unavailable: {e}")

    st.markdown("</div>", unsafe_allow_html=True)


# ─── PDF export ───────────────────────────────────────────────────────

def _safe(s: str) -> str:
    return (
        s.replace("—", "-").replace("–", "-")
         .replace("…", "...")
         .replace("‘", "'").replace("’", "'")
         .replace("“", '"').replace("”", '"')
    )


class _ComparisonPdf(FPDF):
    def header(self):
        self.set_font("helvetica", "B", 14)
        self.set_text_color(0, 153, 255)
        self.cell(0, 10, "AfriPlan - Cross-Pipeline Comparison",
                  new_x="LMARGIN", new_y="NEXT")
        self.set_text_color(0, 0, 0)
        self.set_draw_color(0, 153, 255)
        self.line(10, self.get_y() + 1, 200, self.get_y() + 1)
        self.ln(4)


def export_comparison_to_pdf(cmp: PipelineComparison) -> bytes:
    pdf = _ComparisonPdf(orientation="P", unit="mm", format="A4")
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_font("helvetica", "", 10)

    pdf.cell(0, 6, _safe(f"Project: {cmp.project_name}"), new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 5, _safe(f"PDF run: {cmp.pdf_run_id}     DXF run: {cmp.dxf_run_id}"),
             new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 5, _safe(f"Generated: {cmp.generated_at:%Y-%m-%d %H:%M UTC}"),
             new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)

    pdf.set_font("helvetica", "B", 11)
    pdf.cell(0, 6, "Summary", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("helvetica", "", 10)
    diff = f"{(cmp.total_difference_pct or 0)*100:.1f}%" if cmp.total_difference_pct is not None else "n/a"
    pdf.cell(0, 5, _safe(f"PDF total ex VAT:  R {cmp.pdf_total_excl_vat:,.2f}"), new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 5, _safe(f"DXF total ex VAT:  R {cmp.dxf_total_excl_vat:,.2f}"), new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 5, _safe(f"Total difference:  {diff}"), new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 5, _safe(f"Agreement score:   {cmp.agreement_score*100:.0f}%"), new_x="LMARGIN", new_y="NEXT")
    if cmp.winner_vs_baseline:
        pdf.cell(0, 5, _safe(f"Winner vs baseline: {cmp.winner_vs_baseline.upper()}"),
                 new_x="LMARGIN", new_y="NEXT")
    pdf.ln(3)

    # Section table
    pdf.set_font("helvetica", "B", 10)
    pdf.set_fill_color(220, 240, 250)
    widths = [70, 28, 28, 22, 22]
    for w, h in zip(widths, ["Section", "PDF (R)", "DXF (R)", "Delta R", "Delta %"]):
        pdf.cell(w, 6, h, border=1, fill=True, align="C")
    pdf.ln(6)

    pdf.set_font("helvetica", "", 9)
    for section, agg in sorted(cmp.section_agreements.items()):
        delta_pct = f"{agg.delta_pct*100:+.1f}%" if agg.delta_pct is not None else "-"
        pdf.cell(widths[0], 6, _safe(section[:50]), border=1)
        pdf.cell(widths[1], 6, f"{agg.pdf_subtotal:,.0f}", border=1, align="R")
        pdf.cell(widths[2], 6, f"{agg.dxf_subtotal:,.0f}", border=1, align="R")
        pdf.cell(widths[3], 6, f"{agg.delta_zar:,.0f}", border=1, align="R")
        pdf.cell(widths[4], 6, delta_pct, border=1, align="R")
        pdf.ln(6)

    out = pdf.output(dest="S")
    if isinstance(out, str):
        out = out.encode("latin-1")
    return bytes(out)
