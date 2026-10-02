"""
v2 orchestrator — runs Passes 1–3 (LLM eyes) and merges into PdfFacts.

Given classified pages, route each to its pass tool, call the vision LLM with
the pass prompt, and merge the validated tool output into a single PdfFacts.
Passes 4–5 (deterministic) then run via passes.assemble.build_boq_from_facts.

Merging across pages collapses a multi-sheet SLD or layout into one coherent
fact set: a board, feeder or room read on two sheets is ONE item (matched by
name, spacing/hyphens ignored), the fuller reading wins, and every disagreement
between sheets becomes a gap (issue 011).
"""

from __future__ import annotations

import logging
import re
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from pydantic import BaseModel, ConfigDict

from agent.pdf_pipeline.llm import LLMError, PdfLLM
from agent.pdf_pipeline.models import PageClassification, PageType, StageCost
from agent.pdf_pipeline.passes.assemble import build_boq_from_facts
from agent.pdf_pipeline.passes.facts import (
    _ROOM_INT_FIELDS,
    Feeder,
    LayoutTakeoff,
    PdfFacts,
    PowerSpine,
    ProjectContext,
    SpineDB,
    parse_layout_takeoff,
    parse_power_spine,
    parse_project_context,
)
from agent.pdf_pipeline.prompts.pass_prompts import PROMPT_BY_PASS_TOOL
from agent.pdf_pipeline.prompts.pass_schemas import TOOL_FOR_SHEET_TYPE
from agent.pdf_pipeline.stages.ingest import IngestedPage
from agent.shared import BillOfQuantities, BQSection, ContractorProfile, GapItem
from agent.shared.routes import equipment_key
from core.config import ESCALATE_MODEL, EXTRACT_MODEL, PDF_PARALLEL_PAGES

log = logging.getLogger(__name__)


# ─── Lightweight raw-input validators ─────────────────────────────────
#
# Thin, deliberately permissive Pydantic models that check only the fields
# each tool schema actually marks "required" — enough to make the existing
# retry-with-feedback / escalate-to-Opus path in PdfLLM.call_with_tool
# actually fire (previously dead code: no validator was ever passed, so
# schema validation never ran and Opus escalation never triggered except
# when the model failed to call the tool at all).

class _RawSpineDB(BaseModel):
    model_config = ConfigDict(extra="allow")
    name: str
    circuits: list
    confidence: float


class _RawFeeder(BaseModel):
    model_config = ConfigDict(extra="allow")
    from_source: str
    to_db: str
    length_annotated: bool


class _RawPowerSpineInput(BaseModel):
    model_config = ConfigDict(extra="allow")
    distribution_boards: List[_RawSpineDB]
    feeders: List[_RawFeeder]


class _RawTakeoffRoom(BaseModel):
    model_config = ConfigDict(extra="allow")
    room_name: str
    confidence: float


class _RawLayoutTakeoffInput(BaseModel):
    model_config = ConfigDict(extra="allow")
    rooms: List[_RawTakeoffRoom]


class _RawProjectContextInput(BaseModel):
    model_config = ConfigDict(extra="allow")
    # Nothing is required in READ_PROJECT_CONTEXT_TOOL's schema — this pass
    # is low-stakes context, not billable facts, so there is no meaningful
    # validation to add beyond "did the tool get called" (already checked).


VALIDATOR_BY_TOOL: Dict[str, type[BaseModel]] = {
    "read_project_context": _RawProjectContextInput,
    "read_power_spine": _RawPowerSpineInput,
    "read_layout_takeoff": _RawLayoutTakeoffInput,
}


@dataclass
class _PageOutcome:
    """What one page produced — read in parallel, merged afterwards in page order."""
    tool_name: str = ""
    tool_input: Optional[dict] = None
    spine: Optional[PowerSpine] = None
    gaps: List[GapItem] = field(default_factory=list)
    costs: List[StageCost] = field(default_factory=list)
    error: str = ""


def _read_page(llm: PdfLLM, cls: PageClassification, page: IngestedPage, tool: dict) -> _PageOutcome:
    prompt = PROMPT_BY_PASS_TOOL[tool["name"]]
    validator = VALIDATOR_BY_TOOL.get(tool["name"])
    try:
        # The power-spine pass gets DB panel ratings wrong in a way that's
        # too costly to trust from a single sample (confirmed via repeated
        # real test runs: the same SLD page read 4 times gave 4 different
        # totals). Every other pass has been reliable single-shot, so only
        # this one pays the 3x-sampling cost.
        if cls.page_type == PageType.SLD:
            spine, gaps, costs = _extract_power_spine_voted(llm, page, cls.page_index, prompt, tool, validator)
            return _PageOutcome(tool_name=tool["name"], spine=spine, gaps=gaps, costs=costs)
        result = llm.call_with_tool(
            model=EXTRACT_MODEL,
            user_text=prompt,
            page_image_b64=page.image_b64,
            tools=[tool],
            forced_tool_name=tool["name"],
            stage_name=f"pass:{tool['name']}:p{cls.page_index}",
            max_tokens=4096,
            validator=validator,
            escalate_to=ESCALATE_MODEL,
            temperature=0.0,
        )
        return _PageOutcome(tool_name=tool["name"], tool_input=result.tool_input, costs=[result.cost])
    except LLMError as e:
        log.error("Pass extraction failed on page %d: %s", cls.page_index, e)
        return _PageOutcome(tool_name=tool["name"], error=f"p{cls.page_index} {tool['name']}: {e}")


def extract_facts(
    llm: PdfLLM,
    pages: List[IngestedPage],
    classifications: List[PageClassification],
) -> Tuple[PdfFacts, List[StageCost]]:
    """Run Passes 1–3 across the classified pages → merged PdfFacts.

    Pages are read in parallel (PDF_PARALLEL_PAGES requests in flight) — the
    wall-clock of a run is then set by the slowest page, not the sum of all
    pages — and merged afterwards in page order, so the result is the same as a
    one-by-one run."""
    facts = PdfFacts()
    costs: List[StageCost] = []
    by_index: Dict[int, IngestedPage] = {p.page_index: p for p in pages}

    jobs = []
    for cls in classifications:
        page = by_index.get(cls.page_index)
        if page is None or cls.page_type == PageType.UNKNOWN:
            continue
        tool = TOOL_FOR_SHEET_TYPE.get(cls.page_type.value)
        if tool is not None:
            jobs.append((cls, page, tool))

    with ThreadPoolExecutor(max_workers=PDF_PARALLEL_PAGES) as pool:
        outcomes = list(pool.map(lambda j: _read_page(llm, *j), jobs))

    for (cls, _page, _tool), out in zip(jobs, outcomes):
        costs.extend(out.costs)
        if out.error:
            facts.takeoff.warnings.append(out.error)
        elif out.spine is not None:
            _merge_spine(facts.spine, out.spine, page=cls.page_index, gaps=facts.extraction_gaps)
            facts.extraction_gaps.extend(out.gaps)
        else:
            _merge(facts, out.tool_name, out.tool_input, page=cls.page_index)

    facts.extraction_gaps.extend(_site_lighting_gaps(facts.takeoff))
    facts.extraction_gaps.extend(_check_spine_orphans(facts.spine))
    facts.extraction_gaps.extend(_check_source_alignment(facts.spine))
    return facts, costs


# ─── merge helpers (order-independent accumulation) ─────────────────────

def _merge(facts: PdfFacts, tool_name: str, tool_input: dict, page: int = -1) -> None:
    if tool_name == "read_project_context":
        _merge_context(facts.context, parse_project_context(tool_input))
    elif tool_name == "read_power_spine":
        _merge_spine(facts.spine, parse_power_spine(tool_input), page=page, gaps=facts.extraction_gaps)
    elif tool_name == "read_layout_takeoff":
        _merge_takeoff(facts.takeoff, parse_layout_takeoff(tool_input), page=page, gaps=facts.extraction_gaps)


def _first(a: str, b: str) -> str:
    return a or b


def _merge_context(dst: ProjectContext, src: ProjectContext) -> None:
    dst.project_name = _first(dst.project_name, src.project_name)
    dst.client_name = _first(dst.client_name, src.client_name)
    dst.consultant_name = _first(dst.consultant_name, src.consultant_name)
    dst.contractor_name = _first(dst.contractor_name, src.contractor_name)
    dst.site_address = _first(dst.site_address, src.site_address)
    dst.standard = _first(dst.standard, src.standard)
    dst.revision = _first(dst.revision, src.revision)
    for x in src.drawing_numbers:
        if x not in dst.drawing_numbers:
            dst.drawing_numbers.append(x)
    for x in src.buildings:
        if x not in dst.buildings:
            dst.buildings.append(x)
    for x in src.free_issue_items:
        if x not in dst.free_issue_items:
            dst.free_issue_items.append(x)
    dst.drawing_index.extend(src.drawing_index)
    dst.legend.update(src.legend)
    dst.notes.extend(src.notes)


#  Issue 011: a board, feeder or room drawn on two sheets (an SLD page and a
#  schedule, a lighting plan and a plug plan) is ONE item. Merge by name — the
#  shared equipment_key ignores spacing/hyphens, so 'DB-1' and 'DB1' meet — and
#  record every disagreement as a gap instead of silently picking a value.

def _conflict(gaps: Optional[List[GapItem]], section: BQSection, block: str, what: str,
              a, pa: str, b, pb: str, kept) -> None:
    if gaps is None:
        return
    gaps.append(GapItem(
        section=section, building_block=block,
        description=f"{block}: {what} reads {a} on {pa} but {b} on {pb}",
        assumption=f"Used {kept}.",
        suggested_action="Check both sheets; correct the bill if the other value is right.",
        severity="medium", drawing_ref=f"{pa}, {pb}",
    ))


def _pg(pages: List[int]) -> str:
    return ", ".join(f"p{p}" for p in pages if p >= 0) or "another sheet"


def _merge_spine(dst: PowerSpine, src: PowerSpine, page: int = -1,
                 gaps: Optional[List[GapItem]] = None) -> None:
    by_key = {equipment_key(d.name): d for d in dst.distribution_boards if d.name}
    pages = dst._pages                                       # key → sheets it was read on
    for db in src.distribution_boards:
        k = equipment_key(db.name)
        old = by_key.get(k) if k else None
        if old is None:
            dst.distribution_boards.append(db)
            if k:
                by_key[k] = db
                pages[("db", k)] = [page]
            continue
        seen = _pg(pages.get(("db", k), []))
        for field in ("main_breaker_a", "phases", "ka_rating"):
            a, b = getattr(old, field), getattr(db, field)
            if a and b and a != b:
                _conflict(gaps, BQSection.DISTRIBUTION, old.name, field.replace("_", " "),
                          a, seen, b, _pg([page]), a)
            elif not a and b:
                setattr(old, field, b)
        if len(db.circuits) > len(old.circuits):             # the fuller reading of the board wins
            old.circuits = db.circuits
        for field in ("elcb_present", "surge_protection"):
            setattr(old, field, getattr(old, field) or getattr(db, field))
        old.location = old.location or db.location
        old.source_snippet = old.source_snippet or db.source_snippet
        old.confidence = max(old.confidence, db.confidence)
        pages[("db", k)].append(page)

    by_run = {(equipment_key(f.from_source), equipment_key(f.to_db)): f for f in dst.feeders}
    for fd in src.feeders:
        k = (equipment_key(fd.from_source), equipment_key(fd.to_db))
        old = by_run.get(k)
        if old is None:
            dst.feeders.append(fd)
            by_run[k] = fd
            pages[("feeder", k)] = [page]
            continue
        label = f"{old.from_source}→{old.to_db}"
        if old.cable_size_mm2 and fd.cable_size_mm2 and old.cable_size_mm2 != fd.cable_size_mm2:
            _conflict(gaps, BQSection.SUBMAIN_CABLES, label, "cable size (mm²)", f"{old.cable_size_mm2:g}",
                      _pg(pages.get(("feeder", k), [])), f"{fd.cable_size_mm2:g}", _pg([page]),
                      f"{old.cable_size_mm2:g} mm²")
        elif not old.cable_size_mm2:
            old.cable_size_mm2 = fd.cable_size_mm2
        if fd.length_annotated and not old.length_annotated:  # a written length beats none
            old.length_m, old.length_annotated = fd.length_m, True
        old.earth_size_mm2 = old.earth_size_mm2 or fd.earth_size_mm2
        old.confidence = max(old.confidence, fd.confidence)
        pages[("feeder", k)].append(page)

    # keep the richest incoming supply seen
    if src.incoming_supply.kiosk_present or src.incoming_supply.meter_count or \
       src.incoming_supply.supply_source != "unknown":
        if dst.incoming_supply.supply_source == "unknown":
            dst.incoming_supply = src.incoming_supply
    dst.warnings.extend(src.warnings)


_ROOM_COUNTS = _ROOM_INT_FIELDS                 # every count box on the form
_SITE_LIGHTS = ("pole_lights", "solar_post_lights", "high_mast_poles")
_LIGHT_COUNTS = ("downlights", "panel_lights", "bulkheads", "vapour_proof", "floodlights",
                 "emergency_lights", "fluorescent_battens", "prismatic_lights", *_SITE_LIGHTS)


def _room_key(r) -> Tuple[str, str]:
    return equipment_key(r.served_by_db) if r.served_by_db else "", " ".join(r.room_name.lower().split())


def _merge_takeoff(dst: LayoutTakeoff, src: LayoutTakeoff, page: int = -1,
                   gaps: Optional[List[GapItem]] = None) -> None:
    """A room already read on ANOTHER sheet is the same room: counts merge field by
    field, taking the higher reading (a lighting sheet shows 0 sockets, a plug sheet
    0 lights) and flagging real disagreements. Same-named rooms on one sheet stay apart."""
    for room in src.rooms:
        k = _room_key(room)
        old = next((r for r in dst.rooms if room.room_name and _room_key(r) == k
                    and page not in r.source_pages), None)
        if old is None:
            room.source_pages = [page]
            dst.rooms.append(room)
            continue
        for field in _ROOM_COUNTS:
            a, b = getattr(old, field), getattr(room, field)
            if a and b and a != b:
                _conflict(gaps, BQSection.LIGHTING if field in _LIGHT_COUNTS else BQSection.POWER_OUTLETS,
                          old.room_name, field.replace("_", " "), a, _pg(old.source_pages), b, _pg([page]),
                          f"the higher count, {max(a, b)}")
            setattr(old, field, max(a, b))
        old.served_by_db = old.served_by_db or room.served_by_db
        old.area_m2 = old.area_m2 or room.area_m2
        old.circuit_tags += [t for t in room.circuit_tags if t not in old.circuit_tags]
        old.confidence = max(old.confidence, room.confidence)
        old.counts_from_legend_schedule = old.counts_from_legend_schedule or room.counts_from_legend_schedule
        old.source_pages.append(page)
    dst.legend.update(src.legend)
    dst.warnings.extend(src.warnings)


def _site_lighting_gaps(takeoff: LayoutTakeoff) -> List[GapItem]:
    """Site lighting found on more than one sheet: the same poles are often drawn on the
    site plan AND each building's layout. Names differ, so it can't be merged — say so."""
    per_page: Dict[int, int] = {}
    for r in takeoff.rooms:
        n = sum(getattr(r, f) for f in _SITE_LIGHTS)
        if n:
            for p in r.source_pages or [-1]:
                per_page[p] = per_page.get(p, 0) + n
    if len(per_page) < 2:
        return []
    detail = ", ".join(f"{n} on p{p}" if p >= 0 else f"{n} on an unknown sheet" for p, n in sorted(per_page.items()))
    return [GapItem(
        section=BQSection.LIGHTING, building_block="Site lighting",
        description=f"Site lighting read on {len(per_page)} sheets ({detail}) — the same poles may be counted twice",
        assumption="All counts billed as read.",
        suggested_action="Compare the sheets; remove poles that appear on more than one.",
        severity="medium", drawing_ref=_pg(sorted(per_page)),
    )]


# ─── Self-consistency voting for the power-spine pass ────────────────
#
# One SLD page is sampled 3 times independently (moderate temperature, so
# the samples can actually disagree) and merged deterministically:
#   - a DB name found in >=2 of 3 samples wins by majority; its numeric
#     fields (main_breaker_a, phases, voltage_v) are each separately
#     majority-voted, since a board's identity being stable doesn't mean
#     every field on it was read the same way every time
#   - a DB found in only 1 of 3 samples is still kept (dropping it would
#     make the exact "board silently vanishes" problem worse, not better)
#     but flagged as low-confidence
#   - any field with no majority (3-way disagreement) keeps the
#     highest-confidence sample's value and gets flagged
# This directly targets what the real test runs showed: some fields are
# *stably* wrong (no amount of re-sampling fixes them — see the alignment
# check in assemble.py instead) while others are *randomly* wrong from one
# call to the next, which is exactly what voting is for.

_SPINE_VOTE_SAMPLES = 3
_SPINE_VOTE_TEMPERATURE = 0.5
_VOTED_DB_FIELDS = ("main_breaker_a", "phases", "voltage_v")


def _normalise_db_name(name: str) -> str:
    return re.sub(r"\s+", "", name).strip().upper()


def _extract_power_spine_voted(
    llm: PdfLLM,
    page: IngestedPage,
    page_index: int,
    prompt: str,
    tool: dict,
    validator: Optional[type[BaseModel]],
) -> Tuple[PowerSpine, List[GapItem], List[StageCost]]:
    def sample(i: int):
        try:
            return llm.call_with_tool(
                model=EXTRACT_MODEL,
                user_text=prompt,
                page_image_b64=page.image_b64,
                tools=[tool],
                forced_tool_name=tool["name"],
                stage_name=f"pass:{tool['name']}:p{page_index}:sample{i}",
                max_tokens=4096,
                validator=validator,
                escalate_to=ESCALATE_MODEL,
                temperature=_SPINE_VOTE_TEMPERATURE,   # ignored by models that reject it
            )
        except LLMError as e:                          # vote with the samples that arrived
            log.warning("Power-spine sample %d on page %d failed: %s", i, page_index, e)
            return None

    with ThreadPoolExecutor(max_workers=_SPINE_VOTE_SAMPLES) as pool:
        results = [r for r in pool.map(sample, range(_SPINE_VOTE_SAMPLES)) if r is not None]
    if not results:
        raise LLMError(f"every power-spine sample failed on page {page_index}")
    costs: List[StageCost] = [r.cost for r in results]
    samples: List[PowerSpine] = [parse_power_spine(r.tool_input) for r in results]

    merged, gaps = _vote_spine(samples, page_index)
    return merged, gaps, costs


def _vote_spine(samples: List[PowerSpine], page_index: int) -> Tuple[PowerSpine, List[GapItem]]:
    gaps: List[GapItem] = []

    # Group each sample's DB entries by normalised name.
    by_name: Dict[str, List[SpineDB]] = {}
    for spine in samples:
        seen_this_sample = set()
        for db in spine.distribution_boards:
            key = _normalise_db_name(db.name)
            if not key or key in seen_this_sample:
                continue  # ignore blank names / a page re-listing the same board twice in one sample
            seen_this_sample.add(key)
            by_name.setdefault(key, []).append(db)

    voted_dbs: List[SpineDB] = []
    for key, votes in by_name.items():
        best = max(votes, key=lambda d: d.confidence)
        if len(votes) < _SPINE_VOTE_SAMPLES:
            gaps.append(GapItem(
                section=BQSection.DISTRIBUTION, severity="medium",
                description=f"Distribution board '{best.name}' was only found in {len(votes)} of "
                            f"{_SPINE_VOTE_SAMPLES} independent reads of this drawing.",
                assumption=f"Included using the reading with the highest reported confidence ({best.name}).",
                suggested_action="Confirm this board actually appears on the drawing before pricing.",
                drawing_ref=f"p{page_index}",
            ))
        merged_fields = {}
        for field_name in _VOTED_DB_FIELDS:
            values = [getattr(v, field_name) for v in votes]
            counts = Counter(values)
            top_value, top_count = counts.most_common(1)[0]
            tied = sum(1 for _, c in counts.items() if c == top_count) > 1
            if tied and len(set(values)) > 1:
                merged_fields[field_name] = getattr(best, field_name)
                gaps.append(GapItem(
                    section=BQSection.DISTRIBUTION, severity="high",
                    description=f"'{best.name}' {field_name.replace('_', ' ')}: independent reads "
                                f"disagreed ({', '.join(str(v) for v in values)}).",
                    assumption=f"Used the highest-confidence reading: {getattr(best, field_name)}.",
                    suggested_action="Verify this rating against the drawing or on site before pricing.",
                    drawing_ref=f"p{page_index}",
                ))
            else:
                merged_fields[field_name] = top_value
        voted = best.model_copy(update=merged_fields)
        voted_dbs.append(voted)

    # Feeders: dedupe identical (from, to) pairs across the 3 samples,
    # preferring whichever sample actually had an annotated length/size —
    # the earlier bug where the same physical cable produced both a real
    # entry and a zero-size phantom is exactly what this collapses.
    feeders_by_pair: Dict[Tuple[str, str], Feeder] = {}
    for spine in samples:
        for fd in spine.feeders:
            pair = (_normalise_db_name(fd.from_source), _normalise_db_name(fd.to_db))
            if pair == ("", ""):
                continue
            existing = feeders_by_pair.get(pair)
            if existing is None or _feeder_richness(fd) > _feeder_richness(existing):
                feeders_by_pair[pair] = fd

    incoming = max(samples, key=lambda s: s.incoming_supply.meter_count or s.incoming_supply.kiosk_present).incoming_supply
    warnings = [w for s in samples for w in s.warnings]

    merged_spine = PowerSpine(
        distribution_boards=voted_dbs,
        feeders=list(feeders_by_pair.values()),
        incoming_supply=incoming,
        warnings=warnings,
    )
    return merged_spine, gaps


def _feeder_richness(fd: Feeder) -> Tuple[bool, float]:
    """Prefer a feeder reading that actually has real data over a blank one."""
    return (fd.length_annotated, fd.cable_size_mm2)


# ─── Deterministic cross-reference check ──────────────────────────────
#
# A DB name that shows up as a feeder endpoint but never got its own panel
# line item is exactly the bug confirmed 4/4 times on a real drawing set:
# two independent extraction passes (or, after voting, two independent
# concepts within one pass) disagreeing about which boards exist. This is
# plain Python, no LLM call, and it runs once against the fully merged
# spine (all pages), not per-page — a board can legitimately be named on
# one page and itemized on another.

_DB_NAME_RE = re.compile(r"^DB[\s\-]?\S", re.IGNORECASE)


def _check_spine_orphans(spine: PowerSpine) -> List[GapItem]:
    listed = {_normalise_db_name(db.name) for db in spine.distribution_boards}
    referenced: Dict[str, str] = {}  # normalised -> original spelling, first seen
    for fd in spine.feeders:
        for raw in (fd.from_source, fd.to_db):
            if raw and _DB_NAME_RE.match(raw.strip()):
                referenced.setdefault(_normalise_db_name(raw), raw.strip())

    gaps: List[GapItem] = []
    for key, original in referenced.items():
        if key in listed:
            continue
        gaps.append(GapItem(
            section=BQSection.DISTRIBUTION, severity="high",
            description=f"'{original}' is referenced as a feeder source/destination but was "
                        f"never itemized as its own distribution board.",
            assumption="Not priced — no panel line item exists for this board.",
            suggested_action=f"Check the SLD for '{original}''s own panel schedule and add it to "
                              f"the bill before pricing; this is very likely a real board that was missed.",
            drawing_ref="SLD",
        ))
    return gaps


# ─── Deterministic source-alignment check ─────────────────────────────
#
# The model is asked (READ_POWER_SPINE_PROMPT) to quote the exact busbar
# header it read a board's rating from. This confirmed our real
# 400A-vs-100A bug: the true header reads "400V, 100A", and a model that
# reports main_breaker_a=400 while quoting that exact text fails this check
# immediately, with no ambiguity — a free (no extra LLM call), deterministic
# net for the one misread we could concretely reproduce.

_AMP_TOKEN_RE = re.compile(r"(\d+)\s*A\b", re.IGNORECASE)


def _check_source_alignment(spine: PowerSpine) -> List[GapItem]:
    gaps: List[GapItem] = []
    for db in spine.distribution_boards:
        if not db.source_snippet or not db.main_breaker_a:
            continue  # nothing to cross-check
        amp_tokens = {int(m.group(1)) for m in _AMP_TOKEN_RE.finditer(db.source_snippet)}
        if amp_tokens and db.main_breaker_a not in amp_tokens:
            gaps.append(GapItem(
                section=BQSection.DISTRIBUTION, severity="high",
                description=f"'{db.name}' main breaker was read as {db.main_breaker_a}A, but that "
                            f"number doesn't appear as an amperage in the quoted source text "
                            f"('{db.source_snippet}') — possible misread (e.g. the voltage figure).",
                assumption=f"Kept the reported value ({db.main_breaker_a}A) but flagging the mismatch.",
                suggested_action="Verify this board's main breaker rating directly against the drawing.",
                drawing_ref="SLD",
            ))
    return gaps


# ─── convenience: facts → priced bill ───────────────────────────────────

def build_bill(
    facts: PdfFacts,
    *,
    project_name: str = "",
    run_id: str = "",
    contractor: Optional[ContractorProfile] = None,
    routes=None,
) -> BillOfQuantities:
    """Thin wrapper around the deterministic assembler (`routes`: a measured site plan)."""
    return build_boq_from_facts(
        facts, project_name=project_name, run_id=run_id, contractor=contractor, routes=routes,
    )
