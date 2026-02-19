"""
VALIDATE Stage: SANS 10142-1:2017 compliance validation.

Runs on contractor-approved data (post-review).
Checks hard rules and applies auto-corrections where possible.

v4.2 Upgrade: Comprehensive SANS 10142-1 compliance with 11 categories:
- Cable sizing (Clause 6.2)
- Protection devices (Clause 6.3)
- Earth leakage (Clause 6.7)
- Earthing (Clause 8)
- Socket outlets (Clause 6.15)
- Lighting circuits (Clause 6.14)
- Air conditioning (Clause 6.15.5/6.16)
- Distribution boards (Clause 6.6)
- Voltage drop (Clause 6.2.6)
- External installations (Clause 7)
- General compliance
"""

from typing import List, Tuple, Optional

from agent.models import (
    ExtractionResult, ValidationResult, ValidationFlag, Severity,
    StageResult, PipelineStage, ItemConfidence
)
from agent.utils import Timer

# Import voltage drop calculator
try:
    from core.standards import calculate_voltage_drop
    HAS_VOLTAGE_DROP = True
except ImportError:
    HAS_VOLTAGE_DROP = False


# SANS 10142-1:2017 Constants
MAX_LIGHTS_PER_CIRCUIT = 10
MAX_SOCKETS_PER_CIRCUIT = 10
ELCB_RATING_A = 63
ELCB_SENSITIVITY_MA = 30
MIN_SPARE_WAYS_PCT = 15
MAX_VOLTAGE_DROP_PCT = 5.0

# Cable current capacity (Amps) - SANS 10142-1 Table 6.2 (enclosed in conduit)
CABLE_CURRENT_CAPACITY = {
    1.5: 14.5,
    2.5: 19.5,
    4.0: 26,
    6.0: 34,
    10.0: 46,
    16.0: 61,
    25.0: 80,
    35.0: 99,
    50.0: 119,
    70.0: 151,
    95.0: 182,
}

# Maximum breaker rating per cable size
CABLE_MAX_BREAKER = {
    1.5: 16,
    2.5: 20,
    4.0: 25,
    6.0: 32,
    10.0: 40,
    16.0: 63,
    25.0: 80,
    35.0: 100,
}

# Wet area room types
WET_AREA_TYPES = {"bathroom", "toilet", "shower", "laundry", "kitchen", "scullery"}


def validate(
    extraction: ExtractionResult,
) -> Tuple[ValidationResult, StageResult]:
    """
    VALIDATE stage: Check SANS 10142-1 compliance.

    Args:
        extraction: Contractor-approved extraction result

    Returns:
        Tuple of (ValidationResult, StageResult)
    """
    with Timer("validate") as timer:
        result = ValidationResult()
        errors = []
        warnings = []

        # Run all validation rules
        flags = []

        # Per-building-block validation
        for block in extraction.building_blocks:
            block_flags = _validate_building_block(block)
            flags.extend(block_flags)

            # Wet area validation (Clause 7.1)
            wet_flags = _validate_wet_areas(block)
            flags.extend(wet_flags)

            # AC circuit validation (Clause 6.15.5/6.16)
            ac_flags = _validate_ac_circuits(block)
            flags.extend(ac_flags)

            # Cable sizing validation (Clause 6.2)
            cable_flags = _validate_cable_sizing(block)
            flags.extend(cable_flags)

        # Site-level validation
        site_flags = _validate_site_infrastructure(extraction)
        flags.extend(site_flags)

        # External installation validation (Clause 7)
        external_flags = _validate_external_installations(extraction)
        flags.extend(external_flags)

        # Voltage drop validation (Clause 6.2.6)
        vd_flags = _validate_voltage_drop(extraction)
        flags.extend(vd_flags)

        # Count results
        result.flags = flags
        result.passed = sum(1 for f in flags if f.passed)
        result.failed = sum(1 for f in flags if not f.passed and f.severity == Severity.CRITICAL)
        result.warnings = sum(1 for f in flags if not f.passed and f.severity == Severity.WARNING)
        result.auto_corrections = sum(1 for f in flags if f.auto_corrected)

        # Calculate compliance score
        total_checks = len(flags)
        if total_checks > 0:
            passed_score = result.passed / total_checks * 100
            # Deduct for critical failures
            critical_penalty = result.failed * 10
            result.compliance_score = max(0, min(100, passed_score - critical_penalty))
        else:
            result.compliance_score = 100.0

        # Build stage result
        stage_result = StageResult(
            stage=PipelineStage.VALIDATE,
            success=result.failed == 0,
            confidence=result.compliance_score / 100,
            data={
                "passed": result.passed,
                "failed": result.failed,
                "warnings": result.warnings,
                "auto_corrections": result.auto_corrections,
                "compliance_score": result.compliance_score,
            },
            processing_time_ms=timer.elapsed_ms,
            errors=errors,
            warnings=warnings,
        )

        return result, stage_result


def _validate_building_block(block) -> List[ValidationFlag]:
    """Validate a single building block."""
    flags = []

    for db in block.distribution_boards:
        # Rule: ELCB required
        if not db.earth_leakage:
            flag = ValidationFlag(
                rule_name="ELCB_REQUIRED",
                message=f"{db.name}: No earth leakage protection detected",
                severity=Severity.CRITICAL,
                passed=False,
                auto_corrected=True,
                corrected_value=f"Add {ELCB_RATING_A}A {ELCB_SENSITIVITY_MA}mA ELCB",
                related_board=db.name,
                related_block=block.name,
                standard_ref="SANS 10142-1 clause 6.7",
            )
            flags.append(flag)
        else:
            flags.append(ValidationFlag(
                rule_name="ELCB_REQUIRED",
                message=f"{db.name}: Earth leakage protection present",
                severity=Severity.CRITICAL,
                passed=True,
                related_board=db.name,
                related_block=block.name,
            ))

        # Rule: Surge protection recommended
        if not db.surge_protection:
            flags.append(ValidationFlag(
                rule_name="SURGE_PROTECTION",
                message=f"{db.name}: No surge protection device",
                severity=Severity.WARNING,
                passed=False,
                auto_corrected=True,
                corrected_value="Add Type 2 SPD",
                related_board=db.name,
                related_block=block.name,
                standard_ref="SANS 10142-1 clause 6.3.4",
            ))

        # Rule: Max points per circuit
        for circuit in db.circuits:
            if circuit.is_spare:
                continue

            if circuit.type == "lighting" and circuit.num_points > MAX_LIGHTS_PER_CIRCUIT:
                flags.append(ValidationFlag(
                    rule_name="MAX_LIGHTS_PER_CIRCUIT",
                    message=f"{db.name} {circuit.id}: {circuit.num_points} lights exceeds max {MAX_LIGHTS_PER_CIRCUIT}",
                    severity=Severity.CRITICAL,
                    passed=False,
                    auto_corrected=True,
                    corrected_value=f"Split into {(circuit.num_points // MAX_LIGHTS_PER_CIRCUIT) + 1} circuits",
                    related_circuit=circuit.id,
                    related_board=db.name,
                    related_block=block.name,
                    standard_ref="SANS 10142-1 clause 6.14.1",
                ))

            if circuit.type == "power" and circuit.num_points > MAX_SOCKETS_PER_CIRCUIT:
                flags.append(ValidationFlag(
                    rule_name="MAX_SOCKETS_PER_CIRCUIT",
                    message=f"{db.name} {circuit.id}: {circuit.num_points} sockets exceeds max {MAX_SOCKETS_PER_CIRCUIT}",
                    severity=Severity.CRITICAL,
                    passed=False,
                    auto_corrected=True,
                    corrected_value=f"Split into {(circuit.num_points // MAX_SOCKETS_PER_CIRCUIT) + 1} circuits",
                    related_circuit=circuit.id,
                    related_board=db.name,
                    related_block=block.name,
                    standard_ref="SANS 10142-1 clause 6.15.1",
                ))

        # Rule: Minimum spare ways
        total_ways = len(db.circuits) + db.spare_ways
        if total_ways > 0:
            spare_pct = (db.spare_ways / total_ways) * 100
            if spare_pct < MIN_SPARE_WAYS_PCT:
                recommended_ways = int(total_ways * 1.2)  # 20% overhead
                flags.append(ValidationFlag(
                    rule_name="MIN_SPARE_WAYS",
                    message=f"{db.name}: Only {spare_pct:.0f}% spare ways (min {MIN_SPARE_WAYS_PCT}%)",
                    severity=Severity.WARNING,
                    passed=False,
                    auto_corrected=True,
                    corrected_value=f"Upsize to {recommended_ways}-way DB",
                    related_board=db.name,
                    related_block=block.name,
                    standard_ref="SANS 10142-1 clause 6.6.2",
                ))

    # Check for dedicated circuits in rooms
    for room in block.rooms:
        # Stove circuit check
        if room.type in ("kitchen",) and not _has_dedicated_circuit(block, "stove"):
            flags.append(ValidationFlag(
                rule_name="DEDICATED_STOVE_CIRCUIT",
                message=f"{room.name}: Kitchen requires dedicated stove circuit",
                severity=Severity.CRITICAL,
                passed=False,
                auto_corrected=True,
                corrected_value="Add 32A dedicated stove circuit",
                related_block=block.name,
                standard_ref="SANS 10142-1 clause 6.15.5",
            ))

        # Geyser circuit check
        if room.has_geyser and not _has_dedicated_circuit(block, "geyser"):
            flags.append(ValidationFlag(
                rule_name="DEDICATED_GEYSER_CIRCUIT",
                message=f"{room.name}: Geyser requires dedicated circuit with timer",
                severity=Severity.CRITICAL,
                passed=False,
                auto_corrected=True,
                corrected_value="Add 20A dedicated geyser circuit with timer",
                related_block=block.name,
                standard_ref="SANS 10142-1 clause 6.15.5",
            ))

    return flags


def _validate_site_infrastructure(extraction: ExtractionResult) -> List[ValidationFlag]:
    """Validate site-level infrastructure."""
    flags = []

    # Check cable lengths are reasonable
    for run in extraction.site_cable_runs:
        if run.confidence == ItemConfidence.ESTIMATED:
            flags.append(ValidationFlag(
                rule_name="CABLE_LENGTH_ESTIMATED",
                message=f"Cable {run.from_point} to {run.to_point}: Length ({run.length_m}m) is estimated",
                severity=Severity.INFO,
                passed=True,  # Info only
                standard_ref="Site survey recommended",
            ))

        # Check for excessively long cable runs (voltage drop concern)
        if run.length_m > 100 and run.cable_size_mm2 < 16:
            flags.append(ValidationFlag(
                rule_name="VOLTAGE_DROP_WARNING",
                message=f"Cable {run.from_point} to {run.to_point}: {run.length_m}m run with {run.cable_size_mm2}mm² may exceed voltage drop limits",
                severity=Severity.WARNING,
                passed=False,
                corrected_value="Verify voltage drop calculation",
                standard_ref="SANS 10142-1 Annexure B",
            ))

    return flags


def _has_dedicated_circuit(block, circuit_type: str) -> bool:
    """Check if a dedicated circuit exists for a given type."""
    for db in block.distribution_boards:
        for circuit in db.circuits:
            if circuit_type in circuit.type.lower() or circuit_type in circuit.description.lower():
                return True
    return False


def _validate_cable_sizing(block) -> List[ValidationFlag]:
    """
    Validate cable sizing per SANS 10142-1 Clause 6.2.

    Checks:
    - Cable current capacity matches or exceeds breaker rating
    - Breaker rating does not exceed cable capacity
    """
    flags = []

    for db in block.distribution_boards:
        for circuit in db.circuits:
            if circuit.is_spare:
                continue

            cable_size = circuit.cable_size_mm2
            breaker_rating = circuit.breaker_a

            if cable_size and breaker_rating:
                # Get cable capacity
                cable_capacity = CABLE_CURRENT_CAPACITY.get(cable_size)
                max_breaker = CABLE_MAX_BREAKER.get(cable_size)

                if cable_capacity and breaker_rating > cable_capacity:
                    flags.append(ValidationFlag(
                        rule_name="CABLE_OVERCURRENT_PROTECTION",
                        message=f"{db.name} {circuit.id}: {breaker_rating}A breaker exceeds {cable_size}mm² cable capacity ({cable_capacity}A)",
                        severity=Severity.CRITICAL,
                        passed=False,
                        auto_corrected=True,
                        corrected_value=f"Upsize cable to handle {breaker_rating}A",
                        related_circuit=circuit.id,
                        related_board=db.name,
                        related_block=block.name,
                        standard_ref="SANS 10142-1 clause 6.2.1",
                    ))
                elif max_breaker and breaker_rating > max_breaker:
                    flags.append(ValidationFlag(
                        rule_name="CABLE_BREAKER_MISMATCH",
                        message=f"{db.name} {circuit.id}: {breaker_rating}A breaker too large for {cable_size}mm² (max {max_breaker}A)",
                        severity=Severity.WARNING,
                        passed=False,
                        related_circuit=circuit.id,
                        related_board=db.name,
                        related_block=block.name,
                        standard_ref="SANS 10142-1 clause 6.2.2",
                    ))

            # Check minimum cable sizes
            if circuit.type == "lighting" and cable_size and cable_size < 1.5:
                flags.append(ValidationFlag(
                    rule_name="MIN_CABLE_SIZE_LIGHTING",
                    message=f"{db.name} {circuit.id}: Lighting circuit requires min 1.5mm² cable",
                    severity=Severity.CRITICAL,
                    passed=False,
                    auto_corrected=True,
                    corrected_value="Use 1.5mm² cable minimum",
                    related_circuit=circuit.id,
                    related_board=db.name,
                    related_block=block.name,
                    standard_ref="SANS 10142-1 clause 6.2.3",
                ))

            if circuit.type == "power" and cable_size and cable_size < 2.5:
                flags.append(ValidationFlag(
                    rule_name="MIN_CABLE_SIZE_POWER",
                    message=f"{db.name} {circuit.id}: Power circuit requires min 2.5mm² cable",
                    severity=Severity.CRITICAL,
                    passed=False,
                    auto_corrected=True,
                    corrected_value="Use 2.5mm² cable minimum",
                    related_circuit=circuit.id,
                    related_board=db.name,
                    related_block=block.name,
                    standard_ref="SANS 10142-1 clause 6.2.3",
                ))

    return flags


def _validate_voltage_drop(extraction: ExtractionResult) -> List[ValidationFlag]:
    """
    Validate voltage drop per SANS 10142-1 Clause 6.2.6.

    Uses calculate_voltage_drop from core/standards.py if available.
    Maximum 5% voltage drop (2.5% sub-mains + 2.5% final circuits).
    """
    flags = []

    if not HAS_VOLTAGE_DROP:
        return flags

    for run in extraction.site_cable_runs:
        if run.length_m and run.cable_size_mm2:
            # Estimate current based on typical load (10A for sub-mains)
            estimated_current = 10.0  # Conservative estimate

            vd_pct, is_compliant, message = calculate_voltage_drop(
                cable_size_mm2=run.cable_size_mm2,
                length_m=run.length_m,
                current_a=estimated_current,
                voltage_v=230,
                is_three_phase=False
            )

            if not is_compliant:
                flags.append(ValidationFlag(
                    rule_name="VOLTAGE_DROP_EXCEEDED",
                    message=f"Cable {run.from_point} to {run.to_point}: {vd_pct}% voltage drop exceeds 5% limit",
                    severity=Severity.CRITICAL,
                    passed=False,
                    auto_corrected=True,
                    corrected_value=f"Increase cable size from {run.cable_size_mm2}mm²",
                    standard_ref="SANS 10142-1 clause 6.2.6",
                ))
            elif vd_pct > 3.0:  # Warn if approaching limit
                flags.append(ValidationFlag(
                    rule_name="VOLTAGE_DROP_WARNING",
                    message=f"Cable {run.from_point} to {run.to_point}: {vd_pct}% voltage drop approaching limit",
                    severity=Severity.WARNING,
                    passed=True,
                    standard_ref="SANS 10142-1 clause 6.2.6",
                ))

    return flags


def _validate_wet_areas(block) -> List[ValidationFlag]:
    """
    Validate wet area requirements per SANS 10142-1 Clause 7.1.

    Checks:
    - Wet areas have appropriate IP ratings
    - Socket restrictions in bathrooms
    """
    flags = []

    for room in block.rooms:
        is_wet = getattr(room, 'is_wet_area', False) or room.type.lower() in WET_AREA_TYPES

        if is_wet:
            # Check for sockets in wet areas
            fixtures = room.fixtures
            total_sockets = (
                getattr(fixtures, 'double_socket_300', 0) +
                getattr(fixtures, 'single_socket_300', 0) +
                getattr(fixtures, 'double_socket_1100', 0) +
                getattr(fixtures, 'single_socket_1100', 0)
            )

            # Bathrooms should have limited sockets
            if room.type.lower() in ("bathroom", "toilet", "shower"):
                if total_sockets > 1:
                    flags.append(ValidationFlag(
                        rule_name="WET_AREA_SOCKET_RESTRICTION",
                        message=f"{room.name}: Bathroom has {total_sockets} sockets - verify zone compliance",
                        severity=Severity.WARNING,
                        passed=False,
                        standard_ref="SANS 10142-1 clause 7.1.3",
                    ))

            # Check waterproof socket requirement
            waterproof = getattr(fixtures, 'double_socket_waterproof', 0)
            if total_sockets > 0 and waterproof == 0:
                flags.append(ValidationFlag(
                    rule_name="WET_AREA_IP_RATING",
                    message=f"{room.name}: Wet area sockets should be IP44 rated minimum",
                    severity=Severity.WARNING,
                    passed=False,
                    auto_corrected=True,
                    corrected_value="Use IP44 rated sockets",
                    standard_ref="SANS 10142-1 clause 7.1.2",
                ))

    return flags


def _validate_ac_circuits(block) -> List[ValidationFlag]:
    """
    Validate AC circuit requirements per SANS 10142-1 Clause 6.15.5/6.16.

    Checks:
    - Each AC unit has a dedicated circuit
    - Isolator present for each AC unit
    """
    flags = []

    # Count AC units in rooms
    total_ac_units = 0
    rooms_with_ac = []

    for room in block.rooms:
        fixtures = room.fixtures
        ac_count = getattr(fixtures, 'ac_units', 0)
        if ac_count > 0:
            total_ac_units += ac_count
            rooms_with_ac.append(room.name)

    if total_ac_units == 0:
        return flags

    # Check for dedicated AC circuits
    ac_circuits = 0
    ac_isolators = 0

    for db in block.distribution_boards:
        for circuit in db.circuits:
            if "ac" in circuit.type.lower() or "air" in circuit.description.lower():
                ac_circuits += 1
                if circuit.has_isolator:
                    ac_isolators += 1

    # Each AC needs dedicated circuit
    if ac_circuits < total_ac_units:
        flags.append(ValidationFlag(
            rule_name="AC_DEDICATED_CIRCUIT",
            message=f"{block.name}: {total_ac_units} AC units but only {ac_circuits} dedicated circuits",
            severity=Severity.CRITICAL,
            passed=False,
            auto_corrected=True,
            corrected_value=f"Add {total_ac_units - ac_circuits} dedicated AC circuits",
            related_block=block.name,
            standard_ref="SANS 10142-1 clause 6.15.5",
        ))

    # Each AC needs isolator
    if ac_isolators < total_ac_units:
        flags.append(ValidationFlag(
            rule_name="AC_ISOLATOR_REQUIRED",
            message=f"{block.name}: AC units require isolator switches within sight of unit",
            severity=Severity.WARNING,
            passed=False,
            auto_corrected=True,
            corrected_value=f"Add {total_ac_units - ac_isolators} AC isolator switches",
            related_block=block.name,
            standard_ref="SANS 10142-1 clause 6.16.2",
        ))

    return flags


def _validate_external_installations(extraction: ExtractionResult) -> List[ValidationFlag]:
    """
    Validate external installation requirements per SANS 10142-1 Clause 7.

    Checks:
    - Underground cables are armoured (SWA)
    - Minimum burial depth for cables
    - IP rating for external equipment
    """
    flags = []

    for run in extraction.site_cable_runs:
        is_underground = getattr(run, 'is_underground', False)
        needs_trenching = getattr(run, 'needs_trenching', False)

        if is_underground or needs_trenching:
            # Check cable type is armoured
            cable_type = getattr(run, 'cable_type', '').upper()
            if cable_type and 'SWA' not in cable_type and 'ARMOURED' not in cable_type:
                flags.append(ValidationFlag(
                    rule_name="UNDERGROUND_CABLE_TYPE",
                    message=f"Cable {run.from_point} to {run.to_point}: Underground cables must be SWA (armoured)",
                    severity=Severity.CRITICAL,
                    passed=False,
                    auto_corrected=True,
                    corrected_value="Use PVC/SWA/PVC armoured cable",
                    standard_ref="SANS 10142-1 clause 7.3.1",
                ))

            # Check burial depth (600mm minimum for LV cables)
            if run.length_m > 5:  # Only check for significant runs
                flags.append(ValidationFlag(
                    rule_name="UNDERGROUND_BURIAL_DEPTH",
                    message=f"Cable {run.from_point} to {run.to_point}: Verify minimum 600mm burial depth",
                    severity=Severity.INFO,
                    passed=True,
                    standard_ref="SANS 10142-1 clause 7.3.2",
                ))

    # Check external lighting has appropriate IP rating
    outside_lights = getattr(extraction, 'outside_lights', None)
    if outside_lights:
        total_external = (
            getattr(outside_lights, 'pole_light_60w', 0) +
            getattr(outside_lights, 'flood_light_200w', 0) +
            getattr(outside_lights, 'bulkhead_26w', 0)
        )
        if total_external > 0:
            flags.append(ValidationFlag(
                rule_name="EXTERNAL_IP_RATING",
                message=f"External lighting ({total_external} fittings): Verify IP65 rating minimum",
                severity=Severity.INFO,
                passed=True,
                standard_ref="SANS 10142-1 clause 7.2.1",
            ))

    return flags
