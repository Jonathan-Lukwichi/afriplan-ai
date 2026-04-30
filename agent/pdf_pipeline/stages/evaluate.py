"""
Stage P4 — Evaluate.

LLM-aware evaluation: confidence aggregation, cross-page consistency,
baseline regression, SANS compliance flags, composite gate.

This stage makes ZERO API calls — it operates only on the extraction
already in memory.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Optional

from agent.pdf_pipeline.models import (
    CrossPageDisagreement,
    PdfEvaluation,
    PdfExtraction,
)
from agent.shared import ComplianceFlag, Severity
from core.config import BASELINES_DIR, PDF_THRESHOLDS


def evaluate(
    extraction: PdfExtraction,
    *,
    baseline_project: Optional[str] = None,
) -> PdfEvaluation:
    confidences = list(extraction.per_field_confidence.values())
    mean_conf = sum(confidences) / len(confidences) if confidences else 0.0
    min_conf = min(confidences) if confidences else 0.0
    low_fields = [
        k for k, v in extraction.per_field_confidence.items()
        if v < PDF_THRESHOLDS.min_field_confidence
    ]

    agreements, disagreements = _cross_page_consistency(extraction)
    total_compared = agreements + len(disagreements)
    consistency_score = agreements / total_compared if total_compared > 0 else 1.0

    mape = _baseline_mape(extraction, baseline_project)
    sans_violations, sans_warnings = _sans_checks(extraction)

    # Composite score: equal weight on confidence and consistency,
    # with baseline regression as a third equal weight if available.
    components = [mean_conf, consistency_score]
    if mape is not None:
        components.append(max(0.0, 1.0 - mape))
    overall_score = sum(components) / len(components) if components else 0.0

    failure_reasons: list[str] = []
    passed = True

    if mean_conf < PDF_THRESHOLDS.min_mean_confidence:
        failure_reasons.append(
            f"mean_confidence {mean_conf:.2f} < {PDF_THRESHOLDS.min_mean_confidence:.2f}"
        )
        passed = False

    if consistency_score < PDF_THRESHOLDS.min_consistency_score:
        failure_reasons.append(
            f"consistency_score {consistency_score:.2f} < {PDF_THRESHOLDS.min_consistency_score:.2f}"
        )
        passed = False

    if mape is not None and mape > PDF_THRESHOLDS.max_baseline_mape:
        failure_reasons.append(
            f"baseline_mape {mape:.2f} > {PDF_THRESHOLDS.max_baseline_mape:.2f}"
        )
        passed = False

    if overall_score < PDF_THRESHOLDS.min_overall_score:
        failure_reasons.append(
            f"overall_score {overall_score:.2f} < {PDF_THRESHOLDS.min_overall_score:.2f}"
        )
        passed = False

    if any(f.severity == Severity.CRITICAL for f in sans_violations):
        failure_reasons.append("Critical SANS violation present")
        passed = False

    return PdfEvaluation(
        mean_confidence=mean_conf,
        min_confidence=min_conf,
        low_confidence_fields=low_fields,
        cross_page_agreements=agreements,
        cross_page_disagreements=disagreements,
        consistency_score=consistency_score,
        baseline_project=baseline_project,
        baseline_mape=mape,
        sans_violations=sans_violations,
        sans_warnings=sans_warnings,
        passed=passed,
        overall_score=overall_score,
        failure_reasons=failure_reasons,
    )


# ─── helpers ──────────────────────────────────────────────────────────

def _cross_page_consistency(
    extraction: PdfExtraction,
) -> tuple[int, list[CrossPageDisagreement]]:
    """
    Compare same-named DBs across SLD and Schedule pages. If a DB called
    DB-PFA appears on both pages, both should report the same circuit
    count and main breaker rating.
    """
    by_name: Dict[str, list] = {}
    for db in extraction.distribution_boards:
        if db.name:
            by_name.setdefault(db.name, []).append(db)

    agreements = 0
    disagreements: list[CrossPageDisagreement] = []

    for name, dbs in by_name.items():
        if len(dbs) < 2:
            continue
        first = dbs[0]
        for other in dbs[1:]:
            if first.main_breaker_a == other.main_breaker_a:
                agreements += 1
            else:
                disagreements.append(
                    CrossPageDisagreement(
                        value_kind=f"{name} main_breaker_a",
                        page_a=first.page_source,
                        value_a=first.main_breaker_a,
                        page_b=other.page_source,
                        value_b=other.main_breaker_a,
                        severity="warning",
                    )
                )
            if len(first.circuits) == len(other.circuits):
                agreements += 1
            else:
                disagreements.append(
                    CrossPageDisagreement(
                        value_kind=f"{name} circuit_count",
                        page_a=first.page_source,
                        value_a=len(first.circuits),
                        page_b=other.page_source,
                        value_b=len(other.circuits),
                        severity="warning",
                    )
                )

    return agreements, disagreements


def _baseline_mape(
    extraction: PdfExtraction,
    baseline_project: Optional[str],
) -> Optional[float]:
    if not baseline_project:
        return None
    path = Path(BASELINES_DIR) / f"{baseline_project}.json"
    if not path.exists():
        return None
    with path.open("r", encoding="utf-8") as f:
        baseline = json.load(f)

    expected = baseline.get("pdf_fixture_counts") or {}
    if not expected:
        return None

    actual = _aggregate_fixture_counts(extraction)
    errors: list[float] = []
    for k, v in expected.items():
        if v == 0:
            continue
        errors.append(abs(actual.get(k, 0) - v) / v)
    return sum(errors) / len(errors) if errors else None


def _aggregate_fixture_counts(ext: PdfExtraction) -> Dict[str, int]:
    """Total fixtures of each type across all rooms."""
    keys = (
        "downlights",
        "panel_lights",
        "bulkheads",
        "floodlights",
        "emergency_lights",
        "exit_signs",
        "pool_flood_light",
        "pool_underwater_light",
        "double_sockets",
        "single_sockets",
        "waterproof_sockets",
        "floor_sockets",
        "data_outlets",
        "switches_1lever",
        "switches_2lever",
        "switches_3lever",
        "isolators",
        "day_night_switches",
    )
    out = {k: 0 for k in keys}
    for room in ext.fixtures_per_room.values():
        for k in keys:
            out[k] += getattr(room, k, 0) or 0
    return out


def _sans_checks(
    extraction: PdfExtraction,
) -> tuple[list[ComplianceFlag], list[ComplianceFlag]]:
    """
    Apply the SANS 10142-1:2017 hard rules over the extracted DBs.
    Critical → blocks the gate; Warning → flagged but doesn't block.
    """
    violations: list[ComplianceFlag] = []
    warnings: list[ComplianceFlag] = []

    for db in extraction.distribution_boards:
        # Max 10 points per circuit
        for c in db.circuits:
            if c.is_spare:
                continue
            if c.num_points > 10:
                violations.append(
                    ComplianceFlag(
                        rule_code="SANS-10142-1:2017-7.12.2.1",
                        rule_title="Maximum 10 final-circuit points",
                        severity=Severity.CRITICAL,
                        message=f"Circuit {c.circuit_id} has {c.num_points} points (max 10)",
                        location=f"{db.name} / {c.circuit_id}",
                        suggested_fix=f"Split {c.circuit_id} into two final circuits",
                    )
                )

        if not db.elcb_present:
            warnings.append(
                ComplianceFlag(
                    rule_code="SANS-10142-1:2017-6.7",
                    rule_title="Earth-leakage protection",
                    severity=Severity.WARNING,
                    message=f"DB {db.name} has no ELCB recorded",
                    location=db.name,
                    suggested_fix="Verify 30 mA RCD on all sockets and lighting circuits",
                )
            )

        # Min 15% spare ways heuristic
        total = len(db.circuits)
        if total > 0:
            spares = sum(1 for c in db.circuits if c.is_spare)
            if spares / total < 0.15:
                warnings.append(
                    ComplianceFlag(
                        rule_code="AFP-SPARE-WAYS",
                        rule_title="Minimum 15% spare DB ways",
                        severity=Severity.INFO,
                        message=f"DB {db.name} has {spares}/{total} spares (<15%)",
                        location=db.name,
                        suggested_fix="Upsize DB to leave 15% spare ways for future expansion",
                    )
                )

    return violations, warnings
