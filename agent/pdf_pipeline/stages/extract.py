"""
Stage P3 — Extract.

For every classified page, route to the right tool schema and call
Sonnet 4.5 with retry-with-error-feedback. Escalate to Opus 4.6 if
Sonnet fails twice in a row. Aggregate results into a single
PdfExtraction.
"""

from __future__ import annotations

import logging
from typing import Dict, List, Tuple

from agent.pdf_pipeline.llm import LLMError, PdfLLM
from agent.pdf_pipeline.models import (
    CircuitRow,
    CircuitSchedule,
    DistributionBoard,
    FixtureCounts,
    PageClassification,
    PageType,
    PdfExtraction,
    StageCost,
)
from agent.pdf_pipeline.prompts.page_prompts import PROMPT_BY_PAGE_TYPE
from agent.pdf_pipeline.prompts.tool_schemas import TOOLS_BY_PAGE_TYPE
from agent.pdf_pipeline.stages.ingest import IngestedPage
from agent.shared import ProjectMetadata
from core.config import OPUS_4_6, SONNET_4_5

log = logging.getLogger(__name__)


def extract(
    llm: PdfLLM,
    pages: List[IngestedPage],
    classifications: List[PageClassification],
) -> Tuple[PdfExtraction, List[StageCost]]:
    """
    Walk every classified page and accumulate extracted shapes into a
    single PdfExtraction object. Returns (extraction, per-page costs).
    """
    extraction = PdfExtraction(pages_processed=classifications)
    costs: List[StageCost] = []

    by_index: Dict[int, IngestedPage] = {p.page_index: p for p in pages}

    for cls in classifications:
        page = by_index.get(cls.page_index)
        if page is None:
            continue
        if cls.page_type == PageType.UNKNOWN:
            extraction.extraction_warnings.append(
                f"Page {cls.page_index} classified as UNKNOWN — skipped extraction"
            )
            continue

        tool_schema = TOOLS_BY_PAGE_TYPE.get(cls.page_type.value)
        prompt = PROMPT_BY_PAGE_TYPE.get(cls.page_type.value)
        if tool_schema is None or prompt is None:
            continue

        try:
            result = llm.call_with_tool(
                model=SONNET_4_5,
                user_text=prompt,
                page_image_b64=page.image_b64,
                tools=[tool_schema],
                forced_tool_name=tool_schema["name"],
                stage_name=f"extract:{cls.page_type.value}:p{cls.page_index}",
                max_tokens=4096,
                escalate_to=OPUS_4_6,
            )
        except LLMError as e:
            log.error("Extraction failed on page %d: %s", cls.page_index, e)
            extraction.extraction_warnings.append(
                f"Page {cls.page_index} ({cls.page_type.value}): {e}"
            )
            continue

        costs.append(result.cost)
        _merge_into_extraction(
            extraction=extraction,
            page_type=cls.page_type,
            tool_input=result.tool_input,
            page_index=cls.page_index,
        )

    return extraction, costs


# ─── Per-tool merge helpers ───────────────────────────────────────────

def _merge_into_extraction(
    *,
    extraction: PdfExtraction,
    page_type: PageType,
    tool_input: dict,
    page_index: int,
) -> None:
    if page_type == PageType.SLD:
        _merge_sld(extraction, tool_input, page_index)
    elif page_type == PageType.LIGHTING_LAYOUT:
        _merge_lighting(extraction, tool_input, page_index)
    elif page_type == PageType.PLUGS_LAYOUT:
        _merge_plugs(extraction, tool_input, page_index)
    elif page_type == PageType.SCHEDULE:
        _merge_schedule(extraction, tool_input, page_index)
    elif page_type in (PageType.NOTES, PageType.REGISTER):
        _merge_notes(extraction, tool_input)


def _to_circuit_row(d: dict) -> CircuitRow:
    return CircuitRow(
        circuit_id=str(d.get("circuit_id", "")),
        description=str(d.get("description", "")),
        breaker_a=int(d.get("breaker_a", 0)),
        breaker_poles=int(d.get("breaker_poles", 1)),
        cable_size_mm2=float(d.get("cable_size_mm2", 0.0)),
        cable_cores=int(d.get("cable_cores", 0)),
        num_points=int(d.get("num_points", 0)),
        is_spare=bool(d.get("is_spare", False)),
        notes=str(d.get("notes", "")),
    )


def _merge_sld(ext: PdfExtraction, tool_input: dict, page_index: int) -> None:
    for db_dict in tool_input.get("distribution_boards", []):
        db = DistributionBoard(
            name=str(db_dict.get("name", "")),
            location=str(db_dict.get("location", "")),
            main_breaker_a=int(db_dict.get("main_breaker_a", 0)),
            phases=int(db_dict.get("phases", 3)),
            voltage_v=int(db_dict.get("voltage_v", 400)),
            elcb_present=bool(db_dict.get("elcb_present", False)),
            surge_protection=bool(db_dict.get("surge_protection", False)),
            circuits=[_to_circuit_row(c) for c in db_dict.get("circuits", [])],
            page_source=page_index,
        )
        ext.distribution_boards.append(db)
        if "confidence" in db_dict:
            ext.per_field_confidence[f"db:{db.name or page_index}"] = float(db_dict["confidence"])
    for w in tool_input.get("extraction_warnings", []) or []:
        ext.extraction_warnings.append(f"p{page_index} sld: {w}")


def _merge_schedule(ext: PdfExtraction, tool_input: dict, page_index: int) -> None:
    sched = CircuitSchedule(
        title=str(tool_input.get("title", "")),
        page_source=page_index,
        rows=[_to_circuit_row(r) for r in tool_input.get("rows", [])],
    )
    ext.schedules.append(sched)
    for w in tool_input.get("extraction_warnings", []) or []:
        ext.extraction_warnings.append(f"p{page_index} schedule: {w}")


def _lighting_fields() -> tuple[str, ...]:
    return (
        "downlights",
        "panel_lights",
        "bulkheads",
        "floodlights",
        "emergency_lights",
        "exit_signs",
        "pool_flood_light",
        "pool_underwater_light",
    )


def _outlet_fields() -> tuple[str, ...]:
    return (
        "double_sockets",
        "single_sockets",
        "waterproof_sockets",
        "floor_sockets",
        "data_outlets",
        "switches_1lever",
        "switches_2lever",
        "switches_3lever",
        "isolators",
        "day_night_switches",
    )


def _ensure_room(ext: PdfExtraction, room_name: str) -> FixtureCounts:
    if room_name not in ext.fixtures_per_room:
        ext.fixtures_per_room[room_name] = FixtureCounts(room_name=room_name)
    return ext.fixtures_per_room[room_name]


def _merge_lighting(ext: PdfExtraction, tool_input: dict, page_index: int) -> None:
    for room in tool_input.get("rooms", []):
        rn = str(room.get("room_name", "")) or f"Room (p{page_index})"
        rec = _ensure_room(ext, rn)
        rec.room_type = rec.room_type or str(room.get("room_type", ""))
        rec.page_source = page_index
        for f in _lighting_fields():
            if f in room:
                setattr(rec, f, getattr(rec, f) + int(room[f]))
        if "confidence" in room:
            ext.per_field_confidence[f"lighting:{rn}"] = float(room["confidence"])
    for k, v in (tool_input.get("legend") or {}).items():
        ext.legends[k] = v
    for w in tool_input.get("extraction_warnings", []) or []:
        ext.extraction_warnings.append(f"p{page_index} lighting: {w}")


def _merge_plugs(ext: PdfExtraction, tool_input: dict, page_index: int) -> None:
    for room in tool_input.get("rooms", []):
        rn = str(room.get("room_name", "")) or f"Room (p{page_index})"
        rec = _ensure_room(ext, rn)
        rec.room_type = rec.room_type or str(room.get("room_type", ""))
        rec.page_source = page_index
        for f in _outlet_fields():
            if f in room:
                setattr(rec, f, getattr(rec, f) + int(room[f]))
        if "confidence" in room:
            ext.per_field_confidence[f"plugs:{rn}"] = float(room["confidence"])
    for w in tool_input.get("extraction_warnings", []) or []:
        ext.extraction_warnings.append(f"p{page_index} plugs: {w}")


def _merge_notes(ext: PdfExtraction, tool_input: dict) -> None:
    pm = ext.project
    pm.project_name    = pm.project_name    or str(tool_input.get("project_name", ""))
    pm.client_name     = pm.client_name     or str(tool_input.get("client_name", ""))
    pm.consultant_name = pm.consultant_name or str(tool_input.get("consultant_name", ""))
    pm.site_address    = pm.site_address    or str(tool_input.get("site_address", ""))
    drawings = tool_input.get("drawing_numbers", []) or []
    for d in drawings:
        if d and d not in pm.drawing_numbers:
            pm.drawing_numbers.append(str(d))
    if "revision" in tool_input and pm.revision is None:
        try:
            pm.revision = int(tool_input["revision"])
        except (TypeError, ValueError):
            pass
    for n in tool_input.get("notes", []) or []:
        ext.notes.append(str(n))
    for k, v in (tool_input.get("legend") or {}).items():
        ext.legends[k] = v
