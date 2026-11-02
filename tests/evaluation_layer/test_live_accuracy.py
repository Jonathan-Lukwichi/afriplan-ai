"""Extraction accuracy on a run: only when the upload IS a reference project with its real bill on file."""

from __future__ import annotations

import json

import pytest

from agent.shared.boq import BillOfQuantities
from evaluation.live import find_reference_project, reading_summary
from evaluation.network import DrawingType
from evaluation.reference import RefBuilding, ReferenceBoq, RefLine


def _project(root, name="demo", *, bill=True):
    d = root / name
    d.mkdir()
    files = [{"path": f"raw/{n}", "sha256": "x", "role": role} for n, role in (
        ("A-01-LIGHTING 0101.dwg", "lighting_layout"), ("A-01-PLUG 0101.dwg", "plug_layout"),
        ("A-01-SLD 0101.dwg", "sld"), ("Site Plan 0101.dwg", "site_plan"),
        ("Priced Bill.xlsx", "reference_boq"))]
    (d / "manifest.json").write_text(json.dumps({"project": name, "files": files}), encoding="utf-8")
    if bill:
        (d / "reference_boq.json").write_text("{}", encoding="utf-8")


UPLOAD = ["A-01-LIGHTING 0101.dwg", "A-01-PLUG  0101.dwg", "A-01-SLD 0101.dwg", "Site Plan 0101.dwg"]


def test_the_whole_drawing_set_finds_its_project(tmp_path):
    _project(tmp_path)
    assert find_reference_project(UPLOAD, root=tmp_path) == "demo"


def test_one_sheet_of_a_set_is_not_judged_against_the_whole_bill(tmp_path):
    _project(tmp_path)
    assert find_reference_project(UPLOAD[:1], root=tmp_path) is None


def test_an_unknown_project_has_no_accuracy(tmp_path):
    _project(tmp_path)
    assert find_reference_project(["Other-LIGHTING.dwg", "Other-SLD.dwg"], root=tmp_path) is None


def test_a_project_whose_real_bill_is_not_here_has_no_accuracy(tmp_path):
    """The deployed app: manifests are committed, the client's priced bills never are."""
    _project(tmp_path, bill=False)
    assert find_reference_project(UPLOAD, root=tmp_path) is None


def test_no_projects_folder_is_not_an_error(tmp_path):
    assert find_reference_project(UPLOAD, root=tmp_path / "missing") is None


@pytest.fixture
def scored(monkeypatch, tmp_path):
    import evaluation.live as live
    _project(tmp_path)
    line = RefLine(building="A", sheet="A", description="600x1200 Recessed LED panel", unit="No",
                   qty=10, rate=100, total=1000, role="supply", key_family="light_panel", key_spec="")
    ref = ReferenceBoq(project="demo", buildings=[RefBuilding(name="A", sheet="A", lines=[line], in_summary=True)])
    monkeypatch.setattr(live, "load_reference", lambda p: ref)
    monkeypatch.setattr(live, "load_manifest", lambda p: None)
    monkeypatch.setattr(live, "uploaded_from_manifest", lambda m, b, source: {DrawingType.LIGHTING})
    return live


def test_the_summary_says_how_much_was_read_with_no_money_in_it(scored):
    boq = BillOfQuantities(project_name="demo", pipeline="dxf", line_items=[])
    out = scored.reading_summary(boq, "demo", pipeline="dxf")
    assert set(out) >= {"project", "reading_score", "coverage", "qty_accuracy", "items_judged",
                        "items_found", "items_within_10pct", "item_precision", "biggest_misses"}
    assert "zar" not in json.dumps(out).lower() and "ref_value" not in json.dumps(out)


def test_no_bill_queries_means_no_second_number(scored):
    boq = BillOfQuantities(project_name="demo", pipeline="dxf", line_items=[])
    assert scored.reading_summary(boq, "demo", pipeline="dxf")["if_queries_confirmed"] is None


def test_a_queried_item_stops_counting_against_the_second_number_only(scored, tmp_path, monkeypatch):
    """The bill may be wrong on an item: the scorer's own number never moves."""
    monkeypatch.setattr(scored, "DATA_ROOT", tmp_path)
    (tmp_path / "demo" / "bill_queries.json").write_text(
        json.dumps([{"key": "light_panel", "note": "Bill differs from the drawing"}]), encoding="utf-8")
    boq = BillOfQuantities(project_name="demo", pipeline="dxf", line_items=[])
    out = scored.reading_summary(boq, "demo", pipeline="dxf")
    assert out["reading_score"] == 0.0
    assert out["if_queries_confirmed"] == {"score": pytest.approx(1.0), "items": ["Bill differs from the drawing"]}


def test_the_projects_folder_can_be_elsewhere(monkeypatch, tmp_path):
    """A git worktree has no client data: its app reads the bills in the main checkout."""
    import importlib

    import evaluation.dataset as dataset
    monkeypatch.setenv("AFRIPLAN_PROJECTS_DIR", str(tmp_path))
    try:
        assert importlib.reload(dataset).DATA_ROOT == tmp_path
    finally:
        monkeypatch.delenv("AFRIPLAN_PROJECTS_DIR")
        importlib.reload(dataset)


def test_reading_summary_is_importable_where_the_router_needs_it():
    assert callable(reading_summary)
