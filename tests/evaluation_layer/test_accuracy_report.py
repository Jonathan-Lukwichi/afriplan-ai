"""Accuracy report: the metrics explained, every reader's score, and where the points were lost."""

import json

from evaluation.accuracy_report import build_accuracy_report, render_accuracy_markdown
from evaluation.metrics import PredLine, score
from evaluation.network import DrawingType as D
from evaluation.reference import RefBuilding, RefLine, ReferenceBoq


def _l(fam, qty, rate):
    return RefLine(sheet="H", building="H", description=fam, qty=qty, rate=rate, total=qty * rate, key_family=fam)


def _cards():
    ref = ReferenceBoq(project="t", buildings=[RefBuilding(name="H", sheet="H", in_summary=True, lines=[
        _l("light_panel", 20, 2000), _l("swa_cable", 100, 450), _l("connection_fee", 1, 5000)])])
    cad = score([PredLine(building="H", family="swa_cable", qty=60, rate=450, total=27_000)], ref, uploaded={D.SLD})
    both = score([PredLine(building="H", family="swa_cable", qty=90, rate=450, total=40_500),
                  PredLine(building="H", family="light_panel", qty=20, rate=1000, total=20_000)],
                 ref, uploaded={D.SLD, D.LIGHTING})
    return {"CAD alone": cad, "Combined (delivered)": both}


def test_report_json_holds_every_reader_and_the_gap_breakdown_of_the_delivered_bill():
    rep = build_accuracy_report(_cards(), project="t", run="r1", delivered="Combined (delivered)")
    json.dumps(rep)                                                    # plain JSON, saved as a file
    assert set(rep["readers"]) == {"CAD alone", "Combined (delivered)"}
    assert rep["readers"]["Combined (delivered)"]["reproduction_score"] > rep["readers"]["CAD alone"]["reproduction_score"]
    assert {"reproduction_score", "coverage", "precision", "qty_accuracy", "rate_accuracy",
            "total_accuracy"} <= set(rep["metrics_explained"])
    gaps = rep["delivered_gaps"]
    rs = rep["readers"]["Combined (delivered)"]["reproduction_score"]
    assert abs(sum(gaps["by_cause"].values()) - (1 - rs)) < 1e-6
    assert gaps["items"][0]["family"] == "connection_fee"             # biggest loss first


def test_reading_accuracy_leads_the_report_for_every_reader():
    rep = build_accuracy_report(_cards(), project="t", run="r1", delivered="Combined (delivered)")
    for r in rep["readers"].values():
        assert {"reading_score", "coverage", "qty_accuracy", "item_precision"} <= set(r["reading"])
    md = render_accuracy_markdown(rep)
    assert md.index("## Reading accuracy") < md.index("## Every reader")
    assert "connection_fee" in md.split("## Every reader")[0]          # excluded items are named, not hidden


def test_markdown_explains_the_metrics_and_lists_the_losses_with_their_fix():
    md = render_accuracy_markdown(build_accuracy_report(_cards(), project="t", run="r1",
                                                        delivered="Combined (delivered)"))
    assert "# Accuracy report" in md
    assert "## What we measure" in md and "Reproduction Score" in md
    assert "| CAD alone |" in md and "| Combined (delivered) |" in md
    assert "## Where the missing points are" in md
    assert "connection_fee" in md and "never on a drawing" in md
    assert "## Rates" in md and "light_panel" in md                    # priced at half the real rate
