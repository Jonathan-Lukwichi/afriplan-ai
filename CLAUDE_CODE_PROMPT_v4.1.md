# CLAUDE_CODE_PROMPT.md — AfriPlan v4.1 Build Instructions

## Pre-requisite
Read `CLAUDE.md` and `agent/models.py` first. The philosophy has changed:
- The AI extracts **draft quantities** (not a final quotation)
- The contractor **reviews and corrects** the extraction
- The tool generates a **structured Excel BQ** with formulas
- The contractor fills in **their own prices**

Every file imports from `agent/models.py`. Never define data shapes inline.

---

## Phase 1: Agent Infrastructure

### 1.1 agent/utils.py
Same as v4.0. Contains:
- `parse_json_safely(text)` → handles backticks, trailing commas
- `encode_image_to_base64(bytes)` → base64 string
- `estimate_cost_zar(model, input_tokens, output_tokens)` → cost in ZAR
- `Timer` context manager

### 1.2 agent/prompts/
Same as v4.0 with one addition to every prompt:

Add to ALL extraction prompts (SLD, lighting, plugs, outside lights):
```
For each value you extract, set a confidence level:
- "extracted": you read this directly from the drawing
- "inferred": you calculated this from other values
- "estimated": you are using a default or guessing

Example: If you can read "384W" in the circuit schedule → "extracted"
If you count 8 lights at 48W each to get 384W → "inferred"
If you can't clearly read the value → "estimated"
```

### 1.3 agent/prompts/schemas.py
Same as v4.0 but add `confidence` field to all schema examples:
```json
{
  "distribution_boards": [
    {
      "name": "DB-PFA",
      "confidence": "extracted",
      "circuits": [
        {"id": "L1", "wattage_w": 384, "confidence": "extracted"},
        {"id": "P1", "wattage_w": 3680, "confidence": "inferred"}
      ]
    }
  ]
}
```

---

## Phase 2: Pipeline Stages

### 2.1 agent/stages/ingest.py
Identical to v4.0. No changes needed.

### 2.2 agent/stages/classify.py
Identical to v4.0. No changes needed.

### 2.3 agent/stages/discover.py
Same extraction logic as v4.0 but:

1. Parse `confidence` field from every AI response and map to `ItemConfidence` enum
2. Default any unparsed confidence to `ItemConfidence.ESTIMATED`
3. For cable lengths NOT marked on drawings, set `confidence=ESTIMATED`
4. For cable lengths marked on outside lights drawing, set `confidence=EXTRACTED`

### 2.4 agent/stages/review.py — **NEW STAGE**

```python
"""REVIEW stage: Manages contractor review state and correction tracking."""

from agent.models import (
    ExtractionResult, CorrectionEntry, CorrectionLog, ItemConfidence
)


class ReviewManager:
    """Tracks changes made during contractor review."""

    def __init__(self, extraction: ExtractionResult):
        self.extraction = extraction
        self.corrections: list[CorrectionEntry] = []
        self._count_ai_items()

    def _count_ai_items(self):
        """Count total items the AI extracted (for accuracy calculation)."""
        count = 0
        for block in self.extraction.building_blocks:
            count += len(block.distribution_boards)
            for db in block.distribution_boards:
                count += len(db.circuits)
            for room in block.rooms:
                # Count non-zero fixture fields
                fixtures = room.fixtures
                for field_name in fixtures.model_fields:
                    val = getattr(fixtures, field_name, 0)
                    if isinstance(val, int) and val > 0:
                        count += 1
            count += len(block.heavy_equipment)
        count += len(self.extraction.site_cable_runs)
        self.total_ai_items = count

    def log_correction(
        self,
        field_path: str,
        original_value,
        corrected_value,
        item_type: str,
        building_block: str = "",
        page_source: str = "",
    ):
        """Log a contractor correction."""
        from datetime import datetime
        entry = CorrectionEntry(
            field_path=field_path,
            original_value=original_value,
            corrected_value=corrected_value,
            item_type=item_type,
            building_block=building_block,
            page_source=page_source,
            timestamp=datetime.now().isoformat(),
        )
        self.corrections.append(entry)

    def get_correction_log(self) -> CorrectionLog:
        """Build final correction log after review is complete."""
        added = sum(1 for c in self.corrections if c.original_value in (0, None, ""))
        removed = sum(1 for c in self.corrections if c.corrected_value in (0, None, ""))
        changed = len(self.corrections) - added - removed

        return CorrectionLog(
            project_name=self.extraction.metadata.project_name,
            corrections=self.corrections,
            total_ai_items=self.total_ai_items,
            total_corrected=changed,
            total_added=added,
            total_removed=removed,
        )

    def complete_review(self):
        """Mark review as complete."""
        self.extraction.review_completed = True
        self.extraction.corrections = self.get_correction_log()
```

### 2.5 agent/stages/validate.py
Same as v4.0 — runs on contractor-approved data (post-review).

### 2.6 agent/stages/price.py — **REDESIGNED**

```python
"""PRICE stage: Generate dual BQ — quantity-only + estimated."""

from agent.models import (
    ExtractionResult, ValidationResult, PricingResult,
    BQLineItem, BQSection, BlockPricingSummary, ItemConfidence,
    ContractorProfile, SiteConditions
)
from core.constants import DEFAULT_PRICES, CABLE_PRICES, LABOUR_RATES


def price(
    extraction: ExtractionResult,
    validation: ValidationResult,
    contractor: ContractorProfile = None,
    site: SiteConditions = None,
) -> PricingResult:
    """
    Generate DUAL BQ:
    1. quantity_bq: items + quantities, no prices (contractor fills in)
    2. estimated_bq: items + quantities + default prices (ballpark)
    """
    result = PricingResult()

    # Build quantity items (descriptions + quantities)
    quantity_items = []
    item_no = 0

    for block in extraction.building_blocks:
        # Section B: Distribution Boards
        for db in block.distribution_boards:
            item_no += 1
            quantity_items.append(BQLineItem(
                item_no=item_no,
                section=BQSection.DISTRIBUTION,
                description=f"{db.name} — {db.total_ways}-way DB, {db.main_breaker_a}A main breaker",
                unit="each",
                qty=1,
                source=db.confidence,
                building_block=block.name,
            ))

        # Section C: Cables per circuit
        for db in block.distribution_boards:
            for circuit in db.active_circuits:
                if circuit.type == "sub_board_feed":
                    continue  # Handled separately
                item_no += 1
                cable_desc = f"{circuit.cable_size_mm2}mm² {circuit.cable_cores}C {circuit.cable_type}"
                length = circuit.feed_cable_length_m or _estimate_cable_length(circuit)
                quantity_items.append(BQLineItem(
                    item_no=item_no,
                    section=BQSection.CABLES,
                    description=f"{cable_desc} — {db.name} {circuit.id} ({circuit.description})",
                    unit="m",
                    qty=length,
                    source=circuit.confidence,
                    building_block=block.name,
                    notes="AI estimated length" if circuit.confidence == ItemConfidence.ESTIMATED else "",
                ))

        # Section E: Light Fittings per room
        for room in block.rooms:
            f = room.fixtures
            fixture_map = [
                ("recessed_led_600x1200", "600×1200 Recessed LED 3×18W", f.recessed_led_600x1200),
                ("surface_mount_led_18w", "18W LED Surface Mount", f.surface_mount_led_18w),
                ("flood_light_30w", "30W LED Flood Light", f.flood_light_30w),
                ("flood_light_200w", "200W LED Flood Light", f.flood_light_200w),
                ("downlight_led_6w", "6W LED Downlight White", f.downlight_led_6w),
                ("vapor_proof_2x24w", "2×24W Vapor Proof LED (IP65)", f.vapor_proof_2x24w),
                ("vapor_proof_2x18w", "2×18W Vapor Proof LED", f.vapor_proof_2x18w),
                ("prismatic_2x18w", "2×18W Prismatic LED", f.prismatic_2x18w),
                ("bulkhead_26w", "26W Bulkhead Outdoor", f.bulkhead_26w),
                ("bulkhead_24w", "24W Bulkhead Outdoor", f.bulkhead_24w),
                ("fluorescent_50w_5ft", "50W 5ft Fluorescent", f.fluorescent_50w_5ft),
                ("pole_light_60w", "Outdoor Pole Light 2300mm 60W (incl. pole + base)", f.pole_light_60w),
            ]
            for field_name, desc, qty in fixture_map:
                if qty > 0:
                    item_no += 1
                    quantity_items.append(BQLineItem(
                        item_no=item_no,
                        section=BQSection.LIGHTS,
                        description=f"{desc} — {room.name}",
                        unit="each",
                        qty=qty,
                        source=room.confidence,
                        building_block=block.name,
                    ))

        # Section F: Sockets & Switches (similar pattern)
        # ... implement for all socket/switch types

        # Section G: Heavy Equipment
        for equip in block.heavy_equipment:
            item_no += 1
            vsd_label = " with VSD" if equip.has_vsd else ""
            quantity_items.append(BQLineItem(
                item_no=item_no,
                section=BQSection.EQUIPMENT,
                description=f"{equip.name} ({equip.rating_kw}kW{vsd_label})",
                unit="each",
                qty=equip.qty,
                source=equip.confidence,
                building_block=block.name,
            ))

    # Section J: Site Works
    for run in extraction.site_cable_runs:
        item_no += 1
        quantity_items.append(BQLineItem(
            item_no=item_no,
            section=BQSection.CABLES,
            description=f"{run.cable_spec} — {run.from_point} to {run.to_point}",
            unit="m",
            qty=run.length_m,
            source=run.confidence,
            notes=f"Distance from drawing" if run.confidence == ItemConfidence.EXTRACTED else "",
        ))
        if run.needs_trenching:
            item_no += 1
            quantity_items.append(BQLineItem(
                item_no=item_no,
                section=BQSection.SITE_WORKS,
                description=f"Trenching 600mm deep — {run.from_point} to {run.to_point}",
                unit="m",
                qty=run.length_m,
                source=run.confidence,
            ))

    # Section I: Compliance additions from validation
    if validation:
        for flag in validation.flags:
            if flag.auto_corrected:
                item_no += 1
                quantity_items.append(BQLineItem(
                    item_no=item_no,
                    section=BQSection.COMPLIANCE,
                    description=f"Compliance: {flag.corrected_value}",
                    unit="each",
                    qty=1,
                    source=ItemConfidence.INFERRED,
                    notes=f"Added per {flag.standard_ref}: {flag.message}",
                ))

    # Section K: Labour (calculated from totals)
    total_circuits = extraction.total_circuits
    total_points = extraction.total_points
    total_dbs = extraction.total_dbs
    total_heavy = len(extraction.all_heavy_equipment)

    labour_items = [
        (f"Circuit installation ({total_circuits} circuits)", "circuit", total_circuits),
        (f"Point installation ({total_points} points)", "point", total_points),
        (f"DB installation and wiring ({total_dbs} boards)", "each", total_dbs),
        (f"Heavy equipment connection ({total_heavy} units)", "each", total_heavy),
        (f"Testing and commissioning ({total_dbs} boards)", "each", total_dbs),
        (f"COC certification ({len(extraction.supply_points)} supplies)", "each",
         max(1, len(extraction.supply_points))),
    ]
    for desc, unit, qty in labour_items:
        if qty > 0:
            item_no += 1
            quantity_items.append(BQLineItem(
                item_no=item_no,
                section=BQSection.LABOUR,
                description=desc,
                unit=unit,
                qty=qty,
                source=ItemConfidence.INFERRED,
            ))

    # Store quantity BQ
    result.quantity_bq = quantity_items
    result.total_items = len(quantity_items)

    # --- Generate Estimated BQ (copy quantity items + add default prices) ---
    estimated_items = []
    for item in quantity_items:
        est_item = item.model_copy()
        # Look up default price
        price = _get_default_price(est_item, contractor)
        est_item.unit_price_zar = price
        est_item.total_zar = round(price * est_item.qty, 2)
        estimated_items.append(est_item)

    # Apply site condition multipliers
    if site:
        for item in estimated_items:
            if item.section == BQSection.LABOUR:
                item.total_zar = round(item.total_zar * site.labour_multiplier, 2)
            if item.section == BQSection.SITE_WORKS:
                item.total_zar = round(item.total_zar * site.trenching_multiplier, 2)

    result.estimated_bq = estimated_items
    result.site_labour_multiplier = site.labour_multiplier if site else 1.0
    result.site_trenching_multiplier = site.trenching_multiplier if site else 1.0

    # Calculate estimated totals
    subtotal = sum(i.total_zar for i in estimated_items)
    contingency_pct = (contractor.contingency_pct if contractor else 5.0) / 100
    markup_pct = (contractor.markup_pct if contractor else 20.0) / 100

    result.estimate_subtotal_zar = subtotal
    result.estimate_contingency_zar = round(subtotal * contingency_pct, 2)
    subtotal_with_contingency = subtotal + result.estimate_contingency_zar
    result.estimate_margin_zar = round(subtotal_with_contingency * markup_pct, 2)
    result.estimate_total_excl_vat_zar = round(
        subtotal_with_contingency + result.estimate_margin_zar, 2
    )
    result.estimate_vat_zar = round(result.estimate_total_excl_vat_zar * 0.15, 2)
    result.estimate_total_incl_vat_zar = round(
        result.estimate_total_excl_vat_zar + result.estimate_vat_zar, 2
    )

    # Payment schedule
    total = result.estimate_total_incl_vat_zar
    result.deposit_zar = round(total * 0.40, 2)
    result.second_payment_zar = round(total * 0.40, 2)
    result.final_payment_zar = round(total * 0.20, 2)

    # Quality indicators
    result.items_from_extraction = sum(
        1 for i in quantity_items if i.source == ItemConfidence.EXTRACTED
    )
    result.items_estimated = sum(
        1 for i in quantity_items if i.source == ItemConfidence.ESTIMATED
    )
    result.items_rate_only = sum(1 for i in quantity_items if i.is_rate_only)

    return result


def _estimate_cable_length(circuit) -> float:
    """Default cable length estimates when not on drawing."""
    if circuit.type in ("sub_board_feed",):
        return 15.0  # Same floor default
    if circuit.type in ("lighting", "power"):
        return 8.0   # Average circuit run
    if circuit.type in ("ac", "geyser", "pump"):
        return 12.0  # Dedicated circuit
    return 10.0


def _get_default_price(item, contractor=None):
    """Look up default unit price. Use contractor custom price if available."""
    if contractor and item.description in contractor.custom_prices:
        return contractor.custom_prices[item.description]
    # Fall back to DEFAULT_PRICES lookup from core/constants.py
    return DEFAULT_PRICES.get(item.description, 0.0)
```

### 2.7 agent/stages/output.py
Assembly stage — builds final PipelineResult with weighted confidence.

### 2.8 agent/pipeline.py
7-stage orchestrator. Key difference from v4.0:

```python
class AfriPlanAgent:
    def extract(self, files: list) -> PipelineResult:
        """Stages 1-3: INGEST → CLASSIFY → DISCOVER. Returns extraction for review."""
        # ... run first 3 stages
        # DOES NOT run validate/price — waits for review

    def finalize(
        self,
        extraction: ExtractionResult,
        contractor: ContractorProfile = None,
        site: SiteConditions = None,
    ) -> PipelineResult:
        """Stages 5-7: VALIDATE → PRICE → OUTPUT. Runs after review is complete."""
        # ... run final 3 stages using contractor-approved data
```

The pipeline is split into two calls because the REVIEW stage happens in the UI between them.

---

## Phase 3: Core Business Logic

### 3.1 core/constants.py
Default pricing tables. Structure:

```python
DEFAULT_PRICES = {
    # Lights
    "600×1200 Recessed LED 3×18W": 650.0,
    "18W LED Surface Mount": 280.0,
    "30W LED Flood Light": 450.0,
    "200W LED Flood Light": 2800.0,
    # ... all 12 light types

    # Sockets
    "16A Double Switched @300mm": 160.0,
    # ... all 8 socket types

    # Switches
    "1-Lever 1-Way Switch": 60.0,
    # ... all 7 switch types

    # Equipment
    "Pool Pump with VSD": 12500.0,
    "Heat Pump 12.5kW": 18000.0,
    # ... all equipment types

    # Labour
    "circuit": 450.0,     # Per circuit installed
    "point": 85.0,        # Per point installed
    "each_db": 1500.0,    # Per DB installed
    "each_heavy": 2500.0, # Per heavy equipment connection
    "each_test": 800.0,   # Per DB tested
    "each_coc": 3500.0,   # Per COC certificate

    # Site works
    "trenching_per_m": 180.0,
    "sand_bed_per_m": 45.0,
    "warning_tape_per_m": 15.0,
}

# Cable prices per meter (keyed by "size_cores_type")
CABLE_PRICES = {
    "1.5_3_GP": 12.0,
    "2.5_3_GP": 18.0,
    "4_4_SWA": 65.0,
    "6_3_GP": 35.0,
    "10_4_SWA": 95.0,
    "16_4_SWA": 135.0,
    "25_4_SWA": 195.0,
    "35_4_SWA": 265.0,
    "50_4_SWA": 350.0,
    "70_4_SWA": 480.0,
    "95_4_SWA": 650.0,
}
```

### 3.2 core/standards.py
SANS 10142-1 rules. Same as v4.0.

---

## Phase 4: Exports

### 4.1 exports/excel_bq.py — **CRITICAL NEW FILE**

Generate a professional Excel workbook using `openpyxl`:

```python
"""Generate Excel BQ workbook with quantity + estimated sheets and live formulas."""

import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side, numbers
from openpyxl.utils import get_column_letter
from agent.models import PricingResult, BQSection, ContractorProfile, ItemConfidence


# Confidence → cell fill colour
CONFIDENCE_FILLS = {
    ItemConfidence.EXTRACTED: PatternFill(start_color="C6EFCE", fill_type="solid"),  # green
    ItemConfidence.INFERRED: PatternFill(start_color="FFEB9C", fill_type="solid"),   # yellow
    ItemConfidence.ESTIMATED: PatternFill(start_color="FFC7CE", fill_type="solid"),  # red
    ItemConfidence.MANUAL: PatternFill(start_color="BDD7EE", fill_type="solid"),     # blue
}


def generate_bq_workbook(
    pricing: PricingResult,
    contractor: ContractorProfile = None,
    project_name: str = "",
) -> openpyxl.Workbook:
    wb = openpyxl.Workbook()

    # Sheet 1: Cover
    ws_cover = wb.active
    ws_cover.title = "Cover"
    _build_cover(ws_cover, contractor, project_name)

    # Sheet 2: Quantity BQ (THE primary deliverable)
    ws_qty = wb.create_sheet("Quantity BQ")
    _build_quantity_sheet(ws_qty, pricing.quantity_bq)

    # Sheet 3: Estimated BQ (ballpark reference)
    ws_est = wb.create_sheet("Estimated BQ")
    _build_estimated_sheet(ws_est, pricing.estimated_bq, pricing)

    # Sheet 4: Summary
    ws_sum = wb.create_sheet("Summary")
    _build_summary_sheet(ws_sum, pricing)

    # Sheet 5: Notes
    ws_notes = wb.create_sheet("Notes")
    _build_notes_sheet(ws_notes, pricing)

    return wb


def _build_quantity_sheet(ws, items):
    """
    Quantity BQ: Item | Section | Description | Unit | Qty | Unit Price (R) | Total (R)
    Qty is filled. Unit Price is EMPTY. Total is a FORMULA: =E_row * F_row
    """
    headers = ["Item", "Section", "Description", "Unit", "Qty", "Unit Price (R)", "Total (R)", "Confidence"]
    for col, header in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col, value=header)
        cell.font = Font(bold=True, size=11)
        cell.fill = PatternFill(start_color="4472C4", fill_type="solid")
        cell.font = Font(bold=True, color="FFFFFF", size=11)

    current_section = None
    row = 2

    for item in items:
        # Section header row
        if item.section != current_section:
            current_section = item.section
            ws.cell(row=row, column=1).value = ""
            section_cell = ws.cell(row=row, column=2, value=current_section.value)
            section_cell.font = Font(bold=True, size=11)
            section_cell.fill = PatternFill(start_color="D9E2F3", fill_type="solid")
            for col in range(1, 9):
                ws.cell(row=row, column=col).fill = PatternFill(start_color="D9E2F3", fill_type="solid")
            row += 1

        ws.cell(row=row, column=1, value=item.item_no)
        ws.cell(row=row, column=2, value=item.section.value.split(" - ")[0])  # "A", "B", etc.
        ws.cell(row=row, column=3, value=item.description)
        ws.cell(row=row, column=4, value=item.unit)

        qty_cell = ws.cell(row=row, column=5, value=item.qty)
        qty_cell.number_format = '#,##0.0'

        # Unit Price: EMPTY — contractor fills this in
        price_cell = ws.cell(row=row, column=6)
        price_cell.number_format = '#,##0.00'
        # Unlock this cell for editing
        price_cell.protection = openpyxl.styles.Protection(locked=False)

        # Total: FORMULA
        ws.cell(row=row, column=7).value = f"=E{row}*F{row}"
        ws.cell(row=row, column=7).number_format = '#,##0.00'

        # Confidence colour
        conf_cell = ws.cell(row=row, column=8, value=item.source.value if hasattr(item.source, 'value') else str(item.source))
        if item.source in CONFIDENCE_FILLS:
            conf_cell.fill = CONFIDENCE_FILLS[item.source]

        row += 1

    # Subtotals at bottom
    row += 1
    ws.cell(row=row, column=5, value="SUBTOTAL").font = Font(bold=True)
    ws.cell(row=row, column=7).value = f"=SUM(G2:G{row-1})"
    ws.cell(row=row, column=7).font = Font(bold=True)
    ws.cell(row=row, column=7).number_format = '#,##0.00'

    row += 1
    ws.cell(row=row, column=5, value="Contingency (%)").font = Font(bold=True)
    ws.cell(row=row, column=6, value=5.0)  # Editable
    ws.cell(row=row, column=6).protection = openpyxl.styles.Protection(locked=False)
    ws.cell(row=row, column=7).value = f"=G{row-1}*F{row}/100"
    ws.cell(row=row, column=7).number_format = '#,##0.00'

    row += 1
    ws.cell(row=row, column=5, value="Markup (%)").font = Font(bold=True)
    ws.cell(row=row, column=6, value=20.0)  # Editable
    ws.cell(row=row, column=6).protection = openpyxl.styles.Protection(locked=False)
    ws.cell(row=row, column=7).value = f"=(G{row-2}+G{row-1})*F{row}/100"
    ws.cell(row=row, column=7).number_format = '#,##0.00'

    row += 1
    ws.cell(row=row, column=5, value="TOTAL EXCL VAT").font = Font(bold=True, size=12)
    ws.cell(row=row, column=7).value = f"=G{row-3}+G{row-2}+G{row-1}"
    ws.cell(row=row, column=7).font = Font(bold=True, size=12)
    ws.cell(row=row, column=7).number_format = '#,##0.00'

    row += 1
    ws.cell(row=row, column=5, value="VAT (15%)").font = Font(bold=True)
    ws.cell(row=row, column=7).value = f"=G{row-1}*0.15"
    ws.cell(row=row, column=7).number_format = '#,##0.00'

    row += 1
    ws.cell(row=row, column=5, value="TOTAL INCL VAT").font = Font(bold=True, size=14)
    ws.cell(row=row, column=7).value = f"=G{row-2}+G{row-1}"
    ws.cell(row=row, column=7).font = Font(bold=True, size=14, color="C00000")
    ws.cell(row=row, column=7).number_format = 'R #,##0.00'

    # Column widths
    ws.column_dimensions['A'].width = 6
    ws.column_dimensions['B'].width = 8
    ws.column_dimensions['C'].width = 55
    ws.column_dimensions['D'].width = 8
    ws.column_dimensions['E'].width = 10
    ws.column_dimensions['F'].width = 15
    ws.column_dimensions['G'].width = 15
    ws.column_dimensions['H'].width = 12
```

### 4.2 exports/pdf_summary.py
One-page PDF using `reportlab` or `fpdf2`. Project summary + estimated range.

---

## Phase 5: Frontend Pages

### 5.1 pages/5_Profile.py — Contractor Profile

```python
"""Contractor Profile — saved preferences for BQ generation."""
import streamlit as st
import json
from pathlib import Path
from agent.models import ContractorProfile, LabourRates

st.title("⚡ Contractor Profile")

# Load from session or file
profile = st.session_state.get("contractor_profile", ContractorProfile())

col1, col2 = st.columns(2)
with col1:
    profile.company_name = st.text_input("Company Name", profile.company_name)
    profile.registration_number = st.text_input("ECSA/CIDB Number", profile.registration_number)
    profile.contact_name = st.text_input("Contact Person", profile.contact_name)
    profile.preferred_supplier = st.selectbox(
        "Preferred Supplier",
        ["Voltex", "ARB Electrical", "Major Tech", "Eurolux", "Other"],
    )

with col2:
    profile.markup_pct = st.number_input("Default Markup (%)", value=profile.markup_pct, step=1.0)
    profile.contingency_pct = st.number_input("Contingency (%)", value=profile.contingency_pct, step=1.0)
    profile.labour_rates.electrician_daily_zar = st.number_input(
        "Electrician Daily Rate (R)", value=profile.labour_rates.electrician_daily_zar
    )
    profile.labour_rates.assistant_daily_zar = st.number_input(
        "Assistant Daily Rate (R)", value=profile.labour_rates.assistant_daily_zar
    )

# Custom prices section
st.subheader("Custom Unit Prices")
st.caption("Override default prices with your supplier quotes")
# ... editable table of common items with custom prices

if st.button("Save Profile", type="primary"):
    st.session_state["contractor_profile"] = profile
    st.success("Profile saved!")
```

### 5.2 pages/1_Upload.py
Multi-file upload. Calls `agent.extract()`. Stores result in session state. Redirects to Review page.

### 5.3 pages/2_Review.py — **THE MAIN SCREEN**

Full implementation as described in CLAUDE.md Stage 4: REVIEW.

Key components:
1. Two-panel layout (st.columns([3,2]))
2. Building block tabs
3. Expandable DB cards with `st.data_editor` for circuit tables
4. Room cards with `st.number_input` for each fixture type
5. Confidence colour badges next to each value
6. Drawing image viewer in right panel
7. Correction tracking (log every edit)
8. Summary bar at bottom (green/yellow/red/blue counts)
9. "Review Complete" button → triggers validate + price

### 5.4 pages/3_Site_Conditions.py
Form matching `SiteConditions` model. Shows calculated multipliers live.

### 5.5 pages/4_Results.py
Tabs: Quantity BQ | Estimated BQ | Validation | Export.
Export buttons for Excel, PDF, ZIP.

---

## Phase 6: Tests

### tests/test_models.py
- All Pydantic models instantiate with defaults
- Computed fields work (total_lights, total_points, labour_multiplier)
- SiteConditions multipliers calculate correctly
- CorrectionLog accuracy_pct calculation

### tests/test_review.py
- ReviewManager tracks corrections
- Accuracy calculation: 100 items, 5 corrected = 95%
- Complete_review sets flag

### tests/test_pricing.py
- Dual BQ generation (quantity has price=0, estimated has prices)
- Site condition multipliers applied to estimated BQ
- Contractor custom prices override defaults
- Excel formulas generate correctly

### tests/test_excel.py
- Workbook has 5 sheets
- Quantity sheet has empty price column
- Total cell contains formula not value
- Confidence colours applied

---

## Verification Checklist

After building all phases, test end-to-end:

1. ✅ Upload 3 Wedela PDFs → DISCOVER extracts ~280 items with confidence flags
2. ✅ Review screen shows items colour-coded green/yellow/red
3. ✅ Edit 5 fixture counts → items turn blue, corrections logged
4. ✅ Click "Review Complete" → validation runs on corrected data
5. ✅ Site conditions: set renovation + difficult access → labour multiplier shows ×1.56
6. ✅ Quantity BQ has ~180 line items with empty price column
7. ✅ Estimated BQ has default prices with "ESTIMATE" label
8. ✅ Download Excel → open in Excel:
   - Quantity sheet: enter R650 in first unit price cell → Total auto-calculates
   - Change contingency from 5% to 8% → grand total updates
   - Estimated sheet: all prices filled, labelled "FOR REFERENCE ONLY"
9. ✅ Correction report shows accuracy percentage
10. ✅ Saved contractor profile persists across sessions

If all 10 pass, the tool is ready for contractor beta testing.
