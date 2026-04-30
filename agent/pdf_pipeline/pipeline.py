"""
PDF Pipeline orchestrator.

P1 ingest → P2 classify → P3 extract → P4 evaluate → P5 generate

This file's only job is to wire the stages together and aggregate cost
telemetry. Per blueprint §0, it does not import from agent.dxf_pipeline.
"""

from __future__ import annotations

import logging
import time
import uuid
from datetime import datetime
from typing import Optional

from agent.pdf_pipeline.llm import PdfLLM, build_default_pdf_llm
from agent.pdf_pipeline.models import (
    PdfEvaluation,
    PdfExtraction,
    PdfPipelineRun,
)
from agent.pdf_pipeline.stages.classify import classify_pages
from agent.pdf_pipeline.stages.evaluate import evaluate as evaluate_stage
from agent.pdf_pipeline.stages.extract import extract as extract_stage
from agent.pdf_pipeline.stages.generate import generate_boq
from agent.pdf_pipeline.stages.ingest import ingest as ingest_stage
from agent.shared import ContractorProfile, ProjectMetadata
from agent.shared.persistence import persist_run
from core.config import RUNS_DIR_PDF

log = logging.getLogger(__name__)


def run_pdf_pipeline(
    file_bytes: bytes,
    file_name: str = "input.pdf",
    *,
    api_key: Optional[str] = None,
    llm: Optional[PdfLLM] = None,
    project: Optional[ProjectMetadata] = None,
    contractor: Optional[ContractorProfile] = None,
    baseline_project: Optional[str] = None,
    include_estimated_pricing: bool = True,
    persist: bool = False,
) -> PdfPipelineRun:
    """
    Run the PDF pipeline end-to-end. Returns a PdfPipelineRun (always —
    even on failure, with `success=False` and `error` populated).

    Pass `llm` to inject a mocked client for tests.
    """
    run_id = uuid.uuid4().hex[:12]
    project = project or ProjectMetadata()
    contractor = contractor or ContractorProfile()
    started = time.perf_counter()

    # ── P1 — Ingest ──────────────────────────────────────────────────
    ingest_result = ingest_stage(file_bytes, file_name=file_name)
    if not ingest_result.pages_processed:
        return _failure_run(
            run_id=run_id,
            file_name=file_name,
            sha=ingest_result.file_sha256,
            page_count=ingest_result.page_count_total,
            duration_s=time.perf_counter() - started,
            error="No pages extracted from PDF",
        )

    # ── LLM client ───────────────────────────────────────────────────
    if llm is None:
        llm = build_default_pdf_llm(api_key=api_key)

    # ── P2 — Classify ────────────────────────────────────────────────
    classifications, classify_costs = classify_pages(llm, ingest_result.pages_processed)

    # ── P3 — Extract ─────────────────────────────────────────────────
    extraction, extract_costs = extract_stage(llm, ingest_result.pages_processed, classifications)

    # Inject pre-existing project metadata if caller supplied any
    if project.project_name and not extraction.project.project_name:
        extraction.project.project_name = project.project_name
    if project.client_name and not extraction.project.client_name:
        extraction.project.client_name = project.client_name

    # ── P4 — Evaluate ────────────────────────────────────────────────
    evaluation = evaluate_stage(extraction, baseline_project=baseline_project)

    # ── P5 — Generate (only if gate passed) ──────────────────────────
    boq = None
    if evaluation.passed:
        project_name = (
            extraction.project.project_name
            or project.project_name
            or ingest_result.file_name
        )
        boq = generate_boq(
            extraction,
            project_name=project_name,
            run_id=run_id,
            contractor=contractor,
            include_estimated_pricing=include_estimated_pricing,
        )

    all_costs = list(classify_costs) + list(extract_costs)
    total_cost = sum(c.cost_zar for c in all_costs)

    run = PdfPipelineRun(
        run_id=run_id,
        timestamp=datetime.utcnow(),
        input_file=ingest_result.file_name,
        input_sha256=ingest_result.file_sha256,
        page_count=ingest_result.page_count_total,
        extraction=extraction,
        evaluation=evaluation,
        boq=boq,
        stage_costs=all_costs,
        cost_zar=round(total_cost, 4),
        duration_s=round(time.perf_counter() - started, 3),
        success=evaluation.passed,
        error=None if evaluation.passed else "; ".join(evaluation.failure_reasons),
    )
    if persist:
        persist_run(run, pipeline="pdf", run_id=run_id, runs_root=RUNS_DIR_PDF.split("/")[0])
    return run


def _failure_run(
    *,
    run_id: str,
    file_name: str,
    sha: str,
    page_count: int,
    duration_s: float,
    error: str,
) -> PdfPipelineRun:
    return PdfPipelineRun(
        run_id=run_id,
        timestamp=datetime.utcnow(),
        input_file=file_name,
        input_sha256=sha,
        page_count=page_count,
        extraction=PdfExtraction(),
        evaluation=PdfEvaluation(passed=False, failure_reasons=[error]),
        boq=None,
        stage_costs=[],
        cost_zar=0.0,
        duration_s=duration_s,
        success=False,
        error=error,
    )
