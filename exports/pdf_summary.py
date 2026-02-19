"""
AfriPlan Electrical v4.1 - PDF Summary Export

Generates professional PDF quotation summary using fpdf2.
"""

import io
from typing import Optional, Dict, Any
from datetime import datetime

try:
    from fpdf import FPDF
    HAS_FPDF = True
except ImportError:
    FPDF = object  # Placeholder so class definition doesn't fail
    HAS_FPDF = False

from agent.models import (
    PricingResult, ExtractionResult, ValidationResult,
    ContractorProfile, ServiceTier
)


class QuotationPDF(FPDF):  # type: ignore
    """Custom PDF class for quotation documents."""

    def __init__(self, contractor: Optional[ContractorProfile] = None):
        super().__init__()
        self.contractor = contractor

    def header(self):
        # Logo/Company name
        self.set_font("Helvetica", "B", 20)
        self.set_text_color(0, 212, 255)  # Cyan

        if self.contractor and self.contractor.company_name:
            self.cell(0, 10, self.contractor.company_name, align="L")
        else:
            self.cell(0, 10, "ELECTRICAL QUOTATION", align="L")

        self.ln(8)
        self.set_font("Helvetica", "", 9)
        self.set_text_color(100, 100, 100)

        if self.contractor:
            if self.contractor.physical_address:
                self.cell(0, 4, self.contractor.physical_address, align="L")
                self.ln(4)
            if self.contractor.contact_phone:
                self.cell(0, 4, f"Tel: {self.contractor.contact_phone}", align="L")
                self.ln(4)
            if self.contractor.contact_email:
                self.cell(0, 4, f"Email: {self.contractor.contact_email}", align="L")
                self.ln(4)
            if self.contractor.registration_number:
                self.cell(0, 4, f"Reg: {self.contractor.registration_number}", align="L")
                self.ln(4)

        self.ln(5)
        self.set_draw_color(0, 212, 255)
        self.line(10, self.get_y(), 200, self.get_y())
        self.ln(5)

    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(128, 128, 128)
        self.cell(0, 10, f"Page {self.page_no()}/{{nb}}", align="C")


def generate_pdf_summary(
    pricing: PricingResult,
    extraction: ExtractionResult,
    validation: Optional[ValidationResult] = None,
    project_name: str = "Project",
    tier: ServiceTier = ServiceTier.COMMERCIAL,
    contractor: Optional[ContractorProfile] = None,
) -> bytes:
    """
    Generate PDF quotation summary.

    Args:
        pricing: PricingResult with BQ data
        extraction: ExtractionResult with project details
        validation: ValidationResult with compliance data
        project_name: Project name
        tier: Service tier
        contractor: Contractor profile

    Returns:
        PDF file as bytes
    """
    if not HAS_FPDF:
        raise ImportError("fpdf2 is required for PDF generation")

    pdf = QuotationPDF(contractor)
    pdf.alias_nb_pages()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)

    # Title
    pdf.set_font("Helvetica", "B", 16)
    pdf.set_text_color(0, 0, 0)
    pdf.cell(0, 10, "ELECTRICAL INSTALLATION QUOTATION", align="C")
    pdf.ln(15)

    # Project Details
    _add_section_header(pdf, "PROJECT DETAILS")

    pdf.set_font("Helvetica", "", 10)
    details = [
        ("Project Name:", project_name),
        ("Date:", datetime.now().strftime("%Y-%m-%d")),
        ("Reference:", f"AP-{datetime.now().strftime('%Y%m%d%H%M')}"),
        ("Project Type:", tier.value.title()),
        ("Validity:", "30 days from date of quotation"),
    ]

    for label, value in details:
        pdf.set_font("Helvetica", "B", 10)
        pdf.cell(50, 6, label)
        pdf.set_font("Helvetica", "", 10)
        pdf.cell(0, 6, str(value))
        pdf.ln(6)

    pdf.ln(5)

    # Scope Summary
    _add_section_header(pdf, "SCOPE SUMMARY")

    pdf.set_font("Helvetica", "", 10)
    scope_items = [
        f"Building blocks: {len(extraction.building_blocks)}",
        f"Distribution boards: {extraction.total_dbs}",
        f"Circuits: {extraction.total_circuits}",
        f"Electrical points: {extraction.total_points}",
        f"Site cable runs: {len(extraction.site_cable_runs)}",
    ]

    for item in scope_items:
        pdf.cell(5, 6, chr(149))  # Bullet
        pdf.cell(0, 6, item)
        pdf.ln(6)

    pdf.ln(5)

    # Compliance
    if validation:
        _add_section_header(pdf, "COMPLIANCE STATUS")

        pdf.set_font("Helvetica", "", 10)
        score = validation.compliance_score
        if score >= 90:
            pdf.set_text_color(34, 197, 94)  # Green
            status = "COMPLIANT"
        elif score >= 70:
            pdf.set_text_color(245, 158, 11)  # Amber
            status = "REQUIRES ATTENTION"
        else:
            pdf.set_text_color(239, 68, 68)  # Red
            status = "NON-COMPLIANT"

        pdf.cell(0, 6, f"Compliance Score: {score:.0f}% - {status}")
        pdf.set_text_color(0, 0, 0)
        pdf.ln(6)

        if validation.auto_corrections > 0:
            pdf.cell(0, 6, f"Auto-corrections applied: {validation.auto_corrections}")
            pdf.ln(6)

        pdf.ln(5)

    # Pricing Summary
    _add_section_header(pdf, "ESTIMATED PRICING SUMMARY")

    pdf.set_font("Helvetica", "I", 9)
    pdf.set_text_color(128, 128, 128)
    pdf.cell(0, 5, "Note: Prices are estimates only. Final quotation subject to site survey.")
    pdf.set_text_color(0, 0, 0)
    pdf.ln(8)

    # Pricing table
    pdf.set_font("Helvetica", "", 10)
    pricing_rows = [
        ("Materials subtotal:", f"R {pricing.estimate_subtotal_zar:,.2f}"),
        ("Contingency (5%):", f"R {pricing.estimate_contingency_zar:,.2f}"),
        ("Contractor margin:", f"R {pricing.estimate_margin_zar:,.2f}"),
        ("Total excl VAT:", f"R {pricing.estimate_total_excl_vat_zar:,.2f}"),
        ("VAT (15%):", f"R {pricing.estimate_vat_zar:,.2f}"),
    ]

    for label, value in pricing_rows:
        pdf.cell(100, 7, label)
        pdf.cell(0, 7, value, align="R")
        pdf.ln(7)

    # Total
    pdf.set_draw_color(0, 212, 255)
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(2)

    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(100, 10, "ESTIMATED TOTAL (incl VAT):")
    pdf.cell(0, 10, f"R {pricing.estimate_total_incl_vat_zar:,.2f}", align="R")
    pdf.ln(12)

    # Payment Terms
    _add_section_header(pdf, "PAYMENT TERMS")

    pdf.set_font("Helvetica", "", 10)
    payment_rows = [
        ("Deposit (40%):", f"R {pricing.deposit_zar:,.2f}", "On acceptance"),
        ("Progress (40%):", f"R {pricing.second_payment_zar:,.2f}", "On 50% completion"),
        ("Final (20%):", f"R {pricing.final_payment_zar:,.2f}", "On completion + COC"),
    ]

    for label, amount, timing in payment_rows:
        pdf.cell(50, 6, label)
        pdf.cell(50, 6, amount)
        pdf.cell(0, 6, timing)
        pdf.ln(6)

    pdf.ln(5)

    # Terms & Conditions
    _add_section_header(pdf, "TERMS & CONDITIONS")

    pdf.set_font("Helvetica", "", 9)
    terms = [
        "Quotation valid for 30 days from date of issue",
        "Prices exclude any additional work not specified",
        "Certificate of Compliance (COC) included",
        "All work to SANS 10142-1:2017 standards",
        "12-month workmanship warranty",
        "Material prices subject to supplier availability",
    ]

    for term in terms:
        pdf.cell(5, 5, chr(149))
        pdf.cell(0, 5, term)
        pdf.ln(5)

    # Signature block
    pdf.ln(10)
    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(0, 6, "ACCEPTANCE")
    pdf.ln(8)

    pdf.set_font("Helvetica", "", 10)
    pdf.cell(90, 6, "Client Signature: _____________________")
    pdf.cell(0, 6, "Date: _____________________")
    pdf.ln(10)
    pdf.cell(90, 6, "Contractor Signature: _________________")
    pdf.cell(0, 6, "Date: _____________________")

    # Footer note
    pdf.ln(15)
    pdf.set_font("Helvetica", "I", 8)
    pdf.set_text_color(128, 128, 128)
    pdf.multi_cell(0, 4,
        "This quotation was generated using AfriPlan Electrical v4.1. "
        "Quantities extracted from drawings provided. Final pricing subject to site survey."
    )

    # Output to bytes
    output = io.BytesIO()
    pdf.output(output)
    output.seek(0)
    return output.getvalue()


def _add_section_header(pdf: FPDF, title: str) -> None:
    """Add a section header to the PDF."""
    pdf.set_font("Helvetica", "B", 11)
    pdf.set_fill_color(31, 41, 55)  # Dark gray
    pdf.set_text_color(255, 255, 255)
    pdf.cell(0, 8, f"  {title}", fill=True)
    pdf.set_text_color(0, 0, 0)
    pdf.ln(10)
