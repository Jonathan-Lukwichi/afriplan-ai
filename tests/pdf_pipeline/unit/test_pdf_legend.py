"""
Tests for PDF legend-first recognition (agent/pdf_pipeline/passes/legend.py)
and the shared coverage-gap logic driving the PDF run.
"""

from __future__ import annotations

from agent.pdf_pipeline.models import PageType
from agent.pdf_pipeline.passes.facts import LayoutTakeoff, PdfFacts, ProjectContext
from agent.pdf_pipeline.passes.legend import build_pdf_legend
from agent.pdf_pipeline.passes.run import run_pdf_estimator
from agent.shared.legend import billed_canonical_items, coverage_gaps


def test_build_pdf_legend_from_context_map():
    facts = PdfFacts(context=ProjectContext(legend={
        "sym_ds": "16A Double Switched Socket @300mm",
        "sym_dl": "6W LED downlight",
        "sym_hdr": "LIGHTS",                 # header → not an item
    }))
    legend = build_pdf_legend(facts)
    items = {e.canonical_item for e in legend.entries}
    assert "16A Double Switched Socket" in items
    assert "LED Downlight" in items
    assert legend.source == "pdf"
    assert all(e.canonical_item != "LIGHTS" for e in legend.entries)


def test_pdf_legend_merges_takeoff_legend():
    facts = PdfFacts(
        context=ProjectContext(legend={"a": "16A Double Switched Socket"}),
        takeoff=LayoutTakeoff(legend={"b": "30W LED flood light"}),
    )
    items = {e.canonical_item for e in build_pdf_legend(facts).entries}
    assert {"16A Double Switched Socket", "LED Floodlight"} <= items


def test_coverage_matches_across_wording():
    # legend wording != billed wording, but same canonical → NOT a gap
    facts = PdfFacts(context=ProjectContext(legend={"p": "Recessed LED Panel"}))
    legend = build_pdf_legend(facts)
    billed = billed_canonical_items(["600x1200 Recessed 3x18W LED panel — Hall"])
    assert coverage_gaps(legend, billed) == []


# ─── full-run integration (MockAnthropic) ────────────────────────────

PROJECT_CTX = {
    "project_name": "Wedela",
    "legend": {
        "s1": "16A Double Switched Socket @300mm",
        "s2": "6W LED downlight",
        "s3": "30W LED flood light",
    },
}
LAYOUT = {"rooms": [{"room_name": "Hall", "served_by_db": "DB1",
                     "downlights": 4, "confidence": 0.9}]}  # only downlights counted


def _classifications(types):
    from agent.pdf_pipeline.models import PageClassification
    return [PageClassification(page_index=i, page_type=t, confidence=0.9, rationale="t")
            for i, t in enumerate(types)]


def _pdf(titles):
    import fitz
    doc = fitz.open()
    for t in titles:
        doc.new_page(width=595, height=842).insert_text((50, 100), t, fontsize=20)
    b = doc.tobytes(); doc.close(); return b


def test_pdf_run_attaches_legend_and_flags_uncounted(mock_llm):
    llm = mock_llm(tool_responses={
        "read_project_context": PROJECT_CTX,
        "read_layout_takeoff": LAYOUT,
    })
    files = [(_pdf(["Register"]), "reg.pdf"), (_pdf(["Layout"]), "layout.pdf")]
    run = run_pdf_estimator(
        files, llm=llm,
        manual_types={"reg.pdf": "register", "layout.pdf": "lighting_layout"},
    )
    assert run.legend is not None
    items = {e.canonical_item for e in run.legend.entries}
    assert {"16A Double Switched Socket", "LED Downlight", "LED Floodlight"} <= items
    # downlights were counted → no gap; socket + flood were NOT → gaps
    gap_text = " ".join(g.description for g in run.boq.gaps)
    assert "16A Double Switched Socket" in gap_text
    assert "LED Floodlight" in gap_text
    assert "LED Downlight" not in gap_text
