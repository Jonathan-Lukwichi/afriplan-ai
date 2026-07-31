"""
POST /api/runs, GET /api/runs/{run_id} — the keyed run-cache pattern.

DXF is a single-file, no-LLM, sub-second job. PDF is a multi-file, LLM-backed
job that can take up to ~60s (vision calls with retry/escalation inside
PdfLLM.call_with_tool) - both run as background threadpool jobs behind the
same create/poll contract so the frontend doesn't need to know which.
"""

from __future__ import annotations

import uuid
from typing import List

from fastapi import APIRouter, BackgroundTasks, File, Form, HTTPException, UploadFile
from fastapi.concurrency import run_in_threadpool

from agent.dxf_pipeline.passes.run import run_dxf_estimator
from agent.pdf_pipeline.passes.run import run_pdf_estimator
from core.run_store import RunRecord, run_store

router = APIRouter(prefix="/api/runs", tags=["runs"])


def _run_dxf_job(run_id: str, file_bytes: bytes, file_name: str) -> None:
    try:
        result = run_dxf_estimator(file_bytes, file_name)
        record = run_store.get(run_id)
        record.result = result
        record.status = "passed" if result.success else "failed"
        record.error = result.error
    except Exception as e:  # noqa: BLE001 — a crashed job must still resolve the poll
        record = run_store.get(run_id)
        record.status = "failed"
        record.error = str(e)


def _run_pdf_job(run_id: str, files: list[tuple[bytes, str]]) -> None:
    try:
        result = run_pdf_estimator(files)
        record = run_store.get(run_id)
        record.result = result
        record.status = "passed" if result.success else "failed"
        record.error = result.error
    except Exception as e:  # noqa: BLE001 — a crashed job must still resolve the poll
        record = run_store.get(run_id)
        record.status = "failed"
        record.error = str(e)


@router.post("")
async def create_run(
    background_tasks: BackgroundTasks,
    files: List[UploadFile] = File(...),
    pipeline: str = Form("dxf"),
):
    if pipeline not in ("dxf", "pdf"):
        raise HTTPException(400, f"pipeline '{pipeline}' not supported")
    if pipeline == "dxf" and len(files) != 1:
        raise HTTPException(400, "the DXF pipeline takes exactly one file")

    run_id = uuid.uuid4().hex[:12]
    input_label = files[0].filename if len(files) == 1 else f"{len(files)} files"

    if pipeline == "dxf":
        file_bytes = await files[0].read()
        run_store.put(RunRecord(
            run_id=run_id, pipeline="dxf", status="running",
            input_file=files[0].filename or "input.dxf",
        ))
        background_tasks.add_task(
            run_in_threadpool, _run_dxf_job, run_id, file_bytes, files[0].filename or "input.dxf",
        )
    else:
        pairs = [(await f.read(), f.filename or "input.pdf") for f in files]
        run_store.put(RunRecord(
            run_id=run_id, pipeline="pdf", status="running", input_file=input_label,
        ))
        background_tasks.add_task(run_in_threadpool, _run_pdf_job, run_id, pairs)

    return {"run_id": run_id, "status": "running"}


@router.get("/{run_id}")
def get_run(run_id: str):
    record = run_store.get(run_id)
    if record is None:
        raise HTTPException(404, "run not found")
    return {
        "run_id": record.run_id,
        "pipeline": record.pipeline,
        "status": record.status,
        "input_file": record.input_file,
        "error": record.error,
        "result": record.result.model_dump(mode="json") if record.result is not None else None,
    }
