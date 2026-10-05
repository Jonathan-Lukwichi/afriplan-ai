"""DOE execution layer (doe/execution/project.py): any folder in; bad or missing page forms stop the run."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
_spec = importlib.util.spec_from_file_location("doe_project", ROOT / "doe" / "execution" / "project.py")
project = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(project)


def test_discover_finds_drawings_sets_aside_old_revisions_and_skips_outputs(tmp_path):
    for name in ("WD-A-LIGHTING 100225.dwg", "WD-A-LIGHTING 100425.dwg", "Set.pdf", "notes.txt"):
        (tmp_path / name).write_bytes(b"x")
    (tmp_path / "sub").mkdir()
    (tmp_path / "sub" / "SLD.dxf").write_bytes(b"x")
    (tmp_path / project.OUT_DIR).mkdir()
    (tmp_path / project.OUT_DIR / "old.pdf").write_bytes(b"x")
    cad, pdfs, superseded = project.discover(tmp_path)
    assert [p.name for p in cad] == ["SLD.dxf", "WD-A-LIGHTING 100425.dwg"]
    assert [p.name for p in pdfs] == ["Set.pdf"]
    assert superseded == {"WD-A-LIGHTING 100225.dwg": "WD-A-LIGHTING 100425.dwg"}


def _work(tmp_path, forms: dict) -> Path:
    wd = tmp_path / "work"
    (wd / "forms").mkdir(parents=True)
    pages = [{"index": i, "sheet": f"Set p{i}"} for i in range(len(forms))]
    (wd / "manifest.json").write_text(json.dumps({"pages": pages}), encoding="utf-8")
    for i, form in forms.items():
        if form is not None:
            (wd / "forms" / f"p{i:02d}.json").write_text(json.dumps(form), encoding="utf-8")
    return wd


GOOD_LAYOUT = {"page_type": "lighting_layout", "tool": "read_layout_takeoff",
               "input": {"rooms": [{"room_name": "Office", "downlights": 4, "confidence": 0.9}]}}


def test_valid_forms_become_facts(tmp_path):
    wd = _work(tmp_path, {0: GOOD_LAYOUT, 1: {"page_type": "unknown", "tool": "none", "input": {}}})
    facts, _, report = project.read_forms(wd)
    assert facts.takeoff.rooms[0].downlights == 4 and facts.takeoff.rooms[0].source_pages == [0]
    assert len(report) == 2


def test_a_missing_form_stops_the_run(tmp_path):
    wd = _work(tmp_path, {0: GOOD_LAYOUT, 1: None})
    with pytest.raises(SystemExit, match="p01.*not read"):
        project.read_forms(wd)


def test_a_form_that_breaks_the_schema_is_rejected(tmp_path):
    bad = {"page_type": "lighting_layout", "tool": "read_layout_takeoff",
           "input": {"rooms": [{"room_name": "Office", "downlights": -3, "confidence": 0.9}]}}
    wd = _work(tmp_path, {0: bad})
    with pytest.raises(SystemExit, match="rejected"):
        project.read_forms(wd)


def test_a_scored_run_saves_its_accuracy_report_as_markdown_and_json(tmp_path):
    from evaluation.metrics import PredLine, score
    from evaluation.network import DrawingType
    from evaluation.reference import RefBuilding, RefLine, ReferenceBoq
    ref = ReferenceBoq(project="t", buildings=[RefBuilding(name="H", sheet="H", in_summary=True, lines=[
        RefLine(sheet="H", building="H", description="db", qty=2, rate=3000, total=6000, key_family="db")])])
    card = score([PredLine(building="H", family="db", qty=1, rate=3000, total=3000)], ref, uploaded={DrawingType.SLD})
    out, archive = tmp_path / "AfriPlan_Output", tmp_path / "reports" / "accuracy"
    out.mkdir()

    written = project.write_accuracy_report({"Combined (delivered)": card}, project="Club", reference="wedela",
                                            stamp="20261005-1200", out=out, archive=archive)

    assert (out / "accuracy_report.md").read_text(encoding="utf-8").startswith("# Accuracy report")
    data = json.loads((out / "accuracy_report.json").read_text(encoding="utf-8"))
    assert data["readers"]["Combined (delivered)"]["reproduction_score"] == pytest.approx(0.5)
    assert sorted(p.name for p in archive.iterdir()) == ["20261005-1200-wedela-doe-accuracy.json",
                                                          "20261005-1200-wedela-doe-accuracy.md"]
    assert len(written) == 4


def test_an_invented_field_is_rejected(tmp_path):
    bad = {"page_type": "lighting_layout", "tool": "read_layout_takeoff",
           "input": {"rooms": [{"room_name": "Office", "price_zar": 900, "confidence": 0.9}]}}
    with pytest.raises(SystemExit, match="rejected"):
        project.read_forms(_work(tmp_path, {0: bad}))
