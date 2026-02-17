"""
AfriPlan Electrical v4.1 — Excel BQ Export

v4.1 Critical Feature: Dual BQ export
- Quantity-only BQ (primary deliverable): Descriptions + quantities, prices empty
- Estimated BQ (reference): Same items with default prices filled in
"""

import io
from typing import List, Optional, Dict, Any
from datetime import datetime

try:
    from openpyxl import Workbook
    from openpyxl.styles import Font, Alignment, Border, Side, PatternFill, NamedStyle
    from openpyxl.utils import get_column_letter
    HAS_OPENPYXL = True
except ImportError:
    HAS_OPENPYXL = False

from agent.models import (
    PricingResult, BQLineItem, BQSection, ContractorProfile,
    ExtractionResult, ItemConfidence
)


# Brand colors
BRAND_CYAN = "00D4FF"
BRAND_DARK = "0A0E1A"
HEADER_GRAY = "1F2937"
SECTION_GRAY = "374151"


def export_quantity_bq(
    pricing: PricingResult,
    project_name: str = "Project",
    contractor: Optional[ContractorProfile] = None,
) -> bytes:
    """
    Export quantity-only BQ to Excel.

    This is the PRIMARY deliverable — quantities only, no prices.
    Contractor fills in their own prices.

    Args:
        pricing: PricingResult with quantity_bq
        project_name: Project name for header
        contractor: Contractor profile for letterhead

    Returns:
        Excel file as bytes
    """
    if not HAS_OPENPYXL:
        raise ImportError("openpyxl is required for Excel export")

    wb = Workbook()
    ws = wb.active
    ws.title = "Bill of Quantities"

    # Setup styles
    _setup_styles(wb)

    # Header
    row = 1
    ws.merge_cells(f"A{row}:F{row}")
    ws[f"A{row}"] = "BILL OF QUANTITIES — ELECTRICAL INSTALLATION"
    ws[f"A{row}"].font = Font(name="Arial", size=16, bold=True, color=BRAND_CYAN)
    ws[f"A{row}"].alignment = Alignment(horizontal="center")

    row += 2
    ws[f"A{row}"] = f"Project: {project_name}"
    ws[f"A{row}"].font = Font(bold=True)
    row += 1
    ws[f"A{row}"] = f"Date: {datetime.now().strftime('%Y-%m-%d')}"
    row += 1
    ws[f"A{row}"] = f"Reference: AP-{datetime.now().strftime('%Y%m%d%H%M')}"

    if contractor and contractor.company_name:
        row += 2
        ws[f"A{row}"] = f"Contractor: {contractor.company_name}"

    # Instructions
    row += 2
    ws.merge_cells(f"A{row}:F{row}")
    ws[f"A{row}"] = "Please complete Unit Price column. Total = Qty × Unit Price"
    ws[f"A{row}"].font = Font(italic=True, color="666666")

    # Table header
    row += 2
    headers = ["No.", "Description", "Unit", "Qty", "Unit Price (R)", "Total (R)"]
    for col, header in enumerate(headers, 1):
        cell = ws.cell(row=row, column=col, value=header)
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = PatternFill(start_color=HEADER_GRAY, fill_type="solid")
        cell.alignment = Alignment(horizontal="center", vertical="center")

    # Set column widths
    ws.column_dimensions["A"].width = 6
    ws.column_dimensions["B"].width = 55
    ws.column_dimensions["C"].width = 10
    ws.column_dimensions["D"].width = 10
    ws.column_dimensions["E"].width = 15
    ws.column_dimensions["F"].width = 15

    # Data rows
    row += 1
    current_section = None

    for item in pricing.quantity_bq:
        # Section header
        if item.section != current_section:
            current_section = item.section
            ws.merge_cells(f"A{row}:F{row}")
            ws[f"A{row}"] = item.section.value
            ws[f"A{row}"].font = Font(bold=True, color="FFFFFF")
            ws[f"A{row}"].fill = PatternFill(start_color=SECTION_GRAY, fill_type="solid")
            row += 1

        # Item row
        ws.cell(row=row, column=1, value=item.item_no)
        ws.cell(row=row, column=2, value=item.description)
        ws.cell(row=row, column=3, value=item.unit)
        ws.cell(row=row, column=4, value=item.qty)

        # Price column - leave empty for contractor to fill
        price_cell = ws.cell(row=row, column=5, value="")
        price_cell.number_format = "#,##0.00"

        # Total column - formula
        total_cell = ws.cell(row=row, column=6)
        total_cell.value = f"=D{row}*E{row}"
        total_cell.number_format = "#,##0.00"

        # Highlight estimated items in yellow
        if item.source == ItemConfidence.ESTIMATED:
            for col in range(1, 7):
                ws.cell(row=row, column=col).fill = PatternFill(
                    start_color="FFFACD", fill_type="solid"
                )

        row += 1

    # Summary section
    row += 1
    ws.cell(row=row, column=4, value="Subtotal:").font = Font(bold=True)
    ws.cell(row=row, column=6, value=f"=SUM(F1:F{row-1})").number_format = "#,##0.00"

    row += 1
    ws.cell(row=row, column=4, value="Contingency (5%):").font = Font(bold=True)
    ws.cell(row=row, column=6, value=f"=F{row-1}*0.05").number_format = "#,##0.00"

    row += 1
    ws.cell(row=row, column=4, value="Total excl VAT:").font = Font(bold=True)
    ws.cell(row=row, column=6, value=f"=F{row-2}+F{row-1}").number_format = "#,##0.00"

    row += 1
    ws.cell(row=row, column=4, value="VAT (15%):").font = Font(bold=True)
    ws.cell(row=row, column=6, value=f"=F{row-1}*0.15").number_format = "#,##0.00"

    row += 1
    ws.cell(row=row, column=4, value="TOTAL incl VAT:").font = Font(bold=True, size=12)
    ws.cell(row=row, column=6, value=f"=F{row-2}+F{row-1}")
    ws.cell(row=row, column=6).font = Font(bold=True, size=12)
    ws.cell(row=row, column=6).number_format = "#,##0.00"

    # Notes
    row += 2
    ws[f"A{row}"] = "Notes:"
    ws[f"A{row}"].font = Font(bold=True)
    row += 1
    ws[f"A{row}"] = "• Yellow highlighted items have estimated quantities - please verify"
    row += 1
    ws[f"A{row}"] = "• All prices exclude VAT unless stated"
    row += 1
    ws[f"A{row}"] = "• Quotation valid for 30 days"

    # Save to bytes
    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    return output.getvalue()


def export_estimated_bq(
    pricing: PricingResult,
    project_name: str = "Project",
    contractor: Optional[ContractorProfile] = None,
) -> bytes:
    """
    Export estimated BQ to Excel.

    This is the SECONDARY deliverable — includes default prices for reference.

    Args:
        pricing: PricingResult with estimated_bq
        project_name: Project name for header
        contractor: Contractor profile for letterhead

    Returns:
        Excel file as bytes
    """
    if not HAS_OPENPYXL:
        raise ImportError("openpyxl is required for Excel export")

    wb = Workbook()
    ws = wb.active
    ws.title = "Estimated BQ"

    # Setup styles
    _setup_styles(wb)

    # Header
    row = 1
    ws.merge_cells(f"A{row}:F{row}")
    ws[f"A{row}"] = "ESTIMATED BILL OF QUANTITIES — FOR REFERENCE ONLY"
    ws[f"A{row}"].font = Font(name="Arial", size=16, bold=True, color="F59E0B")
    ws[f"A{row}"].alignment = Alignment(horizontal="center")

    row += 2
    ws.merge_cells(f"A{row}:F{row}")
    ws[f"A{row}"] = "⚠️ PRICES ARE ESTIMATES ONLY — USE YOUR OWN SUPPLIER PRICES"
    ws[f"A{row}"].font = Font(bold=True, color="EF4444")
    ws[f"A{row}"].fill = PatternFill(start_color="FEE2E2", fill_type="solid")

    row += 2
    ws[f"A{row}"] = f"Project: {project_name}"
    ws[f"A{row}"].font = Font(bold=True)
    row += 1
    ws[f"A{row}"] = f"Date: {datetime.now().strftime('%Y-%m-%d')}"

    # Table header
    row += 2
    headers = ["No.", "Description", "Unit", "Qty", "Est. Price (R)", "Est. Total (R)"]
    for col, header in enumerate(headers, 1):
        cell = ws.cell(row=row, column=col, value=header)
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = PatternFill(start_color=HEADER_GRAY, fill_type="solid")
        cell.alignment = Alignment(horizontal="center", vertical="center")

    # Set column widths
    ws.column_dimensions["A"].width = 6
    ws.column_dimensions["B"].width = 55
    ws.column_dimensions["C"].width = 10
    ws.column_dimensions["D"].width = 10
    ws.column_dimensions["E"].width = 15
    ws.column_dimensions["F"].width = 15

    # Data rows
    row += 1
    current_section = None

    for item in pricing.estimated_bq:
        # Section header
        if item.section != current_section:
            current_section = item.section
            ws.merge_cells(f"A{row}:F{row}")
            ws[f"A{row}"] = item.section.value
            ws[f"A{row}"].font = Font(bold=True, color="FFFFFF")
            ws[f"A{row}"].fill = PatternFill(start_color=SECTION_GRAY, fill_type="solid")
            row += 1

        # Item row
        ws.cell(row=row, column=1, value=item.item_no)
        ws.cell(row=row, column=2, value=item.description)
        ws.cell(row=row, column=3, value=item.unit)
        ws.cell(row=row, column=4, value=item.qty)
        ws.cell(row=row, column=5, value=item.unit_price_zar).number_format = "#,##0.00"
        ws.cell(row=row, column=6, value=item.total_zar).number_format = "#,##0.00"

        row += 1

    # Summary section
    row += 1
    summaries = [
        ("Subtotal:", pricing.estimate_subtotal_zar),
        ("Contingency (5%):", pricing.estimate_contingency_zar),
        ("Margin:", pricing.estimate_margin_zar),
        ("Total excl VAT:", pricing.estimate_total_excl_vat_zar),
        ("VAT (15%):", pricing.estimate_vat_zar),
        ("TOTAL incl VAT:", pricing.estimate_total_incl_vat_zar),
    ]

    for label, value in summaries:
        ws.cell(row=row, column=4, value=label).font = Font(bold=True)
        ws.cell(row=row, column=6, value=value).number_format = "R #,##0.00"
        if "TOTAL" in label:
            ws.cell(row=row, column=6).font = Font(bold=True, size=12)
        row += 1

    # Save to bytes
    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    return output.getvalue()


def _setup_styles(wb: Workbook) -> None:
    """Setup workbook styles."""
    # Create named styles
    currency_style = NamedStyle(name="currency")
    currency_style.number_format = "R #,##0.00"

    try:
        wb.add_named_style(currency_style)
    except ValueError:
        pass  # Style already exists
