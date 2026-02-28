"""
AfriPlan AI - Benchmark Validation System
==========================================
Compares AI extraction results against ground truth data.
Calculates accuracy metrics for continuous improvement.
"""

import json
from typing import Dict, List, Any, Tuple
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class ValidationResult:
    """Result of validating a single field."""
    field_name: str
    expected: Any
    actual: Any
    match: bool
    tolerance_used: bool = False
    score: float = 0.0
    notes: str = ""


@dataclass
class CategoryScore:
    """Accuracy score for a category of extractions."""
    category: str
    total_fields: int
    matched_fields: int
    accuracy_pct: float
    details: List[ValidationResult] = field(default_factory=list)


@dataclass
class BenchmarkReport:
    """Complete benchmark validation report."""
    project_id: str
    project_name: str
    overall_accuracy: float
    category_scores: Dict[str, CategoryScore] = field(default_factory=dict)
    critical_misses: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)


class BenchmarkValidator:
    """Validates AI extraction against ground truth benchmark."""

    def __init__(self, ground_truth_path: str = None):
        """Load ground truth data."""
        if ground_truth_path is None:
            ground_truth_path = Path(__file__).parent / "ground_truth.json"

        with open(ground_truth_path, 'r', encoding='utf-8') as f:
            self.ground_truth = json.load(f)

        self.projects = {p['id']: p for p in self.ground_truth['projects']}

    def get_project_ids(self) -> List[str]:
        """Return list of available project IDs."""
        return list(self.projects.keys())

    def get_project_by_name(self, name_contains: str) -> Dict:
        """Find project by partial name match."""
        name_lower = name_contains.lower()
        for pid, proj in self.projects.items():
            if name_lower in proj['name'].lower():
                return proj
        return None

    def validate_extraction(self,
                           project_id: str,
                           extracted_data: Dict) -> BenchmarkReport:
        """
        Validate extracted data against ground truth.

        Args:
            project_id: ID of the project to validate against
            extracted_data: Data extracted by AI pipeline

        Returns:
            BenchmarkReport with accuracy scores
        """
        if project_id not in self.projects:
            raise ValueError(f"Unknown project ID: {project_id}")

        gt = self.projects[project_id]
        report = BenchmarkReport(
            project_id=project_id,
            project_name=gt['name'],
            overall_accuracy=0.0
        )

        # Validate each category
        report.category_scores['supply_point'] = self._validate_supply_point(
            gt.get('supply_point', {}),
            extracted_data.get('supply_point', {})
        )

        report.category_scores['distribution_boards'] = self._validate_distribution_boards(
            gt.get('distribution_boards', []),
            extracted_data.get('distribution_boards', [])
        )

        report.category_scores['cable_routes'] = self._validate_cable_routes(
            gt.get('cable_routes', []),
            extracted_data.get('cable_routes', [])
        )

        report.category_scores['circuits'] = self._validate_circuits(
            gt.get('distribution_boards', []),
            extracted_data.get('distribution_boards', [])
        )

        report.category_scores['legend'] = self._validate_legend(
            gt.get('legend', {}),
            extracted_data.get('legend', {})
        )

        report.category_scores['totals'] = self._validate_totals(
            gt.get('totals', {}),
            extracted_data.get('totals', {})
        )

        # Calculate overall accuracy
        total_matched = sum(cs.matched_fields for cs in report.category_scores.values())
        total_fields = sum(cs.total_fields for cs in report.category_scores.values())

        if total_fields > 0:
            report.overall_accuracy = round(total_matched / total_fields * 100, 1)

        # Identify critical misses
        report.critical_misses = self._identify_critical_misses(report)

        # Generate recommendations
        report.recommendations = self._generate_recommendations(report)

        return report

    def _validate_supply_point(self, gt: Dict, extracted: Dict) -> CategoryScore:
        """Validate supply point extraction."""
        results = []

        # Key fields to check
        fields = [
            ('name', str),
            ('voltage_v', int),
            ('main_breaker_a', int),
            ('phases', str),
            ('feeds_to', str),
        ]

        for field_name, field_type in fields:
            expected = gt.get(field_name)
            actual = extracted.get(field_name)

            if expected is None:
                continue

            match = self._compare_values(expected, actual, field_type)
            results.append(ValidationResult(
                field_name=f"supply_point.{field_name}",
                expected=expected,
                actual=actual,
                match=match,
                score=1.0 if match else 0.0
            ))

        # Check cable spec
        gt_cable = gt.get('cable_spec') or gt.get('incoming_cable', {}).get('spec')
        ex_cable = extracted.get('cable_spec') or extracted.get('incoming_cable', {}).get('spec')
        if gt_cable:
            match = self._compare_cable_specs(gt_cable, ex_cable)
            results.append(ValidationResult(
                field_name="supply_point.cable_spec",
                expected=gt_cable,
                actual=ex_cable,
                match=match,
                score=1.0 if match else 0.0
            ))

        matched = sum(1 for r in results if r.match)
        return CategoryScore(
            category="supply_point",
            total_fields=len(results),
            matched_fields=matched,
            accuracy_pct=round(matched / len(results) * 100, 1) if results else 0,
            details=results
        )

    def _validate_distribution_boards(self, gt_dbs: List, extracted_dbs: List) -> CategoryScore:
        """Validate distribution board detection."""
        results = []

        # Get DB names from ground truth
        gt_names = {db['name'].upper().replace(' ', '').replace('-', '') for db in gt_dbs}

        # Get DB names from extraction
        ex_names = set()
        for db in extracted_dbs:
            name = db.get('name', '').upper().replace(' ', '').replace('-', '')
            ex_names.add(name)

        # Check each GT DB was found
        for gt_db in gt_dbs:
            gt_name = gt_db['name']
            normalized = gt_name.upper().replace(' ', '').replace('-', '')

            found = normalized in ex_names
            results.append(ValidationResult(
                field_name=f"db_detection.{gt_name}",
                expected=gt_name,
                actual="FOUND" if found else "MISSING",
                match=found,
                score=1.0 if found else 0.0,
                notes=f"Main={gt_db.get('is_main', False)}, Fed from={gt_db.get('fed_from', 'N/A')}"
            ))

        # Check for extra DBs detected (false positives)
        for ex_db in extracted_dbs:
            ex_name = ex_db.get('name', '')
            normalized = ex_name.upper().replace(' ', '').replace('-', '')

            if normalized not in gt_names:
                results.append(ValidationResult(
                    field_name=f"db_detection.{ex_name}",
                    expected="NOT IN GT",
                    actual=ex_name,
                    match=False,  # Could be a valid detection not in GT
                    score=0.5,  # Partial score for finding something
                    notes="Extra DB detected - verify if valid"
                ))

        matched = sum(1 for r in results if r.match)
        return CategoryScore(
            category="distribution_boards",
            total_fields=len([r for r in results if r.expected != "NOT IN GT"]),
            matched_fields=matched,
            accuracy_pct=round(matched / len(gt_dbs) * 100, 1) if gt_dbs else 0,
            details=results
        )

    def _validate_cable_routes(self, gt_routes: List, extracted_routes: List) -> CategoryScore:
        """Validate cable route extraction."""
        results = []

        if not gt_routes:
            return CategoryScore(
                category="cable_routes",
                total_fields=0,
                matched_fields=0,
                accuracy_pct=100.0,
                details=[]
            )

        for gt_route in gt_routes:
            from_db = gt_route.get('from', '').upper()
            to_db = gt_route.get('to', '').upper()
            gt_cable = gt_route.get('cable_spec', '')

            # Look for matching route in extraction
            found = False
            matched_cable = False

            for ex_route in extracted_routes:
                ex_from = ex_route.get('from', '').upper()
                ex_to = ex_route.get('to', '').upper()

                if self._compare_db_names(from_db, ex_from) and self._compare_db_names(to_db, ex_to):
                    found = True
                    ex_cable = ex_route.get('cable_spec', '')
                    matched_cable = self._compare_cable_specs(gt_cable, ex_cable)
                    break

            results.append(ValidationResult(
                field_name=f"cable_route.{gt_route.get('from')}_to_{gt_route.get('to')}",
                expected=f"{gt_cable}",
                actual="FOUND" if found else "MISSING",
                match=found and matched_cable,
                score=1.0 if (found and matched_cable) else (0.5 if found else 0.0),
                notes=f"Route found: {found}, Cable matched: {matched_cable}"
            ))

        matched = sum(1 for r in results if r.match)
        return CategoryScore(
            category="cable_routes",
            total_fields=len(results),
            matched_fields=matched,
            accuracy_pct=round(matched / len(results) * 100, 1) if results else 0,
            details=results
        )

    def _validate_circuits(self, gt_dbs: List, extracted_dbs: List) -> CategoryScore:
        """Validate circuit schedule extraction for each DB."""
        results = []

        for gt_db in gt_dbs:
            db_name = gt_db['name']
            gt_circuits = gt_db.get('circuits', {})

            # Find matching extracted DB
            ex_db = None
            for edb in extracted_dbs:
                if self._compare_db_names(db_name, edb.get('name', '')):
                    ex_db = edb
                    break

            if ex_db is None:
                # DB not found, all circuits missing
                for circuit_type in ['lighting', 'power', 'isolators', 'dedicated']:
                    gt_list = gt_circuits.get(circuit_type, [])
                    for circuit in gt_list:
                        ref = circuit.get('ref', 'unknown')
                        results.append(ValidationResult(
                            field_name=f"{db_name}.{circuit_type}.{ref}",
                            expected=str(circuit),
                            actual="DB NOT FOUND",
                            match=False,
                            score=0.0
                        ))
                continue

            ex_circuits = ex_db.get('circuits', {})

            # Compare lighting circuits
            gt_lighting = gt_circuits.get('lighting', [])
            ex_lighting = ex_circuits.get('lighting', [])

            for gt_circuit in gt_lighting:
                ref = gt_circuit.get('ref', '')
                gt_points = gt_circuit.get('points', 0)

                # Find matching extracted circuit
                ex_circuit = None
                for ec in ex_lighting:
                    if ec.get('ref', '').upper() == ref.upper():
                        ex_circuit = ec
                        break

                if ex_circuit:
                    ex_points = ex_circuit.get('points', 0)
                    # Allow ±1 tolerance
                    match = abs(gt_points - ex_points) <= 1
                    results.append(ValidationResult(
                        field_name=f"{db_name}.lighting.{ref}.points",
                        expected=gt_points,
                        actual=ex_points,
                        match=match,
                        tolerance_used=(gt_points != ex_points and match),
                        score=1.0 if match else 0.0
                    ))
                else:
                    results.append(ValidationResult(
                        field_name=f"{db_name}.lighting.{ref}",
                        expected=f"{ref}: {gt_points} points",
                        actual="CIRCUIT NOT FOUND",
                        match=False,
                        score=0.0
                    ))

            # Compare power circuits
            gt_power = gt_circuits.get('power', [])
            ex_power = ex_circuits.get('power', [])

            for gt_circuit in gt_power:
                ref = gt_circuit.get('ref', '')
                gt_points = gt_circuit.get('points', 0)

                ex_circuit = None
                for ec in ex_power:
                    if ec.get('ref', '').upper() == ref.upper():
                        ex_circuit = ec
                        break

                if ex_circuit:
                    ex_points = ex_circuit.get('points', 0)
                    match = abs(gt_points - ex_points) <= 1
                    results.append(ValidationResult(
                        field_name=f"{db_name}.power.{ref}.points",
                        expected=gt_points,
                        actual=ex_points,
                        match=match,
                        tolerance_used=(gt_points != ex_points and match),
                        score=1.0 if match else 0.0
                    ))
                else:
                    results.append(ValidationResult(
                        field_name=f"{db_name}.power.{ref}",
                        expected=f"{ref}: {gt_points} points",
                        actual="CIRCUIT NOT FOUND",
                        match=False,
                        score=0.0
                    ))

        matched = sum(1 for r in results if r.match)
        return CategoryScore(
            category="circuits",
            total_fields=len(results),
            matched_fields=matched,
            accuracy_pct=round(matched / len(results) * 100, 1) if results else 0,
            details=results
        )

    def _validate_legend(self, gt_legend: Dict, extracted_legend: Dict) -> CategoryScore:
        """Validate legend extraction."""
        results = []

        # Check lighting types
        gt_lights = gt_legend.get('lighting', [])
        ex_lights = extracted_legend.get('light_types', []) or extracted_legend.get('lighting', [])

        gt_light_names = {lt.get('name', '').lower() for lt in gt_lights}
        ex_light_names = {lt.get('name', '').lower() for lt in ex_lights}

        for gt_light in gt_lights:
            name = gt_light.get('name', '')
            found = name.lower() in ex_light_names
            results.append(ValidationResult(
                field_name=f"legend.lighting.{name}",
                expected=f"{name} ({gt_light.get('wattage_w', '?')}W)",
                actual="FOUND" if found else "MISSING",
                match=found,
                score=1.0 if found else 0.0
            ))

        # Check socket types
        gt_sockets = gt_legend.get('sockets', [])
        ex_sockets = extracted_legend.get('socket_types', []) or extracted_legend.get('sockets', [])

        gt_socket_names = {st.get('name', '').lower() for st in gt_sockets}
        ex_socket_names = {st.get('name', '').lower() for st in ex_sockets}

        for gt_socket in gt_sockets:
            name = gt_socket.get('name', '')
            found = name.lower() in ex_socket_names
            results.append(ValidationResult(
                field_name=f"legend.sockets.{name}",
                expected=name,
                actual="FOUND" if found else "MISSING",
                match=found,
                score=1.0 if found else 0.0
            ))

        matched = sum(1 for r in results if r.match)
        return CategoryScore(
            category="legend",
            total_fields=len(results),
            matched_fields=matched,
            accuracy_pct=round(matched / len(results) * 100, 1) if results else 100,
            details=results
        )

    def _validate_totals(self, gt_totals: Dict, extracted_totals: Dict) -> CategoryScore:
        """Validate total counts."""
        results = []

        fields = [
            ('distribution_boards', 0),
            ('lighting_circuits', 2),
            ('power_circuits', 2),
            ('isolators', 3),
            ('dedicated_circuits', 1),
            ('total_lighting_points', 10),
            ('total_power_points', 5),
        ]

        for field_name, tolerance in fields:
            expected = gt_totals.get(field_name)
            actual = extracted_totals.get(field_name)

            if expected is None:
                continue

            if actual is None:
                match = False
            else:
                match = abs(expected - actual) <= tolerance

            results.append(ValidationResult(
                field_name=f"totals.{field_name}",
                expected=expected,
                actual=actual,
                match=match,
                tolerance_used=(match and expected != actual),
                score=1.0 if match else 0.0,
                notes=f"Tolerance: ±{tolerance}"
            ))

        matched = sum(1 for r in results if r.match)
        return CategoryScore(
            category="totals",
            total_fields=len(results),
            matched_fields=matched,
            accuracy_pct=round(matched / len(results) * 100, 1) if results else 0,
            details=results
        )

    def _compare_values(self, expected: Any, actual: Any, value_type: type) -> bool:
        """Compare two values with type-aware comparison."""
        if expected is None or actual is None:
            return expected == actual

        if value_type == str:
            return str(expected).upper().replace(' ', '') == str(actual).upper().replace(' ', '')
        elif value_type == int:
            try:
                return abs(int(expected) - int(actual)) <= 1
            except (ValueError, TypeError):
                return False
        else:
            return expected == actual

    def _compare_db_names(self, name1: str, name2: str) -> bool:
        """Compare DB names with normalization."""
        n1 = name1.upper().replace(' ', '').replace('-', '').replace('_', '')
        n2 = name2.upper().replace(' ', '').replace('-', '').replace('_', '')
        return n1 == n2 or n1 in n2 or n2 in n1

    def _compare_cable_specs(self, spec1: str, spec2: str) -> bool:
        """Compare cable specifications with normalization."""
        if not spec1 or not spec2:
            return False

        # Normalize: remove spaces, uppercase, extract key parts
        s1 = spec1.upper().replace(' ', '').replace('²', '2').replace('X', 'X')
        s2 = spec2.upper().replace(' ', '').replace('²', '2').replace('X', 'X')

        # Extract size (e.g., "95MM" from "95MM²X4C...")
        import re
        size1 = re.search(r'(\d+)MM', s1)
        size2 = re.search(r'(\d+)MM', s2)

        if size1 and size2:
            return size1.group(1) == size2.group(1)

        return s1 == s2 or s1 in s2 or s2 in s1

    def _identify_critical_misses(self, report: BenchmarkReport) -> List[str]:
        """Identify critical extraction failures."""
        critical = []

        # Missing DBs is critical
        db_score = report.category_scores.get('distribution_boards')
        if db_score and db_score.accuracy_pct < 80:
            missing = [r.expected for r in db_score.details if not r.match and r.expected != "NOT IN GT"]
            if missing:
                critical.append(f"Missing DBs: {', '.join(missing[:5])}")

        # Missing supply point is critical
        supply_score = report.category_scores.get('supply_point')
        if supply_score and supply_score.accuracy_pct < 50:
            critical.append("Supply point not properly detected")

        # Missing cable routes affects BOQ
        cable_score = report.category_scores.get('cable_routes')
        if cable_score and cable_score.accuracy_pct < 50:
            critical.append("Cable routes poorly extracted - affects BOQ accuracy")

        return critical

    def _generate_recommendations(self, report: BenchmarkReport) -> List[str]:
        """Generate improvement recommendations based on results."""
        recs = []

        for category, score in report.category_scores.items():
            if score.accuracy_pct < 70:
                recs.append(f"Improve {category} extraction (currently {score.accuracy_pct}%)")

        if report.overall_accuracy < 75:
            recs.append("Consider using Opus model for low-confidence extractions")
            recs.append("Review and update extraction prompts for this project type")

        return recs

    def generate_report_text(self, report: BenchmarkReport) -> str:
        """Generate human-readable report."""
        lines = [
            "=" * 60,
            f"BENCHMARK VALIDATION REPORT",
            "=" * 60,
            f"Project: {report.project_name}",
            f"Project ID: {report.project_id}",
            f"Overall Accuracy: {report.overall_accuracy}%",
            "",
            "CATEGORY SCORES:",
            "-" * 40,
        ]

        for category, score in report.category_scores.items():
            status = "✓" if score.accuracy_pct >= 80 else "△" if score.accuracy_pct >= 60 else "✗"
            lines.append(f"  {status} {category}: {score.accuracy_pct}% ({score.matched_fields}/{score.total_fields})")

        if report.critical_misses:
            lines.extend([
                "",
                "CRITICAL ISSUES:",
                "-" * 40,
            ])
            for miss in report.critical_misses:
                lines.append(f"  ⚠ {miss}")

        if report.recommendations:
            lines.extend([
                "",
                "RECOMMENDATIONS:",
                "-" * 40,
            ])
            for rec in report.recommendations:
                lines.append(f"  → {rec}")

        lines.append("=" * 60)

        return "\n".join(lines)


def run_benchmark_test():
    """Run a test of the benchmark validator."""
    validator = BenchmarkValidator()

    print("Available projects:", validator.get_project_ids())

    # Simulate an extraction result
    test_extraction = {
        "supply_point": {
            "name": "Kiosk Metering",
            "voltage_v": 400,
            "main_breaker_a": 250,
            "phases": "3PH+N+E",
            "feeds_to": "DB-CR",
            "cable_spec": "95mm²x4C PVC SWA PVC"
        },
        "distribution_boards": [
            {"name": "DB-CR", "is_main": True, "fed_from": "Kiosk"},
            {"name": "DB-PFA", "is_main": False, "fed_from": "DB-CR"},
            {"name": "DB-1", "is_main": False, "fed_from": "DB-CR"},
            {"name": "DB-AB1", "is_main": False, "fed_from": "DB-CR"},
            # Missing: DB-ST, DB-AB2, DB-LGH, DB-SGH
        ],
        "cable_routes": [
            {"from": "Kiosk", "to": "DB-CR", "cable_spec": "95mm² x 4C PVC SWA PVC"},
        ],
        "legend": {
            "lighting": [
                {"name": "600x1200 Recessed 3x18W LED", "wattage_w": 54},
                {"name": "6W LED Downlight", "wattage_w": 6},
            ]
        },
        "totals": {
            "distribution_boards": 4,
            "lighting_circuits": 30,
            "power_circuits": 10,
        }
    }

    report = validator.validate_extraction("WEDELA_001", test_extraction)
    print(validator.generate_report_text(report))


if __name__ == "__main__":
    run_benchmark_test()
