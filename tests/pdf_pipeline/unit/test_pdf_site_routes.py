"""Issue 002 (PDF): feeder routes measured on a vector site-plan PDF — geometry, no LLM."""
import fitz
import pytest

from agent.pdf_pipeline.passes.assemble import DEFAULT_CONFIG, build_boq_from_facts
from agent.pdf_pipeline.passes.facts import Feeder, PdfFacts, PowerSpine
from agent.pdf_pipeline.passes.site_routes import read_pdf_site_routes

PT_PER_M_AT_500 = 72 / 0.0254 / 500      # 5.669 pt per metre at 1:500


def _site_plan_pdf(plotted_dashes: bool) -> bytes:
    """A1-ish page at 1:500: DB-A ─ 100 m east ─ 60 m north ─ DB-B, and a branch 40 m to DB-C."""
    k = PT_PER_M_AT_500
    doc = fitz.open()
    page = doc.new_page(width=2384, height=1684)
    ax, ay = 200.0, 1200.0
    route = [(ax, ay), (ax + 100 * k, ay), (ax + 100 * k, ay - 60 * k)]
    branch = [(ax + 50 * k, ay), (ax + 50 * k, ay + 40 * k)]
    for pts in (route, branch):
        for (x1, y1), (x2, y2) in zip(pts, pts[1:]):
            if plotted_dashes:                   # the plotter's own strokes, 6 pt dash / 3 pt gap
                L = ((x2 - x1) ** 2 + (y2 - y1) ** 2) ** 0.5
                ux, uy = (x2 - x1) / L, (y2 - y1) / L
                t = 0.0
                while t < L:
                    e = min(t + 6, L)
                    page.draw_line((x1 + ux * t, y1 + uy * t), (x1 + ux * e, y1 + uy * e), color=(0, 1, 1))
                    t += 9
            else:
                page.draw_line((x1, y1), (x2, y2), color=(0, 1, 1), dashes="[6 3] 0")
    s = 10.0                                      # DB symbols: rectangle + diagonal, centred on the route ends
    for cx, cy in (route[0], route[-1], branch[-1]):
        page.draw_rect(fitz.Rect(cx - s, cy - s / 2, cx + s, cy + s / 2))
        page.draw_line((cx - s, cy - s / 2), (cx + s, cy + s / 2))
    for text, (x, y) in (("DB-A", (ax - 30, ay - 30)),
                         ("DB-B Fed from DB-A", (route[-1][0] + 20, route[-1][1] - 20)),
                         ("DB-C fed from DB-A", (branch[-1][0] + 20, branch[-1][1] + 25)),
                         ("SITE PLAN   SCALE 1:500 @ A1", (1800, 1600))):
        page.insert_text((x, y), text, fontsize=9)
    return doc.tobytes()


@pytest.mark.parametrize("plotted", [False, True], ids=["dash-pattern", "plotter-strokes"])
def test_routes_are_measured_on_a_vector_site_plan(plotted):
    net, where = read_pdf_site_routes([(_site_plan_pdf(plotted), "WD-OL-001.pdf")])
    assert net is not None and net.found, where
    assert where == "WD-OL-001.pdf p0"
    assert net.units_per_m == pytest.approx(PT_PER_M_AT_500, rel=0.01)
    assert net.route("DB-A", "DB-B").length_m == pytest.approx(160, abs=4)
    assert net.route("DB-A", "DB-C").length_m == pytest.approx(90, abs=4)


def test_a_pdf_without_a_site_plan_has_no_routes():
    doc = fitz.open()
    doc.new_page().insert_text((50, 50), "DB-AB1  400V, 100A, 15kA", fontsize=9)
    net, where = read_pdf_site_routes([(doc.tobytes(), "SLD.pdf")])
    assert net is None and where == ""


def test_site_plan_doubts_reach_the_gap_report():
    net, _ = read_pdf_site_routes([(_site_plan_pdf(False), "site.pdf")])
    net.warnings.append("DB-C tag is about as close to DB-B's symbol — check which route belongs to which board")
    boq = build_boq_from_facts(PdfFacts(spine=PowerSpine(feeders=[
        Feeder(from_source="DB-A", to_db="DB-B", cable_size_mm2=16)])), routes=net)
    assert any("about as close" in g.description and g.severity == "medium" for g in boq.gaps)


def test_pdf_feeders_take_the_measured_route():
    net, _ = read_pdf_site_routes([(_site_plan_pdf(False), "site.pdf")])
    facts = PdfFacts(spine=PowerSpine(feeders=[
        Feeder(from_source="DB-A", to_db="DB-B", cable_size_mm2=16),
        Feeder(from_source="DB-A", to_db="DB-C", cable_size_mm2=6),
        Feeder(from_source="DB-A", to_db="DB-Z", cable_size_mm2=4),
        Feeder(from_source="DB-A", to_db="DB-W", cable_size_mm2=4, length_m=12, length_annotated=True),
    ]))
    boq = build_boq_from_facts(facts, routes=net)
    supply = {l.description: l for l in boq.line_items if l.description.startswith("Supply") and "SWA" in l.description}
    ab = next(l for d, l in supply.items() if "DB-A→DB-B" in d)
    assert ab.qty == pytest.approx(160 * 1.05 + 3, abs=5) and ab.source.value == "inferred"
    assert next(l for d, l in supply.items() if "DB-A→DB-W" in d).qty == 12          # written length wins
    az = next(l for d, l in supply.items() if "DB-A→DB-Z" in d)
    assert az.qty == DEFAULT_CONFIG.assumed_feeder_m
    assert any("no drawn route" in g.description for g in boq.gaps)
    trench = sum(l.qty for l in boq.line_items if l.description.startswith("Trench") and "DB-W" not in l.description
                 and "DB-Z" not in l.description)
    assert trench == pytest.approx(160 + 40, abs=6)                    # the shared 50 m is billed once
