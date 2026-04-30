"""
Stage P5 — Generate BoQ from a PdfExtraction.

Aggregates fixture counts across rooms and emits a BillOfQuantities
matching the canonical 14-section taxonomy. Pricing uses defaults
from core.constants when an estimated BQ is requested.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from typing import Dict, List

from agent.pdf_pipeline.models import PdfExtraction
from agent.shared import (
    BillOfQuantities,
    BQLineItem,
    BQSection,
    ContractorProfile,
    ItemConfidence,
)
from core.constants import LIGHT_PRICES, SOCKET_PRICES, SWITCH_PRICES


# Map fixture-counts attribute → (description, BQ section, default price key, source dict)
_FIXTURE_MAP: List[tuple] = [
    ("downlights",            "LED Downlight",            BQSection.LIGHTING,      "downlight_led_12w",         LIGHT_PRICES),
    ("panel_lights",          "LED Panel 600x600",        BQSection.LIGHTING,      "recessed_led_600x600",      LIGHT_PRICES),
    ("bulkheads",             "Bulkhead Light",           BQSection.LIGHTING,      "bulkhead_24w",              LIGHT_PRICES),
    ("floodlights",           "Floodlight LED 50W",       BQSection.LIGHTING,      "flood_light_50w",           LIGHT_PRICES),
    ("emergency_lights",      "Emergency Light LED",      BQSection.FIRE_SAFETY,   "emergency_light_led",       LIGHT_PRICES),
    ("exit_signs",            "Exit Sign LED",            BQSection.FIRE_SAFETY,   "exit_sign_led",             LIGHT_PRICES),
    ("pool_flood_light",      "Pool Floodlight",          BQSection.LIGHTING,      "flood_light_50w",           LIGHT_PRICES),
    ("pool_underwater_light", "Pool Underwater Light",    BQSection.LIGHTING,      "flood_light_30w",           LIGHT_PRICES),

    ("double_sockets",        "Double Switched Socket 16A",   BQSection.POWER_OUTLETS, "double_socket_300",     SOCKET_PRICES),
    ("single_sockets",        "Single Switched Socket 16A",   BQSection.POWER_OUTLETS, "single_socket_300",     SOCKET_PRICES),
    ("waterproof_sockets",    "Waterproof Double Socket",     BQSection.POWER_OUTLETS, "double_socket_waterproof", SOCKET_PRICES),
    ("floor_sockets",         "Floor Box Power+Data",         BQSection.POWER_OUTLETS, "floor_box",             SOCKET_PRICES),
    ("data_outlets",          "Data Outlet CAT6",             BQSection.DATA_COMMS,    "data_points_cat6",      SOCKET_PRICES),
]


def _switch_price(key: str) -> float:
    return SWITCH_PRICES.get(key, 0.0) if isinstance(SWITCH_PRICES, dict) else 0.0


def generate_boq(
    extraction: PdfExtraction,
    *,
    project_name: str,
    run_id: str,
    contractor: ContractorProfile | None = None,
    include_estimated_pricing: bool = True,
) -> BillOfQuantities:
    contractor = contractor or ContractorProfile()

    section_buckets: Dict[BQSection, List[BQLineItem]] = defaultdict(list)

    # ── 1. Aggregate fixtures across rooms ───────────────────────────
    totals: Dict[str, int] = defaultdict(int)
    for room in extraction.fixtures_per_room.values():
        for attr, *_ in _FIXTURE_MAP:
            totals[attr] += getattr(room, attr, 0) or 0
        # Switches are billed by lever-count; aggregate separately below
        for sw_attr in ("switches_1lever", "switches_2lever", "switches_3lever",
                        "isolators", "day_night_switches"):
            totals[sw_attr] += getattr(room, sw_attr, 0) or 0

    # ── 2. Build line items for fixtures we have ─────────────────────
    for attr, desc, section, price_key, prices in _FIXTURE_MAP:
        qty = totals.get(attr, 0)
        if qty <= 0:
            continue
        unit_price = float(prices.get(price_key, 0.0)) if include_estimated_pricing else 0.0
        section_buckets[section].append(
            BQLineItem(
                section=section,
                category="PDF Extraction",
                description=desc,
                unit="each",
                qty=float(qty),
                unit_price_zar=unit_price,
                total_zar=round(qty * unit_price, 2),
                source=ItemConfidence.EXTRACTED,
                drawing_ref="PDF",
            )
        )

    # ── 3. Switches as their own bucket ──────────────────────────────
    for attr, desc, price_key in [
        ("switches_1lever",     "Light Switch 1-Lever",     "switch_1_lever"),
        ("switches_2lever",     "Light Switch 2-Lever",     "switch_2_lever"),
        ("switches_3lever",     "Light Switch 3-Lever",     "switch_3_lever"),
        ("isolators",           "Isolator Switch 20A",      "isolator_20a"),
        ("day_night_switches",  "Day/Night Switch + Bypass","day_night_switch"),
    ]:
        qty = totals.get(attr, 0)
        if qty <= 0:
            continue
        unit_price = _switch_price(price_key) if include_estimated_pricing else 0.0
        section_buckets[BQSection.LIGHTING].append(
            BQLineItem(
                section=BQSection.LIGHTING,
                category="PDF Extraction",
                description=desc,
                unit="each",
                qty=float(qty),
                unit_price_zar=unit_price,
                total_zar=round(qty * unit_price, 2),
                source=ItemConfidence.EXTRACTED,
                drawing_ref="PDF",
            )
        )

    # ── 4. Distribution boards as line items ─────────────────────────
    for db in extraction.distribution_boards:
        section_buckets[BQSection.DISTRIBUTION].append(
            BQLineItem(
                section=BQSection.DISTRIBUTION,
                category="Distribution Board",
                description=f"{db.name} ({db.main_breaker_a}A {db.phases}-ph)",
                unit="each",
                qty=1.0,
                unit_price_zar=0.0,
                total_zar=0.0,
                source=ItemConfidence.EXTRACTED,
                drawing_ref="PDF SLD",
                is_rate_only=not include_estimated_pricing,
                circuit_details=f"{len(db.circuits)} circuits",
            )
        )

    # ── 5. Flatten, number, total ────────────────────────────────────
    line_items: List[BQLineItem] = []
    for section in sorted(section_buckets.keys(), key=lambda s: s.section_number):
        for idx, item in enumerate(section_buckets[section], start=1):
            item.item_no = idx
            line_items.append(item)

    subtotal = sum(it.total_zar for it in line_items)
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
        pipeline="pdf",
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
