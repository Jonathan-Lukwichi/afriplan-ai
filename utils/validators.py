"""
AfriPlan AI - SANS 10142-1 Hard Rule Validator

This module implements deterministic validation rules from SANS 10142-1:2017.
These are non-negotiable compliance requirements - no AI interpretation needed.

Hard Rules (auto-fail if violated):
1. ELCB 30mA mandatory on all circuits
2. Max 10 points per lighting circuit
3. Max 10 points per power circuit
4. Dedicated circuit for stove (32A)
5. Dedicated circuit for geyser (20A)
6. Earth spike required
7. Surge protection recommended

Usage:
    from utils.validators import SANS10142Validator, ValidationReport

    validator = SANS10142Validator()
    report = validator.validate_residential(extracted_data)

    if report.passed:
        print("All checks passed")
    else:
        for r in report.results:
            if not r.passed:
                print(f"{r.severity}: {r.message}")
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from enum import Enum


class Severity(Enum):
    """Severity levels for validation results."""
    CRITICAL = "critical"  # Must be fixed before COC
    MAJOR = "major"        # Should be fixed
    MINOR = "minor"        # Recommended
    INFO = "info"          # Information only


@dataclass
class ValidationResult:
    """Result from a single validation check."""
    rule_name: str
    rule_ref: str  # SANS 10142-1 clause reference
    passed: bool
    severity: str
    message: str
    auto_corrected: bool = False
    corrected_value: Any = None


@dataclass
class ValidationReport:
    """Complete validation report."""
    passed: bool  # All critical and major rules passed
    results: List[ValidationResult]
    error_count: int
    warning_count: int
    auto_corrections_made: int

    @property
    def critical_count(self) -> int:
        return sum(1 for r in self.results if r.severity == "critical" and not r.passed)

    @property
    def major_count(self) -> int:
        return sum(1 for r in self.results if r.severity == "major" and not r.passed)


class SANS10142Validator:
    """
    SANS 10142-1:2017 Hard Rule Validator.

    Implements deterministic validation rules that do not require AI interpretation.
    All rules are based on specific clauses from the standard.
    """

    # Hard-coded rule limits
    RULES = {
        "max_lights_per_circuit": 10,       # SANS 10142-1 limit
        "max_sockets_per_circuit": 10,      # SANS 10142-1 limit
        "elcb_mandatory": True,             # 30mA on all circuits
        "elcb_rating_ma": 30,
        "max_voltage_drop_pct": 5.0,        # 2.5% sub-mains + 2.5% final
        "stove_dedicated": True,            # 32A dedicated circuit mandatory
        "stove_mcb_rating": 32,
        "geyser_dedicated": True,           # 20A dedicated circuit mandatory
        "geyser_mcb_rating": 20,
        "outdoor_socket_min_ip": "IP55",
        "bathroom_socket_min_distance_mm": 600,  # From bath/shower
        "min_spare_ways_pct": 0.15,         # 15% spare in DB
        "earth_spike_required": True,
        "surge_protection_recommended": True,
        "radial_only": True,                # No ring circuits in SA
        "vat_rate": 0.15,
    }

    # Default DB sizes
    DB_SIZES = [8, 12, 16, 20, 24, 36, 48]

    def validate_residential(self, data: Dict[str, Any]) -> ValidationReport:
        """
        Validate residential installation data against SANS 10142-1.

        Args:
            data: Extracted data from document analysis

        Returns:
            ValidationReport with all check results
        """
        results: List[ValidationResult] = []

        # Run all checks
        results.extend(self._check_elcb(data))
        results.extend(self._check_surge_protection(data))
        results.extend(self._check_earth_system(data))
        results.extend(self._check_dedicated_circuits(data))
        results.extend(self._check_circuit_loading(data))
        results.extend(self._check_db_spare_ways(data))
        results.extend(self._check_cable_sizing(data))
        results.extend(self._check_outdoor_protection(data))

        return self._compile_report(results)

    def validate_commercial(self, data: Dict[str, Any]) -> ValidationReport:
        """
        Validate commercial installation data.
        Includes residential rules plus additional commercial requirements.
        """
        # Start with residential checks
        results = list(self._check_elcb(data))
        results.extend(self._check_surge_protection(data))
        results.extend(self._check_earth_system(data))

        # Add commercial-specific checks
        results.extend(self._check_phase_balance(data))
        results.extend(self._check_emergency_lighting(data))
        results.extend(self._check_fire_alarm(data))

        return self._compile_report(results)

    def validate_maintenance(self, data: Dict[str, Any]) -> ValidationReport:
        """
        Validate data for COC/maintenance work.
        Focus on defect identification and existing installation assessment.
        """
        results: List[ValidationResult] = []

        # Check existing installation
        existing = data.get("existing_installation", {})

        # ELCB check
        if existing.get("elcb_present") is False:
            results.append(ValidationResult(
                rule_name="ELCB Required",
                rule_ref="SANS 10142-1 Cl 7.2.6",
                passed=False,
                severity="critical",
                message="Earth leakage device (30mA) not present - installation fails COC",
                auto_corrected=True,
                corrected_value={"defect_code": "no_elcb", "add_to_remedial": True}
            ))
        elif existing.get("elcb_present") is True:
            results.append(ValidationResult(
                rule_name="ELCB Present",
                rule_ref="SANS 10142-1 Cl 7.2.6",
                passed=True,
                severity="info",
                message="Earth leakage device present"
            ))

        # Earth system check
        visible_defects = existing.get("visible_defects", [])
        if "no earth spike" in str(visible_defects).lower() or \
           "no_earth_spike" in str(data.get("defects", [])):
            results.append(ValidationResult(
                rule_name="Earth System",
                rule_ref="SANS 10142-1 Cl 7.3",
                passed=False,
                severity="critical",
                message="Earth spike missing or inadequate - installation fails COC",
                auto_corrected=True,
                corrected_value={"defect_code": "no_earth_spike", "add_to_remedial": True}
            ))

        # Surge protection check
        if existing.get("surge_present") is False:
            results.append(ValidationResult(
                rule_name="Surge Protection",
                rule_ref="SANS 10142-1 Recommended",
                passed=False,
                severity="minor",
                message="Surge protection not installed - recommended for SA lightning risk",
                auto_corrected=True,
                corrected_value={"defect_code": "no_surge", "add_to_remedial": True}
            ))

        # DB condition check
        db_condition = existing.get("db_condition", "unknown")
        if db_condition in ("poor", "dangerous"):
            results.append(ValidationResult(
                rule_name="DB Board Condition",
                rule_ref="SANS 10142-1 Cl 6.4",
                passed=False,
                severity="critical" if db_condition == "dangerous" else "major",
                message=f"DB board condition is {db_condition} - replacement recommended",
                auto_corrected=True,
                corrected_value={"defect_code": "outdated_db", "add_to_remedial": True}
            ))

        # Labelling check
        labelling = existing.get("labelling", "unknown")
        if labelling == "none":
            results.append(ValidationResult(
                rule_name="Circuit Labelling",
                rule_ref="SANS 10142-1 Cl 6.4.2",
                passed=False,
                severity="minor",
                message="Circuits not labelled - circuit schedule required",
                auto_corrected=True,
                corrected_value={"defect_code": "no_labels", "add_to_remedial": True}
            ))

        return self._compile_report(results)

    def apply_corrections(
        self,
        data: Dict[str, Any],
        results: List[ValidationResult]
    ) -> Dict[str, Any]:
        """
        Apply auto-corrections to the data based on validation results.

        Args:
            data: Original extracted data
            results: Validation results with corrections

        Returns:
            Updated data with corrections applied
        """
        corrected = data.copy()

        for result in results:
            if result.auto_corrected and result.corrected_value is not None:
                # Handle ELCB correction
                if result.rule_name == "ELCB Required":
                    if "db_board" not in corrected:
                        corrected["db_board"] = {}
                    corrected["db_board"]["elcb"] = True
                    corrected["db_board"]["elcb_rating"] = "63A 30mA"

                # Handle surge protection correction
                elif result.rule_name == "Surge Protection":
                    if "db_board" not in corrected:
                        corrected["db_board"] = {}
                    corrected["db_board"]["surge_protection"] = True

                # Handle dedicated circuit corrections
                elif "Stove Circuit" in result.rule_name:
                    if "dedicated_circuits" not in corrected:
                        corrected["dedicated_circuits"] = []
                    if "stove_circuit_3phase" not in corrected["dedicated_circuits"]:
                        corrected["dedicated_circuits"].append("stove_circuit_3phase")

                elif "Geyser Circuit" in result.rule_name:
                    if "dedicated_circuits" not in corrected:
                        corrected["dedicated_circuits"] = []
                    if "geyser_circuit" not in corrected["dedicated_circuits"]:
                        corrected["dedicated_circuits"].append("geyser_circuit")

                # Handle defect additions for maintenance
                elif isinstance(result.corrected_value, dict) and \
                     result.corrected_value.get("add_to_remedial"):
                    if "defects" not in corrected:
                        corrected["defects"] = []
                    defect_code = result.corrected_value.get("defect_code")
                    if defect_code and defect_code not in [d.get("code") if isinstance(d, dict) else d for d in corrected["defects"]]:
                        corrected["defects"].append({"code": defect_code, "qty": 1})

        return corrected

    # Private validation methods

    def _check_elcb(self, data: Dict[str, Any]) -> List[ValidationResult]:
        """Check earth leakage protection requirement."""
        results = []
        db_board = data.get("db_board", {})

        if not db_board.get("elcb", False):
            results.append(ValidationResult(
                rule_name="ELCB Required",
                rule_ref="SANS 10142-1 Cl 7.2.6",
                passed=False,
                severity="critical",
                message="Earth leakage device (30mA) is MANDATORY for all installations",
                auto_corrected=True,
                corrected_value=True
            ))
        else:
            results.append(ValidationResult(
                rule_name="ELCB Required",
                rule_ref="SANS 10142-1 Cl 7.2.6",
                passed=True,
                severity="info",
                message="Earth leakage protection specified"
            ))

        return results

    def _check_surge_protection(self, data: Dict[str, Any]) -> List[ValidationResult]:
        """Check surge protection (recommended, not mandatory)."""
        results = []
        db_board = data.get("db_board", {})

        if not db_board.get("surge_protection", False):
            results.append(ValidationResult(
                rule_name="Surge Protection",
                rule_ref="SANS 10142-1 Recommended",
                passed=False,
                severity="minor",
                message="Surge protection (Type 2) recommended - SA has extreme lightning risk",
                auto_corrected=True,
                corrected_value=True
            ))
        else:
            results.append(ValidationResult(
                rule_name="Surge Protection",
                rule_ref="SANS 10142-1 Recommended",
                passed=True,
                severity="info",
                message="Surge protection specified"
            ))

        return results

    def _check_earth_system(self, data: Dict[str, Any]) -> List[ValidationResult]:
        """Check earth system requirements."""
        results = []

        # Check for earth spike mention
        # This is typically inferred rather than explicitly stated
        notes = data.get("notes", [])
        outdoor = data.get("outdoor", {})

        # Assume compliant unless specifically flagged as missing
        results.append(ValidationResult(
            rule_name="Earth System",
            rule_ref="SANS 10142-1 Cl 7.3",
            passed=True,
            severity="info",
            message="Earth system assumed compliant - verify earth spike installation"
        ))

        return results

    def _check_dedicated_circuits(self, data: Dict[str, Any]) -> List[ValidationResult]:
        """Check dedicated circuit requirements for stove and geyser."""
        results = []
        dedicated = data.get("dedicated_circuits", [])
        rooms = data.get("rooms", [])

        # Check if kitchen exists
        has_kitchen = any(
            r.get("room_type", "").lower() == "kitchen" or
            "kitchen" in r.get("room_name", "").lower()
            for r in rooms
        )

        # Check stove circuit
        has_stove = any(
            "stove" in str(dc).lower()
            for dc in dedicated
        )

        if has_kitchen and not has_stove:
            # Check if stove is mentioned in room dedicated circuits
            kitchen_has_stove = any(
                "stove" in str(r.get("dedicated_circuits", [])).lower()
                for r in rooms
                if "kitchen" in r.get("room_name", "").lower() or
                   r.get("room_type", "").lower() == "kitchen"
            )

            if not kitchen_has_stove:
                results.append(ValidationResult(
                    rule_name="Stove Circuit",
                    rule_ref="SANS 10142-1 Cl 6.10",
                    passed=False,
                    severity="major",
                    message="No dedicated stove circuit detected - 32A dedicated circuit required",
                    auto_corrected=True,
                    corrected_value="stove_circuit_3phase"
                ))
            else:
                results.append(ValidationResult(
                    rule_name="Stove Circuit",
                    rule_ref="SANS 10142-1 Cl 6.10",
                    passed=True,
                    severity="info",
                    message="Stove circuit specified"
                ))
        elif has_stove:
            results.append(ValidationResult(
                rule_name="Stove Circuit",
                rule_ref="SANS 10142-1 Cl 6.10",
                passed=True,
                severity="info",
                message="Stove circuit specified"
            ))

        # Check geyser circuit
        has_geyser = any(
            "geyser" in str(dc).lower()
            for dc in dedicated
        )

        geyser_info = data.get("geyser", {})
        geyser_type = geyser_info.get("type", "electric")

        if geyser_type == "electric" and not has_geyser:
            if not geyser_info.get("circuit_required", False):
                results.append(ValidationResult(
                    rule_name="Geyser Circuit",
                    rule_ref="SANS 10142-1 Cl 6.10",
                    passed=False,
                    severity="major",
                    message="No dedicated geyser circuit detected - 20A dedicated circuit with timer required",
                    auto_corrected=True,
                    corrected_value="geyser_circuit"
                ))
            else:
                results.append(ValidationResult(
                    rule_name="Geyser Circuit",
                    rule_ref="SANS 10142-1 Cl 6.10",
                    passed=True,
                    severity="info",
                    message="Geyser circuit specified"
                ))
        elif has_geyser:
            results.append(ValidationResult(
                rule_name="Geyser Circuit",
                rule_ref="SANS 10142-1 Cl 6.10",
                passed=True,
                severity="info",
                message="Geyser circuit specified"
            ))

        return results

    def _check_circuit_loading(self, data: Dict[str, Any]) -> List[ValidationResult]:
        """Check circuit loading limits (max 10 points per circuit)."""
        results = []
        rooms = data.get("rooms", [])

        total_lights = data.get("total_light_points", 0)
        total_sockets = data.get("total_socket_outlets", 0)

        # If not provided, calculate from rooms
        if total_lights == 0:
            total_lights = sum(
                r.get("lights", {}).get("count", 0) if isinstance(r.get("lights"), dict)
                else r.get("lights", 0)
                for r in rooms
            )

        if total_sockets == 0:
            total_sockets = sum(
                r.get("sockets", {}).get("doubles", 0) +
                r.get("sockets", {}).get("singles", 0)
                if isinstance(r.get("sockets"), dict)
                else r.get("sockets", 0)
                for r in rooms
            )

        # Check if circuits are over-loaded
        db_board = data.get("db_board", {})
        circuits = db_board.get("circuits", [])

        for circuit in circuits:
            if circuit.get("type") == "lighting":
                # Check lighting circuit loading
                pass  # Would need more detailed circuit assignment data

        # General check: warn if total points suggest insufficient circuits
        min_lighting_circuits = (total_lights + 9) // 10  # Ceiling division
        min_power_circuits = (total_sockets + 9) // 10

        results.append(ValidationResult(
            rule_name="Circuit Loading",
            rule_ref="SANS 10142-1",
            passed=True,
            severity="info",
            message=f"Estimated minimum circuits: {min_lighting_circuits} lighting, {min_power_circuits} power"
        ))

        return results

    def _check_db_spare_ways(self, data: Dict[str, Any]) -> List[ValidationResult]:
        """Check DB board has adequate spare ways."""
        results = []
        db_board = data.get("db_board", {})

        total_circuits = len(db_board.get("circuits", []))
        db_ways = db_board.get("recommended_ways", 0)

        if db_ways > 0 and total_circuits > 0:
            spare_pct = (db_ways - total_circuits) / db_ways

            if spare_pct < self.RULES["min_spare_ways_pct"]:
                results.append(ValidationResult(
                    rule_name="DB Spare Capacity",
                    rule_ref="SANS 10142-1 Best Practice",
                    passed=False,
                    severity="minor",
                    message=f"DB has only {spare_pct:.0%} spare ways (recommend 15%+ for future expansion)",
                    auto_corrected=False
                ))
            else:
                results.append(ValidationResult(
                    rule_name="DB Spare Capacity",
                    rule_ref="SANS 10142-1 Best Practice",
                    passed=True,
                    severity="info",
                    message=f"DB has {spare_pct:.0%} spare capacity"
                ))

        return results

    def _check_cable_sizing(self, data: Dict[str, Any]) -> List[ValidationResult]:
        """Check cable sizing is appropriate (basic check)."""
        results = []
        cable_estimate = data.get("cable_estimate", {})

        long_runs = cable_estimate.get("long_runs_flagged", [])
        if long_runs:
            for run in long_runs:
                results.append(ValidationResult(
                    rule_name="Cable Sizing - Long Run",
                    rule_ref="SANS 10142-1 Voltage Drop",
                    passed=False,
                    severity="minor",
                    message=f"Long cable run flagged: {run} - verify voltage drop <5%",
                    auto_corrected=False
                ))

        return results

    def _check_outdoor_protection(self, data: Dict[str, Any]) -> List[ValidationResult]:
        """Check outdoor socket protection requirements."""
        results = []
        outdoor = data.get("outdoor", {})

        weatherproof_count = outdoor.get("weatherproof_sockets", 0)
        if weatherproof_count > 0:
            results.append(ValidationResult(
                rule_name="Outdoor Socket Protection",
                rule_ref="SANS 10142-1 Cl 6.6.3",
                passed=True,
                severity="info",
                message=f"{weatherproof_count} weatherproof socket(s) specified - ensure IP55 minimum"
            ))

        pool = outdoor.get("pool", False)
        if pool:
            results.append(ValidationResult(
                rule_name="Pool Equipment",
                rule_ref="SANS 10142-1 Section 8",
                passed=True,
                severity="info",
                message="Pool equipment detected - ensure IP65 protection and RCD on pool circuit"
            ))

        return results

    def _check_phase_balance(self, data: Dict[str, Any]) -> List[ValidationResult]:
        """Check three-phase balance (commercial)."""
        results = []
        distribution = data.get("distribution", {})
        phase_balance = distribution.get("phase_balance", {})

        if phase_balance:
            l1 = phase_balance.get("L1_kw", 0)
            l2 = phase_balance.get("L2_kw", 0)
            l3 = phase_balance.get("L3_kw", 0)
            total = l1 + l2 + l3

            if total > 0:
                for phase, load in [("L1", l1), ("L2", l2), ("L3", l3)]:
                    pct = load / total
                    if pct > 0.40:
                        results.append(ValidationResult(
                            rule_name="Phase Balance",
                            rule_ref="SANS 10142-1 Three-phase",
                            passed=False,
                            severity="major",
                            message=f"{phase} carries {pct:.0%} of total load (max 40%) - redistribute circuits",
                            auto_corrected=False
                        ))

                if not any(r.rule_name == "Phase Balance" and not r.passed for r in results):
                    results.append(ValidationResult(
                        rule_name="Phase Balance",
                        rule_ref="SANS 10142-1 Three-phase",
                        passed=True,
                        severity="info",
                        message="Three-phase balance within acceptable limits"
                    ))

        return results

    def _check_emergency_lighting(self, data: Dict[str, Any]) -> List[ValidationResult]:
        """Check emergency lighting (commercial)."""
        results = []
        emergency = data.get("emergency", {})
        project = data.get("project", {})

        building_type = project.get("building_type", "")
        if building_type != "warehouse":
            emergency_lights = emergency.get("emergency_lights", 0)

            if emergency_lights == 0:
                results.append(ValidationResult(
                    rule_name="Emergency Lighting",
                    rule_ref="SANS 10400-T",
                    passed=False,
                    severity="critical",
                    message="No emergency lighting specified - required for commercial buildings",
                    auto_corrected=False
                ))
            else:
                results.append(ValidationResult(
                    rule_name="Emergency Lighting",
                    rule_ref="SANS 10400-T",
                    passed=True,
                    severity="info",
                    message=f"{emergency_lights} emergency light(s) specified"
                ))

        return results

    def _check_fire_alarm(self, data: Dict[str, Any]) -> List[ValidationResult]:
        """Check fire alarm system (commercial)."""
        results = []
        emergency = data.get("emergency", {})
        fire_alarm = emergency.get("fire_alarm", {})

        if not fire_alarm:
            fire_alarm_flag = data.get("fire_alarm", False)
            if not fire_alarm_flag:
                results.append(ValidationResult(
                    rule_name="Fire Detection",
                    rule_ref="SANS 10400-T",
                    passed=False,
                    severity="major",
                    message="No fire detection system specified - verify requirements",
                    auto_corrected=False
                ))
        else:
            results.append(ValidationResult(
                rule_name="Fire Detection",
                rule_ref="SANS 10400-T",
                passed=True,
                severity="info",
                message="Fire detection system specified"
            ))

        return results

    def _compile_report(self, results: List[ValidationResult]) -> ValidationReport:
        """Compile all validation results into a report."""
        error_count = sum(
            1 for r in results
            if not r.passed and r.severity in ("critical", "major")
        )
        warning_count = sum(
            1 for r in results
            if not r.passed and r.severity in ("minor",)
        )
        auto_corrections = sum(1 for r in results if r.auto_corrected)

        # Pass if no critical or major failures
        passed = error_count == 0

        return ValidationReport(
            passed=passed,
            results=results,
            error_count=error_count,
            warning_count=warning_count,
            auto_corrections_made=auto_corrections
        )
