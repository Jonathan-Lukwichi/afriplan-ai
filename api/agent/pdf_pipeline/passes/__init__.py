"""
v2 estimator — the 5-pass pipeline.

    Pass 1  orient        LLM  → ProjectContext
    Pass 2  power spine   LLM  → PowerSpine (DB tree + feeders)
    Pass 3  layout takeoff LLM → LayoutTakeoff (per-room counts)
    Pass 4  rule-set      PURE PYTHON  → DerivedQuantities
    Pass 5  assemble+price PURE PYTHON → BillOfQuantities + gaps

Passes 1–3 are the LLM "eyes" (facts only). Passes 4–5 are the deterministic
"brain": given the same facts, they always produce the identical bill.
"""

from agent.pdf_pipeline.passes.assemble import build_boq_from_facts
from agent.pdf_pipeline.passes.facts import (
    Feeder,
    IncomingSupply,
    LayoutTakeoff,
    PdfFacts,
    PowerSpine,
    ProjectContext,
    SpineCircuit,
    SpineDB,
    TakeoffRoom,
    parse_layout_takeoff,
    parse_power_spine,
    parse_project_context,
)
from agent.pdf_pipeline.passes.orchestrator import build_bill, extract_facts
from agent.pdf_pipeline.passes.run import (
    EstimatorRun,
    FileClassification,
    classify_files,
    ingest_files,
    run_pdf_estimator,
)

__all__ = [
    "Feeder",
    "IncomingSupply",
    "LayoutTakeoff",
    "PdfFacts",
    "PowerSpine",
    "ProjectContext",
    "SpineCircuit",
    "SpineDB",
    "TakeoffRoom",
    "parse_layout_takeoff",
    "parse_power_spine",
    "parse_project_context",
    "build_boq_from_facts",
    "build_bill",
    "extract_facts",
    "EstimatorRun",
    "FileClassification",
    "classify_files",
    "ingest_files",
    "run_pdf_estimator",
]
