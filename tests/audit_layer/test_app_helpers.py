"""Helpers the Streamlit pages use to expose the audit layer."""

from audit.boq_rules import AuditFinding
from audit.report import render_findings, summarise_findings
from audit.sufficiency import drawing_type_from_filename, drawing_types_from_page_types
from evaluation.network import DrawingType as D


def test_pdf_page_types_map_to_drawing_types():
    got = drawing_types_from_page_types(["sld", "lighting_layout", "plugs_layout", "notes", "unknown"])
    assert got == {D.SLD, D.LIGHTING, D.PLUGS}
    assert drawing_types_from_page_types(["schedule", "register"]) == {D.SCHEDULE, D.REGISTER}


def test_cad_filename_maps_to_drawing_type():
    assert drawing_type_from_filename("WD-AB-01-SLD 050425.dwg") == D.SLD
    assert drawing_type_from_filename("WD-ECH-01-LIGHTING 100425.dwg") == D.LIGHTING
    assert drawing_type_from_filename("GROUND FLOOR PLAN PLUGS ST.pdf") == D.PLUGS
    assert drawing_type_from_filename("Wedela - Sheet - 001 - Site Plan.dwg") == D.SITE
    assert drawing_type_from_filename("random.dxf") is None


def test_findings_render_and_summarise():
    fs = [AuditFinding(rule="ARITH", severity="high", building="B", message="m", value_at_risk_zar=10),
          AuditFinding(rule="NO_RATE", severity="medium", building="B", message="n", value_at_risk_zar=5)]
    s = summarise_findings(fs)
    assert s["count"] == 2 and s["value_at_risk_zar"] == 15
    assert s["by_rule"][0] == ("ARITH", 1, 10)
    md = render_findings(fs, "T")
    assert md.startswith("# T") and "| ARITH | 1 | R 10 |" in md
