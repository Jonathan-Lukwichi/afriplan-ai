"""Tests for BoQ generation from a DXF extraction."""

from agent.dxf_pipeline import run_dxf_pipeline
from agent.shared import BQSection, ItemConfidence


def test_boq_pipeline_field_is_dxf(small_dxf_bytes):
    result = run_dxf_pipeline(small_dxf_bytes, file_name="s.dxf")
    assert result.boq is not None
    assert result.boq.pipeline == "dxf"


def test_boq_line_items_have_correct_sections(realistic_dxf_bytes):
    result = run_dxf_pipeline(realistic_dxf_bytes, file_name="r.dxf")
    assert result.boq is not None

    by_desc = {it.description: it for it in result.boq.line_items}

    assert by_desc["LED Downlight"].section == BQSection.LIGHTING
    assert by_desc["LED Downlight"].qty == 24

    assert by_desc["Double Socket"].section == BQSection.POWER_OUTLETS
    assert by_desc["Double Socket"].qty == 20

    assert by_desc["Emergency Light"].section == BQSection.FIRE_SAFETY


def test_boq_total_excl_vat_includes_markup_and_contingency(small_dxf_bytes):
    result = run_dxf_pipeline(small_dxf_bytes, file_name="s.dxf")
    assert result.boq is not None
    boq = result.boq
    expected_excl = round(
        boq.subtotal_zar
        + boq.subtotal_zar * (boq.contingency_pct / 100)
        + boq.subtotal_zar * (boq.contractor_markup_pct / 100),
        2,
    )
    assert abs(boq.total_excl_vat_zar - expected_excl) < 0.5


def test_boq_total_incl_vat_consistent(small_dxf_bytes):
    result = run_dxf_pipeline(small_dxf_bytes, file_name="s.dxf")
    boq = result.boq
    expected_incl = round(boq.total_excl_vat_zar * (1 + boq.vat_pct / 100), 2)
    assert abs(boq.total_incl_vat_zar - expected_incl) < 0.5


def test_cable_runs_appear_as_inferred_items(realistic_dxf_bytes):
    result = run_dxf_pipeline(realistic_dxf_bytes, file_name="r.dxf")
    cable_lines = [
        it for it in result.boq.line_items
        if it.unit == "m" and it.source == ItemConfidence.INFERRED
    ]
    assert len(cable_lines) == 1
    # 8 + 7 + 15 = 30 m
    assert abs(cable_lines[0].qty - 30.0) < 1e-3


def test_quantity_only_mode(realistic_dxf_bytes):
    """include_estimated_pricing=False → no unit prices."""
    from agent.dxf_pipeline.pipeline import run_dxf_pipeline as r
    result = r(
        realistic_dxf_bytes,
        file_name="r.dxf",
        include_estimated_pricing=False,
    )
    assert result.boq is not None
    for it in result.boq.line_items:
        assert it.unit_price_zar == 0.0
        assert it.total_zar == 0.0


def test_json_roundtrip(small_dxf_bytes):
    """Result must serialise/deserialise cleanly (needed for runs/ persistence)."""
    from agent.dxf_pipeline.models import DxfPipelineRun

    result = run_dxf_pipeline(small_dxf_bytes, file_name="s.dxf")
    payload = result.model_dump_json()
    parsed = DxfPipelineRun.model_validate_json(payload)
    assert parsed.run_id == result.run_id
    assert parsed.boq.subtotal_zar == result.boq.subtotal_zar
