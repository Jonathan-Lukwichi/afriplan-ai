"""POST /api/runs with a whole DWG/DXF set: one project run (issue 002 — routes live on
the site plan, feeders on the SLDs, so the drawings must be read together)."""
from __future__ import annotations

import io

import ezdxf
from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


def _dxf(*texts) -> bytes:
    doc = ezdxf.new()
    msp = doc.modelspace()
    for i, t in enumerate(texts):
        msp.add_text(t).set_placement((0, 1000 - 200 * i))
    s = io.StringIO()
    doc.write(s)
    return s.getvalue().encode()


def _post(files):
    return client.post("/api/runs", data={"pipeline": "dxf"},
                       files=[("files", (name, data, "application/dxf")) for name, data in files])


def test_several_drawings_become_one_project_run():
    sld = _dxf("DB-B  400V, 63A, 6kA, 50Hz, 3PH+N+E", "20A", "10A")
    other = _dxf("DB-C  400V, 40A, 6kA, 50Hz, 1PH+N+E", "16A")
    r = _post([("WD-B-01-SLD.dxf", sld), ("WD-C-01-SLD.dxf", other)])
    assert r.status_code == 200, r.text
    run = client.get(f"/api/runs/{r.json()['run_id']}").json()
    assert run["status"] == "passed", run["error"]
    assert run["input_file"] == "2 files"
    result = run["result"]
    assert [f["file_name"] for f in result["files"]] == ["WD-B-01-SLD.dxf", "WD-C-01-SLD.dxf"]
    boards = {l["description"].split(":")[0] for l in result["boq"]["line_items"]
              if l["description"].startswith("DB-")}
    assert boards == {"DB-B", "DB-C"}


def test_a_single_drawing_still_works():
    r = _post([("WD-B-01-SLD.dxf", _dxf("DB-B  400V, 63A, 6kA, 50Hz, 3PH+N+E", "20A"))])
    assert r.status_code == 200
    run = client.get(f"/api/runs/{r.json()['run_id']}").json()
    assert run["status"] == "passed" and run["input_file"] == "WD-B-01-SLD.dxf"


def test_coverage_of_a_set_lists_each_drawing_type():
    r = _post([("WD-B-01-SLD.dxf", _dxf("DB-B  400V, 63A, 6kA, 50Hz, 3PH+N+E", "20A")),
               ("WD-B-01-LIGHTING.dxf", _dxf("DB-B/L1"))])
    cov = client.get(f"/api/audit/coverage/{r.json()['run_id']}").json()
    assert {"sld", "lighting_layout"} <= set(cov["uploaded"])
