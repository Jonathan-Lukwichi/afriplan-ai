"""
Deterministic extraction tests.

Per blueprint §4.3: same DXF in → same extraction out. We assert exact
equality on block counts, polyline lengths, and orphan-circle flags.
"""

from agent.dxf_pipeline import run_dxf_pipeline


def test_block_counts_exact_match(small_dxf_bytes):
    """Tiny synthetic DXF: counts must be exact."""
    result = run_dxf_pipeline(small_dxf_bytes, file_name="small.dxf")

    assert result.ingest.open_ok is True
    assert result.extraction.block_counts_by_type == {
        "LED Downlight": 4,
        "Double Socket": 3,
        "2-Lever Switch": 2,
        "Emergency Light": 1,
    }


def test_polyline_length_units_converted_to_metres(small_dxf_bytes):
    """Drawing units = mm; polyline 1000+1000 mm should become 2.0 m."""
    result = run_dxf_pipeline(small_dxf_bytes, file_name="small.dxf")
    assert result.ingest.units_to_metre_factor == 0.001
    assert abs(result.extraction.total_polyline_length_m - 2.0) < 1e-6


def test_polyline_length_in_metres_units(dxf_in_metres):
    """If drawing units are metres, no conversion is applied."""
    result = run_dxf_pipeline(dxf_in_metres, file_name="m.dxf")
    assert result.ingest.units_to_metre_factor == 1.0
    assert abs(result.extraction.total_polyline_length_m - 5.0) < 1e-6


def test_unrecognised_blocks_collected(dxf_with_unrecognised_blocks):
    """Walls and doors are skipped (not unrecognised); 'Some_Junk' is unrecognised."""
    result = run_dxf_pipeline(dxf_with_unrecognised_blocks, file_name="mixed.dxf")
    assert "Some_Junk" in result.extraction.raw_block_names_unrecognised
    assert "Wall_001" not in result.extraction.raw_block_names_unrecognised
    assert "Door_007" not in result.extraction.raw_block_names_unrecognised


def test_layer_0_circles_flagged(realistic_dxf_bytes):
    """Layer-0 circles should land in circles_layer_0 and produce an INFO warning."""
    result = run_dxf_pipeline(realistic_dxf_bytes, file_name="realistic.dxf")
    assert result.evaluation.orphan_layer_0_circles == 2
    codes = [w.rule_code for w in result.evaluation.sans_warnings]
    assert "AFP-DXF-LAYER0-CIRCLES" in codes


def test_repeat_runs_produce_identical_extraction(small_dxf_bytes):
    """Determinism: two runs on identical bytes give identical block counts."""
    a = run_dxf_pipeline(small_dxf_bytes, file_name="x.dxf")
    b = run_dxf_pipeline(small_dxf_bytes, file_name="x.dxf")
    assert a.extraction.block_counts_by_type == b.extraction.block_counts_by_type
    assert a.extraction.total_polyline_length_m == b.extraction.total_polyline_length_m


def test_cost_is_always_zero_on_dxf(realistic_dxf_bytes):
    """The DXF pipeline never pays for inference."""
    result = run_dxf_pipeline(realistic_dxf_bytes, file_name="r.dxf")
    assert result.cost_zar == 0.0


def test_runs_under_5_seconds(realistic_dxf_bytes):
    """Per blueprint §4.4 acceptance criterion 5."""
    result = run_dxf_pipeline(realistic_dxf_bytes, file_name="r.dxf")
    assert result.duration_s < 5.0
