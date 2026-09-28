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
from typing import Callable, Dict, List, Optional, Tuple

import ezdxf
from pydantic import BaseModel, Field

from agent.dxf_pipeline.dwg import ensure_dxf_bytes
from agent.dxf_pipeline.passes.assemble import findings_from_recognition
from agent.dxf_pipeline.passes.legend import extract_legend, in_region, legend_region
from agent.dxf_pipeline.passes.recognize import DxfRecognition, _plain_text, recognise
from agent.dxf_pipeline.passes.revisions import pick_latest_revisions
from agent.dxf_pipeline.passes.shapes import ShapeGroup, find_shape_groups
from agent.dxf_pipeline.passes.site_routes import read_site_routes
from agent.dxf_pipeline.passes.sld import SldFacts, read_sld
from agent.dxf_pipeline.passes.spatial import assign_spatial
from agent.dxf_pipeline.passes.template_count import count_by_template
from agent.shared import (
    BillOfQuantities,
    BQSection,
    ContractorProfile,
    GapItem,
    ItemConfidence,
    ProjectMetadata,
)
from agent.shared.findings import Evidence, Findings, ItemFinding
from agent.shared.legend import Legend, billed_canonical_items, coverage_gaps
from agent.shared.persistence import persist_run
from agent.shared.pricing import price_findings
from agent.shared.routes import RouteNetwork, equipment_key
from agent.shared.symbol_catalogue import catalogue_item

log = logging.getLogger(__name__)


class DxfFileNote(BaseModel):
    """One drawing of a multi-drawing run: what it was read as."""
    file_name: str
    role: str = ""                   # SLD | layout | site plan | other
    converted_from_dwg: bool = False
    ok: bool = True
    error: str = ""


class DxfAiSymbol(BaseModel):
    """One repeated unnamed symbol shape and what it was named as (ADR-0007)."""
    signature: str
    item: str
    named_by: str = "ai"             # ai | person
    count: int = 0
    sheets: List[str] = Field(default_factory=list)
    image_png_b64: str = ""


class DxfEstimatorRun(BaseModel):
    run_id: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    project_name: str = ""
    input_file: str = ""
    files: List[DxfFileNote] = Field(default_factory=list)
    site_plan_file: str = ""         # drawing the feeder routes were measured on
    routes_measured: int = 0         # feeders whose length came from the site plan
    ai_symbols: List[DxfAiSymbol] = Field(default_factory=list)   # shapes named by AI / a person
    ai_cost_zar: float = 0.0         # what naming new shapes cost this run
    converted_from_dwg: bool = False
    electrical_cable_length_m: float = 0.0
    symbol_count: int = 0
    room_count: int = 0
    circuit_ids: List[str] = Field(default_factory=list)
    db_refs: List[str] = Field(default_factory=list)
    legend: Optional[Legend] = None
    findings: Optional[Findings] = None   # what was read, before pricing (ADR-0008)
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
    findings = findings_from_recognition(a.rec, sld=a.sld, routes=routes)
    # Mode 3 — count exploded-line-work legend symbols by template matching.
    findings.items += _template_findings(doc, a.legend)
    findings.gaps += _legend_coverage_gaps(findings, a.legend)
    boq = price_findings(findings, pipeline="dxf", project_name=project_name, run_id=run_id)
    rec, legend, spatial = a.rec, a.legend, a.spatial

    run = DxfEstimatorRun(
        run_id=run_id, input_file=file_name, converted_from_dwg=converted,
        project_name=project_name,
        electrical_cable_length_m=rec.electrical_cable_length_m,
        symbol_count=len(rec.symbols),
        room_count=len(spatial.rooms),
        circuit_ids=rec.circuit_ids(), db_refs=rec.db_refs(),
        legend=legend,
        findings=findings, boq=boq,
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
    name_shapes: Optional[ShapeNamer] = None,
) -> DxfEstimatorRun:
    """
    `name_shapes` (optional, ADR-0007): names repeated unnamed symbol shapes — injected
    by the caller (api/assist), so this pipeline never imports an LLM. Without it the
    run is exactly the deterministic one.

    Run the DXF estimator over a whole drawing set (SLDs, layouts, site plan) as one
    project: boards and feeders from every SLD, billed once; feeder lengths and
    trench measured on the site plan; fittings and wiring from every layout. Each
    line's drawing_ref names the drawing it came from. Always returns a run object.
    """
    if len(files) == 1 and name_shapes is None:
        return run_dxf_estimator(files[0][0], files[0][1], project=project,
                                 contractor=contractor, persist=persist)
    run_id = uuid.uuid4().hex[:12]
    project = project or ProjectMetadata()
    contractor = contractor or ContractorProfile()
    started = time.perf_counter()
    project_name = project.project_name or "Untitled DXF project"

    docs = []
    notes: List[DxfFileNote] = []
    # Two revisions of one sheet would bill its contents twice: read only the newest.
    _, superseded = pick_latest_revisions([name for _, name in files])
    for name, newer in superseded.items():
        notes.append(DxfFileNote(file_name=name, role=f"older revision — replaced by {newer}"))
    for data, name in files:
        if name in superseded:
            continue
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
        if note.file_name in superseded:
            continue
        a = next((x for _, n, x in analyses if n == note.file_name), None)
        if a is not None:
            note.role = ("site plan" if note.file_name == site_plan else
                         "SLD" if a.sld.found else "layout" if a.rec.symbols or a.rec.circuit_tags else "other")
    sld = _merge_sld([a.sld for _, _, a in analyses])

    # ADR-0007: repeated unnamed symbols — geometry counts them, the injected namer names them.
    ai_found, ai_gaps, ai_symbols, ai_cost = ([], [], [], 0.0)
    if name_shapes is not None:
        ai_found, ai_gaps, ai_symbols, ai_cost = _name_shapes(
            [(doc, name) for doc, name, a in analyses if not a.sld.found], name_shapes,
            _item_texts(analyses))
    ai_items = {s.item for s in ai_symbols if catalogue_item(s.item)}

    findings = findings_from_recognition(DxfRecognition(), sld=sld, routes=routes)
    board_names = [b.name for b in sld.boards]
    billed_boards = list(board_names)          # grows: a board tagged on two layouts is billed once
    for doc, name, a in analyses:
        part = findings_from_recognition(a.rec, known_boards=billed_boards)
        billed_boards += a.rec.db_refs()
        part.items += _template_findings(doc, a.legend, skip=ai_items)
        stem = Path(name).stem
        part.items += [f for f in ai_found if f.sheet == stem]
        part.gaps += _legend_coverage_gaps(part, a.legend)
        for f in (*part.boards, *part.items, *part.wires):
            f.sheet = stem
        for g in part.gaps:
            g.drawing_ref = g.drawing_ref or stem
        findings.extend(part)
    findings.gaps += ai_gaps
    for old, newer in superseded.items():
        findings.gaps.append(GapItem(
            section=BQSection.DISTRIBUTION,
            description=f"{old} is an older revision of {newer} — not read, so nothing is counted twice",
            assumption=f"Priced from {newer} only.",
            suggested_action="If the older sheet shows work the newer one does not, upload it on its own.",
            severity="medium", drawing_ref=Path(old).stem,
        ))
    if routes is not None:
        findings.gaps += _route_gaps(routes, sld, Path(site_plan).stem)
    elif sld.feeders:
        findings.gaps.append(GapItem(
            section=BQSection.SUBMAIN_CABLES, description="No site plan with cable routes in this drawing set",
            assumption="Feeder lengths assumed.",
            suggested_action="Upload the electrical site plan (routes + DB tags) to measure feeders.",
            severity="high", drawing_ref="DXF set",
        ))
    boq = price_findings(findings, pipeline="dxf", project_name=project_name, run_id=run_id)

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
        ai_symbols=ai_symbols, ai_cost_zar=round(ai_cost, 2),
        routes_measured=sum(1 for fd in sld.feeders
                            if routes is not None and routes.route(fd.from_source, fd.to_db)),
        findings=findings, boq=boq, duration_s=round(time.perf_counter() - started, 3),
        success=bool(boq.line_items),
        error=None if boq.line_items else "No electrical content recognised in the drawings",
    )
    if persist:
        persist_run(run, pipeline="dxf", run_id=run_id)
    return run


ShapeNamer = Callable[[List[ShapeGroup], List[str]], Tuple[Dict[str, Tuple[str, str]], float]]
_PRICE_MAPS = {"light": "LIGHT_PRICES", "socket": "SOCKET_PRICES", "switch": "SWITCH_PRICES", "db": "DB_PRICES"}


def _item_texts(analyses) -> List[str]:
    """Every line of text on the drawings that names an electrical item: the legend reader's
    entries plus any text the legend vocabulary recognises (on Wedela the legend reader
    missed '2x24W double vapor proof LED fluorescent light' — the most-drawn fitting)."""
    from agent.shared.legend import classify_description
    found = {e.description.strip() for _, _, a in analyses for e in a.legend.entries if e.description.strip()}
    for doc, _name, _a in analyses:
        for e in doc.modelspace().query("TEXT MTEXT"):
            text = " ".join(_plain_text(e).split())
            if 6 <= len(text) <= 120 and classify_description(text):
                found.add(text)
    return sorted(found)


def _name_shapes(docs, name_shapes: ShapeNamer, legend_lines: List[str]):
    """Group every layout's loose symbols into shapes, have them named once, and turn the
    named ones into item findings per drawing: the COUNT is exact geometry, the NAME came
    from the namer — INFERRED, with a gap asking a person to confirm it."""
    from core import constants
    per_sheet: List[ShapeGroup] = []
    for doc, name in docs:
        per_sheet += find_shape_groups(doc, Path(name).stem)
    if not per_sheet:
        return [], [], [], 0.0
    unique: Dict[str, ShapeGroup] = {}
    totals: Dict[str, int] = {}
    sheets: Dict[str, List[str]] = {}
    for g in per_sheet:
        unique.setdefault(g.signature, g)
        totals[g.signature] = totals.get(g.signature, 0) + g.count
        sheets.setdefault(g.signature, []).append(g.sheet)
    reps = [ShapeGroup(signature=s, count=totals[s], sheet=", ".join(sheets[s]), size=g.size,
                       image_png_b64=g.image_png_b64) for s, g in unique.items()]
    names, cost = name_shapes(reps, legend_lines)

    symbols = [DxfAiSymbol(signature=s, item=names[s][0], named_by=names[s][1], count=totals[s],
                           sheets=sheets[s], image_png_b64=unique[s].image_png_b64)
               for s in unique if s in names]
    qty: Dict[Tuple[str, str], int] = {}
    for g in per_sheet:
        item = names.get(g.signature, ("", ""))[0]
        if catalogue_item(item):
            qty[(g.sheet, item)] = qty.get((g.sheet, item), 0) + g.count
    found: List[ItemFinding] = []
    for (sheet, item), n in sorted(qty.items()):
        cat = catalogue_item(item)
        found.append(ItemFinding(
            description=f"{item} — {sheet}", section=cat.section, item=item, qty=float(n),
            material_zar=getattr(constants, _PRICE_MAPS[cat.price_map]).get(cat.price_key, 0.0),
            install_zar=85.0, sheet=sheet, evidence=Evidence.COUNTED,
            confidence=ItemConfidence.INFERRED,
            assumption="Symbol named from the drawing's legend by AI; every copy counted exactly by geometry.",
            notes="Confirm the symbol name on the Take-off page.",
        ))
    gaps: List[GapItem] = []
    for item in sorted({i for _, i in qty}):
        n = sum(v for (s, i), v in qty.items() if i == item)
        by = {names[s][1] for s in names if names[s][0] == item}
        if by == {"person"}:
            continue
        gaps.append(GapItem(
            section=catalogue_item(item).section, description=f"{n} symbols recognised as '{item}' by AI",
            assumption="The count is exact (geometry); the name came from the AI reading the legend.",
            suggested_action="Check the picture on the Take-off page and correct the name if it is wrong.",
            severity="low", drawing_ref="AI symbol naming",
        ))
    return found, gaps, symbols, cost


def _route_gaps(routes: RouteNetwork, sld: SldFacts, sheet: str) -> List[GapItem]:
    """What the site plan says that the SLDs don't — never silent."""
    gaps: List[GapItem] = []
    for w in routes.warnings:
        gaps.append(GapItem(section=BQSection.SUBMAIN_CABLES, description=w,
                                assumption="Route attribution as read.", severity="medium",
                                suggested_action="Check the site plan.", drawing_ref=sheet))
    sld_source = {equipment_key(fd.to_db): equipment_key(fd.from_source) for fd in sld.feeders}
    for to, frm in sorted(routes.fed_from.items()):
        if to in sld_source and sld_source[to] != frm:
            gaps.append(GapItem(
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
                gaps.append(GapItem(
                    section=BQSection.SUBMAIN_CABLES, building_block=routes.names.get(to, to),
                    description=(f"Route {routes.names.get(frm, frm)}→{routes.names.get(to, to)} "
                                 f"measured {r.length_m:.0f} m on the site plan, but no SLD gives its cable"),
                    assumption="Not priced.", severity="high", drawing_ref=sheet,
                    suggested_action="Upload the SLD for this board so the cable can be priced.",
                ))
    return gaps


_SECTION_MATERIAL = {
    BQSection.LIGHTING: 280.0, BQSection.POWER_OUTLETS: 160.0,
    BQSection.DATA_COMMS: 450.0, BQSection.FIRE_SAFETY: 850.0,
    BQSection.DISTRIBUTION: 4500.0, BQSection.SOLAR_PV: 2800.0,
    BQSection.FINAL_CABLES: 200.0,
}


def _template_findings(doc, legend: Legend, skip=frozenset()) -> List[ItemFinding]:
    """
    An item for each legend symbol counted by template matching (mode 3). INFERRED —
    the COUNT is deterministic geometry, the rate is a ballpark for the contractor to
    confirm. Once billed, these items drop out of the legend coverage gaps automatically.
    """
    counts = {k: v for k, v in count_by_template(doc, legend).items() if k not in skip}
    section_of = {e.canonical_item: e.section for e in legend.entries}
    out: List[ItemFinding] = []
    for item, n in sorted(counts.items()):
        section = section_of.get(item, BQSection.FINAL_CABLES)
        out.append(ItemFinding(
            description=f"{item} (template-matched)", section=section, qty=float(n),
            material_zar=_SECTION_MATERIAL.get(section, 200.0), install_zar=85.0,
            sheet="DXF template", evidence=Evidence.COUNTED, confidence=ItemConfidence.INFERRED,
            notes="Counted by legend-glyph template matching — verify count & rate.",
        ))
    return out


def _legend_coverage_gaps(findings: Findings, legend: Legend) -> List[GapItem]:
    """
    A gap for every legend item not present in a priced line — turning a silent miss
    (e.g. exploded-line-work downlights) into a visible 'declared but not counted'.
    Uses the shared LDSE coverage helper on the lines these findings price to.
    """
    lines = price_findings(Findings(boards=findings.boards, feeders=findings.feeders,
                                    items=findings.items, wires=findings.wires), pipeline="dxf").line_items
    return coverage_gaps(legend, billed_canonical_items(l.description for l in lines))
