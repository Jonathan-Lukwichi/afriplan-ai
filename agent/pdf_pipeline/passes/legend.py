"""
PDF legend-first recognition (LDSE for the PDF pipeline).

The vision passes already report the drawing's legend as a {symbol: meaning}
map (ProjectContext.legend from the register/notes sheet, and any per-layout
legend from the take-off). Here we turn that into the shared `Legend`
dictionary so the PDF pipeline is *legend-driven* just like the DXF one:

  • the legend text → priced BOQ item types (via the shared description bridge)
  • anything the legend declares but the take-off did not count → a visible gap

Independent of the DXF pipeline — shares only the LDSE spec (agent.shared.legend).
"""

from __future__ import annotations

from agent.pdf_pipeline.passes.facts import PdfFacts
from agent.shared.legend import Legend, legend_from_symbol_map


def build_pdf_legend(facts: PdfFacts, *, sheet_ref: str = "") -> Legend:
    """
    Merge every legend the vision passes captured (project context + each
    layout take-off) into one deduped Legend dictionary for the drawing set.
    """
    merged: dict = {}
    # project-level legend (register / notes sheet)
    merged.update(facts.context.legend or {})
    # layout-level legend (may add symbols the notes sheet omitted)
    merged.update(facts.takeoff.legend or {})
    return legend_from_symbol_map(merged, source="pdf", sheet_ref=sheet_ref)
