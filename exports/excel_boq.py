"""
Excel BoQ export for v6.1 — takes a BillOfQuantities, emits an .xlsx
with a Cover sheet and a section-grouped BoQ sheet.
"""

from __future__ import annotations

import io
from datetime import datetime

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

from agent.shared import BillOfQuantities, BQSection


_HEADER_FILL = PatternFill("solid", fgColor="00D4FF")
_SECTION_FILL = PatternFill("solid", fgColor="111827")
_BORDER = Border(
    left=Side(style="thin", color="CCCCCC"),
    right=Side(style="thin", color="CCCCCC"),
    top=Side(style="thin", color="CCCCCC"),
    bottom=Side(style="thin", color="CCCCCC"),
)


def _money(cell):
    cell.number_format = '"R "#,##0.00'
    cell.alignment = Alignment(horizontal="right")


def export_boq_to_excel(boq: BillOfQuantities) -> bytes:
    wb = Workbook()

    # ── Cover sheet ────────────────────────────────────────────────
    cover = wb.active
    cover.title = "Cover"

    cover["A1"] = "AfriPlan Electrical — Bill of Quantities"
    cover["A1"].font = Font(size=16, bold=True, color="00D4FF")
    cover.merge_cells("A1:D1")

    rows = [
        ("Project",          boq.project_name),
        ("Pipeline",         boq.pipeline.upper()),
        ("Run ID",           boq.run_id),
        ("Generated",        boq.generated_at.strftime("%Y-%m-%d %H:%M UTC")),
        ("Items",            boq.total_items),
        ("Items extracted",  boq.items_extracted),
        ("Items inferred",   boq.items_inferred),
        ("Items rate-only",  boq.items_rate_only),
        ("",                 ""),
        ("Subtotal",          boq.subtotal_zar),
        (f"Contingency ({boq.contingency_pct}%)", boq.contingency_zar),
        (f"Markup ({boq.contractor_markup_pct}%)", boq.markup_zar),
        ("Total excl VAT",    boq.total_excl_vat_zar),
        (f"VAT ({boq.vat_pct}%)", boq.vat_zar),
        ("Total incl VAT",    boq.total_incl_vat_zar),
    ]
    for i, (k, v) in enumerate(rows, start=3):
        cover[f"A{i}"] = k
        cover[f"B{i}"] = v
        cover[f"A{i}"].font = Font(bold=True)
        if isinstance(v, (int, float)) and k.lower().startswith(("subtotal", "total", "contingency", "markup", "vat")):
            _money(cover[f"B{i}"])
    cover.column_dimensions["A"].width = 28
    cover.column_dimensions["B"].width = 32

    # ── BoQ sheet ──────────────────────────────────────────────────
    sheet = wb.create_sheet("Bill of Quantities")

    headers = ["Item", "Description", "Unit", "Qty", "Unit Price (R)", "Total (R)", "Source", "Notes"]
    for col_idx, h in enumerate(headers, start=1):
        cell = sheet.cell(row=1, column=col_idx, value=h)
        cell.fill = _HEADER_FILL
        cell.font = Font(bold=True, color="0a0e1a")
        cell.border = _BORDER
        cell.alignment = Alignment(horizontal="center")

    row_cursor = 2
    by_section: dict[BQSection, list] = {}
    for it in boq.line_items:
        by_section.setdefault(it.section, []).append(it)

    for section in sorted(by_section.keys(), key=lambda s: s.section_number):
        # Section header
        cell = sheet.cell(row=row_cursor, column=1, value=section.value)
        cell.fill = _SECTION_FILL
        cell.font = Font(bold=True, color="00D4FF")
        sheet.merge_cells(start_row=row_cursor, start_column=1, end_row=row_cursor, end_column=8)
        row_cursor += 1

        section_total = 0.0
        for it in by_section[section]:
            sheet.cell(row=row_cursor, column=1, value=it.item_number_str)
            sheet.cell(row=row_cursor, column=2, value=it.description)
            sheet.cell(row=row_cursor, column=3, value=it.unit)
            sheet.cell(row=row_cursor, column=4, value=it.qty)
            unit = sheet.cell(row=row_cursor, column=5, value=it.unit_price_zar)
            total = sheet.cell(row=row_cursor, column=6, value=it.total_zar)
            sheet.cell(row=row_cursor, column=7, value=it.source.value)
            sheet.cell(row=row_cursor, column=8, value=it.notes)

            _money(unit)
            _money(total)
            for c in range(1, 9):
                sheet.cell(row=row_cursor, column=c).border = _BORDER

            section_total += it.total_zar
            row_cursor += 1

        # Section subtotal
        sheet.cell(row=row_cursor, column=2, value="Section subtotal").font = Font(bold=True, italic=True)
        st_cell = sheet.cell(row=row_cursor, column=6, value=round(section_total, 2))
        st_cell.font = Font(bold=True)
        _money(st_cell)
        row_cursor += 2

    widths = {1: 10, 2: 56, 3: 8, 4: 8, 5: 16, 6: 18, 7: 14, 8: 30}
    for col, w in widths.items():
        sheet.column_dimensions[get_column_letter(col)].width = w

    # ── Serialise ──────────────────────────────────────────────────
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()
