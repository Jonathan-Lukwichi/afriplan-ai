"""
PDF export for v6.1 — takes a BillOfQuantities, emits a one-shot
quotation PDF.
"""

from __future__ import annotations

from collections import defaultdict
from io import BytesIO

from fpdf import FPDF

from agent.shared import BillOfQuantities, BQSection


_BRAND = (0, 212, 255)


class _BoqPdf(FPDF):
    def header(self):
        self.set_font("helvetica", "B", 16)
        self.set_text_color(*_BRAND)
        self.cell(0, 10, "AfriPlan Electrical - Bill of Quantities", new_x="LMARGIN", new_y="NEXT")
        self.set_text_color(0, 0, 0)
        self.set_font("helvetica", "", 10)
        self.set_draw_color(*_BRAND)
        self.set_line_width(0.6)
        self.line(10, self.get_y() + 1, 200, self.get_y() + 1)
        self.ln(5)

    def footer(self):
        self.set_y(-12)
        self.set_font("helvetica", "I", 8)
        self.set_text_color(120, 120, 120)
        self.cell(0, 8, f"Page {self.page_no()}", align="C")


def _safe(s: str) -> str:
    """Replace common Unicode characters that helvetica/latin-1 can't render."""
    return (
        s.replace("—", "-")    # em dash
         .replace("–", "-")    # en dash
         .replace("‘", "'").replace("’", "'")
         .replace("“", '"').replace("”", '"')
         .replace("…", "...")
         .replace(" ", " ")
    )


def export_boq_to_pdf(boq: BillOfQuantities) -> bytes:
    pdf = _BoqPdf(orientation="P", unit="mm", format="A4")
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    # ── Project block ───────────────────────────────────────────
    pdf.set_font("helvetica", "B", 11)
    pdf.cell(0, 6, _safe(f"Project: {boq.project_name}"), new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("helvetica", "", 10)
    pdf.cell(0, 5, f"Pipeline: {boq.pipeline.upper()}    Run ID: {boq.run_id}",
             new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 5, f"Generated: {boq.generated_at.strftime('%Y-%m-%d %H:%M UTC')}",
             new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)

    # ── BoQ table per section ───────────────────────────────────
    by_section: dict[BQSection, list] = defaultdict(list)
    for it in boq.line_items:
        by_section[it.section].append(it)

    for section in sorted(by_section.keys(), key=lambda s: s.section_number):
        pdf.set_fill_color(15, 23, 42)
        pdf.set_text_color(*_BRAND)
        pdf.set_font("helvetica", "B", 10)
        pdf.cell(0, 7, _safe(section.value), new_x="LMARGIN", new_y="NEXT", fill=True)
        pdf.set_text_color(0, 0, 0)

        # Column widths (mm): item | desc | unit | qty | rate | total
        widths = [16, 86, 14, 16, 24, 24]
        pdf.set_fill_color(220, 240, 250)
        pdf.set_font("helvetica", "B", 9)
        for w, h in zip(widths, ["#", "Description", "Unit", "Qty", "Rate (R)", "Total (R)"]):
            pdf.cell(w, 6, h, border=1, fill=True, align="C")
        pdf.ln(6)

        pdf.set_font("helvetica", "", 9)
        section_total = 0.0
        for it in by_section[section]:
            pdf.cell(widths[0], 6, it.item_number_str, border=1)
            pdf.cell(widths[1], 6, _safe(_truncate(it.description, 60)), border=1)
            pdf.cell(widths[2], 6, it.unit, border=1, align="C")
            pdf.cell(widths[3], 6, _fmt(it.qty), border=1, align="R")
            pdf.cell(widths[4], 6, f"{it.unit_price_zar:,.2f}", border=1, align="R")
            pdf.cell(widths[5], 6, f"{it.total_zar:,.2f}", border=1, align="R")
            pdf.ln(6)
            section_total += it.total_zar

        pdf.set_font("helvetica", "B", 9)
        pdf.cell(sum(widths[:5]), 6, "Section subtotal", border=1, align="R")
        pdf.cell(widths[5], 6, f"{section_total:,.2f}", border=1, align="R")
        pdf.ln(8)

    # ── Totals block ────────────────────────────────────────────
    pdf.ln(2)
    pdf.set_font("helvetica", "B", 11)
    for label, value in [
        ("Subtotal",                    boq.subtotal_zar),
        (f"Contingency ({boq.contingency_pct}%)", boq.contingency_zar),
        (f"Markup ({boq.contractor_markup_pct}%)", boq.markup_zar),
        ("Total excl VAT",              boq.total_excl_vat_zar),
        (f"VAT ({boq.vat_pct}%)",       boq.vat_zar),
        ("Total incl VAT",              boq.total_incl_vat_zar),
    ]:
        pdf.cell(140, 7, label, align="R")
        pdf.cell(40, 7, f"R {value:,.2f}", align="R", new_x="LMARGIN", new_y="NEXT")

    out = pdf.output(dest="S")
    if isinstance(out, str):
        out = out.encode("latin-1")
    return bytes(out)


def _truncate(s: str, n: int) -> str:
    s = s.strip()
    return s if len(s) <= n else s[: n - 1] + "..."


def _fmt(x: float) -> str:
    if x == int(x):
        return f"{int(x)}"
    return f"{x:.2f}"
