"""
PDF BOQ export — tender-grade, SANS 10142-1 compliant.

Pages:
  1.  Cover                     project + contractor + quote ref + valid until
  2.  Executive summary         section subtotals + grand totals
  3+. Bill of quantities        14 sections, items + rates + totals
  N-1. Compliance declaration   SANS / NRS / SANS 10400-XA references
  N.  Acceptance + signature    payment terms, validity, sign-off boxes
"""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta
from io import BytesIO
from typing import Optional

from fpdf import FPDF

from agent.shared import BillOfQuantities, BQSection, ContractorProfile, ProjectMetadata


# Brand RGB tuples
_INK = (15, 27, 61)
_BLUEPRINT = (30, 64, 175)
_INK_MUTED = (107, 114, 128)
_PAPER = (245, 242, 234)
_PAPER_DARK = (237, 234, 224)
_HAIRLINE = (220, 215, 200)


def _safe(s: str) -> str:
    """Replace Unicode characters that helvetica's latin-1 encoding can't render."""
    return (
        (s or "")
        .replace("—", "-").replace("–", "-")
        .replace("‘", "'").replace("’", "'")
        .replace("“", '"').replace("”", '"')
        .replace("…", "...")
        .replace("²", "2").replace("³", "3").replace("·", "-")
        .replace(" ", " ")
    )


class _BoqPdf(FPDF):
    """FPDF subclass with project header / contractor footer baked in."""

    project_name: str = ""
    contractor_name: str = ""
    quote_ref: str = ""

    def header(self):
        if self.page_no() == 1:
            return  # cover page — no page header
        self.set_font("helvetica", "B", 10)
        self.set_text_color(*_BLUEPRINT)
        self.cell(0, 6, _safe(self.project_name or "AfriPlan Bill of Quantities"),
                  new_x="LMARGIN", new_y="NEXT")
        self.set_font("helvetica", "", 8)
        self.set_text_color(*_INK_MUTED)
        self.cell(0, 4, _safe(f"Quote {self.quote_ref}"),
                  new_x="LMARGIN", new_y="NEXT")
        self.set_draw_color(*_HAIRLINE)
        self.set_line_width(0.3)
        self.line(10, self.get_y() + 0.5, 200, self.get_y() + 0.5)
        self.ln(4)

    def footer(self):
        if self.page_no() == 1:
            return
        self.set_y(-12)
        self.set_font("helvetica", "I", 8)
        self.set_text_color(*_INK_MUTED)
        self.cell(0, 4, _safe(self.contractor_name), align="L")
        self.set_y(-12)
        self.cell(0, 4, f"Page {self.page_no()}", align="R")


def export_boq_to_pdf(
    boq: BillOfQuantities,
    *,
    project: Optional[ProjectMetadata] = None,
    contractor: Optional[ContractorProfile] = None,
    quote_ref: Optional[str] = None,
    validity_days: int = 30,
) -> bytes:
    """Generate a tender-grade .pdf for the given BOQ."""
    project = project or ProjectMetadata(project_name=boq.project_name)
    contractor = contractor or ContractorProfile()
    issued = boq.generated_at
    valid_until = issued + timedelta(days=validity_days)
    quote_ref = quote_ref or f"AFP-{issued:%Y%m%d}-{boq.run_id[:6].upper()}"

    pdf = _BoqPdf(orientation="P", unit="mm", format="A4")
    pdf.project_name = project.project_name or boq.project_name
    pdf.contractor_name = contractor.company_name or "AfriPlan Electrical"
    pdf.quote_ref = quote_ref
    pdf.set_auto_page_break(auto=True, margin=18)

    _draw_cover(pdf, boq, project, contractor, quote_ref, issued, valid_until)
    _draw_executive_summary(pdf, boq)
    _draw_boq(pdf, boq)
    _draw_compliance(pdf, project)
    _draw_acceptance(pdf, boq, contractor, valid_until)

    out = pdf.output(dest="S")
    if isinstance(out, str):
        out = out.encode("latin-1")
    return bytes(out)


# ─── Cover page ──────────────────────────────────────────────────────

def _draw_cover(
    pdf: _BoqPdf,
    boq: BillOfQuantities,
    project: ProjectMetadata,
    contractor: ContractorProfile,
    quote_ref: str,
    issued: datetime,
    valid_until: datetime,
) -> None:
    pdf.add_page()

    # Top rule
    pdf.set_draw_color(*_INK)
    pdf.set_line_width(0.6)
    pdf.line(20, 20, 190, 20)

    # Eyebrow
    pdf.set_y(28)
    pdf.set_font("helvetica", "", 9)
    pdf.set_text_color(*_BLUEPRINT)
    pdf.cell(0, 5, "AFRIPLAN ELECTRICAL  -  TENDER DOCUMENT", new_x="LMARGIN", new_y="NEXT")

    # Big serif title
    pdf.set_y(40)
    pdf.set_font("times", "B", 32)
    pdf.set_text_color(*_INK)
    pdf.cell(0, 14, "Bill of Quantities", new_x="LMARGIN", new_y="NEXT")

    pdf.set_font("times", "I", 14)
    pdf.set_text_color(*_BLUEPRINT)
    pdf.cell(0, 8, "Electrical Installation",
             new_x="LMARGIN", new_y="NEXT")

    # Quote ref block (right side)
    pdf.set_xy(130, 28)
    pdf.set_font("helvetica", "", 8)
    pdf.set_text_color(*_INK_MUTED)
    pdf.cell(60, 4, "Quote reference", align="R", new_x="LEFT", new_y="NEXT")
    pdf.set_xy(130, 32)
    pdf.set_font("helvetica", "B", 12)
    pdf.set_text_color(*_INK)
    pdf.cell(60, 6, _safe(quote_ref), align="R", new_x="LEFT", new_y="NEXT")
    pdf.set_xy(130, 40)
    pdf.set_font("helvetica", "", 8)
    pdf.set_text_color(*_INK_MUTED)
    pdf.cell(60, 4, _safe(f"Issued {issued:%Y-%m-%d}"), align="R")
    pdf.set_xy(130, 44)
    pdf.cell(60, 4, _safe(f"Valid until {valid_until:%Y-%m-%d}"), align="R")

    # Mid rule
    pdf.set_y(80)
    pdf.set_draw_color(*_HAIRLINE)
    pdf.set_line_width(0.3)
    pdf.line(20, 80, 190, 80)

    # Project block
    pdf.set_y(86)
    _section_title(pdf, "PROJECT")
    _kv_row(pdf, "Project name",     project.project_name or boq.project_name or "-")
    _kv_row(pdf, "Client",           project.client_name or "-")
    _kv_row(pdf, "Consultant",       project.consultant_name or "-")
    _kv_row(pdf, "Site address",     project.site_address or "-")
    _kv_row(pdf, "Drawing standard", project.standard or "SANS 10142-1:2017")
    _kv_row(pdf, "Pipeline used",    boq.pipeline.upper())

    pdf.ln(6)

    # Contractor block
    _section_title(pdf, "CONTRACTOR")
    _kv_row(pdf, "Company",            contractor.company_name or "-")
    _kv_row(pdf, "ECSA / CIDB number", contractor.registration_number or "-")
    _kv_row(pdf, "Contact person",     contractor.contact_name or "-")
    _kv_row(pdf, "Phone",              contractor.contact_phone or "-")
    _kv_row(pdf, "Email",              contractor.contact_email or "-")
    _kv_row(pdf, "VAT number",         contractor.vat_number or "-")

    # Statement
    pdf.set_y(-50)
    pdf.set_font("helvetica", "I", 9)
    pdf.set_text_color(*_INK)
    pdf.multi_cell(
        0, 5,
        _safe(
            "This Bill of Quantities is issued in accordance with SANS 10142-1:2017 "
            "(Wiring of Premises) and is subject to the SA standard tender conditions. "
            "All electrical work shall be certified by issue of a Certificate of "
            "Compliance (COC) on completion."
        ),
    )

    # Bottom rule
    pdf.set_y(-22)
    pdf.set_draw_color(*_INK)
    pdf.set_line_width(0.6)
    pdf.line(20, pdf.get_y(), 190, pdf.get_y())
    pdf.set_y(-16)
    pdf.set_font("helvetica", "", 8)
    pdf.set_text_color(*_INK_MUTED)
    pdf.cell(0, 4, "AFRIPLAN ELECTRICAL  -  v6.1  -  SANS 10142-1:2017", align="C")


def _section_title(pdf: _BoqPdf, text: str) -> None:
    pdf.set_font("helvetica", "B", 10)
    pdf.set_text_color(*_BLUEPRINT)
    pdf.cell(0, 6, text, new_x="LMARGIN", new_y="NEXT")
    pdf.ln(1)


def _kv_row(pdf: _BoqPdf, label: str, value: str) -> None:
    pdf.set_font("helvetica", "B", 9)
    pdf.set_text_color(*_INK)
    pdf.cell(50, 5, _safe(label), new_x="RIGHT", new_y="TOP")
    pdf.set_font("helvetica", "", 9)
    pdf.cell(0, 5, _safe(value), new_x="LMARGIN", new_y="NEXT")


# ─── Executive summary ───────────────────────────────────────────────

def _draw_executive_summary(pdf: _BoqPdf, boq: BillOfQuantities) -> None:
    pdf.add_page()
    pdf.set_font("times", "B", 18)
    pdf.set_text_color(*_INK)
    pdf.cell(0, 10, "Executive Summary", new_x="LMARGIN", new_y="NEXT")
    pdf.set_draw_color(*_INK)
    pdf.set_line_width(0.5)
    pdf.line(10, pdf.get_y() + 1, 200, pdf.get_y() + 1)
    pdf.ln(8)

    # Section subtotals
    pdf.set_font("helvetica", "B", 9)
    pdf.set_fill_color(*_PAPER_DARK)
    pdf.cell(140, 6, "Section", border=1, fill=True)
    pdf.cell(40, 6, "Subtotal (R)", border=1, fill=True, align="R", new_x="LMARGIN", new_y="NEXT")

    pdf.set_font("helvetica", "", 9)
    by_section = boq.section_subtotals_zar
    for section_value, subtotal in sorted(
        by_section.items(),
        key=lambda kv: _section_number(kv[0]),
    ):
        pdf.cell(140, 6, _safe(section_value[:80]), border=1)
        pdf.cell(40, 6, f"R {subtotal:,.2f}", border=1, align="R", new_x="LMARGIN", new_y="NEXT")

    pdf.ln(8)

    # Totals block
    _total_row(pdf, "Subtotal", boq.subtotal_zar)
    _total_row(pdf, f"Contingency ({boq.contingency_pct}%)", boq.contingency_zar)
    _total_row(pdf, f"Markup ({boq.contractor_markup_pct}%)", boq.markup_zar)
    _total_row(pdf, "Total excluding VAT", boq.total_excl_vat_zar, heavy=True)
    _total_row(pdf, f"VAT ({boq.vat_pct}%)", boq.vat_zar)
    _total_row(pdf, "TOTAL INCLUDING VAT", boq.total_incl_vat_zar, big=True)


def _section_number(section_value: str) -> int:
    try:
        return int(section_value.split(":", 1)[0].replace("SECTION", "").strip())
    except (ValueError, IndexError):
        return 99


def _total_row(pdf: _BoqPdf, label: str, value: float, *, heavy: bool = False, big: bool = False) -> None:
    if big:
        pdf.set_font("times", "B", 14)
        pdf.set_text_color(*_BLUEPRINT)
    elif heavy:
        pdf.set_font("helvetica", "B", 11)
        pdf.set_text_color(*_INK)
    else:
        pdf.set_font("helvetica", "", 10)
        pdf.set_text_color(*_INK)

    pdf.cell(140, 7 if big else 6, _safe(label), align="R")
    pdf.cell(40, 7 if big else 6, f"R {value:,.2f}", align="R", new_x="LMARGIN", new_y="NEXT")

    if big or heavy:
        pdf.set_draw_color(*_INK if big else _HAIRLINE)
        pdf.set_line_width(0.5 if big else 0.3)
        y = pdf.get_y()
        pdf.line(10, y, 200, y)


# ─── BoQ pages ───────────────────────────────────────────────────────

def _draw_boq(pdf: _BoqPdf, boq: BillOfQuantities) -> None:
    pdf.add_page()
    pdf.set_font("times", "B", 18)
    pdf.set_text_color(*_INK)
    pdf.cell(0, 10, "Bill of Quantities", new_x="LMARGIN", new_y="NEXT")
    pdf.set_draw_color(*_INK)
    pdf.set_line_width(0.5)
    pdf.line(10, pdf.get_y() + 1, 200, pdf.get_y() + 1)
    pdf.ln(6)

    by_section: dict[BQSection, list] = defaultdict(list)
    for it in boq.line_items:
        by_section[it.section].append(it)

    widths = [16, 86, 14, 16, 24, 24]   # item / desc / unit / qty / rate / total

    for section in sorted(by_section.keys(), key=lambda s: s.section_number):
        # Section header
        pdf.set_fill_color(*_INK)
        pdf.set_text_color(*_PAPER)
        pdf.set_font("helvetica", "B", 10)
        pdf.cell(0, 7, _safe(section.value), border=0, fill=True,
                 new_x="LMARGIN", new_y="NEXT")
        pdf.set_text_color(*_INK)

        # Column headers
        pdf.set_fill_color(*_PAPER_DARK)
        pdf.set_font("helvetica", "B", 9)
        for w, h in zip(widths, ["#", "Description", "Unit", "Qty", "Rate (R)", "Total (R)"]):
            pdf.cell(w, 6, h, border=1, fill=True, align="C")
        pdf.ln(6)

        pdf.set_font("helvetica", "", 9)
        section_total = 0.0
        for it in by_section[section]:
            pdf.cell(widths[0], 6, it.item_number_str, border=1, align="C")
            pdf.cell(widths[1], 6, _safe(_truncate(it.description, 60)), border=1)
            pdf.cell(widths[2], 6, _safe(it.unit), border=1, align="C")
            pdf.cell(widths[3], 6, _fmt_num(it.qty), border=1, align="R")
            pdf.cell(widths[4], 6, f"{it.unit_price_zar:,.2f}", border=1, align="R")
            pdf.cell(widths[5], 6, f"{it.total_zar:,.2f}", border=1, align="R")
            pdf.ln(6)
            section_total += it.total_zar

        # Section subtotal
        pdf.set_font("helvetica", "B", 9)
        pdf.set_fill_color(*_PAPER_DARK)
        pdf.cell(sum(widths[:5]), 6, "Section subtotal", border=1, align="R", fill=True)
        pdf.cell(widths[5], 6, f"{section_total:,.2f}", border=1, align="R", fill=True)
        pdf.ln(10)

    # Grand totals at the end
    _total_row(pdf, "Subtotal", boq.subtotal_zar)
    _total_row(pdf, f"Contingency ({boq.contingency_pct}%)", boq.contingency_zar)
    _total_row(pdf, f"Markup ({boq.contractor_markup_pct}%)", boq.markup_zar)
    _total_row(pdf, "Total excluding VAT", boq.total_excl_vat_zar, heavy=True)
    _total_row(pdf, f"VAT ({boq.vat_pct}%)", boq.vat_zar)
    _total_row(pdf, "TOTAL INCLUDING VAT", boq.total_incl_vat_zar, big=True)


def _truncate(s: str, n: int) -> str:
    s = (s or "").strip()
    return s if len(s) <= n else s[: n - 1] + "..."


def _fmt_num(x: float) -> str:
    return f"{int(x)}" if x == int(x) else f"{x:.2f}"


# ─── Compliance page ─────────────────────────────────────────────────

def _draw_compliance(pdf: _BoqPdf, project: ProjectMetadata) -> None:
    pdf.add_page()
    pdf.set_font("times", "B", 18)
    pdf.set_text_color(*_INK)
    pdf.cell(0, 10, "Compliance & Standards", new_x="LMARGIN", new_y="NEXT")
    pdf.set_draw_color(*_INK)
    pdf.set_line_width(0.5)
    pdf.line(10, pdf.get_y() + 1, 200, pdf.get_y() + 1)
    pdf.ln(8)

    standards = [
        ("SANS 10142-1:2017",
         "Wiring of premises - Low-voltage installations. The master code for "
         "all installations under 1000 V AC."),
        ("NRS 034",
         "After Diversity Maximum Demand for residential installations. Drives "
         "supply sizing and ADMD-based load calculations."),
        ("SANS 10400-XA",
         "Energy efficiency in buildings. Sets lighting power density caps "
         "(LPD W/m2) by occupancy class."),
        ("SANS 10139",
         "Fire detection and alarm systems for buildings. Applies wherever the "
         "BOQ includes fire detection or evacuation systems."),
        ("ECSA / OHS Act",
         "All electrical work to be carried out under the supervision of a "
         "registered Electrician and certified by COC on completion."),
    ]

    pdf.set_fill_color(*_PAPER_DARK)
    pdf.set_font("helvetica", "B", 9)
    pdf.cell(50, 6, "Standard", border=1, fill=True)
    pdf.cell(140, 6, "Application", border=1, fill=True, new_x="LMARGIN", new_y="NEXT")

    for std, desc in standards:
        x_start = pdf.get_x()
        y_start = pdf.get_y()
        pdf.set_font("helvetica", "B", 9)
        pdf.set_text_color(*_INK)
        pdf.multi_cell(50, 6, _safe(std), border=1)
        end_y = pdf.get_y()
        pdf.set_xy(x_start + 50, y_start)
        pdf.set_font("helvetica", "", 9)
        pdf.multi_cell(140, 6, _safe(desc), border=1)
        new_y = max(pdf.get_y(), end_y)
        pdf.set_y(new_y)

    pdf.ln(6)
    pdf.set_font("helvetica", "I", 10)
    pdf.set_text_color(*_INK)
    pdf.multi_cell(
        0, 5,
        _safe(
            "The undersigned contractor warrants that all electrical work supplied "
            "and installed under this Bill of Quantities will comply with SANS "
            "10142-1:2017 in all material respects, and that a Certificate of "
            "Compliance (COC) will be issued on completion of the works."
        ),
    )


# ─── Acceptance + signature ──────────────────────────────────────────

def _draw_acceptance(
    pdf: _BoqPdf,
    boq: BillOfQuantities,
    contractor: ContractorProfile,
    valid_until: datetime,
) -> None:
    pdf.add_page()
    pdf.set_font("times", "B", 18)
    pdf.set_text_color(*_INK)
    pdf.cell(0, 10, "Acceptance & Payment", new_x="LMARGIN", new_y="NEXT")
    pdf.set_draw_color(*_INK)
    pdf.set_line_width(0.5)
    pdf.line(10, pdf.get_y() + 1, 200, pdf.get_y() + 1)
    pdf.ln(8)

    # Key terms
    _kv_row(pdf, "Quotation valid until", valid_until.strftime("%Y-%m-%d"))
    _kv_row(pdf, "Payment terms",
            _payment_terms_explanation(contractor.payment_terms))
    pdf.set_font("helvetica", "B", 10)
    pdf.cell(50, 6, "Total payable (incl VAT)", new_x="RIGHT", new_y="TOP")
    pdf.set_font("times", "B", 14)
    pdf.set_text_color(*_BLUEPRINT)
    pdf.cell(0, 6, f"R {boq.total_incl_vat_zar:,.2f}", new_x="LMARGIN", new_y="NEXT")
    pdf.set_text_color(*_INK)
    pdf.ln(8)

    # Signature blocks (two columns)
    col_w = 90
    left_x = 10
    right_x = 110
    y = pdf.get_y() + 4

    pdf.set_xy(left_x, y)
    pdf.set_font("helvetica", "B", 11)
    pdf.set_text_color(*_INK)
    pdf.cell(col_w, 6, "ACCEPTED BY CLIENT")
    pdf.set_xy(right_x, y)
    pdf.cell(col_w, 6, "ISSUED BY CONTRACTOR", new_x="LMARGIN", new_y="NEXT")

    for label in ("Name", "Signature", "Date", "Company"):
        y = pdf.get_y() + 4
        pdf.set_xy(left_x, y)
        pdf.set_font("helvetica", "B", 9)
        pdf.cell(20, 6, label + ":")
        pdf.set_draw_color(*_HAIRLINE)
        pdf.set_line_width(0.3)
        pdf.line(left_x + 22, y + 6, left_x + col_w - 4, y + 6)

        pdf.set_xy(right_x, y)
        pdf.cell(20, 6, label + ":")
        if label == "Company" and contractor.company_name:
            pdf.set_font("helvetica", "I", 9)
            pdf.set_text_color(*_INK_MUTED)
            pdf.cell(0, 6, " " + _safe(contractor.company_name), new_x="LMARGIN", new_y="NEXT")
            pdf.set_text_color(*_INK)
        else:
            pdf.line(right_x + 22, y + 6, right_x + col_w - 4, y + 6)
            pdf.ln(8)


def _payment_terms_explanation(terms: str) -> str:
    explanations = {
        "40/40/20": "40% deposit on order  ·  40% on materials delivery  ·  20% on completion",
        "50/30/20": "50% deposit on order  ·  30% on materials delivery  ·  20% on completion",
        "30/30/30/10": "30% deposit  ·  30% mid-progress  ·  30% on commissioning  ·  10% on COC",
    }
    return explanations.get(terms, terms or "Per separate agreement")
