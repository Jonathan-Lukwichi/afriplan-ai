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
from typing import Dict, List, Optional, Tuple

from agent.pdf_pipeline.llm import LLMError, PdfLLM
from agent.pdf_pipeline.models import PageClassification, PageType, StageCost
from agent.pdf_pipeline.passes.assemble import build_boq_from_facts
from agent.pdf_pipeline.passes.facts import (
    LayoutTakeoff,
    PdfFacts,
    PowerSpine,
    ProjectContext,
    parse_layout_takeoff,
    parse_power_spine,
    parse_project_context,
)
from agent.pdf_pipeline.prompts.pass_prompts import PROMPT_BY_PASS_TOOL
from agent.pdf_pipeline.prompts.pass_schemas import TOOL_FOR_SHEET_TYPE
from agent.pdf_pipeline.stages.ingest import IngestedPage
from agent.shared import BillOfQuantities, ContractorProfile
from core.config import OPUS_4_6, SONNET_4_5

log = logging.getLogger(__name__)


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

        try:
            result = llm.call_with_tool(
                model=SONNET_4_5,
                user_text=prompt,
                page_image_b64=page.image_b64,
                tools=[tool],
                forced_tool_name=tool["name"],
                stage_name=f"pass:{tool['name']}:p{cls.page_index}",
                max_tokens=4096,
                escalate_to=OPUS_4_6,
            )
        except LLMError as e:
            log.error("Pass extraction failed on page %d: %s", cls.page_index, e)
            facts.takeoff.warnings.append(f"p{cls.page_index} {tool['name']}: {e}")
            continue

        costs.append(result.cost)
        _merge(facts, tool["name"], result.tool_input)

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
