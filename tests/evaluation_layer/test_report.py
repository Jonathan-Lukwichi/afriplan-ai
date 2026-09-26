"""Scorecard → markdown report."""

import pytest

from evaluation.dataset import load_manifest, reference_available, uploaded_from_manifest
from evaluation.metrics import pred_lines_from_reference, score
from evaluation.network import DrawingType as D
from evaluation.reference import load_reference
from evaluation.report import render_markdown


@pytest.mark.skipif(not reference_available("wedela"), reason="client reference BOQ kept locally (gitignored)")
def test_report_has_headline_and_gap_sections():
    ref = load_reference("wedela")
    pred = [p for p in pred_lines_from_reference(ref) if p.family != "chasing"]
    card = score(pred, ref, uploaded=set(D), pipeline="unit-test")
    md = render_markdown(card)
    assert "Reproduction Score" in md
    assert "| Coverage |" in md
    assert "## Not produced" in md and "chasing" in md
    assert "## Per building" in md and "Swimming Pool" in md


def test_uploaded_from_manifest_per_source():
    m = load_manifest("wedela")
    assert uploaded_from_manifest(m, "Small Guard House", source="dwg") == {D.SLD, D.LIGHTING, D.PLUGS, D.ARCHITECTURAL, D.SITE}
    assert uploaded_from_manifest(m, "Storage", source="dwg") == {D.SITE}     # only the site plan
    assert uploaded_from_manifest(m, "Storage", source="pdf") == {D.SLD, D.LIGHTING, D.PLUGS}
