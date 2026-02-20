"""
v5.0 Extraction Validation Checklist

Based on Model_Electrical_BOQ.xlsx structure.
Validates extracted data against expected elements for a complete BOQ.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from enum import Enum


class ChecklistCategory(str, Enum):
    """Categories matching Model BOQ sections."""
    INCOMING = "1. Main Incoming Supply & Metering"
    DISTRIBUTION = "2. Distribution Boards"
    SUBMAIN_CABLES = "3. Sub-Main Distribution Cables"
    FINAL_CABLES = "4. Final Sub-Circuit Cables"
    LIGHTING = "5. Lighting Installation"
    POWER_OUTLETS = "6. Power Outlets Installation"
    DATA_COMMS = "7. Data & Communications"
    CONTAINMENT = "8. Cable Containment"
    UNDERGROUND = "9. Underground Works & Sleeves"
    SOLAR_PV = "10. Solar PV Electrical Provisions"
    EARTHING = "11. Earthing & Bonding"
    FIRE_SAFETY = "12. Fire Safety Provisions"
    TESTING = "13. Testing, Commissioning & Documentation"
    PRELIMS = "14. Preliminary & General"


@dataclass
class ChecklistItem:
    """Individual item to validate."""
    name: str
    category: ChecklistCategory
    expected_unit: str = ""
    extracted: bool = False
    extracted_qty: float = 0
    expected_qty: float = 0  # From model or estimated
    source: str = ""  # Where it was extracted from
    notes: str = ""


@dataclass
class ExtractionChecklist:
    """Complete extraction validation checklist."""
    items: List[ChecklistItem] = field(default_factory=list)

    @property
    def total_items(self) -> int:
        return len(self.items)

    @property
    def extracted_items(self) -> int:
        return sum(1 for item in self.items if item.extracted)

    @property
    def extraction_rate(self) -> float:
        if self.total_items == 0:
            return 0.0
        return (self.extracted_items / self.total_items) * 100

    def items_by_category(self, category: ChecklistCategory) -> List[ChecklistItem]:
        return [item for item in self.items if item.category == category]

    def category_summary(self) -> Dict[ChecklistCategory, Tuple[int, int]]:
        """Returns {category: (extracted_count, total_count)}."""
        summary = {}
        for cat in ChecklistCategory:
            cat_items = self.items_by_category(cat)
            extracted = sum(1 for item in cat_items if item.extracted)
            summary[cat] = (extracted, len(cat_items))
        return summary


def create_model_checklist() -> ExtractionChecklist:
    """
    Create checklist based on Model_Electrical_BOQ.xlsx structure.

    This defines ALL elements that should be extracted for a complete BOQ.
    """
    checklist = ExtractionChecklist()

    # Section 1: Main Incoming Supply & Metering
    checklist.items.extend([
        ChecklistItem("Kiosk Metering Enclosure", ChecklistCategory.INCOMING, "No"),
        ChecklistItem("Incoming LV Cable (95mm² 4C)", ChecklistCategory.INCOMING, "m"),
        ChecklistItem("Sub-main Cable to DB (35mm² 4C)", ChecklistCategory.INCOMING, "m"),
        ChecklistItem("Trenching for Incoming Cable", ChecklistCategory.INCOMING, "m"),
        ChecklistItem("Earth Electrode", ChecklistCategory.INCOMING, "No"),
        ChecklistItem("Main Earth Bar", ChecklistCategory.INCOMING, "No"),
    ])

    # Section 2: Distribution Boards
    checklist.items.extend([
        ChecklistItem("DB-GF (Main Distribution Board)", ChecklistCategory.DISTRIBUTION, "No"),
        ChecklistItem("DB-CA (Common Area DB)", ChecklistCategory.DISTRIBUTION, "No"),
        ChecklistItem("DB-S1 (Suite 1 DB)", ChecklistCategory.DISTRIBUTION, "No"),
        ChecklistItem("DB-S2 (Suite 2 DB)", ChecklistCategory.DISTRIBUTION, "No"),
        ChecklistItem("DB-S3 (Suite 3 DB)", ChecklistCategory.DISTRIBUTION, "No"),
        ChecklistItem("DB-S4 (Suite 4 DB)", ChecklistCategory.DISTRIBUTION, "No"),
    ])

    # Section 3: Sub-Main Cables
    checklist.items.extend([
        ChecklistItem("Sub-main Cable DB-GF to DB-CA (16mm²)", ChecklistCategory.SUBMAIN_CABLES, "m"),
        ChecklistItem("Sub-main Cable DB-GF to DB-S1 (6mm²)", ChecklistCategory.SUBMAIN_CABLES, "m"),
        ChecklistItem("Sub-main Cable DB-GF to DB-S2 (6mm²)", ChecklistCategory.SUBMAIN_CABLES, "m"),
        ChecklistItem("Sub-main Cable DB-GF to DB-S3 (4mm²)", ChecklistCategory.SUBMAIN_CABLES, "m"),
        ChecklistItem("Sub-main Cable DB-GF to DB-S4 (4mm²)", ChecklistCategory.SUBMAIN_CABLES, "m"),
    ])

    # Section 4: Final Cables (grouped by type)
    checklist.items.extend([
        ChecklistItem("Power Circuits (2.5mm² T&E)", ChecklistCategory.FINAL_CABLES, "m"),
        ChecklistItem("Lighting Circuits (1.5mm² T&E)", ChecklistCategory.FINAL_CABLES, "m"),
        ChecklistItem("AC Circuits (2.5mm² T&E)", ChecklistCategory.FINAL_CABLES, "m"),
    ])

    # Section 5: Lighting Installation
    checklist.items.extend([
        ChecklistItem("LED Panels 600x1200mm (3x18W)", ChecklistCategory.LIGHTING, "No"),
        ChecklistItem("LED Ceiling Lights (18W surface)", ChecklistCategory.LIGHTING, "No"),
        ChecklistItem("LED Flood Lights (30W external)", ChecklistCategory.LIGHTING, "No"),
        ChecklistItem("1-Lever 1-Way Switches", ChecklistCategory.LIGHTING, "No"),
        ChecklistItem("2-Lever 1-Way Switches", ChecklistCategory.LIGHTING, "No"),
        ChecklistItem("Day/Night Switch (Photocell)", ChecklistCategory.LIGHTING, "No"),
    ])

    # Section 6: Power Outlets
    checklist.items.extend([
        ChecklistItem("Double Sockets @300mm", ChecklistCategory.POWER_OUTLETS, "No"),
        ChecklistItem("Single Sockets @300mm", ChecklistCategory.POWER_OUTLETS, "No"),
        ChecklistItem("Double Sockets @1100mm", ChecklistCategory.POWER_OUTLETS, "No"),
        ChecklistItem("Single Sockets @1100mm", ChecklistCategory.POWER_OUTLETS, "No"),
        ChecklistItem("30A AC Isolators", ChecklistCategory.POWER_OUTLETS, "No"),
        ChecklistItem("20A AC Isolators", ChecklistCategory.POWER_OUTLETS, "No"),
        ChecklistItem("Floor Boxes", ChecklistCategory.POWER_OUTLETS, "No"),
    ])

    # Section 7: Data & Communications
    checklist.items.extend([
        ChecklistItem("CAT 6 Data Sockets", ChecklistCategory.DATA_COMMS, "No"),
        ChecklistItem("CAT 6 UTP Cable", ChecklistCategory.DATA_COMMS, "m"),
        ChecklistItem("24-Port Patch Panel", ChecklistCategory.DATA_COMMS, "No"),
        ChecklistItem("Data Cabinet", ChecklistCategory.DATA_COMMS, "No"),
    ])

    # Section 8: Cable Containment
    checklist.items.extend([
        ChecklistItem("Power Skirting Trunking (100x50mm)", ChecklistCategory.CONTAINMENT, "m"),
        ChecklistItem("Cable Tray (200mm galvanized)", ChecklistCategory.CONTAINMENT, "m"),
        ChecklistItem("PVC Trunking (P8000)", ChecklistCategory.CONTAINMENT, "m"),
        ChecklistItem("Wire Mesh Basket (150mm)", ChecklistCategory.CONTAINMENT, "m"),
        ChecklistItem("Medium Duty Cable Tray (200mm)", ChecklistCategory.CONTAINMENT, "m"),
        ChecklistItem("PVC Conduit (20mm)", ChecklistCategory.CONTAINMENT, "m"),
        ChecklistItem("PVC Conduit (25mm)", ChecklistCategory.CONTAINMENT, "m"),
    ])

    # Section 9: Underground Works
    checklist.items.extend([
        ChecklistItem("110mm uPVC Sleeves", ChecklistCategory.UNDERGROUND, "No"),
        ChecklistItem("75mm uPVC Sleeves", ChecklistCategory.UNDERGROUND, "No"),
        ChecklistItem("50mm uPVC Sleeves", ChecklistCategory.UNDERGROUND, "No"),
        ChecklistItem("Cable Trench Excavation", ChecklistCategory.UNDERGROUND, "m"),
        ChecklistItem("Warning/Marker Tape", ChecklistCategory.UNDERGROUND, "m"),
    ])

    # Section 10: Solar PV Provisions
    checklist.items.extend([
        ChecklistItem("Solar PV Array Mounting Provision", ChecklistCategory.SOLAR_PV, "Item"),
        ChecklistItem("Battery Room Preparation", ChecklistCategory.SOLAR_PV, "Item"),
        ChecklistItem("Solar DC Cable Routing", ChecklistCategory.SOLAR_PV, "m"),
    ])

    # Section 11: Earthing & Bonding
    checklist.items.extend([
        ChecklistItem("Earth Conductor 25mm² BCEW", ChecklistCategory.EARTHING, "m"),
        ChecklistItem("Earth Conductor 16mm²", ChecklistCategory.EARTHING, "m"),
        ChecklistItem("Earth Conductor 4mm²", ChecklistCategory.EARTHING, "m"),
        ChecklistItem("Equipotential Bonding", ChecklistCategory.EARTHING, "Item"),
        ChecklistItem("Lightning Protection Electrode", ChecklistCategory.EARTHING, "No"),
    ])

    # Section 12: Fire Safety
    checklist.items.extend([
        ChecklistItem("Fire Extinguisher (5kg DCP)", ChecklistCategory.FIRE_SAFETY, "No"),
        ChecklistItem("Fire Hose Reel (30m)", ChecklistCategory.FIRE_SAFETY, "No"),
    ])

    # Section 13: Testing & Documentation
    checklist.items.extend([
        ChecklistItem("Insulation Resistance Testing", ChecklistCategory.TESTING, "Item"),
        ChecklistItem("Earth Fault Loop Testing", ChecklistCategory.TESTING, "Item"),
        ChecklistItem("Earth Continuity Testing", ChecklistCategory.TESTING, "Item"),
        ChecklistItem("Polarity Verification", ChecklistCategory.TESTING, "Item"),
        ChecklistItem("RCD Trip Testing", ChecklistCategory.TESTING, "Item"),
        ChecklistItem("Certificate of Compliance (COC)", ChecklistCategory.TESTING, "No"),
        ChecklistItem("As-Built Drawings", ChecklistCategory.TESTING, "Set"),
        ChecklistItem("O&M Manuals", ChecklistCategory.TESTING, "Set"),
        ChecklistItem("Circuit Labelling", ChecklistCategory.TESTING, "No"),
    ])

    # Section 14: Preliminary & General
    checklist.items.extend([
        ChecklistItem("Site Establishment", ChecklistCategory.PRELIMS, "Item"),
        ChecklistItem("H&S Compliance", ChecklistCategory.PRELIMS, "Item"),
        ChecklistItem("Transport & Waste Removal", ChecklistCategory.PRELIMS, "Item"),
        ChecklistItem("Builder's Work", ChecklistCategory.PRELIMS, "Item"),
        ChecklistItem("Attendance on Other Trades", ChecklistCategory.PRELIMS, "Item"),
        ChecklistItem("Contingency Allowance", ChecklistCategory.PRELIMS, "Item"),
    ])

    return checklist


def validate_extraction(extraction_result, checklist: ExtractionChecklist = None) -> ExtractionChecklist:
    """
    Validate extraction result against the model checklist.

    Args:
        extraction_result: ExtractionResult from discover stage
        checklist: Optional pre-created checklist (creates model checklist if None)

    Returns:
        ExtractionChecklist with extracted flags set
    """
    if checklist is None:
        checklist = create_model_checklist()

    if extraction_result is None:
        return checklist

    # Check Distribution Boards
    for block in extraction_result.building_blocks:
        for db in block.distribution_boards:
            db_name = db.name.upper()

            # Match DB names to checklist items
            for item in checklist.items:
                if item.category == ChecklistCategory.DISTRIBUTION:
                    if db_name in item.name.upper() or item.name.upper().startswith(db_name.split('-')[0]):
                        if db_name == "DB-GF" and "MAIN" in item.name.upper():
                            item.extracted = True
                            item.extracted_qty = 1
                            item.source = f"SLD: {db.name}"
                        elif db_name in item.name.upper():
                            item.extracted = True
                            item.extracted_qty = 1
                            item.source = f"SLD: {db.name}"

            # Count circuits for cable sections
            power_circuits = [c for c in db.circuits if c.type.lower() in ('power', 'plug', 'socket', 'p')]
            lighting_circuits = [c for c in db.circuits if c.type.lower() in ('lighting', 'light', 'l')]
            ac_circuits = [c for c in db.circuits if c.type.lower() in ('ac', 'aircon', 'hvac')]

            # Mark final cables as extracted
            for item in checklist.items:
                if item.category == ChecklistCategory.FINAL_CABLES:
                    if "POWER" in item.name.upper() and power_circuits:
                        item.extracted = True
                        item.source = f"{len(power_circuits)} power circuits from {db.name}"
                    elif "LIGHTING" in item.name.upper() and lighting_circuits:
                        item.extracted = True
                        item.source = f"{len(lighting_circuits)} lighting circuits from {db.name}"
                    elif "AC" in item.name.upper() and ac_circuits:
                        item.extracted = True
                        item.source = f"{len(ac_circuits)} AC circuits from {db.name}"

        # Check fixtures from rooms
        for room in block.rooms:
            fixtures = room.fixtures

            # Lighting fixtures
            total_lights = fixtures.total_lights
            if total_lights > 0:
                for item in checklist.items:
                    if item.category == ChecklistCategory.LIGHTING:
                        if "LED PANEL" in item.name.upper():
                            # Use correct attribute: recessed_led_600x1200
                            if fixtures.recessed_led_600x1200 > 0:
                                item.extracted = True
                                item.extracted_qty += fixtures.recessed_led_600x1200
                                item.source = "Layout drawings"
                        elif "CEILING" in item.name.upper():
                            # Use correct attributes: surface_mount_led_18w, downlight_led_6w
                            ceiling_count = fixtures.surface_mount_led_18w + fixtures.downlight_led_6w
                            if ceiling_count > 0:
                                item.extracted = True
                                item.extracted_qty += ceiling_count
                                item.source = "Layout drawings"
                        elif "FLOOD" in item.name.upper():
                            if fixtures.flood_light_200w > 0 or fixtures.flood_light_30w > 0:
                                item.extracted = True
                                item.extracted_qty += fixtures.flood_light_200w + fixtures.flood_light_30w
                                item.source = "Layout drawings"

            # Switches
            total_switches = fixtures.total_switches
            if total_switches > 0:
                for item in checklist.items:
                    if item.category == ChecklistCategory.LIGHTING:
                        if "1-LEVER" in item.name.upper():
                            # Use correct attribute: switch_1lever_1way
                            if fixtures.switch_1lever_1way > 0:
                                item.extracted = True
                                item.extracted_qty += fixtures.switch_1lever_1way
                                item.source = "Layout drawings"
                        elif "2-LEVER" in item.name.upper():
                            # Use correct attribute: switch_2lever_1way
                            if fixtures.switch_2lever_1way > 0:
                                item.extracted = True
                                item.extracted_qty += fixtures.switch_2lever_1way
                                item.source = "Layout drawings"

            # Sockets
            total_sockets = fixtures.total_sockets
            if total_sockets > 0:
                for item in checklist.items:
                    if item.category == ChecklistCategory.POWER_OUTLETS:
                        if "DOUBLE" in item.name.upper() and "@300" in item.name:
                            # Use correct attribute: double_socket_300
                            if fixtures.double_socket_300 > 0:
                                item.extracted = True
                                item.extracted_qty += fixtures.double_socket_300
                                item.source = "Layout drawings"
                        elif "SINGLE" in item.name.upper() and "@300" in item.name:
                            # Use correct attribute: single_socket_300
                            if fixtures.single_socket_300 > 0:
                                item.extracted = True
                                item.extracted_qty += fixtures.single_socket_300
                                item.source = "Layout drawings"
                        elif "DOUBLE" in item.name.upper() and "@1100" in item.name:
                            # Use correct attribute: double_socket_1100
                            if fixtures.double_socket_1100 > 0:
                                item.extracted = True
                                item.extracted_qty += fixtures.double_socket_1100
                                item.source = "Layout drawings"
                        elif "ISOLATOR" in item.name.upper():
                            # Use correct attributes: isolator_30a, isolator_20a
                            if fixtures.isolator_30a > 0 or fixtures.isolator_20a > 0:
                                item.extracted = True
                                if "30A" in item.name:
                                    item.extracted_qty += fixtures.isolator_30a
                                elif "20A" in item.name:
                                    item.extracted_qty += fixtures.isolator_20a
                                item.source = "Layout drawings"
                        elif "FLOOR BOX" in item.name.upper():
                            # Use correct attribute: floor_box
                            if fixtures.floor_box > 0:
                                item.extracted = True
                                item.extracted_qty += fixtures.floor_box
                                item.source = "Layout drawings"

            # Data points
            if fixtures.data_points_cat6 > 0:
                for item in checklist.items:
                    if item.category == ChecklistCategory.DATA_COMMS:
                        if "DATA SOCKET" in item.name.upper():
                            item.extracted = True
                            item.extracted_qty += fixtures.data_points_cat6
                            item.source = "Layout drawings"

    # Check site cable runs for sub-mains and incoming
    for run in extraction_result.site_cable_runs:
        cable_spec = run.cable_spec.upper()
        from_point = run.from_point.upper()
        to_point = run.to_point.upper()

        for item in checklist.items:
            if item.category == ChecklistCategory.SUBMAIN_CABLES:
                # Match sub-main cables
                if "16" in cable_spec and "DB-CA" in to_point:
                    if "DB-CA" in item.name.upper():
                        item.extracted = True
                        item.extracted_qty = run.length_m
                        item.source = f"SLD: {run.from_point} to {run.to_point}"
                elif "6" in cable_spec and "DB-S1" in to_point:
                    if "DB-S1" in item.name.upper():
                        item.extracted = True
                        item.extracted_qty = run.length_m
                        item.source = f"SLD: {run.from_point} to {run.to_point}"
                elif "6" in cable_spec and "DB-S2" in to_point:
                    if "DB-S2" in item.name.upper():
                        item.extracted = True
                        item.extracted_qty = run.length_m
                        item.source = f"SLD: {run.from_point} to {run.to_point}"

            if item.category == ChecklistCategory.INCOMING:
                if "95" in cable_spec and "KIOSK" in item.name.upper():
                    item.extracted = True
                    item.extracted_qty = run.length_m
                    item.source = f"SLD: {run.from_point} to {run.to_point}"

    # Check supply points
    for supply in extraction_result.supply_points:
        for item in checklist.items:
            if item.category == ChecklistCategory.INCOMING:
                if "KIOSK" in item.name.upper() or "METERING" in item.name.upper():
                    if supply.has_meter or supply.type == "kiosk":
                        item.extracted = True
                        item.extracted_qty = 1
                        item.source = f"SLD: {supply.name}"
                elif "EARTH ELECTRODE" in item.name.upper():
                    item.extracted = True  # Always included with supply
                    item.source = "Standard requirement"
                elif "EARTH BAR" in item.name.upper():
                    item.extracted = True  # Always included with supply
                    item.source = "Standard requirement"

    # Testing & Documentation - always present for complete installation
    for item in checklist.items:
        if item.category == ChecklistCategory.TESTING:
            item.extracted = True
            item.extracted_qty = 1
            item.source = "Standard requirement per SANS 10142-1"

    # Prelims - always present for complete installation
    for item in checklist.items:
        if item.category == ChecklistCategory.PRELIMS:
            item.extracted = True
            item.extracted_qty = 1
            item.source = "Standard requirement"

    return checklist


def get_checklist_summary_text(checklist: ExtractionChecklist) -> str:
    """Generate a text summary of the checklist results."""
    lines = [
        f"EXTRACTION VALIDATION: {checklist.extraction_rate:.0f}% ({checklist.extracted_items}/{checklist.total_items})",
        "=" * 60,
    ]

    for category in ChecklistCategory:
        cat_items = checklist.items_by_category(category)
        extracted = sum(1 for item in cat_items if item.extracted)

        # Status icon
        if extracted == len(cat_items):
            icon = "✓"
        elif extracted > 0:
            icon = "◐"
        else:
            icon = "✗"

        lines.append(f"\n{icon} {category.value}: {extracted}/{len(cat_items)}")

        for item in cat_items:
            status = "✓" if item.extracted else "✗"
            qty_text = f" ({item.extracted_qty:.0f})" if item.extracted and item.extracted_qty > 0 else ""
            source_text = f" - {item.source}" if item.extracted and item.source else ""
            lines.append(f"    {status} {item.name}{qty_text}{source_text}")

    return "\n".join(lines)
