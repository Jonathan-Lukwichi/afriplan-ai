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
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional, Tuple

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
from agent.dxf_pipeline.passes.recognize import DxfRecognition, recognise
from agent.dxf_pipeline.passes.site_routes import read_site_routes
from agent.dxf_pipeline.passes.sld import SldFacts, read_sld
from agent.dxf_pipeline.passes.spatial import assign_spatial
from agent.dxf_pipeline.passes.template_count import count_by_template
from agent.shared import (
    BillOfQuantities,
    BQLineItem,
    BQSection,
    ContractorProfile,
    GapItem,
    ItemConfidence,
    LineKind,
    ProjectMetadata,
)
from agent.shared.legend import Legend, billed_canonical_items, coverage_gaps
from agent.shared.persistence import persist_run
from agent.shared.routes import RouteNetwork, equipment_key
from core.rate_model import DEFAULT_PARAMS, build_rate

log = logging.getLogger(__name__)


class DxfFileNote(BaseModel):
    """One drawing of a multi-drawing run: what it was read as."""
    file_name: str
    role: str = ""                   # SLD | layout | site plan | other
    converted_from_dwg: bool = False
    ok: bool = True
    error: str = ""


class DxfEstimatorRun(BaseModel):
    run_id: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    project_name: str = ""
    input_file: str = ""
    files: List[DxfFileNote] = Field(default_factory=list)
    site_plan_file: str = ""         # drawing the feeder routes were measured on
    routes_measured: int = 0         # feeders whose length came from the site plan
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
    routes: Optional[RouteNetwork] = None,
) -> DxfEstimatorRun:
    """Run the v2 DXF estimator over one DXF/DWG. Always returns a run object.
    `routes`: a site plan's measured cable routes (from another drawing of the same
    project) used to price this drawing's SLD feeders."""
    run_id = uuid.uuid4().hex[:12]
    project = project or ProjectMetadata()
    contractor = contractor or ContractorProfile()
    started = time.perf_counter()

    doc, converted, error = _load(file_bytes, file_name)
    if doc is None:
        return DxfEstimatorRun(
            run_id=run_id, input_file=file_name, converted_from_dwg=converted,
            success=False, error=error, duration_s=round(time.perf_counter() - started, 3),
        )

    project_name = project.project_name or "Untitled DXF project"
    a = _analyse(doc, file_name, project)
    if routes is None:
        own = read_site_routes(doc)          # the drawing may itself be the site plan
        routes = own if own.found else None
    boq = build_boq_from_recognition(
        a.rec, project_name=project_name, run_id=run_id, contractor=contractor, sld=a.sld,
        routes=routes,
    )
    # Mode 3 — count exploded-line-work legend symbols by template matching.
    _integrate_template_counts(boq, doc, a.legend)
    _add_legend_coverage_gaps(boq, a.legend)
    rec, legend, spatial = a.rec, a.legend, a.spatial

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


# ─── shared per-drawing steps ────────────────────────────────────────

def _load(file_bytes: bytes, file_name: str):
    """bytes → (ezdxf document | None, converted_from_dwg, error)."""
    conv = ensure_dxf_bytes(file_bytes, file_name)
    converted = file_name.lower().endswith(".dwg")
    if not conv.ok or conv.dxf_bytes is None:
        return None, converted, conv.error
    try:
        return ezdxf.read(io.StringIO(conv.dxf_bytes.decode("utf-8", "ignore"))), converted, None
    except Exception:  # noqa: BLE001 — fall back to binary/tag reader
        try:
            import tempfile
            with tempfile.NamedTemporaryFile(suffix=".dxf", delete=False) as tf:
                tf.write(conv.dxf_bytes)
                tmp_path = tf.name
            return ezdxf.readfile(tmp_path), converted, None
        except Exception as e:  # noqa: BLE001
            log.exception("Failed to parse DXF")
            return None, converted, f"Could not parse DXF: {e}"


@dataclass
class _Analysis:
    rec: object
    sld: SldFacts
    legend: Legend
    spatial: object


def _analyse(doc, file_name: str, project: ProjectMetadata) -> _Analysis:
    """Recognition, SLD, legend and rooms for one drawing (no pricing)."""
    rec = recognise(doc)
    sld = read_sld(doc, sheet_name=Path(file_name).stem)     # boards + feeders when this is an SLD
    # Pass A–B — legend: read the drawing's own symbol dictionary.
    legend = extract_legend(doc, sheet_ref=Path(file_name).stem)
    # Legend glyphs are the key, not instances: drop symbols inside the legend table (issue 006).
    region = legend_region(doc)
    if region is not None:
        rec.symbols = [s for s in rec.symbols if not in_region(s.x, s.y, region)]
    # Pass 5 — spatial: place each symbol in a room; building hint = file/project.
    spatial = assign_spatial(rec, doc, building=project.project_name or Path(file_name).stem)
    return _Analysis(rec=rec, sld=sld, legend=legend, spatial=spatial)


# ─── a whole drawing set in one run ──────────────────────────────────

def _merge_sld(facts: List[SldFacts]) -> SldFacts:
    """One SLD view of the project. A board or feeder drawn on two sheets is billed
    once (the board with the most circuits read wins); keys ignore spacing/hyphens."""
    boards: dict = {}
    feeders: dict = {}
    for f in facts:
        for b in f.boards:
            k = equipment_key(b.name)
            if k not in boards or len(b.circuits) + b.spares > len(boards[k].circuits) + boards[k].spares:
                boards[k] = b
        for fd in f.feeders:
            feeders.setdefault((equipment_key(fd.from_source), equipment_key(fd.to_db)), fd)
    return SldFacts(boards=list(boards.values()), feeders=list(feeders.values()))


def run_dxf_project(
    files: List[Tuple[bytes, str]],
    *,
    project: Optional[ProjectMetadata] = None,
    contractor: Optional[ContractorProfile] = None,
    persist: bool = False,
) -> DxfEstimatorRun:
    """
    Run the DXF estimator over a whole drawing set (SLDs, layouts, site plan) as one
    project: boards and feeders from every SLD, billed once; feeder lengths and
    trench measured on the site plan; fittings and wiring from every layout. Each
    line's drawing_ref names the drawing it came from. Always returns a run object.
    """
    if len(files) == 1:
        return run_dxf_estimator(files[0][0], files[0][1], project=project,
                                 contractor=contractor, persist=persist)
    run_id = uuid.uuid4().hex[:12]
    project = project or ProjectMetadata()
    contractor = contractor or ContractorProfile()
    started = time.perf_counter()
    project_name = project.project_name or "Untitled DXF project"

    docs = []
    notes: List[DxfFileNote] = []
    for data, name in files:
        doc, converted, error = _load(data, name)
        notes.append(DxfFileNote(file_name=name, converted_from_dwg=converted, ok=doc is not None,
                                 error=error or ""))
        if doc is not None:
            docs.append((doc, name))
    if not docs:
        return DxfEstimatorRun(
            run_id=run_id, input_file=f"{len(files)} files", files=notes, success=False,
            error="None of the drawings could be read: " + "; ".join(n.error for n in notes if n.error),
            duration_s=round(time.perf_counter() - started, 3),
        )

    # The site plan: the drawing whose routes reach the most equipment.
    routes, site_plan = None, ""
    for doc, name in docs:
        net = read_site_routes(doc)
        if net.found and (routes is None or len(net.equipment) > len(routes.equipment)):
            routes, site_plan = net, name
    analyses = [(doc, name, _analyse(doc, name, project)) for doc, name in docs]
    for note in notes:
        a = next((x for _, n, x in analyses if n == note.file_name), None)
        if a is not None:
            note.role = ("site plan" if note.file_name == site_plan else
                         "SLD" if a.sld.found else "layout" if a.rec.symbols or a.rec.circuit_tags else "other")
    sld = _merge_sld([a.sld for _, _, a in analyses])

    boq = build_boq_from_recognition(DxfRecognition(), project_name=project_name, run_id=run_id,
                                     contractor=contractor, sld=sld, routes=routes)
    board_names = [b.name for b in sld.boards]
    billed_boards = list(board_names)          # grows: a board tagged on two layouts is billed once
    for doc, name, a in analyses:
        part = build_boq_from_recognition(a.rec, project_name=project_name, run_id=run_id,
                                          contractor=contractor, known_boards=billed_boards)
        billed_boards += a.rec.db_refs()
        _integrate_template_counts(part, doc, a.legend)
        _add_legend_coverage_gaps(part, a.legend)
        stem = Path(name).stem
        for ln in part.line_items:
            ln.drawing_ref = stem
        for g in part.gaps:
            g.drawing_ref = g.drawing_ref or stem
        boq.line_items.extend(part.line_items)
        boq.gaps.extend(part.gaps)
    if routes is not None:
        _add_route_gaps(boq, routes, sld, Path(site_plan).stem)
    elif sld.feeders:
        boq.gaps.append(GapItem(
            section=BQSection.SUBMAIN_CABLES, description="No site plan with cable routes in this drawing set",
            assumption="Feeder lengths assumed.",
            suggested_action="Upload the electrical site plan (routes + DB tags) to measure feeders.",
            severity="high", drawing_ref="DXF set",
        ))
    for ln in boq.line_items:
        ln.total_zar = round(ln.qty * ln.unit_price_zar, 2)
    _number(boq.line_items)
    _finalise_totals(boq, DEFAULT_PARAMS)
    _count_provenance(boq)

    recs = [a.rec for _, _, a in analyses]
    run = DxfEstimatorRun(
        run_id=run_id, input_file=f"{len(files)} files", project_name=project_name,
        converted_from_dwg=any(n.converted_from_dwg for n in notes),
        electrical_cable_length_m=round(sum(r.electrical_cable_length_m for r in recs), 3),
        symbol_count=sum(len(r.symbols) for r in recs),
        room_count=sum(len(a.spatial.rooms) for _, _, a in analyses),
        circuit_ids=sorted({c for r in recs for c in r.circuit_ids()}),
        db_refs=sorted({d for r in recs for d in r.db_refs()} | set(board_names)),
        files=notes, site_plan_file=site_plan,
        routes_measured=sum(1 for fd in sld.feeders
                            if routes is not None and routes.route(fd.from_source, fd.to_db)),
        boq=boq, duration_s=round(time.perf_counter() - started, 3),
        success=bool(boq.line_items),
        error=None if boq.line_items else "No electrical content recognised in the drawings",
    )
    if persist:
        persist_run(run, pipeline="dxf", run_id=run_id)
    return run


def _add_route_gaps(boq: BillOfQuantities, routes: RouteNetwork, sld: SldFacts, sheet: str) -> None:
    """What the site plan says that the SLDs don't — never silent."""
    for w in routes.warnings:
        boq.gaps.append(GapItem(section=BQSection.SUBMAIN_CABLES, description=w,
                                assumption="Route attribution as read.", severity="medium",
                                suggested_action="Check the site plan.", drawing_ref=sheet))
    sld_source = {equipment_key(fd.to_db): equipment_key(fd.from_source) for fd in sld.feeders}
    for to, frm in sorted(routes.fed_from.items()):
        if to in sld_source and sld_source[to] != frm:
            boq.gaps.append(GapItem(
                section=BQSection.SUBMAIN_CABLES, building_block=routes.names.get(to, to),
                description=(f"Site plan says {routes.names.get(to, to)} is fed from "
                             f"{routes.names.get(frm, frm)}; the SLD says from {sld_source[to]}"),
                assumption="Priced as the SLD shows (the SLD names the cable).",
                suggested_action="Confirm the supply arrangement with the designer.",
                severity="medium", drawing_ref=sheet,
            ))
    priced = {(equipment_key(fd.from_source), equipment_key(fd.to_db)) for fd in sld.feeders}
    for to, frm in sorted(routes.fed_from.items()):
        if (frm, to) not in priced and to not in sld_source:
            r = routes.route(frm, to)
            if r is not None:
                boq.gaps.append(GapItem(
                    section=BQSection.SUBMAIN_CABLES, building_block=routes.names.get(to, to),
                    description=(f"Route {routes.names.get(frm, frm)}→{routes.names.get(to, to)} "
                                 f"measured {r.length_m:.0f} m on the site plan, but no SLD gives its cable"),
                    assumption="Not priced.", severity="high", drawing_ref=sheet,
                    suggested_action="Upload the SLD for this board so the cable can be priced.",
                ))


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
