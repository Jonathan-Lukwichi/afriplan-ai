"""Reference-dataset manifest: checksums make every evaluation reproducible."""

from pathlib import Path

from evaluation.dataset import (
    DatasetFile,
    ProjectManifest,
    load_manifest,
    mark_superseded,
    sha256_file,
    verify_manifest,
)


def _manifest_for(tmp_path: Path, content: bytes) -> ProjectManifest:
    f = tmp_path / "raw" / "a.dwg"
    f.parent.mkdir(parents=True)
    f.write_bytes(content)
    return ProjectManifest(
        project="t", description="", buildings=["B1"], building_codes={"B": "B1"},
        files=[DatasetFile(path="raw/a.dwg", sha256=sha256_file(f), role="sld", building="B1")],
    )


def test_verify_ok_when_checksums_match(tmp_path):
    m = _manifest_for(tmp_path, b"hello")
    assert verify_manifest(m, tmp_path) == []


def test_verify_flags_checksum_mismatch(tmp_path):
    m = _manifest_for(tmp_path, b"hello")
    (tmp_path / "raw" / "a.dwg").write_bytes(b"changed")
    problems = verify_manifest(m, tmp_path)
    assert len(problems) == 1 and "checksum mismatch" in problems[0]


def test_verify_flags_missing_file(tmp_path):
    m = _manifest_for(tmp_path, b"hello")
    (tmp_path / "raw" / "a.dwg").unlink()
    problems = verify_manifest(m, tmp_path)
    assert len(problems) == 1 and "missing" in problems[0]


def test_older_revision_of_same_drawing_is_superseded():
    files = [
        DatasetFile(path="raw/WD-PB-01-LIGHTING  100225.dwg", sha256="a", role="lighting_layout", building="P"),
        DatasetFile(path="raw/WD-PB-01-LIGHTING  100425.dwg", sha256="b", role="lighting_layout", building="P"),
        DatasetFile(path="raw/WD-PB-01-PLUG  100425.dwg", sha256="c", role="plug_layout", building="P"),
    ]
    out = mark_superseded(files)
    assert [f.superseded for f in out] == [True, False, False]
    m = ProjectManifest(project="t", files=out)
    assert [f.path for f in m.files_for(building="P", role="lighting_layout")] == [
        "raw/WD-PB-01-LIGHTING  100425.dwg"
    ]


def test_wedela_manifest_lists_the_seven_billed_buildings():
    m = load_manifest("wedela")
    assert len(m.buildings) == 7
    assert "Ablution Retail Block" in m.buildings
    roles = {f.role for f in m.files}
    assert {"reference_boq", "sld", "lighting_layout", "plug_layout"} <= roles
