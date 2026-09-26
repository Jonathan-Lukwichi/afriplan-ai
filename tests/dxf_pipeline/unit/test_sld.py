"""DXF SLD reading (issue 001): DBs, breakers and feeders from single-line-diagram text."""

import io

import ezdxf

from agent.dxf_pipeline.passes.sld import read_sld


def _sld_doc():
    doc = ezdxf.new()
    msp = doc.modelspace()
    t = lambda s, x, y: msp.add_text(s, dxfattribs={"layer": "0"}).set_placement((x, y))   # noqa: E731
    t("DB-AB1  400V, 100A, 15kA, 50Hz, 3PH+N+E", 0, 1000)
    for i, a in enumerate(["20A", "20A", "10A", "32A"]):
        t(a, 50 * i, 800)
    t("SPARE", 250, 800)
    t("DB-AB2  400V, 63A, 6kA, 50Hz, 1PH+N+E", 5000, 1000)
    for i, a in enumerate(["10A", "16A"]):
        t(a, 5000 + 50 * i, 800)
    m = msp.add_mtext("DB-AB1 FED FROM DB-CR \n         Incoming main cable 16mm²", dxfattribs={"layer": "0"})
    m.set_location((0, 1200))
    m2 = msp.add_mtext("DB-AB2 FED FROM DB-AB1 \n  Incoming main cable 10mm²", dxfattribs={"layer": "0"})
    m2.set_location((5000, 1200))
    t("DB1-fed from DB-CR", 9000, 9000)          # site overview line with no cable size: not a feeder
    return doc


def test_boards_breakers_and_spares():
    sld = read_sld(_sld_doc())
    boards = {b.name: b for b in sld.boards}
    assert set(boards) == {"DB-AB1", "DB-AB2"}
    ab1 = boards["DB-AB1"]
    assert (ab1.main_breaker_a, ab1.phases, ab1.ka) == (100, 3, 15.0)
    assert sorted(a for a, _ in ab1.circuits) == [10, 20, 20, 32] and ab1.spares == 1
    assert boards["DB-AB2"].phases == 1 and len(boards["DB-AB2"].circuits) == 2


def test_feeders_need_a_cable_size():
    feeders = {(f.from_source, f.to_db): f for f in read_sld(_sld_doc()).feeders}
    assert set(feeders) == {("DB-CR", "DB-AB1"), ("DB-AB1", "DB-AB2")}
    assert feeders[("DB-CR", "DB-AB1")].cable_size_mm2 == 16
    assert not feeders[("DB-CR", "DB-AB1")].length_annotated


def test_sld_drawing_produces_priced_boards_and_feeders():
    from agent.dxf_pipeline.passes.run import run_dxf_estimator
    from agent.shared import BQSection, ItemConfidence
    s = io.StringIO(); _sld_doc().write(s)
    run = run_dxf_estimator(s.getvalue().encode(), "WD-AB-01-SLD.dxf")
    assert run.success, run.error
    lines = run.boq.line_items
    dbs = [l for l in lines if l.section == BQSection.DISTRIBUTION]
    assert len(dbs) == 2
    by_name = {l.description.split(":")[0]: l.unit_price_zar for l in dbs}
    assert by_name["DB-AB1"] > 5000                          # 3ph 100A board with its breakers
    assert all(p > 2 * 1200 for p in by_name.values())       # never just an empty enclosure
    swa = [l for l in lines if "SWA feeder" in l.description]
    assert {l.description.split()[0] for l in swa} == {"Supply", "Install"}
    assert any("BCEW" in l.description for l in lines)
    assert any(l.description.startswith("Terminate") and l.qty == 2 for l in lines)
    assumed = [l for l in swa if l.source == ItemConfidence.ASSUMED]
    assert assumed and any("site plan" in g.suggested_action.lower() for g in run.boq.gaps)
