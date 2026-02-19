"""
PRICE Stage: Generate dual BQ — quantity-only + estimated.

v4.6 - Professional BOQ format (14 sections, industry standard).
Based on Wedela Electrical BOQ reference files.

v4.1 philosophy: The tool generates QUANTITIES, not final prices.
- quantity_bq: Items + quantities, prices empty (contractor fills in)
- estimated_bq: Same items with default prices (ballpark reference only)
"""

from typing import Tuple, Optional, List, Dict
from collections import defaultdict

from agent.models import (
    ExtractionResult, ValidationResult, PricingResult, StageResult,
    PipelineStage, BQLineItem, BQSection, BlockPricingSummary,
    ItemConfidence, ContractorProfile, SiteConditions, DistributionBoard
)
from agent.utils import Timer


def price(
    extraction: ExtractionResult,
    validation: Optional[ValidationResult] = None,
    contractor: Optional[ContractorProfile] = None,
    site: Optional[SiteConditions] = None,
) -> Tuple[PricingResult, StageResult]:
    """
    PRICE stage: Generate dual BQ with professional 14-section format.

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

        # Track items by section for hierarchical numbering
        section_item_counts: Dict[BQSection, int] = defaultdict(int)

        def next_item_no(section: BQSection) -> int:
            """Get next item number within section for hierarchical numbering."""
            section_item_counts[section] += 1
            return section_item_counts[section]

        quantity_items: List[BQLineItem] = []

        # Get drawing references from metadata
        drawing_refs = extraction.metadata.drawing_numbers or []
        default_drawing_ref = ", ".join(drawing_refs[:2]) if drawing_refs else ""

        # ═══════════════════════════════════════════════════════════════════════════
        # SECTION 1: MAIN INCOMING SUPPLY & METERING
        # ═══════════════════════════════════════════════════════════════════════════
        for supply in extraction.supply_points:
            # 1.1 Kiosk/metering enclosure
            quantity_items.append(BQLineItem(
                item_no=next_item_no(BQSection.INCOMING),
                section=BQSection.INCOMING,
                description=f"Kiosk metering enclosure complete with Eskom-approved meter panel, CT chamber, and all accessories — {supply.name}",
                unit="No",
                qty=1,
                source=supply.confidence if hasattr(supply, 'confidence') else ItemConfidence.INFERRED,
                drawing_ref=default_drawing_ref,
            ))

            # 1.2 Incoming cable from transformer
            if supply.cable_size_mm2 and supply.cable_size_mm2 > 0:
                cable_desc = f"{supply.cable_size_mm2}mm² x 4C PVC SWA PVC LV cable from transformer to main kiosk metering, incl. terminations, glands, lugs"
            else:
                cable_desc = "95mm² x 4C PVC SWA PVC LV cable from transformer to main kiosk metering, incl. terminations, glands, lugs"

            quantity_items.append(BQLineItem(
                item_no=next_item_no(BQSection.INCOMING),
                section=BQSection.INCOMING,
                description=cable_desc,
                unit="m",
                qty=30,  # Default estimate
                source=ItemConfidence.ESTIMATED,
                drawing_ref=default_drawing_ref,
                notes="Length to be verified on site",
            ))

            # 1.3 Cable trenching for incoming supply
            quantity_items.append(BQLineItem(
                item_no=next_item_no(BQSection.INCOMING),
                section=BQSection.INCOMING,
                description="Cable trenching, backfilling, compaction and marker tape for incoming LV supply cable route",
                unit="m",
                qty=30,
                source=ItemConfidence.ESTIMATED,
                drawing_ref=default_drawing_ref,
            ))

            # 1.4 Earth electrode
            quantity_items.append(BQLineItem(
                item_no=next_item_no(BQSection.INCOMING),
                section=BQSection.INCOMING,
                description=f"Earth electrode installation complete - copper-clad earth rod, earth clamp, 25mm² BCEW to main earth bar — {supply.name}",
                unit="No",
                qty=1,
                source=ItemConfidence.INFERRED,
                drawing_ref=default_drawing_ref,
            ))

            # 1.5 Main earth bar
            quantity_items.append(BQLineItem(
                item_no=next_item_no(BQSection.INCOMING),
                section=BQSection.INCOMING,
                description="Main earth bar with connections and labels",
                unit="No",
                qty=1,
                source=ItemConfidence.INFERRED,
                drawing_ref=default_drawing_ref,
            ))

        # ═══════════════════════════════════════════════════════════════════════════
        # SECTION 2: DISTRIBUTION BOARDS
        # ═══════════════════════════════════════════════════════════════════════════
        for block in extraction.building_blocks:
            for db in block.distribution_boards:
                # Generate detailed DB description with circuit schedule
                db_desc = _generate_db_description(db, extraction.metadata)
                subsection = f"2{chr(65 + block.distribution_boards.index(db))} - {db.name}"

                quantity_items.append(BQLineItem(
                    item_no=next_item_no(BQSection.DISTRIBUTION),
                    section=BQSection.DISTRIBUTION,
                    subsection=subsection,
                    description=db_desc,
                    unit="No",
                    qty=1,
                    source=db.confidence,
                    building_block=block.name,
                    drawing_ref=default_drawing_ref,
                ))

        # ═══════════════════════════════════════════════════════════════════════════
        # SECTION 3: SUB-MAIN DISTRIBUTION CABLES
        # ═══════════════════════════════════════════════════════════════════════════
        for block in extraction.building_blocks:
            for db in block.distribution_boards:
                for circuit in db.circuits:
                    if circuit.type == "sub_board_feed":
                        cable_spec = f"{circuit.cable_cores or 3}Cx{circuit.cable_size_mm2}mm² PVC SWA PVC cable"
                        to_db = circuit.description or f"sub-DB from {db.name}"

                        quantity_items.append(BQLineItem(
                            item_no=next_item_no(BQSection.SUBMAIN_CABLES),
                            section=BQSection.SUBMAIN_CABLES,
                            description=f"{cable_spec}: {db.name} -> {to_db}, incl. glands, lugs, terminations",
                            unit="m",
                            qty=circuit.feed_cable_length_m or 15,
                            source=circuit.confidence,
                            building_block=block.name,
                            drawing_ref=default_drawing_ref,
                        ))

        # ═══════════════════════════════════════════════════════════════════════════
        # SECTION 4: FINAL SUB-CIRCUIT CABLES
        # ═══════════════════════════════════════════════════════════════════════════
        # 4A - Power Circuit Cables (2.5mm²)
        for block in extraction.building_blocks:
            for db in block.distribution_boards:
                power_circuits = [c for c in db.active_circuits
                                  if c.type in ("power", "socket") and c.type != "sub_board_feed"]
                for circuit in power_circuits:
                    cable_size = circuit.cable_size_mm2 or 2.5
                    points = circuit.num_points or 1
                    wattage = circuit.wattage_w or 3680

                    quantity_items.append(BQLineItem(
                        item_no=next_item_no(BQSection.FINAL_CABLES),
                        section=BQSection.FINAL_CABLES,
                        subsection="4A - Power Circuit Cables (2.5mm²)",
                        description=f"{cable_size}mm² T&E: {db.name} {circuit.id} ({points} points, {wattage:.0f}W)",
                        unit="m",
                        qty=circuit.feed_cable_length_m or _estimate_cable_length(circuit),
                        source=circuit.confidence,
                        building_block=block.name,
                        circuit_details=f"({points} points, {wattage:.0f}W)",
                        drawing_ref=default_drawing_ref,
                    ))

        # 4B - Lighting Circuit Cables (1.5mm²)
        for block in extraction.building_blocks:
            for db in block.distribution_boards:
                lighting_circuits = [c for c in db.active_circuits
                                     if c.type in ("lighting", "light") and c.type != "sub_board_feed"]
                for circuit in lighting_circuits:
                    cable_size = circuit.cable_size_mm2 or 1.5
                    points = circuit.num_points or 1
                    wattage = circuit.wattage_w or 100

                    quantity_items.append(BQLineItem(
                        item_no=next_item_no(BQSection.FINAL_CABLES),
                        section=BQSection.FINAL_CABLES,
                        subsection="4B - Lighting Circuit Cables (1.5mm²)",
                        description=f"{cable_size}mm² T&E: {db.name} {circuit.id} ({points} points, {wattage:.0f}W)",
                        unit="m",
                        qty=circuit.feed_cable_length_m or _estimate_cable_length(circuit),
                        source=circuit.confidence,
                        building_block=block.name,
                        circuit_details=f"({points} points, {wattage:.0f}W)",
                        drawing_ref=default_drawing_ref,
                    ))

        # 4C - AC Circuit Cables (2.5mm²)
        for block in extraction.building_blocks:
            for db in block.distribution_boards:
                ac_circuits = [c for c in db.active_circuits
                               if c.type in ("ac", "aircon", "hvac") and c.type != "sub_board_feed"]
                for circuit in ac_circuits:
                    cable_size = circuit.cable_size_mm2 or 2.5
                    wattage = circuit.wattage_w or 1650

                    quantity_items.append(BQLineItem(
                        item_no=next_item_no(BQSection.FINAL_CABLES),
                        section=BQSection.FINAL_CABLES,
                        subsection="4C - Air Conditioning Circuit Cables (2.5mm²)",
                        description=f"{cable_size}mm² T&E: {db.name} {circuit.id} (1 point, {wattage:.0f}W)",
                        unit="m",
                        qty=circuit.feed_cable_length_m or _estimate_cable_length(circuit),
                        source=circuit.confidence,
                        building_block=block.name,
                        circuit_details=f"(1 point, {wattage:.0f}W)",
                        drawing_ref=default_drawing_ref,
                    ))

        # ═══════════════════════════════════════════════════════════════════════════
        # SECTION 5: LIGHTING INSTALLATION
        # ═══════════════════════════════════════════════════════════════════════════
        # Aggregate light fittings by type across all rooms
        light_aggregation: Dict[str, Dict] = defaultdict(lambda: {"qty": 0, "locations": [], "rooms": []})

        for block in extraction.building_blocks:
            for room in block.rooms:
                f = room.fixtures
                fixture_map = [
                    ("recessed_led_600x1200", "600 x 1200mm Recessed 3 x 18W LED fluorescent light fitting, complete with LED tubes, ceiling frame", f.recessed_led_600x1200),
                    ("surface_mount_led_18w", "18W LED ceiling light surface mount, complete with wiring and fixings", f.surface_mount_led_18w),
                    ("flood_light_30w", "30W LED flood light, IP65, external use, with bracket", f.flood_light_30w),
                    ("flood_light_200w", "200W LED flood light, IP65, external use, with bracket", f.flood_light_200w),
                    ("downlight_led_6w", "6W LED Downlight White recessed", f.downlight_led_6w),
                    ("vapor_proof_2x24w", "2x24W Vapor Proof LED (IP65) fitting", f.vapor_proof_2x24w),
                    ("vapor_proof_2x18w", "2x18W Vapor Proof LED fitting", f.vapor_proof_2x18w),
                    ("prismatic_2x18w", "2x18W Prismatic LED fitting", f.prismatic_2x18w),
                    ("bulkhead_26w", "26W Bulkhead Outdoor light", f.bulkhead_26w),
                    ("bulkhead_24w", "24W Bulkhead Outdoor light", f.bulkhead_24w),
                    ("fluorescent_50w_5ft", "50W 5ft Fluorescent fitting", f.fluorescent_50w_5ft),
                    ("pole_light_60w", "Outdoor Pole Light 2300mm 60W (incl. pole + base)", f.pole_light_60w),
                    ("pool_flood_light", "Pool Area Flood Light 150W (IP65)", f.pool_flood_light),
                    ("pool_underwater_light", "Pool Underwater Light 35W (IP68)", f.pool_underwater_light),
                ]
                for field_name, desc, qty in fixture_map:
                    if qty > 0:
                        light_aggregation[field_name]["qty"] += qty
                        light_aggregation[field_name]["desc"] = desc
                        light_aggregation[field_name]["locations"].append(f"{room.name}({qty})")
                        if block.name not in light_aggregation[field_name]["rooms"]:
                            light_aggregation[field_name]["rooms"].append(block.name)

        # 5A - Light Fittings (aggregated)
        for field_name, data in light_aggregation.items():
            if data["qty"] > 0:
                locations_str = ", ".join(data["locations"][:5])
                if len(data["locations"]) > 5:
                    locations_str += f"... (+{len(data['locations']) - 5} more)"

                quantity_items.append(BQLineItem(
                    item_no=next_item_no(BQSection.LIGHTING),
                    section=BQSection.LIGHTING,
                    subsection="5A - Light Fittings",
                    description=f"{data['desc']}.\nLocations: {locations_str}\nTotal count: {data['qty']}",
                    unit="No",
                    qty=data["qty"],
                    source=ItemConfidence.EXTRACTED,
                    locations=data["locations"],
                    drawing_ref=default_drawing_ref,
                ))

        # 5B - Switches
        switch_aggregation: Dict[str, Dict] = defaultdict(lambda: {"qty": 0, "locations": []})
        for block in extraction.building_blocks:
            for room in block.rooms:
                f = room.fixtures
                switch_map = [
                    ("switch_1lever", "1-lever, 1-way switch @ 1200mm AFFL, flush-mount with cover plate", f.switch_1lever_1way),
                    ("switch_2lever", "2-lever, 1-way switch @ 1200mm AFFL, flush-mount with cover plate", f.switch_2lever_1way),
                    ("day_night", "Day/night switch (photocell) @ 2000mm AFFL for external lighting", f.day_night_switch),
                ]
                for field_name, desc, qty in switch_map:
                    if qty > 0:
                        switch_aggregation[field_name]["qty"] += qty
                        switch_aggregation[field_name]["desc"] = desc

        for field_name, data in switch_aggregation.items():
            if data["qty"] > 0:
                quantity_items.append(BQLineItem(
                    item_no=next_item_no(BQSection.LIGHTING),
                    section=BQSection.LIGHTING,
                    subsection="5B - Switches",
                    description=data["desc"],
                    unit="No",
                    qty=data["qty"],
                    source=ItemConfidence.EXTRACTED,
                    drawing_ref=default_drawing_ref,
                ))

        # ═══════════════════════════════════════════════════════════════════════════
        # SECTION 6: POWER OUTLETS INSTALLATION
        # ═══════════════════════════════════════════════════════════════════════════
        # 6A - Socket Outlets (aggregated)
        socket_aggregation: Dict[str, Dict] = defaultdict(lambda: {"qty": 0, "locations": []})
        for block in extraction.building_blocks:
            for room in block.rooms:
                f = room.fixtures
                socket_map = [
                    ("double_300", "16A double switched socket @ 300mm AFFL, flush-mount, cover plate (white). General office use.", f.double_socket_300),
                    ("single_300", "16A single switched socket @ 300mm AFFL, flush-mount, cover plate", f.single_socket_300),
                    ("double_1100", "16A double switched socket @ 1100mm AFFL, flush-mount, cover plate. Kitchenettes/countertops.", f.double_socket_1100),
                    ("single_1100", "16A single switched socket @ 1100mm AFFL, flush-mount, cover plate. Kitchenettes.", f.single_socket_1100),
                    ("waterproof", "16A double waterproof socket (IP65)", f.double_socket_waterproof),
                    ("ceiling", "16A double ceiling socket", f.double_socket_ceiling),
                ]
                for field_name, desc, qty in socket_map:
                    if qty > 0:
                        socket_aggregation[field_name]["qty"] += qty
                        socket_aggregation[field_name]["desc"] = desc

        for field_name, data in socket_aggregation.items():
            if data["qty"] > 0:
                quantity_items.append(BQLineItem(
                    item_no=next_item_no(BQSection.POWER_OUTLETS),
                    section=BQSection.POWER_OUTLETS,
                    subsection="6A - Socket Outlets",
                    description=data["desc"],
                    unit="No",
                    qty=data["qty"],
                    source=ItemConfidence.EXTRACTED,
                    drawing_ref=default_drawing_ref,
                ))

        # 6B - AC Isolators
        isolator_count = 0
        for block in extraction.building_blocks:
            for room in block.rooms:
                isolator_count += room.fixtures.isolator_30a + room.fixtures.isolator_20a

        if isolator_count > 0:
            quantity_items.append(BQLineItem(
                item_no=next_item_no(BQSection.POWER_OUTLETS),
                section=BQSection.POWER_OUTLETS,
                subsection="6B - AC Isolators",
                description="30A isolator switch @ 2000mm AFFL for A/C unit, with wiring",
                unit="No",
                qty=isolator_count,
                source=ItemConfidence.EXTRACTED,
                drawing_ref=default_drawing_ref,
            ))

        # 6C - Floor Boxes
        floor_box_count = sum(
            room.fixtures.floor_box
            for block in extraction.building_blocks
            for room in block.rooms
        )
        if floor_box_count > 0:
            quantity_items.append(BQLineItem(
                item_no=next_item_no(BQSection.POWER_OUTLETS),
                section=BQSection.POWER_OUTLETS,
                subsection="6C - Floor Boxes",
                description="Floor box with 2x 16A socket outlets, data port, brass/SS cover plate, sub-floor conduit",
                unit="No",
                qty=floor_box_count,
                source=ItemConfidence.EXTRACTED,
                drawing_ref=default_drawing_ref,
            ))

        # ═══════════════════════════════════════════════════════════════════════════
        # SECTION 7: DATA & COMMUNICATIONS
        # ═══════════════════════════════════════════════════════════════════════════
        total_data_points = sum(
            room.fixtures.data_points_cat6
            for block in extraction.building_blocks
            for room in block.rooms
        )

        if total_data_points > 0:
            # Data sockets
            quantity_items.append(BQLineItem(
                item_no=next_item_no(BQSection.DATA_COMMS),
                section=BQSection.DATA_COMMS,
                description="CAT 6 data socket outlet, flush faceplate, keystone jack, back box",
                unit="No",
                qty=total_data_points,
                source=ItemConfidence.EXTRACTED,
                drawing_ref=default_drawing_ref,
            ))

            # CAT6 cable (30m per point)
            quantity_items.append(BQLineItem(
                item_no=next_item_no(BQSection.DATA_COMMS),
                section=BQSection.DATA_COMMS,
                description="CAT 6 UTP cable per data point (patch panel to outlet), tested & certified",
                unit="m",
                qty=total_data_points * 30,
                source=ItemConfidence.ESTIMATED,
                drawing_ref=default_drawing_ref,
            ))

            # Patch panel
            quantity_items.append(BQLineItem(
                item_no=next_item_no(BQSection.DATA_COMMS),
                section=BQSection.DATA_COMMS,
                description="24-port CAT 6 patch panel for 19\" data cabinet",
                unit="No",
                qty=max(1, (total_data_points + 23) // 24),
                source=ItemConfidence.INFERRED,
                drawing_ref=default_drawing_ref,
            ))

            # Data cabinet
            quantity_items.append(BQLineItem(
                item_no=next_item_no(BQSection.DATA_COMMS),
                section=BQSection.DATA_COMMS,
                description="9U/12U wall-mount data cabinet with fan, power strip, cable management, lock",
                unit="No",
                qty=1,
                source=ItemConfidence.INFERRED,
                drawing_ref=default_drawing_ref,
            ))

        # ═══════════════════════════════════════════════════════════════════════════
        # SECTION 8: CABLE CONTAINMENT
        # ═══════════════════════════════════════════════════════════════════════════
        total_circuits = extraction.total_circuits

        if total_circuits > 0:
            # Skirting trunking
            quantity_items.append(BQLineItem(
                item_no=next_item_no(BQSection.CONTAINMENT),
                section=BQSection.CONTAINMENT,
                description="2-compartment steel grey power skirting trunking (100x50mm) with all accessories (corners, tees, end caps, couplers)",
                unit="m",
                qty=max(20, total_circuits * 3),
                source=ItemConfidence.ESTIMATED,
                drawing_ref=default_drawing_ref,
            ))

            # Cable tray for AC
            ac_count = sum(
                1 for block in extraction.building_blocks
                for equip in block.heavy_equipment
                if equip.type.lower() in ("ac", "aircon", "hvac")
            )
            if ac_count > 0:
                quantity_items.append(BQLineItem(
                    item_no=next_item_no(BQSection.CONTAINMENT),
                    section=BQSection.CONTAINMENT,
                    description="200mm galvanized cable tray (aircon), with supports, brackets, covers, couplers",
                    unit="m",
                    qty=ac_count * 10,
                    source=ItemConfidence.ESTIMATED,
                    drawing_ref=default_drawing_ref,
                ))

            # PVC conduit
            quantity_items.append(BQLineItem(
                item_no=next_item_no(BQSection.CONTAINMENT),
                section=BQSection.CONTAINMENT,
                description="20mm PVC conduit (concealed/surface) with saddles, bends, junction boxes, draw wires",
                unit="m",
                qty=total_circuits * 5,
                source=ItemConfidence.ESTIMATED,
                drawing_ref=default_drawing_ref,
            ))

        # ═══════════════════════════════════════════════════════════════════════════
        # SECTION 9: UNDERGROUND WORKS & SLEEVES
        # ═══════════════════════════════════════════════════════════════════════════
        for sleeve in extraction.underground_sleeves:
            quantity_items.append(BQLineItem(
                item_no=next_item_no(BQSection.UNDERGROUND),
                section=BQSection.UNDERGROUND,
                description=f"{sleeve.diameter_mm}mm uPVC sleeves for underground cable crossing, with draw wires and end seals",
                unit="No",
                qty=sleeve.qty if hasattr(sleeve, 'qty') else 1,
                source=ItemConfidence.EXTRACTED,
                drawing_ref=default_drawing_ref,
            ))

        # Site cable runs (trenching)
        for run in extraction.site_cable_runs:
            if run.needs_trenching:
                quantity_items.append(BQLineItem(
                    item_no=next_item_no(BQSection.UNDERGROUND),
                    section=BQSection.UNDERGROUND,
                    description=f"Excavation of cable trenches 600mm deep x 300mm wide, incl. backfill, compaction, marker tape — {run.from_point} to {run.to_point}",
                    unit="m",
                    qty=run.length_m,
                    source=run.confidence,
                    drawing_ref=default_drawing_ref,
                ))

        # ═══════════════════════════════════════════════════════════════════════════
        # SECTION 10: SOLAR PV ELECTRICAL PROVISIONS
        # ═══════════════════════════════════════════════════════════════════════════
        # Check for solar equipment
        has_solar = any(
            equip.type.lower() in ("solar", "solar_inverter", "pv", "battery")
            for block in extraction.building_blocks
            for equip in block.heavy_equipment
        )

        if has_solar:
            quantity_items.append(BQLineItem(
                item_no=next_item_no(BQSection.SOLAR_PV),
                section=BQSection.SOLAR_PV,
                description="Solar PV array electrical provisions (conduit, cable routing) - panels/inverter by solar contractor",
                unit="Item",
                qty=1,
                source=ItemConfidence.INFERRED,
                drawing_ref=default_drawing_ref,
            ))

            quantity_items.append(BQLineItem(
                item_no=next_item_no(BQSection.SOLAR_PV),
                section=BQSection.SOLAR_PV,
                description="Battery room electrical preparation - cable tray, ventilation provision, earth bonding, dedicated circuit",
                unit="Item",
                qty=1,
                source=ItemConfidence.INFERRED,
                drawing_ref=default_drawing_ref,
            ))

        # ═══════════════════════════════════════════════════════════════════════════
        # SECTION 11: EARTHING & BONDING
        # ═══════════════════════════════════════════════════════════════════════════
        for supply in extraction.supply_points:
            # Main earth conductor
            quantity_items.append(BQLineItem(
                item_no=next_item_no(BQSection.EARTHING),
                section=BQSection.EARTHING,
                description=f"25mm² BCEW earth conductor: kiosk to main DB — {supply.name}",
                unit="m",
                qty=25,
                source=ItemConfidence.ESTIMATED,
                drawing_ref=default_drawing_ref,
            ))

        # Sub-main earth conductor
        if extraction.total_dbs > 1:
            quantity_items.append(BQLineItem(
                item_no=next_item_no(BQSection.EARTHING),
                section=BQSection.EARTHING,
                description="16mm² green/yellow earth conductor for sub-main distribution",
                unit="m",
                qty=extraction.total_dbs * 15,
                source=ItemConfidence.ESTIMATED,
                drawing_ref=default_drawing_ref,
            ))

        # Final circuit earth
        quantity_items.append(BQLineItem(
            item_no=next_item_no(BQSection.EARTHING),
            section=BQSection.EARTHING,
            description="4mm² green/yellow earth conductor for final sub-circuits",
            unit="m",
            qty=extraction.total_circuits * 10,
            source=ItemConfidence.ESTIMATED,
            drawing_ref=default_drawing_ref,
        ))

        # Equipotential bonding
        quantity_items.append(BQLineItem(
            item_no=next_item_no(BQSection.EARTHING),
            section=BQSection.EARTHING,
            description="Equipotential bonding to all exposed metalwork, pipes, cable trays, DB enclosures per SANS 10142-1",
            unit="Item",
            qty=1,
            source=ItemConfidence.INFERRED,
            drawing_ref=default_drawing_ref,
        ))

        # ═══════════════════════════════════════════════════════════════════════════
        # SECTION 12: FIRE SAFETY PROVISIONS
        # ═══════════════════════════════════════════════════════════════════════════
        # Add fire safety items based on building count
        if len(extraction.building_blocks) > 0:
            quantity_items.append(BQLineItem(
                item_no=next_item_no(BQSection.FIRE_SAFETY),
                section=BQSection.FIRE_SAFETY,
                description="5kg DCP fire extinguisher with bracket",
                unit="No",
                qty=len(extraction.building_blocks),
                source=ItemConfidence.INFERRED,
                drawing_ref=default_drawing_ref,
            ))

        # ═══════════════════════════════════════════════════════════════════════════
        # SECTION 13: TESTING, COMMISSIONING & DOCUMENTATION
        # ═══════════════════════════════════════════════════════════════════════════
        total_dbs = extraction.total_dbs
        total_supplies = len(extraction.supply_points) or 1

        testing_items = [
            ("Insulation resistance testing of all circuits per SANS 10142-1", "Item", 1),
            ("Earth fault loop impedance testing of all circuits", "Item", 1),
            ("Earth continuity and bonding verification testing", "Item", 1),
            ("Polarity verification of all socket outlets and light fittings", "Item", 1),
            ("RCD/Earth leakage trip testing at each distribution board", "Item", 1),
            (f"Certificate of Compliance (CoC) per OHS Act 85 of 1993", "No", total_supplies),
            ("As-built drawings (updated set)", "Set", 1),
            ("O&M manuals including datasheets, test certificates, warranties", "Set", 1),
            (f"Circuit labelling and DB schedule printing for all {total_dbs} distribution boards", "No", total_dbs),
        ]

        for desc, unit, qty in testing_items:
            if qty > 0:
                quantity_items.append(BQLineItem(
                    item_no=next_item_no(BQSection.TESTING),
                    section=BQSection.TESTING,
                    description=desc,
                    unit=unit,
                    qty=qty,
                    source=ItemConfidence.INFERRED,
                    is_rate_only=True,
                    drawing_ref=default_drawing_ref,
                ))

        # ═══════════════════════════════════════════════════════════════════════════
        # SECTION 14: PRELIMINARY & GENERAL
        # ═══════════════════════════════════════════════════════════════════════════
        prelim_items = [
            ("Site establishment and de-establishment, incl. temporary electrical supply", "Item", 1),
            ("Health and safety compliance, H&S file, PPE, method statements", "Item", 1),
            ("Transport of materials to site and removal of construction waste", "Item", 1),
            ("Builder's work (chasing, core drilling, making good, painting)", "Item", 1),
            ("Attendance on other trades (plumbing, HVAC, data contractors)", "Item", 1),
            ("Contingency allowance (10%)", "Item", 1),
        ]

        for desc, unit, qty in prelim_items:
            quantity_items.append(BQLineItem(
                item_no=next_item_no(BQSection.PRELIMS),
                section=BQSection.PRELIMS,
                description=desc,
                unit=unit,
                qty=qty,
                source=ItemConfidence.INFERRED,
                is_rate_only=True,
                drawing_ref="N/A",
            ))

        # ═══════════════════════════════════════════════════════════════════════════
        # SORT BY SECTION ORDER
        # ═══════════════════════════════════════════════════════════════════════════
        # Sort items by section number to ensure correct order
        section_order = {s: s.section_number for s in BQSection}
        quantity_items.sort(key=lambda x: (section_order.get(x.section, 99), x.item_no))

        # Store quantity BQ (primary deliverable)
        result.quantity_bq = quantity_items
        result.total_items = len(quantity_items)

        # ═══════════════════════════════════════════════════════════════════════════
        # GENERATE ESTIMATED BQ (copy quantity items + add default prices)
        # ═══════════════════════════════════════════════════════════════════════════
        estimated_items = []
        for item in quantity_items:
            est_item = item.model_copy()
            price_val = _get_default_price(est_item, contractor)
            est_item.unit_price_zar = price_val
            est_item.total_zar = round(price_val * est_item.qty, 2)
            estimated_items.append(est_item)

        # Apply site condition multipliers
        if site:
            for item in estimated_items:
                if item.section == BQSection.PRELIMS:
                    item.total_zar = round(item.total_zar * site.labour_multiplier, 2)
                if item.section == BQSection.UNDERGROUND:
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


def _generate_db_description(db: DistributionBoard, metadata=None) -> str:
    """
    Generate detailed DB description with full circuit schedule.

    Example output:
    DB-GF - Main Distribution Board, Ground Floor.
    400V AC, 3Ph+N+E, 100A rated. Per SLD TJM-SLD-001:
    - Q1: 100A 4-pole main CB
    - Q2: 63A earth leakage relay
    ...
    """
    # Build header
    voltage = db.voltage_v or 400
    # db.phase is a PhaseConfig enum ("1PH" or "3PH")
    phase_value = db.phase.value if hasattr(db.phase, 'value') else str(db.phase)
    phases_str = f"{phase_value}+N+E"
    rating = db.main_breaker_a or 100

    lines = [
        f"{db.name} - {db.description or 'Distribution Board'}.",
        f"{voltage}V AC, {phases_str}, {rating}A rated.",
    ]

    # Add circuit schedule
    breaker_num = 1

    # Main breaker
    lines.append(f"- Q{breaker_num}: {rating}A 4-pole main CB")
    breaker_num += 1

    # Earth leakage
    if db.earth_leakage:
        el_rating = db.earth_leakage_rating_a or 63
        lines.append(f"- Q{breaker_num}: {el_rating}A earth leakage relay")
        breaker_num += 1

    # Circuit breakers
    for circuit in db.circuits[:15]:  # Limit to prevent overly long descriptions
        breaker_a = circuit.breaker_a or 20
        breaker_type = circuit.breaker_type.upper() if circuit.breaker_type else "CB"

        if circuit.type == "sub_board_feed":
            cable_info = f"{circuit.cable_size_mm2}mm²" if circuit.cable_size_mm2 else ""
            lines.append(f"- Q{breaker_num}: {breaker_a}A {breaker_type} -> {circuit.description} ({cable_info})")
        else:
            load_info = f"{circuit.wattage_w:.0f}W" if circuit.wattage_w else ""
            cable_info = f"{circuit.cable_size_mm2}mm²" if circuit.cable_size_mm2 else ""
            points_info = f"{circuit.num_points}pts" if circuit.num_points else ""
            details = ", ".join(filter(None, [load_info, cable_info, points_info]))
            lines.append(f"- Q{breaker_num}: {breaker_a}A -> {circuit.id} ({details})")

        breaker_num += 1

    # Spare ways
    spare_ways = db.spare_ways or (db.total_ways - len(db.circuits)) if db.total_ways else 0
    if spare_ways > 0:
        for _ in range(min(spare_ways, 3)):  # Show up to 3 spares
            lines.append(f"- Q{breaker_num}: SPARE")
            breaker_num += 1

    # Protection devices
    if db.surge_protection:
        lines.append("- Surge protection device")

    lines.append("- Phase/earth bars, glands, labelling, powder-coated enclosure with lock")

    return "\n".join(lines)


def _estimate_cable_length(circuit) -> float:
    """Default cable length estimates when not on drawing."""
    if circuit.type in ("sub_board_feed",):
        return 15.0
    if circuit.type in ("lighting", "light"):
        return 10.0
    if circuit.type in ("power", "socket"):
        return 12.0
    if circuit.type in ("ac", "aircon", "hvac"):
        return 15.0
    if circuit.type in ("pool_pump", "heat_pump", "circulation_pump", "borehole_pump"):
        return 25.0
    if circuit.type in ("isolator",):
        return 10.0
    return 10.0


def _get_default_price(item: BQLineItem, contractor: Optional[ContractorProfile] = None) -> float:
    """Look up default unit price. Use contractor custom price if available."""
    if contractor and item.description in contractor.custom_prices:
        return contractor.custom_prices[item.description]

    # Default prices (ZAR) - simplified lookup
    default_prices = {
        # Section 1 - Incoming
        "Kiosk metering": 15000.0,
        "95mm²": 450.0,  # per meter
        "Cable trenching": 180.0,  # per meter
        "Earth electrode": 1200.0,
        "earth bar": 850.0,

        # Section 2 - DBs
        "Distribution Board": 5500.0,

        # Section 3 - Sub-main cables
        "SWA PVC cable": 180.0,  # per meter average

        # Section 4 - Final cables
        "T&E": 25.0,  # per meter average

        # Section 5 - Lighting
        "Recessed": 650.0,
        "surface mount": 280.0,
        "flood light": 450.0,
        "200W LED flood": 2800.0,
        "Downlight": 180.0,
        "Vapor Proof": 750.0,
        "Prismatic": 580.0,
        "Bulkhead": 350.0,
        "Fluorescent": 320.0,
        "Pole Light": 4500.0,
        "Pool Area Flood": 1800.0,
        "Pool Underwater": 2500.0,
        "1-lever": 60.0,
        "2-lever": 95.0,
        "Day/night": 450.0,

        # Section 6 - Power outlets
        "double switched socket": 160.0,
        "single switched socket": 120.0,
        "waterproof socket": 280.0,
        "ceiling socket": 200.0,
        "isolator switch": 320.0,
        "Floor box": 1800.0,

        # Section 7 - Data
        "CAT 6 data socket": 450.0,
        "CAT 6 UTP cable": 15.0,  # per meter
        "patch panel": 1200.0,
        "data cabinet": 3500.0,

        # Section 8 - Containment
        "skirting trunking": 85.0,  # per meter
        "cable tray": 120.0,  # per meter
        "PVC conduit": 35.0,  # per meter

        # Section 9 - Underground
        "uPVC sleeves": 180.0,
        "Excavation": 180.0,  # per meter

        # Section 10 - Solar
        "Solar PV": 2500.0,
        "Battery room": 3500.0,

        # Section 11 - Earthing
        "BCEW earth conductor": 85.0,  # per meter
        "green/yellow earth": 45.0,  # per meter
        "Equipotential bonding": 2500.0,

        # Section 12 - Fire safety
        "fire extinguisher": 850.0,

        # Section 13 - Testing
        "Insulation resistance": 1500.0,
        "Earth fault loop": 1200.0,
        "Earth continuity": 800.0,
        "Polarity verification": 600.0,
        "RCD/Earth leakage": 500.0,
        "Certificate of Compliance": 1500.0,
        "As-built drawings": 3500.0,
        "O&M manuals": 2500.0,
        "Circuit labelling": 350.0,

        # Section 14 - Prelims
        "Site establishment": 8500.0,
        "Health and safety": 4500.0,
        "Transport": 3500.0,
        "Builder's work": 5500.0,
        "Attendance": 2500.0,
        "Contingency": 0.0,  # Calculated separately
    }

    # Try partial match
    for key, price_val in default_prices.items():
        if key.lower() in item.description.lower():
            return price_val

    # Section-based defaults (v4.6 - 14 sections)
    section_defaults = {
        BQSection.INCOMING: 5000.0,
        BQSection.DISTRIBUTION: 5500.0,
        BQSection.SUBMAIN_CABLES: 180.0,
        BQSection.FINAL_CABLES: 25.0,
        BQSection.LIGHTING: 400.0,
        BQSection.POWER_OUTLETS: 150.0,
        BQSection.DATA_COMMS: 500.0,
        BQSection.CONTAINMENT: 60.0,
        BQSection.UNDERGROUND: 180.0,
        BQSection.SOLAR_PV: 3000.0,
        BQSection.EARTHING: 850.0,
        BQSection.FIRE_SAFETY: 850.0,
        BQSection.TESTING: 1000.0,
        BQSection.PRELIMS: 4000.0,
    }

    return section_defaults.get(item.section, 100.0)
