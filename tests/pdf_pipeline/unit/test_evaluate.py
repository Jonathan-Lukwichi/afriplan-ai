"""Tests for the evaluation stage (LLM-aware gate)."""

from agent.pdf_pipeline.models import (
    CircuitRow,
    DistributionBoard,
    FixtureCounts,
    PdfExtraction,
)
from agent.pdf_pipeline.stages.evaluate import evaluate
from agent.shared import Severity


def _ext_with_high_confidence() -> PdfExtraction:
    return PdfExtraction(
        per_field_confidence={
            "lighting:Lounge": 0.95,
            "lighting:Kitchen": 0.92,
            "plugs:Lounge": 0.88,
        },
        fixtures_per_room={
            "Lounge": FixtureCounts(room_name="Lounge", downlights=6, double_sockets=4),
        },
    )


def test_high_confidence_passes_gate():
    ext = _ext_with_high_confidence()
    ev = evaluate(ext)
    assert ev.passed is True
    assert ev.mean_confidence > 0.85
    assert ev.failure_reasons == []


def test_low_confidence_fails_gate():
    ext = PdfExtraction(per_field_confidence={"x": 0.2, "y": 0.3})
    ev = evaluate(ext)
    assert ev.passed is False
    assert any("mean_confidence" in r for r in ev.failure_reasons)
    assert "x" in ev.low_confidence_fields


def test_max_10_points_violation_blocks_gate():
    """Critical SANS violation must block the gate."""
    ext = PdfExtraction(
        per_field_confidence={"db:DB-MAIN": 0.95},
        distribution_boards=[
            DistributionBoard(
                name="DB-MAIN",
                main_breaker_a=63,
                phases=3,
                circuits=[
                    CircuitRow(circuit_id="L1", num_points=14),  # > 10 → critical
                ],
            )
        ],
    )
    ev = evaluate(ext)
    assert any(f.severity == Severity.CRITICAL for f in ev.sans_violations)
    assert ev.passed is False


def test_cross_page_disagreement_recorded():
    """Two DBs with the same name but different breaker → disagreement."""
    ext = PdfExtraction(
        per_field_confidence={"db:DB-PFA-sld": 0.9, "db:DB-PFA-sched": 0.9},
        distribution_boards=[
            DistributionBoard(name="DB-PFA", main_breaker_a=63, phases=3, page_source=1),
            DistributionBoard(name="DB-PFA", main_breaker_a=80, phases=3, page_source=4),
        ],
    )
    ev = evaluate(ext)
    assert len(ev.cross_page_disagreements) >= 1
    assert ev.cross_page_disagreements[0].value_kind.startswith("DB-PFA")
    assert ev.consistency_score < 1.0
