"""End-to-end pipeline tests using the MockAnthropic fixture."""

from agent.pdf_pipeline import run_pdf_pipeline
from agent.shared import BQSection


def test_pipeline_with_empty_extraction_fails_gate(synthetic_pdf_bytes, mock_llm):
    """Default mock returns empty results → confidence is 0 → gate fails."""
    llm = mock_llm()
    run = run_pdf_pipeline(
        synthetic_pdf_bytes,
        file_name="test.pdf",
        llm=llm,
    )
    assert run.success is False
    assert run.boq is None
    assert run.evaluation.passed is False
    assert run.evaluation.mean_confidence == 0.0


def test_pipeline_with_realistic_mock_passes(synthetic_pdf_bytes, mock_llm):
    """When mocks return high-confidence non-empty data, pipeline passes."""

    # Note: mock returns the same lighting layout for every page that's
    # classified as lighting_layout. 3 pages × the rooms below = 3× counts
    # in the BoQ. The point of this test is gate-pass + BoQ structure, not
    # exact totals — see test_pipeline_aggregates_across_pages for that.
    tool_responses = {
        "classify_page": {"page_type": "lighting_layout", "confidence": 0.9, "rationale": "rooms visible"},
        "extract_lighting_layout": {
            "rooms": [
                {
                    "room_name": "Lounge",
                    "room_type": "living",
                    "downlights": 6,
                    "panel_lights": 0,
                    "bulkheads": 0,
                    "floodlights": 0,
                    "emergency_lights": 0,
                    "exit_signs": 0,
                    "pool_flood_light": 0,
                    "pool_underwater_light": 0,
                    "confidence": 0.92,
                },
                {
                    "room_name": "Kitchen",
                    "room_type": "kitchen",
                    "downlights": 4,
                    "panel_lights": 0,
                    "bulkheads": 0,
                    "floodlights": 0,
                    "emergency_lights": 0,
                    "exit_signs": 0,
                    "pool_flood_light": 0,
                    "pool_underwater_light": 0,
                    "confidence": 0.88,
                },
            ],
            "legend": {"DL": "LED Downlight"},
            "extraction_warnings": [],
        },
    }
    llm = mock_llm(tool_responses=tool_responses)
    run = run_pdf_pipeline(synthetic_pdf_bytes, file_name="test.pdf", llm=llm)

    assert run.evaluation.passed is True
    assert run.boq is not None
    assert run.boq.pipeline == "pdf"

    # Lighting fixtures should appear in the BoQ. The test PDF has 3 pages,
    # each classified as lighting_layout with the same 2 rooms (6 + 4 = 10
    # downlights per page). Counts accumulate: 3 × 10 = 30.
    desc_to_qty = {it.description: it.qty for it in run.boq.line_items}
    assert desc_to_qty.get("LED Downlight") == 30.0


def test_pipeline_telemetry_aggregates(synthetic_pdf_bytes, mock_llm):
    """Stage costs are populated for every classify + extract call."""
    llm = mock_llm()
    run = run_pdf_pipeline(synthetic_pdf_bytes, file_name="test.pdf", llm=llm)
    # 3 pages → 3 classify calls. Extraction calls follow only when classified
    # to a known type; default mock returns 'unknown' so extract is skipped.
    assert len(run.stage_costs) >= 3
    assert all(c.input_tokens > 0 for c in run.stage_costs)


def test_pipeline_repeats_produce_same_extraction_with_same_mock(synthetic_pdf_bytes, mock_llm):
    """Determinism check: same mock responses → same extraction shape."""
    tool_responses = {
        "classify_page": {"page_type": "unknown", "confidence": 0.5, "rationale": "x"},
    }
    a = run_pdf_pipeline(synthetic_pdf_bytes, llm=mock_llm(tool_responses=tool_responses))
    b = run_pdf_pipeline(synthetic_pdf_bytes, llm=mock_llm(tool_responses=tool_responses))
    assert a.input_sha256 == b.input_sha256
    assert a.evaluation.mean_confidence == b.evaluation.mean_confidence
