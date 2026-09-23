"""
Deterministic scoring of a BillOfQuantities against a baseline.

A baseline JSON (see baselines/*.json) may declare any subset of:
    total_excl_vat_zar, total_incl_vat_zar   scalar totals
    section_totals_zar                        {label: zar}  (informational)
    building_totals_zar                       {building: zar}
    fixture_counts                            {fixture_key: count}
    feeder_lengths_m                          {label: metres}   (informational)

Every present field becomes one or more MetricScore rows. Accuracy for a
metric is max(0, 1 − |predicted − actual| / |actual|). The overall score is
the mean of the metric accuracies. Missing baseline fields are simply not
scored (and noted), never penalised.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Optional

from pydantic import BaseModel, Field

from agent.shared import BillOfQuantities


# ─── Result models ───────────────────────────────────────────────────

class MetricScore(BaseModel):
    name: str
    group: str                    # "total" | "building" | "fixture" | "section"
    predicted: float
    actual: float
    abs_pct_error: float
    accuracy: float

    @property
    def pretty(self) -> str:
        return (
            f"{self.name:<40} pred={self.predicted:>14,.2f}  "
            f"actual={self.actual:>14,.2f}  acc={self.accuracy:6.1%}"
        )


class ScoreReport(BaseModel):
    project_name: str = ""
    baseline_name: str = ""
    metrics: List[MetricScore] = Field(default_factory=list)
    overall_accuracy: float = 0.0
    mean_abs_pct_error: float = 0.0
    notes: List[str] = Field(default_factory=list)

    def group_accuracy(self, group: str) -> Optional[float]:
        rows = [m.accuracy for m in self.metrics if m.group == group]
        return sum(rows) / len(rows) if rows else None

    def render(self) -> str:
        lines = [f"Score report — {self.project_name or self.baseline_name}", "=" * 72]
        for m in self.metrics:
            lines.append(m.pretty)
        lines.append("-" * 72)
        lines.append(f"Overall accuracy: {self.overall_accuracy:.1%}   "
                     f"(MAPE {self.mean_abs_pct_error:.1%}, {len(self.metrics)} metrics)")
        for n in self.notes:
            lines.append(f"note: {n}")
        return "\n".join(lines)


# ─── Fixture description keywords (BOQ line → fixture key) ────────────

_FIXTURE_KEYWORDS: Dict[str, List[str]] = {
    "downlights": ["downlight"],
    "panel_lights": ["recessed", "panel"],
    "bulkheads": ["bulkhead"],
    "vapour_proof": ["vapour", "vapor"],
    "floodlights": ["flood"],
    "emergency_lights": ["emergency light"],
    "pole_lights": ["pole light"],
    "double_sockets": ["double switched socket", "double socket"],
    "single_sockets": ["single switched socket", "single socket"],
    "waterproof_sockets": ["waterproof socket"],
    "data_outlets": ["data outlet", "cat6", "data socket"],
    "switches_1lever": ["1-lever", "1 lever"],
    "switches_2lever": ["2-lever", "2 lever"],
    "switches_3lever": ["3-lever", "3 lever"],
    "isolators": ["isolator"],
    "day_night_switches": ["day/night", "day night"],
}


# ─── Scoring primitives ──────────────────────────────────────────────

def _ape(predicted: float, actual: float) -> float:
    """Absolute percentage error, safe for zero actuals."""
    if actual == 0:
        return 0.0 if predicted == 0 else 1.0
    return abs(predicted - actual) / abs(actual)


def _metric(name: str, group: str, predicted: float, actual: float) -> MetricScore:
    ape = _ape(predicted, actual)
    return MetricScore(
        name=name, group=group, predicted=round(predicted, 2), actual=round(actual, 2),
        abs_pct_error=round(ape, 4), accuracy=round(max(0.0, 1.0 - ape), 4),
    )


def _predicted_fixture_count(boq: BillOfQuantities, fixture_key: str) -> float:
    kws = _FIXTURE_KEYWORDS.get(fixture_key, [])
    if not kws:
        return 0.0
    total = 0.0
    for it in boq.line_items:
        d = it.description.lower()
        # count each fitting line once (avoid double counting Supply+Install of cables — fittings are combined)
        if any(kw in d for kw in kws):
            total += it.qty
    return total


def _predicted_building_total(boq: BillOfQuantities, building: str) -> float:
    key = building.lower()
    return round(sum(
        it.total_zar for it in boq.line_items
        if key in (it.building_block or "").lower() or (it.building_block or "").lower() in key
    ), 2)


# ─── Public entry ────────────────────────────────────────────────────

def score_boq(boq: BillOfQuantities, baseline: Dict) -> ScoreReport:
    """Score a produced BOQ against a baseline dict."""
    metrics: List[MetricScore] = []
    notes: List[str] = []

    if "total_excl_vat_zar" in baseline:
        metrics.append(_metric("Total excl VAT", "total",
                               boq.total_excl_vat_zar, baseline["total_excl_vat_zar"]))
    if "total_incl_vat_zar" in baseline:
        metrics.append(_metric("Total incl VAT", "total",
                               boq.total_incl_vat_zar, baseline["total_incl_vat_zar"]))

    for building, actual in (baseline.get("building_totals_zar") or {}).items():
        predicted = _predicted_building_total(boq, building)
        metrics.append(_metric(f"Building · {building}", "building", predicted, actual))
        if predicted == 0.0:
            notes.append(f"No BOQ lines matched building '{building}' — check building_block mapping.")

    for fixture_key, actual in (baseline.get("fixture_counts") or {}).items():
        predicted = _predicted_fixture_count(boq, fixture_key)
        metrics.append(_metric(f"Count · {fixture_key}", "fixture", predicted, float(actual)))

    if "section_totals_zar" in baseline:
        notes.append("section_totals_zar present but section mapping is A–H specific; "
                     "compare manually against boq.section_subtotals_zar.")
    if "feeder_lengths_m" in baseline:
        notes.append("feeder_lengths_m present; feeder-length scoring requires named "
                     "feeders in the BOQ and is informational for now.")

    overall = round(sum(m.accuracy for m in metrics) / len(metrics), 4) if metrics else 0.0
    mape = round(sum(m.abs_pct_error for m in metrics) / len(metrics), 4) if metrics else 0.0

    return ScoreReport(
        project_name=baseline.get("project_name", ""),
        metrics=metrics, overall_accuracy=overall, mean_abs_pct_error=mape, notes=notes,
    )


def load_baseline(name_or_path: str, baselines_dir: str = "baselines") -> Dict:
    """Load a baseline by name ('wedela') or explicit path."""
    p = Path(name_or_path)
    if not p.exists():
        p = Path(baselines_dir) / f"{name_or_path}.json"
    with p.open("r", encoding="utf-8") as f:
        return json.load(f)
