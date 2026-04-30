"""
Stage D4 — Evaluate.

Deterministic-pipeline gate. Computes coverage, runs baseline regression
if a ground-truth file exists, raises anomaly flags. No LLM — same
extraction always produces the same evaluation.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from agent.dxf_pipeline.models import DxfEvaluation, DxfExtraction, DxfLayerAnalysis
from agent.shared import ComplianceFlag, Severity
from core.config import DXF_THRESHOLDS, BASELINES_DIR


def _coverage_score(extraction: DxfExtraction) -> float:
    total = len(extraction.blocks)
    if total == 0:
        return 0.0
    recognised = sum(1 for b in extraction.blocks if b.recognised)
    return recognised / total


def _baseline_mape(
    extraction: DxfExtraction,
    baseline_project: Optional[str],
) -> Optional[float]:
    """
    Compare extracted block counts against baseline ground truth.

    Returns mean absolute percentage error across categories that exist
    in the baseline. Returns None if no baseline file is found.
    """
    if not baseline_project:
        return None

    path = Path(BASELINES_DIR) / f"{baseline_project}.json"
    if not path.exists():
        return None

    with path.open("r", encoding="utf-8") as f:
        baseline = json.load(f)

    expected = baseline.get("dxf_block_counts_by_type") or baseline.get("block_counts_by_type")
    if not expected:
        return None

    errors: list[float] = []
    for canonical, expected_qty in expected.items():
        actual = extraction.block_counts_by_type.get(canonical, 0)
        if expected_qty == 0:
            continue
        err = abs(actual - expected_qty) / expected_qty
        errors.append(err)

    if not errors:
        return None
    return sum(errors) / len(errors)


def evaluate(
    extraction: DxfExtraction,
    layer_analysis: DxfLayerAnalysis,
    baseline_project: Optional[str] = None,
) -> DxfEvaluation:
    """Run the deterministic evaluation gate."""

    total = len(extraction.blocks)
    recognised = sum(1 for b in extraction.blocks if b.recognised)
    coverage = recognised / total if total > 0 else 0.0

    # Anomalies
    orphan_circles = len(extraction.circles_layer_0)
    long_polylines = [
        round(p.length_m, 2)
        for p in extraction.polylines
        if p.length_m > DXF_THRESHOLDS.flag_polyline_longer_than_m
    ]

    # Baseline regression
    mape = _baseline_mape(extraction, baseline_project)

    # Compose compliance flags
    sans_warnings: list[ComplianceFlag] = []
    sans_violations: list[ComplianceFlag] = []

    if coverage < DXF_THRESHOLDS.min_coverage_score:
        sans_warnings.append(
            ComplianceFlag(
                rule_code="AFP-DXF-COVERAGE",
                rule_title="DXF block coverage below threshold",
                severity=Severity.WARNING,
                message=(
                    f"Recognised {recognised} of {total} blocks "
                    f"({coverage:.0%}); pattern dictionary may need extension."
                ),
                suggested_fix="Extend ELECTRICAL_BLOCK_PATTERNS in agent/dxf_pipeline/patterns.py",
            )
        )

    if orphan_circles > 0 and DXF_THRESHOLDS.flag_orphan_layer_0_circles:
        sans_warnings.append(
            ComplianceFlag(
                rule_code="AFP-DXF-LAYER0-CIRCLES",
                rule_title="Circles on layer 0 may be unblocked light fittings",
                severity=Severity.INFO,
                message=f"Found {orphan_circles} CIRCLE entities on layer 0",
                suggested_fix="Verify these are intended geometry, not mis-blocked lights.",
            )
        )

    for length_m in long_polylines:
        sans_warnings.append(
            ComplianceFlag(
                rule_code="AFP-DXF-LONG-CABLE",
                rule_title="Suspiciously long cable run",
                severity=Severity.INFO,
                message=f"Polyline of {length_m} m exceeds {DXF_THRESHOLDS.flag_polyline_longer_than_m} m threshold",
                suggested_fix="Confirm this is a single cable run, not stitched architecture.",
            )
        )

    # Composite score: coverage is the primary deterministic signal
    score_components: list[float] = [coverage]
    if mape is not None:
        score_components.append(max(0.0, 1.0 - mape))   # 1.0 - MAPE → higher is better
    overall = sum(score_components) / len(score_components)

    failure_reasons: list[str] = []
    passed = True
    if coverage < DXF_THRESHOLDS.min_coverage_score:
        failure_reasons.append(f"coverage_score {coverage:.2f} < {DXF_THRESHOLDS.min_coverage_score:.2f}")
        passed = False
    if mape is not None and mape > DXF_THRESHOLDS.max_baseline_mape:
        failure_reasons.append(f"baseline_mape {mape:.2f} > {DXF_THRESHOLDS.max_baseline_mape:.2f}")
        passed = False
    if overall < DXF_THRESHOLDS.min_overall_score:
        failure_reasons.append(f"overall_score {overall:.2f} < {DXF_THRESHOLDS.min_overall_score:.2f}")
        passed = False

    return DxfEvaluation(
        total_blocks=total,
        recognised_blocks=recognised,
        coverage_score=coverage,
        baseline_project=baseline_project,
        baseline_mape=mape,
        sans_violations=sans_violations,
        sans_warnings=sans_warnings,
        orphan_layer_0_circles=orphan_circles,
        layers_named_electrical_with_no_blocks=layer_analysis.layers_named_electrical_with_no_blocks,
        suspiciously_long_polylines_m=long_polylines,
        passed=passed,
        overall_score=overall,
        failure_reasons=failure_reasons,
    )
