"""Two revisions of the same drawing in one upload: keep the newest, say so (never count twice)."""
from agent.dxf_pipeline.passes.revisions import pick_latest_revisions, sheet_and_revision


def test_sheet_number_and_issue_date_are_read_from_the_file_name():
    assert sheet_and_revision("WD-PB-01-LIGHTING  100225.dwg")[0] == sheet_and_revision("WD-PB-01-LIGHTING 100425.dwg")[0]
    assert sheet_and_revision("WD-PB-01-LIGHTING  100225.dwg")[1] < sheet_and_revision("WD-PB-01-LIGHTING 100425.dwg")[1]
    # different sheets never collide
    assert sheet_and_revision("WD-AB-01-LIGHTING 250325.dwg")[0] != sheet_and_revision("WD-AB-01-PLUG 250325.dwg")[0]
    assert sheet_and_revision("WD-SGH-01- SLD 050425.dwg")[0] == sheet_and_revision("WD-SGH-01-SLD 100425.dwg")[0]


def test_revision_letters_and_numbers_are_ordered():
    assert sheet_and_revision("E-101 Rev A.dwg")[0] == sheet_and_revision("E-101 Rev C.dwg")[0]
    assert sheet_and_revision("E-101 Rev A.dwg")[1] < sheet_and_revision("E-101 Rev C.dwg")[1]
    assert sheet_and_revision("E-101_R2.dwg")[1] < sheet_and_revision("E-101_R10.dwg")[1]


def test_the_older_revision_is_dropped_and_reported():
    names = ["WD-PB-01-LIGHTING  100225.dwg", "WD-PB-01-LIGHTING  100425.dwg", "WD-PB-01-PLUG  100425.dwg"]
    keep, dropped = pick_latest_revisions(names)
    assert keep == ["WD-PB-01-LIGHTING  100425.dwg", "WD-PB-01-PLUG  100425.dwg"]
    assert dropped == {"WD-PB-01-LIGHTING  100225.dwg": "WD-PB-01-LIGHTING  100425.dwg"}


def test_files_without_a_revision_mark_are_all_kept():
    names = ["site.dwg", "Site.dwg", "lighting.dwg"]
    keep, dropped = pick_latest_revisions(names)
    assert keep == names and dropped == {}


def test_order_of_upload_does_not_matter():
    a, b = "WD-PB-01-LIGHTING 100425.dwg", "WD-PB-01-LIGHTING 100225.dwg"
    assert pick_latest_revisions([a, b])[0] == [a]
    assert pick_latest_revisions([b, a])[0] == [a]


def test_project_run_ignores_the_older_revision_and_says_so():
    import io
    import ezdxf
    from agent.dxf_pipeline.passes.run import run_dxf_project

    def dxf(tag):
        doc = ezdxf.new()
        doc.modelspace().add_text(tag, dxfattribs={"layer": "E-LIGHTING"}).set_placement((0, 0))
        s = io.StringIO(); doc.write(s)
        return s.getvalue().encode()

    run = run_dxf_project([(dxf("DB-X/L1"), "WD-X-01-LIGHTING 100225.dxf"),
                           (dxf("DB-X/L1"), "WD-X-01-LIGHTING 100425.dxf")])
    roles = {n.file_name: n.role for n in run.files}
    assert roles["WD-X-01-LIGHTING 100225.dxf"].startswith("older revision")
    assert any("older revision" in g.description and "100225" in g.description for g in run.boq.gaps)
    assert {l.drawing_ref for l in run.boq.line_items} == {"WD-X-01-LIGHTING 100425"}
