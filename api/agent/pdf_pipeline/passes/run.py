"""
v2 estimator — multi-file ingest, file classification, and the run entry.

DECISION 1: the PDF pipeline ingests a SET of drawings, auto-classified.
DECISION 2: run separately from DXF; own result.

Flow:
    ingest_files  → one flat, globally-indexed page list across all files
    classify      → per-page type (robust to mixed files: a legend page inside
                    an SLD file is handled correctly), with a file-level summary
                    and a manual per-file override as the low-confidence fallback
    extract_facts → Passes 1–3 (LLM eyes)         [passes.orchestrator]
    build_bill    → Passes 4–5 (deterministic)    [passes.assemble]

Only the classify + extract steps touch the LLM; the bill itself is
deterministic given the facts.
"""

from __future__ import annotations

import logging
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional, Sequence, Tuple

from pydantic import BaseModel, Field

from agent.pdf_pipeline.llm import LLMError, PdfLLM, build_default_pdf_llm
from agent.pdf_pipeline.models import PageClassification, PageType, StageCost
from agent.pdf_pipeline.passes.facts import PdfFacts
from agent.pdf_pipeline.passes.legend import build_pdf_legend
from agent.pdf_pipeline.passes.assemble import findings_from_facts
from agent.pdf_pipeline.passes.orchestrator import extract_facts
from agent.pdf_pipeline.passes.site_routes import read_pdf_site_routes
from agent.shared.legend import Legend, billed_canonical_items, coverage_gaps
from agent.pdf_pipeline.prompts.page_prompts import CLASSIFY_PROMPT
from agent.pdf_pipeline.prompts.tool_schemas import CLASSIFY_PAGE_TOOL
from agent.pdf_pipeline.stages.ingest import IngestedPage, ingest
from agent.shared import BillOfQuantities, ContractorProfile, ProjectMetadata
from agent.shared.findings import Findings
from agent.shared.persistence import persist_run
from agent.shared.pricing import price_findings
from concurrent.futures import ThreadPoolExecutor

from core.config import CLASSIFY_MODEL, PDF_PARALLEL_PAGES

log = logging.getLogger(__name__)

# Below this classification confidence, a file is flagged for a manual tag.
CLASSIFY_CONFIDENCE_FLOOR = 0.6


# ─── Multi-file ingest ───────────────────────────────────────────────

@dataclass
class FileIngest:
    file_name: str
    file_sha256: str
    first_global_index: int
    pages: List[IngestedPage] = field(default_factory=list)


def ingest_files(files: Sequence[Tuple[bytes, str]]) -> Tuple[List[IngestedPage], List[FileIngest]]:
    """
    Ingest a set of PDFs into one globally-indexed page list. Each page keeps a
    unique global page_index so downstream stages can treat the set as one.
    """
    all_pages: List[IngestedPage] = []
    file_ingests: List[FileIngest] = []
    offset = 0

    for data, name in files:
        res = ingest(data, file_name=name)
        remapped = [
            IngestedPage(
                page_index=offset + p.page_index,
                width_px=p.width_px, height_px=p.height_px, image_b64=p.image_b64,
            )
            for p in res.pages_processed
        ]
        file_ingests.append(FileIngest(
            file_name=name, file_sha256=res.file_sha256,
            first_global_index=offset, pages=remapped,
        ))
        all_pages.extend(remapped)
        offset += len(remapped)

    return all_pages, file_ingests


# ─── File classification (per-page, with file summary + manual override) ─

class FileClassification(BaseModel):
    file_name: str
    sheet_type: PageType = PageType.UNKNOWN     # dominant type for the file
    confidence: float = 0.0
    page_count: int = 0
    needs_manual: bool = False
    manual: bool = False                         # True if the caller tagged it


def classify_files(
    llm: PdfLLM,
    file_ingests: List[FileIngest],
    *,
    manual_types: Optional[Dict[str, str]] = None,
) -> Tuple[List[PageClassification], List[FileClassification], List[StageCost]]:
    """
    Classify every page. A file the caller tagged in `manual_types` forces all
    its pages to that type (the low-confidence fallback). Returns per-page
    classifications, per-file summaries, and costs.
    """
    manual_types = manual_types or {}
    page_classes: List[PageClassification] = []
    file_classes: List[FileClassification] = []
    costs: List[StageCost] = []

    for fi in file_ingests:
        override = manual_types.get(fi.file_name)
        if override:
            ptype = _as_page_type(override)
            for p in fi.pages:
                page_classes.append(PageClassification(
                    page_index=p.page_index, page_type=ptype,
                    confidence=1.0, rationale="manual tag",
                ))
            file_classes.append(FileClassification(
                file_name=fi.file_name, sheet_type=ptype, confidence=1.0,
                page_count=len(fi.pages), manual=True,
            ))
            continue

        def classify(p):
            try:
                return llm.call_with_tool(
                    model=CLASSIFY_MODEL, user_text=CLASSIFY_PROMPT, page_image_b64=p.image_b64,
                    tools=[CLASSIFY_PAGE_TOOL], forced_tool_name="classify_page",
                    stage_name=f"classify:{fi.file_name}:p{p.page_index}", max_tokens=512,
                )
            except LLMError as e:          # one page's network failure must not sink the run
                log.error("Classifying %s p%d failed: %s", fi.file_name, p.page_index, e)
                return None

        # every page at once (results kept in page order, so the run stays deterministic)
        with ThreadPoolExecutor(max_workers=PDF_PARALLEL_PAGES) as pool:
            results = list(pool.map(classify, fi.pages))
        per_page: List[PageClassification] = []
        for p, result in zip(fi.pages, results):
            if result is None:
                per_page.append(PageClassification(
                    page_index=p.page_index, page_type=PageType.UNKNOWN, confidence=0.0,
                    rationale="page could not be read (connection to the AI failed) — upload again"))
                continue
            costs.append(result.cost)
            per_page.append(PageClassification(
                page_index=p.page_index,
                page_type=_as_page_type(result.tool_input.get("page_type", "unknown")),
                confidence=float(result.tool_input.get("confidence", 0.0)),
                rationale=str(result.tool_input.get("rationale", "")),
            ))
        page_classes.extend(per_page)
        file_classes.append(_summarise_file(fi.file_name, per_page))

    return page_classes, file_classes, costs


def _as_page_type(value: str) -> PageType:
    try:
        return PageType(value)
    except ValueError:
        return PageType.UNKNOWN


def _summarise_file(file_name: str, per_page: List[PageClassification]) -> FileClassification:
    """Dominant non-trivial page type = the file's type; flag low confidence."""
    meaningful = [c for c in per_page if c.page_type not in (PageType.UNKNOWN, PageType.NOTES)]
    pool = meaningful or per_page
    counts: Dict[PageType, int] = {}
    for c in pool:
        counts[c.page_type] = counts.get(c.page_type, 0) + 1
    dominant = max(counts, key=counts.get) if counts else PageType.UNKNOWN
    confs = [c.confidence for c in pool] or [0.0]
    mean_conf = sum(confs) / len(confs)
    return FileClassification(
        file_name=file_name, sheet_type=dominant, confidence=round(mean_conf, 3),
        page_count=len(per_page), needs_manual=mean_conf < CLASSIFY_CONFIDENCE_FLOOR,
    )


# ─── Run object ──────────────────────────────────────────────────────

class EstimatorRun(BaseModel):
    run_id: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    project_name: str = ""
    files: List[FileClassification] = Field(default_factory=list)
    page_count: int = 0
    facts: PdfFacts = Field(default_factory=PdfFacts)
    legend: Optional[Legend] = None
    findings: Optional[Findings] = None   # what was read, before pricing (ADR-0008)
    boq: Optional[BillOfQuantities] = None
    site_plan_file: str = ""          # 'file p<n>' whose routes priced the feeders (issue 002)
    routes_measured: int = 0          # feeders whose length came from that site plan
    stage_costs: List[StageCost] = Field(default_factory=list)
    cost_zar: float = 0.0
    duration_s: float = 0.0
    success: bool = False
    error: Optional[str] = None

    @property
    def gap_count(self) -> int:
        return len(self.boq.gaps) if self.boq else 0


# ─── The run entry ───────────────────────────────────────────────────

def run_pdf_estimator(
    files: Sequence[Tuple[bytes, str]],
    *,
    api_key: Optional[str] = None,
    llm: Optional[PdfLLM] = None,
    project: Optional[ProjectMetadata] = None,
    contractor: Optional[ContractorProfile] = None,
    manual_types: Optional[Dict[str, str]] = None,
    persist: bool = False,
) -> EstimatorRun:
    """
    Run the v2 PDF estimator over a set of drawings. Always returns an
    EstimatorRun (even on failure, with success=False).
    """
    run_id = uuid.uuid4().hex[:12]
    project = project or ProjectMetadata()
    contractor = contractor or ContractorProfile()
    started = time.perf_counter()

    all_pages, file_ingests = ingest_files(files)
    if not all_pages:
        return EstimatorRun(
            run_id=run_id, success=False, error="No pages extracted from the uploaded files",
            duration_s=round(time.perf_counter() - started, 3),
        )

    if llm is None:
        llm = build_default_pdf_llm(api_key=api_key)

    page_classes, file_classes, classify_costs = classify_files(
        llm, file_ingests, manual_types=manual_types
    )
    facts, pass_costs = extract_facts(llm, all_pages, page_classes)

    # Seed any caller-supplied project metadata that the drawings didn't carry
    if project.project_name and not facts.context.project_name:
        facts.context.project_name = project.project_name

    project_name = facts.context.project_name or project.project_name or "Untitled project"
    # Feeder routes measured on a vector site plan — geometry, not the LLM (R 0).
    routes, site_plan = read_pdf_site_routes(files)
    findings = findings_from_facts(facts, routes=routes)
    boq = price_findings(findings, pipeline="pdf", project_name=project_name, run_id=run_id)

    # LDSE — legend-first: read the drawing's legend, flag declared-but-uncounted items.
    legend = build_pdf_legend(facts, sheet_ref=project_name)
    if boq is not None:
        billed = billed_canonical_items(l.description for l in boq.line_items)
        boq.gaps.extend(coverage_gaps(legend, billed))

    all_costs = list(classify_costs) + list(pass_costs)
    run = EstimatorRun(
        run_id=run_id,
        project_name=project_name,
        files=file_classes,
        page_count=len(all_pages),
        facts=facts,
        legend=legend,
        findings=findings, boq=boq,
        site_plan_file=site_plan,
        routes_measured=sum(1 for fd in facts.spine.feeders
                            if routes is not None and not fd.length_annotated
                            and routes.route(fd.from_source, fd.to_db) is not None),
        stage_costs=all_costs,
        cost_zar=round(sum(c.cost_zar for c in all_costs), 4),
        duration_s=round(time.perf_counter() - started, 3),
        success=bool(boq.line_items),
        error=None if boq.line_items else "No billable items extracted from the drawings",
    )
    if persist:
        persist_run(run, pipeline="pdf", run_id=run_id)
    return run
