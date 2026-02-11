"""
AfriPlan Electrical - PDF Generation Functions
Professional quotation PDF exports for all tiers
"""

from datetime import datetime

# Brand color - Fluorescent Blue/Cyan
BRAND_COLOR = (0, 212, 255)  # #00D4FF


def generate_electrical_pdf(elec_req: dict, circuit_info: dict, bq_items: list,
                            admd_data: dict = None, vd_data: dict = None):
    """Generate professional electrical quotation PDF for residential.

    Args:
        elec_req: Electrical requirements from calculation
        circuit_info: Circuit information from calculation
        bq_items: List of BQ items
        admd_data: Optional ADMD calculation results
        vd_data: Optional voltage drop calculation results
    """
    from fpdf import FPDF

    pdf = FPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)

    # Header
    pdf.set_font('Helvetica', 'B', 20)
    pdf.set_text_color(30, 41, 59)
    pdf.cell(0, 15, 'ELECTRICAL INSTALLATION QUOTATION', new_x="LMARGIN", new_y="NEXT", align='C')

    # Subheader - SANS compliant
    pdf.set_font('Helvetica', 'I', 10)
    pdf.set_text_color(*BRAND_COLOR)
    pdf.cell(0, 6, 'SANS 10142 Compliant Installation', new_x="LMARGIN", new_y="NEXT", align='C')

    # Project Info
    pdf.set_font('Helvetica', '', 10)
    pdf.set_text_color(100, 116, 139)
    pdf.cell(0, 6, f"Date: {datetime.now().strftime('%d %B %Y')}", new_x="LMARGIN", new_y="NEXT", align='C')
    pdf.cell(0, 6, f"Quote Ref: EQ-{datetime.now().strftime('%Y%m%d%H%M')}", new_x="LMARGIN", new_y="NEXT", align='C')
    pdf.ln(5)

    # Summary Section
    pdf.set_font('Helvetica', 'B', 12)
    pdf.set_fill_color(*BRAND_COLOR)  # Cyan
    pdf.set_text_color(255, 255, 255)
    pdf.cell(0, 8, '  PROJECT SUMMARY', fill=True, new_x="LMARGIN", new_y="NEXT")

    pdf.set_text_color(30, 41, 59)
    pdf.set_font('Helvetica', '', 10)
    pdf.cell(95, 6, f"  Total Light Points: {elec_req['total_lights']}", new_x="RIGHT")
    pdf.cell(95, 6, f"Total Plug Points: {elec_req['total_plugs']}", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(95, 6, f"  Total Load: {circuit_info['total_load_kva']} kVA", new_x="RIGHT")
    pdf.cell(95, 6, f"Main Breaker: {circuit_info['main_size']}", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(95, 6, f"  DB Board: {circuit_info['db_size'].replace('_', ' ')}", new_x="RIGHT")
    pdf.cell(95, 6, f"Total Circuits: {circuit_info['total_circuits']}", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(5)

    # ADMD Section (if provided)
    if admd_data:
        pdf.set_font('Helvetica', 'B', 12)
        pdf.set_fill_color(*BRAND_COLOR)
        pdf.set_text_color(255, 255, 255)
        pdf.cell(0, 8, '  ESKOM SUPPLY APPLICATION (ADMD)', fill=True, new_x="LMARGIN", new_y="NEXT")

        pdf.set_text_color(30, 41, 59)
        pdf.set_font('Helvetica', '', 10)
        pdf.cell(95, 6, f"  Dwelling Type: {admd_data.get('dwelling_name', 'N/A')}", new_x="RIGHT")
        pdf.cell(95, 6, f"ADMD: {admd_data.get('adjusted_admd_kva', 0)} kVA", new_x="LMARGIN", new_y="NEXT")
        pdf.cell(95, 6, f"  Recommended Supply: {admd_data.get('recommended_supply', 'N/A')}", new_x="RIGHT")
        pdf.cell(95, 6, f"Supply Type: {admd_data.get('supply_type', 'N/A')}", new_x="LMARGIN", new_y="NEXT")
        pdf.ln(5)

    # Voltage Drop Section (if provided)
    if vd_data:
        pdf.set_font('Helvetica', 'B', 12)
        pdf.set_fill_color(*BRAND_COLOR)
        pdf.set_text_color(255, 255, 255)
        pdf.cell(0, 8, '  VOLTAGE DROP VERIFICATION', fill=True, new_x="LMARGIN", new_y="NEXT")

        pdf.set_text_color(30, 41, 59)
        pdf.set_font('Helvetica', '', 10)
        status_icon = "PASS" if vd_data.get('compliant', False) else "FAIL"
        pdf.cell(95, 6, f"  Cable Size: {vd_data.get('cable_size_mm2', 'N/A')} mm²", new_x="RIGHT")
        pdf.cell(95, 6, f"Length: {vd_data.get('length_m', 0)} m", new_x="LMARGIN", new_y="NEXT")
        pdf.cell(95, 6, f"  Voltage Drop: {vd_data.get('voltage_drop_percent', 0):.2f}%", new_x="RIGHT")
        pdf.cell(95, 6, f"Compliance: {status_icon}", new_x="LMARGIN", new_y="NEXT")
        pdf.ln(5)

    # BQ Table Header
    pdf.set_font('Helvetica', 'B', 12)
    pdf.set_fill_color(*BRAND_COLOR)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(0, 8, '  BILL OF QUANTITIES', fill=True, new_x="LMARGIN", new_y="NEXT")

    # Table header
    pdf.set_font('Helvetica', 'B', 9)
    pdf.set_fill_color(30, 41, 59)
    pdf.cell(70, 7, ' Item', border=1, fill=True, align='L')
    pdf.cell(25, 7, 'Qty', border=1, fill=True, align='C')
    pdf.cell(25, 7, 'Unit', border=1, fill=True, align='C')
    pdf.cell(35, 7, 'Rate (R)', border=1, fill=True, align='R')
    pdf.cell(35, 7, 'Total (R)', border=1, fill=True, align='R')
    pdf.ln()

    # Table rows
    pdf.set_font('Helvetica', '', 8)
    pdf.set_text_color(30, 41, 59)
    current_category = ""

    for item in bq_items:
        if item["category"] != current_category:
            current_category = item["category"]
            pdf.set_font('Helvetica', 'B', 9)
            pdf.set_fill_color(240, 240, 240)
            pdf.set_text_color(30, 41, 59)
            pdf.cell(190, 6, f" {current_category}", border=1, fill=True, new_x="LMARGIN", new_y="NEXT")
            pdf.set_font('Helvetica', '', 8)

        pdf.cell(70, 6, f" {item['item'][:38]}", border=1, align='L')
        pdf.cell(25, 6, str(item["qty"]), border=1, align='C')
        pdf.cell(25, 6, item["unit"], border=1, align='C')
        pdf.cell(35, 6, f"{item['rate']:,.0f}", border=1, align='R')
        pdf.cell(35, 6, f"{item['total']:,.0f}", border=1, align='R')
        pdf.ln()

    # Totals
    pdf.ln(3)
    subtotal = sum(item["total"] for item in bq_items)
    vat = subtotal * 0.15
    total = subtotal + vat

    pdf.set_font('Helvetica', 'B', 10)
    pdf.cell(155, 7, 'Subtotal (excl VAT):', align='R')
    pdf.cell(35, 7, f'R {subtotal:,.0f}', align='R', new_x="LMARGIN", new_y="NEXT")
    pdf.cell(155, 7, 'VAT (15%):', align='R')
    pdf.cell(35, 7, f'R {vat:,.0f}', align='R', new_x="LMARGIN", new_y="NEXT")

    pdf.set_fill_color(*BRAND_COLOR)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(155, 8, 'TOTAL (incl VAT):', fill=True, align='R')
    pdf.cell(35, 8, f'R {total:,.0f}', fill=True, align='R', new_x="LMARGIN", new_y="NEXT")

    # Notes
    pdf.ln(5)
    pdf.set_text_color(100, 116, 139)
    pdf.set_font('Helvetica', 'I', 8)
    pdf.multi_cell(0, 4,
        "Notes:\n"
        "- Quote valid for 30 days from date of issue\n"
        "- Prices based on current SA market rates\n"
        "- COC Certificate included upon completion\n"
        "- Excludes builders work (chasing, making good)\n"
        "- SANS 10142 compliant installation\n"
        "- Payment: 40% deposit, 40% on progress, 20% on completion"
    )

    # Footer
    pdf.ln(5)
    pdf.set_font('Helvetica', 'B', 9)
    pdf.set_text_color(*BRAND_COLOR)
    pdf.cell(0, 6, 'Generated by AfriPlan Electrical - www.afriplan.co.za', new_x="LMARGIN", new_y="NEXT", align='C')

    return bytes(pdf.output())


def generate_generic_electrical_pdf(bq_items: list, summary: dict, tier: str, subtype: str):
    """Generate generic electrical quotation PDF for all project types."""
    from fpdf import FPDF

    pdf = FPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)

    # Header
    pdf.set_font('Helvetica', 'B', 20)
    pdf.set_text_color(30, 41, 59)
    tier_names = {"residential": "RESIDENTIAL", "commercial": "COMMERCIAL", "industrial": "INDUSTRIAL", "infrastructure": "INFRASTRUCTURE"}
    pdf.cell(0, 15, f'{tier_names.get(tier, "ELECTRICAL")} QUOTATION', new_x="LMARGIN", new_y="NEXT", align='C')

    # Project Info
    pdf.set_font('Helvetica', '', 10)
    pdf.set_text_color(100, 116, 139)
    pdf.cell(0, 6, f"Project Type: {subtype.replace('_', ' ').title()}", new_x="LMARGIN", new_y="NEXT", align='C')
    pdf.cell(0, 6, f"Date: {datetime.now().strftime('%d %B %Y')}", new_x="LMARGIN", new_y="NEXT", align='C')
    pdf.cell(0, 6, f"Quote Ref: {tier[:3].upper()}-{datetime.now().strftime('%Y%m%d%H%M')}", new_x="LMARGIN", new_y="NEXT", align='C')
    pdf.ln(5)

    # Summary Section
    if summary:
        pdf.set_font('Helvetica', 'B', 12)
        pdf.set_fill_color(*BRAND_COLOR)
        pdf.set_text_color(255, 255, 255)
        pdf.cell(0, 8, '  PROJECT SUMMARY', fill=True, new_x="LMARGIN", new_y="NEXT")

        pdf.set_text_color(30, 41, 59)
        pdf.set_font('Helvetica', '', 10)
        for key, val in summary.items():
            pdf.cell(95, 6, f"  {key}: {val}", new_x="LMARGIN", new_y="NEXT")
        pdf.ln(5)

    # BQ Table Header
    pdf.set_font('Helvetica', 'B', 12)
    pdf.set_fill_color(*BRAND_COLOR)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(0, 8, '  BILL OF QUANTITIES', fill=True, new_x="LMARGIN", new_y="NEXT")

    # Table header
    pdf.set_font('Helvetica', 'B', 9)
    pdf.set_fill_color(30, 41, 59)
    pdf.cell(70, 7, ' Item', border=1, fill=True, align='L')
    pdf.cell(25, 7, 'Qty', border=1, fill=True, align='C')
    pdf.cell(25, 7, 'Unit', border=1, fill=True, align='C')
    pdf.cell(35, 7, 'Rate (R)', border=1, fill=True, align='R')
    pdf.cell(35, 7, 'Total (R)', border=1, fill=True, align='R')
    pdf.ln()

    # Table rows
    pdf.set_font('Helvetica', '', 8)
    pdf.set_text_color(30, 41, 59)
    current_category = ""

    for item in bq_items:
        if item["category"] != current_category:
            current_category = item["category"]
            pdf.set_font('Helvetica', 'B', 9)
            pdf.set_fill_color(240, 240, 240)
            pdf.set_text_color(30, 41, 59)
            pdf.cell(190, 6, f" {current_category}", border=1, fill=True, new_x="LMARGIN", new_y="NEXT")
            pdf.set_font('Helvetica', '', 8)

        pdf.cell(70, 6, f" {item['item'][:38]}", border=1, align='L')
        pdf.cell(25, 6, str(item["qty"]), border=1, align='C')
        pdf.cell(25, 6, item["unit"], border=1, align='C')
        pdf.cell(35, 6, f"{item['rate']:,.0f}", border=1, align='R')
        pdf.cell(35, 6, f"{item['total']:,.0f}", border=1, align='R')
        pdf.ln()

    # Totals
    pdf.ln(3)
    subtotal = sum(item["total"] for item in bq_items)
    vat = subtotal * 0.15
    total = subtotal + vat

    pdf.set_font('Helvetica', 'B', 10)
    pdf.cell(155, 7, 'Subtotal (excl VAT):', align='R')
    pdf.cell(35, 7, f'R {subtotal:,.0f}', align='R', new_x="LMARGIN", new_y="NEXT")
    pdf.cell(155, 7, 'VAT (15%):', align='R')
    pdf.cell(35, 7, f'R {vat:,.0f}', align='R', new_x="LMARGIN", new_y="NEXT")

    pdf.set_fill_color(*BRAND_COLOR)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(155, 8, 'TOTAL (incl VAT):', fill=True, align='R')
    pdf.cell(35, 8, f'R {total:,.0f}', fill=True, align='R', new_x="LMARGIN", new_y="NEXT")

    # Notes
    pdf.ln(5)
    pdf.set_text_color(100, 116, 139)
    pdf.set_font('Helvetica', 'I', 8)
    pdf.multi_cell(0, 4,
        "Notes:\n"
        "- Quote valid for 30 days from date of issue\n"
        "- Prices based on current SA market rates\n"
        "- All work compliant with applicable SANS standards\n"
        "- Payment: 40% deposit, 40% on progress, 20% on completion"
    )

    # Footer
    pdf.ln(5)
    pdf.set_font('Helvetica', 'B', 9)
    pdf.set_text_color(*BRAND_COLOR)
    pdf.cell(0, 6, 'Generated by AfriPlan Electrical - www.afriplan.co.za', new_x="LMARGIN", new_y="NEXT", align='C')

    return bytes(pdf.output())
