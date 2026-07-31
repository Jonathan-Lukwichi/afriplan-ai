"""
Export a PipelineComparison to a PDF report.

The original app's render_comparison_panel() (Streamlit UI) is discarded
here per plan — the React ComparisonPanel component replaces it. This file
keeps only the pure, framework-independent PDF export.
"""

from __future__ import annotations

from agent.comparison.models import PipelineComparison


def _safe(s: str) -> str:
    return (
        s.replace("—", "-").replace("–", "-")
         .replace("…", "...")
         .replace("'", "'").replace("'", "'")
         .replace(""", '"').replace(""", '"')
    )


def export_comparison_to_pdf(cmp: PipelineComparison) -> bytes:
    from fpdf import FPDF

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
