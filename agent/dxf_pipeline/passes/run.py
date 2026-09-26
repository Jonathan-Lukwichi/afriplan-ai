"""
v2 DXF estimator run entry.

    bytes (.dxf or .dwg)
        → ensure_dxf_bytes   (auto-convert DWG via ODA)
        → ezdxf.readfile
        → recognise           (isolate + symbols + circuits + measure)
        → build_boq_from_recognition   (deterministic A–H priced bill)
        → DxfEstimatorRun

Fully deterministic given a DXF (the only non-determinism is the optional
external DWG→DXF conversion, which is itself reproducible). No LLM, R0.00.
"""

from __future__ import annotations

import io
import logging
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import List, Optional

import ezdxf
from pydantic import BaseModel, Field

from agent.dxf_pipeline.dwg import ensure_dxf_bytes
from agent.dxf_pipeline.passes.assemble import (
    _count_provenance,
    _finalise_totals,
    _number,
    build_boq_from_recognition,
)
from agent.dxf_pipeline.passes.legend import extract_legend, in_region, legend_region
from agent.dxf_pipeline.passes.recognize import recognise
from agent.dxf_pipeline.passes.spatial import assign_spatial
from agent.dxf_pipeline.passes.template_count import count_by_template
from agent.shared import (
    BillOfQuantities,
    BQLineItem,
    BQSection,
    ContractorProfile,
    ItemConfidence,
    LineKind,
    ProjectMetadata,
)
from agent.shared.legend import Legend, billed_canonical_items, coverage_gaps
from agent.shared.persistence import persist_run
from core.rate_model import DEFAULT_PARAMS, build_rate

log = logging.getLogger(__name__)


class DxfEstimatorRun(BaseModel):
    run_id: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    project_name: str = ""
    input_file: str = ""
    converted_from_dwg: bool = False
    electrical_cable_length_m: float = 0.0
    symbol_count: int = 0
    room_count: int = 0
    circuit_ids: List[str] = Field(default_factory=list)
    db_refs: List[str] = Field(default_factory=list)
    legend: Optional[Legend] = None
    boq: Optional[BillOfQuantities] = None
    duration_s: float = 0.0
    success: bool = False
    error: Optional[str] = None

    @property
    def gap_count(self) -> int:
        return len(self.boq.gaps) if self.boq else 0


def run_dxf_estimator(
    file_bytes: bytes,
    file_name: str = "input.dxf",
    *,
    project: Optional[ProjectMetadata] = None,
    contractor: Optional[ContractorProfile] = None,
    persist: bool = False,
) -> DxfEstimatorRun:
    """Run the v2 DXF estimator over one DXF/DWG. Always returns a run object."""
    run_id = uuid.uuid4().hex[:12]
    project = project or ProjectMetadata()
    contractor = contractor or ContractorProfile()
    started = time.perf_counter()

    conv = ensure_dxf_bytes(file_bytes, file_name)
    if not conv.ok or conv.dxf_bytes is None:
        return DxfEstimatorRun(
            run_id=run_id, input_file=file_name, success=False, error=conv.error,
            duration_s=round(time.perf_counter() - started, 3),
        )
    converted = file_name.lower().endswith(".dwg")

    try:
        doc = ezdxf.read(io.StringIO(conv.dxf_bytes.decode("utf-8", "ignore")))
    except Exception:  # noqa: BLE001 — fall back to binary/tag reader
        try:
            import tempfile
            with tempfile.NamedTemporaryFile(suffix=".dxf", delete=False) as tf:
                tf.write(conv.dxf_bytes)
                tmp_path = tf.name
            doc = ezdxf.readfile(tmp_path)
        except Exception as e:  # noqa: BLE001
            log.exception("Failed to parse DXF")
            return DxfEstimatorRun(
                run_id=run_id, input_file=file_name, converted_from_dwg=converted,
                success=False, error=f"Could not parse DXF: {e}",
                duration_s=round(time.perf_counter() - started, 3),
            )

    rec = recognise(doc)
    project_name = project.project_name or "Untitled DXF project"
    # Pass A–B — legend: read the drawing's own symbol dictionary.
    legend = extract_legend(doc, sheet_ref=Path(file_name).stem)
    # Legend glyphs are the key, not instances: drop symbols inside the legend table (issue 006).
    region = legend_region(doc)
    if region is not None:
        rec.symbols = [s for s in rec.symbols if not in_region(s.x, s.y, region)]
    # Pass 5 — spatial: place each symbol in a room; building hint = file/project.
    building_hint = project.project_name or Path(file_name).stem
    spatial = assign_spatial(rec, doc, building=building_hint)
    boq = build_boq_from_recognition(
        rec, project_name=project_name, run_id=run_id, contractor=contractor,
    )
    # Mode 3 — count exploded-line-work legend symbols by template matching.
    _integrate_template_counts(boq, doc, legend)
    _add_legend_coverage_gaps(boq, legend)

    run = DxfEstimatorRun(
        run_id=run_id, input_file=file_name, converted_from_dwg=converted,
        project_name=project_name,
        electrical_cable_length_m=rec.electrical_cable_length_m,
        symbol_count=len(rec.symbols),
        room_count=len(spatial.rooms),
        circuit_ids=rec.circuit_ids(), db_refs=rec.db_refs(),
        legend=legend,
        boq=boq,
        duration_s=round(time.perf_counter() - started, 3),
        success=bool(boq.line_items),
        error=None if boq.line_items else "No electrical content recognised in the DXF",
    )
    if persist:
        persist_run(run, pipeline="dxf", run_id=run_id)
    return run


_SECTION_MATERIAL = {
    BQSection.LIGHTING: 280.0, BQSection.POWER_OUTLETS: 160.0,
    BQSection.DATA_COMMS: 450.0, BQSection.FIRE_SAFETY: 850.0,
    BQSection.DISTRIBUTION: 4500.0, BQSection.SOLAR_PV: 2800.0,
    BQSection.FINAL_CABLES: 200.0,
}


def _integrate_template_counts(boq: BillOfQuantities, doc, legend: Legend) -> None:
    """
    Add a priced line for each legend symbol counted by template matching
    (mode 3). Marked INFERRED — the COUNT is deterministic geometry, the rate is
    a ballpark for the contractor to confirm. Once billed, these items drop out
    of the legend coverage gaps automatically.
    """
    counts = count_by_template(doc, legend)
    if not counts:
        return
    section_of = {e.canonical_item: e.section for e in legend.entries}
    for item, n in sorted(counts.items()):
        section = section_of.get(item, BQSection.FINAL_CABLES)
        material = _SECTION_MATERIAL.get(section, 200.0)
        rate = build_rate(material_cost=material, install_labour=85.0, params=DEFAULT_PARAMS)
        boq.line_items.append(BQLineItem(
            section=section, description=f"{item} (template-matched)", unit="No",
            qty=float(n), unit_price_zar=round(rate.combined_rate, 2),
            source=ItemConfidence.INFERRED, line_kind=LineKind.COMBINED,
            drawing_ref="DXF template",
            notes="Counted by legend-glyph template matching — verify count & rate.",
        ))
    for l in boq.line_items:
        l.total_zar = round(l.qty * l.unit_price_zar, 2)
    _number(boq.line_items)
    _finalise_totals(boq, DEFAULT_PARAMS)
    _count_provenance(boq)


def _add_legend_coverage_gaps(boq: BillOfQuantities, legend: Legend) -> None:
    """
    Emit a gap for every legend item not present in a priced line — turning a
    silent miss (e.g. exploded-line-work downlights) into a visible
    'declared but not counted'. Uses the shared LDSE coverage helper.
    """
    billed = billed_canonical_items(l.description for l in boq.line_items)
    boq.gaps.extend(coverage_gaps(legend, billed))
