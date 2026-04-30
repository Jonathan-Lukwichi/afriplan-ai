"""
Stage D5 — Generate.

Convert a DxfExtraction into a BillOfQuantities. Since the DXF
extraction is precise about counts and lengths, the BQ items are
likewise precise. Pricing is ballpark (default unit prices from
patterns.py) — contractor overrides per their profile downstream.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from typing import Dict, List

from agent.dxf_pipeline.models import DxfExtraction
from agent.dxf_pipeline.patterns import (
    EXACT_BLOCK_MAP,
    REGEX_BLOCK_PATTERNS,
    FixtureCategory,
)
from agent.shared import (
    BillOfQuantities,
    BQLineItem,
    BQSection,
    ContractorProfile,
    ItemConfidence,
)


# Map fixture category → BQ section
_CATEGORY_TO_SECTION: Dict[FixtureCategory, BQSection] = {
    FixtureCategory.LIGHTING: BQSection.LIGHTING,
    FixtureCategory.POWER: BQSection.POWER_OUTLETS,
    FixtureCategory.SWITCH: BQSection.LIGHTING,
    FixtureCategory.DATA: BQSection.DATA_COMMS,
    FixtureCategory.SAFETY: BQSection.FIRE_SAFETY,
    FixtureCategory.HVAC: BQSection.FINAL_CABLES,
    FixtureCategory.WATER: BQSection.FINAL_CABLES,
    FixtureCategory.DISTRIBUTION: BQSection.DISTRIBUTION,
    FixtureCategory.OTHER: BQSection.FINAL_CABLES,
}


def _lookup_unit_price(canonical_name: str) -> float:
    """Return the default unit price for a canonical fixture name (or 0)."""
    for spec in EXACT_BLOCK_MAP.values():
        if spec.canonical_name == canonical_name:
            return spec.default_unit_price_zar
    for _, spec in REGEX_BLOCK_PATTERNS:
        if spec.canonical_name == canonical_name:
            return spec.default_unit_price_zar
    return 0.0


def _lookup_section(canonical_name: str) -> BQSection:
    """Return the BQSection for a canonical name (defaults to FINAL_CABLES)."""
    for spec in EXACT_BLOCK_MAP.values():
        if spec.canonical_name == canonical_name:
            return _CATEGORY_TO_SECTION.get(spec.category, BQSection.FINAL_CABLES)
    for _, spec in REGEX_BLOCK_PATTERNS:
        if spec.canonical_name == canonical_name:
            return _CATEGORY_TO_SECTION.get(spec.category, BQSection.FINAL_CABLES)
    return BQSection.FINAL_CABLES


def generate_boq(
    extraction: DxfExtraction,
    project_name: str,
    run_id: str,
    contractor: ContractorProfile | None = None,
    *,
    include_estimated_pricing: bool = True,
) -> BillOfQuantities:
    """
    Build a BQ from extracted block counts plus polyline-derived cable runs.
    """
    contractor = contractor or ContractorProfile()

    # ── 1. One BQ line per recognised fixture type ───────────────────
    section_buckets: Dict[BQSection, List[BQLineItem]] = defaultdict(list)

    for canonical_name, qty in sorted(
        extraction.block_counts_by_type.items(),
        key=lambda kv: (-kv[1], kv[0]),
    ):
        section = _lookup_section(canonical_name)
        unit_price = _lookup_unit_price(canonical_name) if include_estimated_pricing else 0.0
        total = round(qty * unit_price, 2)

        section_buckets[section].append(
            BQLineItem(
                section=section,
                category="DXF Extraction",
                description=canonical_name,
                unit="each",
                qty=float(qty),
                unit_price_zar=unit_price,
                total_zar=total,
                source=ItemConfidence.EXTRACTED,
                drawing_ref="DXF",
                notes="Counted from INSERT block references",
            )
        )

    # ── 2. Cable runs from polyline length on electrical layers ──────
    if extraction.total_polyline_length_m > 0:
        cable_unit_price = 35.0   # nominal R/m for 2.5mm² SURFIX
        polyline_total = round(extraction.total_polyline_length_m, 2)
        cable_total = round(polyline_total * cable_unit_price, 2) if include_estimated_pricing else 0.0

        section_buckets[BQSection.FINAL_CABLES].append(
            BQLineItem(
                section=BQSection.FINAL_CABLES,
                category="Cable run length",
                description="Final-circuit cable (geometry-derived, sized by contractor)",
                unit="m",
                qty=polyline_total,
                unit_price_zar=cable_unit_price if include_estimated_pricing else 0.0,
                total_zar=cable_total,
                source=ItemConfidence.INFERRED,
                drawing_ref="DXF polylines",
                is_rate_only=not include_estimated_pricing,
                notes=(
                    "Length is the sum of LINE/POLYLINE entities on electrical layers. "
                    "Contractor must decide cable sizing per circuit."
                ),
            )
        )

    # ── 3. Flatten, number, and total ────────────────────────────────
    line_items: List[BQLineItem] = []
    for section in sorted(section_buckets.keys(), key=lambda s: s.section_number):
        for idx, item in enumerate(section_buckets[section], start=1):
            item.item_no = idx
            line_items.append(item)

    subtotal = sum(item.total_zar for item in line_items)
    contingency = round(subtotal * (contractor.contingency_pct / 100.0), 2)
    markup = round(subtotal * (contractor.markup_pct / 100.0), 2)
    total_excl_vat = round(subtotal + contingency + markup, 2)
    vat = round(total_excl_vat * (contractor.vat_pct / 100.0), 2)
    total_incl_vat = round(total_excl_vat + vat, 2)

    items_extracted = sum(1 for it in line_items if it.source == ItemConfidence.EXTRACTED)
    items_inferred = sum(1 for it in line_items if it.source == ItemConfidence.INFERRED)
    items_estimated = sum(1 for it in line_items if it.source == ItemConfidence.ESTIMATED)
    items_rate_only = sum(1 for it in line_items if it.is_rate_only)

    return BillOfQuantities(
        project_name=project_name,
        pipeline="dxf",
        run_id=run_id,
        generated_at=datetime.utcnow(),
        line_items=line_items,
        contractor_markup_pct=contractor.markup_pct,
        contingency_pct=contractor.contingency_pct,
        vat_pct=contractor.vat_pct,
        subtotal_zar=round(subtotal, 2),
        contingency_zar=contingency,
        markup_zar=markup,
        total_excl_vat_zar=total_excl_vat,
        vat_zar=vat,
        total_incl_vat_zar=total_incl_vat,
        items_extracted=items_extracted,
        items_inferred=items_inferred,
        items_estimated=items_estimated,
        items_rate_only=items_rate_only,
    )
