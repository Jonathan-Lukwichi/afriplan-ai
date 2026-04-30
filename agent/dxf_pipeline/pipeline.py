"""
DXF Pipeline orchestrator.

D1 ingest → D2 layers → D3 extract → D4 evaluate → D5 generate

This file contains zero LLM calls, zero imports from
agent.pdf_pipeline, and zero network access. CI-enforced (see
tests/architecture/test_independence.py).
"""

from __future__ import annotations

import time
import uuid
from datetime import datetime
from typing import Optional

from agent.dxf_pipeline.models import DxfPipelineRun
from agent.dxf_pipeline.stages.evaluate import evaluate
from agent.dxf_pipeline.stages.extract import extract
from agent.dxf_pipeline.stages.generate import generate_boq
from agent.dxf_pipeline.stages.ingest import ingest
from agent.dxf_pipeline.stages.layers import analyse_layers
from agent.shared import ContractorProfile, ProjectMetadata
from agent.shared.persistence import persist_run
from core.config import RUNS_DIR_DXF


def run_dxf_pipeline(
    file_bytes: bytes,
    file_name: str = "input.dxf",
    *,
    project: Optional[ProjectMetadata] = None,
    contractor: Optional[ContractorProfile] = None,
    baseline_project: Optional[str] = None,
    include_estimated_pricing: bool = True,
    persist: bool = False,
) -> DxfPipelineRun:
    """
    Run the DXF pipeline end-to-end on raw bytes.

    Returns a DxfPipelineRun (always — even on failure, with `success=False`
    and `error` populated). This is the single entry point used by the UI
    and by tests.
    """
    run_id = uuid.uuid4().hex[:12]
    project = project or ProjectMetadata()
    contractor = contractor or ContractorProfile()
    started = time.perf_counter()

    # ── D1 — Ingest ──────────────────────────────────────────────────
    ingest_result, doc = ingest(file_bytes, file_name)
    if not ingest_result.open_ok or doc is None:
        return DxfPipelineRun(
            run_id=run_id,
            timestamp=datetime.utcnow(),
            input_file=ingest_result.file_name,
            input_sha256=ingest_result.file_sha256,
            drawing_units=ingest_result.drawing_units,
            project=project,
            ingest=ingest_result,
            layer_analysis=_empty_layer_analysis(),
            extraction=_empty_extraction(),
            evaluation=_empty_evaluation(reason=ingest_result.error or "Failed to open DXF"),
            duration_s=time.perf_counter() - started,
            success=False,
            error=ingest_result.error,
        )

    # ── D2 — Layer analysis ──────────────────────────────────────────
    layer_analysis = analyse_layers(doc)

    # ── D3 — Extract ─────────────────────────────────────────────────
    extraction = extract(
        doc,
        units_to_metre=ingest_result.units_to_metre_factor,
        layer_index=layer_analysis.layers,
    )

    # Annotate project with detected blocks if not pre-supplied
    if not project.building_blocks and layer_analysis.building_blocks_detected:
        project = project.model_copy(
            update={"building_blocks": list(layer_analysis.building_blocks_detected)}
        )

    # ── D4 — Evaluate ────────────────────────────────────────────────
    evaluation = evaluate(extraction, layer_analysis, baseline_project=baseline_project)

    # ── D5 — Generate (only if gate passed; on fail, leave boq=None) ─
    boq = None
    if evaluation.passed:
        boq = generate_boq(
            extraction,
            project_name=project.project_name or ingest_result.file_name,
            run_id=run_id,
            contractor=contractor,
            include_estimated_pricing=include_estimated_pricing,
        )

    run = DxfPipelineRun(
        run_id=run_id,
        timestamp=datetime.utcnow(),
        input_file=ingest_result.file_name,
        input_sha256=ingest_result.file_sha256,
        drawing_units=ingest_result.drawing_units,
        project=project,
        ingest=ingest_result,
        layer_analysis=layer_analysis,
        extraction=extraction,
        evaluation=evaluation,
        boq=boq,
        cost_zar=0.0,
        duration_s=time.perf_counter() - started,
        success=evaluation.passed,
        error=None if evaluation.passed else "; ".join(evaluation.failure_reasons),
    )
    if persist:
        persist_run(run, pipeline="dxf", run_id=run_id, runs_root=RUNS_DIR_DXF.split("/")[0])
    return run


# ─── Empty result helpers (used on early failure) ─────────────────────

def _empty_layer_analysis():
    from agent.dxf_pipeline.models import DxfLayerAnalysis
    return DxfLayerAnalysis()


def _empty_extraction():
    from agent.dxf_pipeline.models import DxfExtraction
    return DxfExtraction()


def _empty_evaluation(reason: str):
    from agent.dxf_pipeline.models import DxfEvaluation
    return DxfEvaluation(
        passed=False,
        overall_score=0.0,
        failure_reasons=[reason],
    )
