"""
v2 orchestrator — runs Passes 1–3 (LLM eyes) and merges into PdfFacts.

Given classified pages, route each to its pass tool, call the vision LLM with
the pass prompt, and merge the validated tool output into a single PdfFacts.
Passes 4–5 (deterministic) then run via passes.assemble.build_boq_from_facts.

Merging across pages is order-independent accumulation (extend lists, keep the
first non-empty scalar) so a multi-sheet SLD or multi-sheet layout collapses
into one coherent fact set.
"""

from __future__ import annotations

import logging
import re
from collections import Counter
from typing import Dict, List, Optional, Tuple

from pydantic import BaseModel, ConfigDict

from agent.pdf_pipeline.llm import LLMError, PdfLLM
from agent.pdf_pipeline.models import PageClassification, PageType, StageCost
from agent.pdf_pipeline.passes.assemble import build_boq_from_facts
from agent.pdf_pipeline.passes.facts import (
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
from core.config import OPUS_4_6, SONNET_4_5

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


def extract_facts(
    llm: PdfLLM,
    pages: List[IngestedPage],
    classifications: List[PageClassification],
) -> Tuple[PdfFacts, List[StageCost]]:
    """Run Passes 1–3 across the classified pages → merged PdfFacts."""
    facts = PdfFacts()
    costs: List[StageCost] = []
    by_index: Dict[int, IngestedPage] = {p.page_index: p for p in pages}

    for cls in classifications:
        page = by_index.get(cls.page_index)
        if page is None or cls.page_type == PageType.UNKNOWN:
            continue
        tool = TOOL_FOR_SHEET_TYPE.get(cls.page_type.value)
        if tool is None:
            continue
        prompt = PROMPT_BY_PASS_TOOL[tool["name"]]
        validator = VALIDATOR_BY_TOOL.get(tool["name"])

        # The power-spine pass gets DB panel ratings wrong in a way that's
        # too costly to trust from a single sample (confirmed via repeated
        # real test runs: the same SLD page read 4 times gave 4 different
        # totals). Every other pass has been reliable single-shot, so only
        # this one pays the 3x-sampling cost.
        if cls.page_type == PageType.SLD:
            try:
                spine, gaps, call_costs = _extract_power_spine_voted(
                    llm, page, cls.page_index, prompt, tool, validator,
                )
            except LLMError as e:
                log.error("Power-spine extraction failed on page %d: %s", cls.page_index, e)
                facts.takeoff.warnings.append(f"p{cls.page_index} {tool['name']}: {e}")
                continue
            costs.extend(call_costs)
            _merge_spine(facts.spine, spine)
            facts.extraction_gaps.extend(gaps)
            continue

        try:
            result = llm.call_with_tool(
                model=SONNET_4_5,
                user_text=prompt,
                page_image_b64=page.image_b64,
                tools=[tool],
                forced_tool_name=tool["name"],
                stage_name=f"pass:{tool['name']}:p{cls.page_index}",
                max_tokens=4096,
                validator=validator,
                escalate_to=OPUS_4_6,
                temperature=0.0,
            )
        except LLMError as e:
            log.error("Pass extraction failed on page %d: %s", cls.page_index, e)
            facts.takeoff.warnings.append(f"p{cls.page_index} {tool['name']}: {e}")
            continue

        costs.append(result.cost)
        _merge(facts, tool["name"], result.tool_input)

    facts.extraction_gaps.extend(_check_spine_orphans(facts.spine))
    facts.extraction_gaps.extend(_check_source_alignment(facts.spine))
    return facts, costs


# ─── merge helpers (order-independent accumulation) ─────────────────────

def _merge(facts: PdfFacts, tool_name: str, tool_input: dict) -> None:
    if tool_name == "read_project_context":
        _merge_context(facts.context, parse_project_context(tool_input))
    elif tool_name == "read_power_spine":
        _merge_spine(facts.spine, parse_power_spine(tool_input))
    elif tool_name == "read_layout_takeoff":
        _merge_takeoff(facts.takeoff, parse_layout_takeoff(tool_input))


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


def _merge_spine(dst: PowerSpine, src: PowerSpine) -> None:
    dst.distribution_boards.extend(src.distribution_boards)
    dst.feeders.extend(src.feeders)
    # keep the richest incoming supply seen
    if src.incoming_supply.kiosk_present or src.incoming_supply.meter_count or \
       src.incoming_supply.supply_source != "unknown":
        if dst.incoming_supply.supply_source == "unknown":
            dst.incoming_supply = src.incoming_supply
    dst.warnings.extend(src.warnings)


def _merge_takeoff(dst: LayoutTakeoff, src: LayoutTakeoff) -> None:
    dst.rooms.extend(src.rooms)
    dst.legend.update(src.legend)
    dst.warnings.extend(src.warnings)


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
    samples: List[PowerSpine] = []
    costs: List[StageCost] = []
    for i in range(_SPINE_VOTE_SAMPLES):
        result = llm.call_with_tool(
            model=SONNET_4_5,
            user_text=prompt,
            page_image_b64=page.image_b64,
            tools=[tool],
            forced_tool_name=tool["name"],
            stage_name=f"pass:{tool['name']}:p{page_index}:sample{i}",
            max_tokens=4096,
            validator=validator,
            escalate_to=OPUS_4_6,
            temperature=_SPINE_VOTE_TEMPERATURE,
        )
        costs.append(result.cost)
        samples.append(parse_power_spine(result.tool_input))

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
) -> BillOfQuantities:
    """Thin wrapper around the deterministic assembler."""
    return build_boq_from_facts(
        facts, project_name=project_name, run_id=run_id, contractor=contractor,
    )
