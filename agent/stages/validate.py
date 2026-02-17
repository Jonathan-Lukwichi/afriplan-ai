"""
VALIDATE Stage: SANS 10142-1:2017 compliance validation.

Runs on contractor-approved data (post-review).
Checks hard rules and applies auto-corrections where possible.
"""

from typing import List, Tuple, Optional

from agent.models import (
    ExtractionResult, ValidationResult, ValidationFlag, Severity,
    StageResult, PipelineStage, ItemConfidence
)
from agent.utils import Timer


# SANS 10142-1:2017 Constants
MAX_LIGHTS_PER_CIRCUIT = 10
MAX_SOCKETS_PER_CIRCUIT = 10
ELCB_RATING_A = 63
ELCB_SENSITIVITY_MA = 30
MIN_SPARE_WAYS_PCT = 15
MAX_VOLTAGE_DROP_PCT = 5.0


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

        # Site-level validation
        site_flags = _validate_site_infrastructure(extraction)
        flags.extend(site_flags)

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
                standard_ref="SANS 10142-1 clause 6.12",
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
                standard_ref="SANS 10142-1 clause 4.4.5",
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
                    standard_ref="SANS 10142-1 clause 6.5.1.1",
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
                    standard_ref="SANS 10142-1 clause 6.5.1.1",
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
                    standard_ref="SANS 10142-1 clause 6.2.4",
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
                standard_ref="SANS 10142-1 clause 6.5.4",
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
                standard_ref="SANS 10142-1 clause 6.5.4",
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
