"""
PRICE Stage: Generate dual BQ — quantity-only + estimated.

v4.1 philosophy: The tool generates QUANTITIES, not final prices.
- quantity_bq: Items + quantities, prices empty (contractor fills in)
- estimated_bq: Same items with default prices (ballpark reference only)
"""

from typing import Tuple, Optional, List

from agent.models import (
    ExtractionResult, ValidationResult, PricingResult, StageResult,
    PipelineStage, BQLineItem, BQSection, BlockPricingSummary,
    ItemConfidence, ContractorProfile, SiteConditions
)
from agent.utils import Timer


def price(
    extraction: ExtractionResult,
    validation: Optional[ValidationResult] = None,
    contractor: Optional[ContractorProfile] = None,
    site: Optional[SiteConditions] = None,
) -> Tuple[PricingResult, StageResult]:
    """
    PRICE stage: Generate dual BQ.

    Args:
        extraction: Validated extraction result
        validation: Validation result with compliance additions
        contractor: Contractor profile with custom prices
        site: Site conditions affecting pricing

    Returns:
        Tuple of (PricingResult, StageResult)
    """
    with Timer("price") as timer:
        result = PricingResult()
        errors = []
        warnings = []

        quantity_items: List[BQLineItem] = []
        item_no = 0

        # Process each building block
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

                # Add ELCB if present
                if db.earth_leakage:
                    item_no += 1
                    quantity_items.append(BQLineItem(
                        item_no=item_no,
                        section=BQSection.DISTRIBUTION,
                        description=f"ELCB {db.earth_leakage_rating_a}A 30mA — {db.name}",
                        unit="each",
                        qty=1,
                        source=db.confidence,
                        building_block=block.name,
                    ))

                # Add surge protection if present
                if db.surge_protection:
                    item_no += 1
                    quantity_items.append(BQLineItem(
                        item_no=item_no,
                        section=BQSection.DISTRIBUTION,
                        description=f"Surge Protection Device Type 2 — {db.name}",
                        unit="each",
                        qty=1,
                        source=db.confidence,
                        building_block=block.name,
                    ))

            # Section C: Cables per circuit
            for db in block.distribution_boards:
                for circuit in db.active_circuits:
                    if circuit.type == "sub_board_feed":
                        continue  # Handled in site cables

                    item_no += 1
                    cable_desc = f"{circuit.cable_size_mm2}mm² {circuit.cable_cores}C {circuit.cable_type}"
                    length = circuit.feed_cable_length_m or _estimate_cable_length(circuit)

                    notes = ""
                    if circuit.confidence == ItemConfidence.ESTIMATED:
                        notes = "AI estimated length - verify on site"

                    quantity_items.append(BQLineItem(
                        item_no=item_no,
                        section=BQSection.CABLES,
                        description=f"{cable_desc} — {db.name} {circuit.id} ({circuit.description})",
                        unit="m",
                        qty=length,
                        source=circuit.confidence,
                        building_block=block.name,
                        notes=notes,
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

            # Section E: Switches & Controls (v4.2 - split from sockets)
            for room in block.rooms:
                f = room.fixtures
                switch_map = [
                    ("switch_1lever_1way", "1-Lever 1-Way Switch @1200mm", f.switch_1lever_1way),
                    ("switch_2lever_1way", "2-Lever 1-Way Switch @1200mm", f.switch_2lever_1way),
                    ("switch_1lever_2way", "1-Lever 2-Way Switch @1200mm", f.switch_1lever_2way),
                    ("day_night_switch", "Day/Night Switch @2000mm", f.day_night_switch),
                    ("isolator_30a", "30A Isolator Switch @2000mm", f.isolator_30a),
                    ("isolator_20a", "20A Isolator Switch @2000mm", f.isolator_20a),
                    ("master_switch", "Master Switch", f.master_switch),
                ]
                for field_name, desc, qty in switch_map:
                    if qty > 0:
                        item_no += 1
                        quantity_items.append(BQLineItem(
                            item_no=item_no,
                            section=BQSection.SWITCHES,
                            description=f"{desc} — {room.name}",
                            unit="each",
                            qty=qty,
                            source=room.confidence,
                            building_block=block.name,
                        ))

            # Section F: Power Sockets (v4.2 - sockets only)
            for room in block.rooms:
                f = room.fixtures
                socket_map = [
                    ("double_socket_300", "16A Double Switched Socket @300mm", f.double_socket_300),
                    ("single_socket_300", "16A Single Switched Socket @300mm", f.single_socket_300),
                    ("double_socket_1100", "16A Double Switched Socket @1100mm", f.double_socket_1100),
                    ("single_socket_1100", "16A Single Switched Socket @1100mm", f.single_socket_1100),
                    ("double_socket_waterproof", "16A Double Waterproof Socket", f.double_socket_waterproof),
                    ("double_socket_ceiling", "16A Double Ceiling Socket", f.double_socket_ceiling),
                    ("data_points_cat6", "CAT6 Data Point", f.data_points_cat6),
                    ("floor_box", "Floor Box with Power + Data", f.floor_box),
                ]
                for field_name, desc, qty in socket_map:
                    if qty > 0:
                        item_no += 1
                        quantity_items.append(BQLineItem(
                            item_no=item_no,
                            section=BQSection.SOCKETS,
                            description=f"{desc} — {room.name}",
                            unit="each",
                            qty=qty,
                            source=room.confidence,
                            building_block=block.name,
                        ))

            # Section G: Air Conditioning Electrical (v4.2 - dedicated AC section)
            for equip in block.heavy_equipment:
                if equip.type.lower() in ("ac", "air_con", "aircon", "hvac", "split_unit"):
                    item_no += 1
                    vsd_label = " with VSD" if equip.has_vsd else ""
                    quantity_items.append(BQLineItem(
                        item_no=item_no,
                        section=BQSection.AC_ELECTRICAL,
                        description=f"{equip.name} electrical connection ({equip.rating_kw}kW{vsd_label})",
                        unit="each",
                        qty=equip.qty,
                        source=equip.confidence,
                        building_block=block.name,
                    ))
                    # Add isolator for AC
                    item_no += 1
                    quantity_items.append(BQLineItem(
                        item_no=item_no,
                        section=BQSection.AC_ELECTRICAL,
                        description=f"AC Isolator 32A for {equip.name}",
                        unit="each",
                        qty=equip.qty,
                        source=equip.confidence,
                        building_block=block.name,
                    ))

            # Other heavy equipment (pumps, geysers, motors) → Cables section
            for equip in block.heavy_equipment:
                if equip.type.lower() not in ("ac", "air_con", "aircon", "hvac", "split_unit"):
                    item_no += 1
                    vsd_label = " with VSD" if equip.has_vsd else ""
                    quantity_items.append(BQLineItem(
                        item_no=item_no,
                        section=BQSection.CABLES,
                        description=f"{equip.name} dedicated circuit ({equip.rating_kw}kW{vsd_label})",
                        unit="each",
                        qty=equip.qty,
                        source=equip.confidence,
                        building_block=block.name,
                        notes="Includes cable, breaker, and connection",
                    ))

        # Section H: External & Solar (v4.2 - site cable runs)
        for run in extraction.site_cable_runs:
            item_no += 1
            notes = "Distance from drawing" if run.confidence == ItemConfidence.EXTRACTED else "Distance estimated"
            quantity_items.append(BQLineItem(
                item_no=item_no,
                section=BQSection.EXTERNAL,
                description=f"{run.cable_spec} — {run.from_point} to {run.to_point}",
                unit="m",
                qty=run.length_m,
                source=run.confidence,
                notes=notes,
            ))

            if run.needs_trenching:
                item_no += 1
                quantity_items.append(BQLineItem(
                    item_no=item_no,
                    section=BQSection.EXTERNAL,
                    description=f"Trenching 600mm deep — {run.from_point} to {run.to_point}",
                    unit="m",
                    qty=run.length_m,
                    source=run.confidence,
                ))

        # Section I: Earthing & Bonding (v4.2 - new section)
        # Add basic earthing items for each supply point
        for supply in extraction.supply_points:
            item_no += 1
            quantity_items.append(BQLineItem(
                item_no=item_no,
                section=BQSection.EARTHING,
                description=f"Earth electrode 1.5m copper-clad — {supply.name}",
                unit="each",
                qty=1,
                source=ItemConfidence.INFERRED,
                notes="Per SANS 10142-1 Clause 8",
            ))
            item_no += 1
            quantity_items.append(BQLineItem(
                item_no=item_no,
                section=BQSection.EARTHING,
                description=f"Earth bar and connections — {supply.name}",
                unit="each",
                qty=1,
                source=ItemConfidence.INFERRED,
            ))

        # Add main bonding for each building block
        for block in extraction.building_blocks:
            item_no += 1
            quantity_items.append(BQLineItem(
                item_no=item_no,
                section=BQSection.EARTHING,
                description=f"Main bonding conductor 16mm² — {block.name}",
                unit="m",
                qty=15,  # Default estimate
                source=ItemConfidence.ESTIMATED,
                building_block=block.name,
                notes="Bonding to water/gas pipes per Clause 8.3",
            ))

        # Compliance additions from validation (v4.2 - route to appropriate sections)
        if validation:
            for flag in validation.flags:
                if flag.auto_corrected and not flag.passed:
                    # Route compliance items to appropriate sections
                    section = BQSection.DISTRIBUTION  # Default
                    if "earth" in flag.corrected_value.lower():
                        section = BQSection.EARTHING
                    elif "surge" in flag.corrected_value.lower():
                        section = BQSection.DISTRIBUTION
                    elif "elcb" in flag.corrected_value.lower() or "rcd" in flag.corrected_value.lower():
                        section = BQSection.DISTRIBUTION

                    item_no += 1
                    quantity_items.append(BQLineItem(
                        item_no=item_no,
                        section=section,
                        description=f"Compliance: {flag.corrected_value}",
                        unit="each",
                        qty=1,
                        source=ItemConfidence.INFERRED,
                        notes=f"Added per {flag.standard_ref}: {flag.message}",
                    ))

        # Section J: Testing & Commissioning (v4.2)
        total_circuits = extraction.total_circuits
        total_dbs = extraction.total_dbs
        total_supplies = len(extraction.supply_points) or 1

        testing_items = [
            (f"Insulation resistance testing ({total_circuits} circuits)", "circuit", total_circuits),
            (f"Earth continuity testing ({total_dbs} boards)", "each", total_dbs),
            (f"Polarity testing ({total_circuits} circuits)", "circuit", total_circuits),
            (f"RCD/ELCB testing ({total_dbs} boards)", "each", total_dbs),
            (f"COC certification ({total_supplies} supplies)", "each", total_supplies),
        ]
        for desc, unit, qty in testing_items:
            if qty > 0:
                item_no += 1
                quantity_items.append(BQLineItem(
                    item_no=item_no,
                    section=BQSection.TESTING,
                    description=desc,
                    unit=unit,
                    qty=qty,
                    source=ItemConfidence.INFERRED,
                    is_rate_only=True,
                ))

        # Section K: Preliminaries & General (v4.2)
        total_points = extraction.total_points
        total_heavy = len(extraction.all_heavy_equipment)

        prelim_items = [
            (f"Circuit installation labour ({total_circuits} circuits)", "circuit", total_circuits),
            (f"Point installation labour ({total_points} points)", "point", total_points),
            (f"DB installation and wiring ({total_dbs} boards)", "each", total_dbs),
            (f"Heavy equipment connection ({total_heavy} units)", "each", total_heavy),
            ("Site establishment", "item", 1),
            ("Health & safety compliance", "item", 1),
            ("As-built drawings", "set", 1),
        ]
        for desc, unit, qty in prelim_items:
            if qty > 0:
                item_no += 1
                quantity_items.append(BQLineItem(
                    item_no=item_no,
                    section=BQSection.PRELIMS,
                    description=desc,
                    unit=unit,
                    qty=qty,
                    source=ItemConfidence.INFERRED,
                    is_rate_only=True,
                ))

        # Store quantity BQ (primary deliverable)
        result.quantity_bq = quantity_items
        result.total_items = len(quantity_items)

        # Generate Estimated BQ (copy quantity items + add default prices)
        estimated_items = []
        for item in quantity_items:
            est_item = item.model_copy()
            price_val = _get_default_price(est_item, contractor)
            est_item.unit_price_zar = price_val
            est_item.total_zar = round(price_val * est_item.qty, 2)
            estimated_items.append(est_item)

        # Apply site condition multipliers (v4.2 - updated sections)
        if site:
            for item in estimated_items:
                if item.section == BQSection.PRELIMS:
                    item.total_zar = round(item.total_zar * site.labour_multiplier, 2)
                if item.section == BQSection.EXTERNAL:
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

        # Build stage result
        stage_result = StageResult(
            stage=PipelineStage.PRICE,
            success=True,
            confidence=result.quantity_confidence,
            data={
                "total_items": result.total_items,
                "items_extracted": result.items_from_extraction,
                "items_estimated": result.items_estimated,
                "estimate_total_zar": result.estimate_total_incl_vat_zar,
            },
            processing_time_ms=timer.elapsed_ms,
            errors=errors,
            warnings=warnings,
        )

        return result, stage_result


def _estimate_cable_length(circuit) -> float:
    """Default cable length estimates when not on drawing."""
    if circuit.type in ("sub_board_feed",):
        return 15.0  # Same floor default
    if circuit.type in ("lighting", "power"):
        return 8.0   # Average circuit run
    if circuit.type in ("ac", "geyser", "pump"):
        return 12.0  # Dedicated circuit
    return 10.0


def _get_default_price(item: BQLineItem, contractor: Optional[ContractorProfile] = None) -> float:
    """Look up default unit price. Use contractor custom price if available."""
    # Check contractor custom prices first
    if contractor and item.description in contractor.custom_prices:
        return contractor.custom_prices[item.description]

    # Default prices (ZAR) - simplified lookup
    default_prices = {
        # Lights
        "600×1200 Recessed LED 3×18W": 650.0,
        "18W LED Surface Mount": 280.0,
        "30W LED Flood Light": 450.0,
        "200W LED Flood Light": 2800.0,
        "6W LED Downlight White": 180.0,
        "2×24W Vapor Proof LED (IP65)": 850.0,
        "2×18W Vapor Proof LED": 720.0,
        "2×18W Prismatic LED": 580.0,
        "26W Bulkhead Outdoor": 380.0,
        "24W Bulkhead Outdoor": 350.0,
        "50W 5ft Fluorescent": 320.0,
        "Outdoor Pole Light 2300mm 60W (incl. pole + base)": 4500.0,

        # Sockets
        "16A Double Switched Socket @300mm": 160.0,
        "16A Single Switched Socket @300mm": 120.0,
        "16A Double Switched Socket @1100mm": 180.0,
        "16A Single Switched Socket @1100mm": 140.0,
        "16A Double Waterproof Socket": 280.0,
        "16A Double Ceiling Socket": 200.0,
        "CAT6 Data Point": 450.0,
        "Floor Box with Power + Data": 1800.0,

        # Switches
        "1-Lever 1-Way Switch @1200mm": 60.0,
        "2-Lever 1-Way Switch @1200mm": 95.0,
        "1-Lever 2-Way Switch @1200mm": 85.0,
        "Day/Night Switch @2000mm": 450.0,
        "30A Isolator Switch @2000mm": 320.0,
        "20A Isolator Switch @2000mm": 280.0,
        "Master Switch": 550.0,

        # Labour rates
        "circuit": 450.0,
        "point": 85.0,
        "each": 1500.0,  # DB install

        # Site works
        "Trenching 600mm deep": 180.0,  # per meter
    }

    # Try exact match
    for key, price_val in default_prices.items():
        if key in item.description:
            return price_val

    # Section-based defaults (v4.2 - 11 sections)
    section_defaults = {
        BQSection.DISTRIBUTION: 2500.0,
        BQSection.CABLES: 25.0,  # per meter average
        BQSection.CONTAINMENT: 45.0,  # per meter
        BQSection.LIGHTS: 500.0,
        BQSection.SWITCHES: 80.0,
        BQSection.SOCKETS: 150.0,
        BQSection.AC_ELECTRICAL: 2500.0,
        BQSection.EXTERNAL: 180.0,  # per meter
        BQSection.EARTHING: 850.0,
        BQSection.TESTING: 350.0,
        BQSection.PRELIMS: 450.0,
    }

    return section_defaults.get(item.section, 100.0)
