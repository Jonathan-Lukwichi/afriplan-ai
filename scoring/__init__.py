"""
Estimator scoring harness.

Scores a produced BillOfQuantities against a hand-validated baseline (the
priced reference bill) and reports accuracy per metric — totals, section /
building sub-totals, fixture counts, feeder lengths. Pure and deterministic:
no LLM, no network. The baseline is ground truth; the pipeline is the
approximation being measured.
"""

from scoring.harness import (
    MetricScore,
    ScoreReport,
    load_baseline,
    score_boq,
)

__all__ = ["MetricScore", "ScoreReport", "load_baseline", "score_boq"]
