"""
POST /api/runs, GET /api/runs/{run_id} — the keyed run-cache pattern.

DXF-only for now (Phase 4); the PDF branch (Phase 5) adds `pipeline=pdf` to
the same two endpoints, since the store and polling contract are shared.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, BackgroundTasks, File, Form, HTTPException, UploadFile
from fastapi.concurrency import run_in_threadpool

from agent.dxf_pipeline.passes.run import run_dxf_estimator
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


@router.post("")
async def create_run(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    pipeline: str = Form("dxf"),
):
    if pipeline != "dxf":
        raise HTTPException(400, f"pipeline '{pipeline}' not supported yet")

    file_bytes = await file.read()
    run_id = uuid.uuid4().hex[:12]
    run_store.put(RunRecord(
        run_id=run_id, pipeline="dxf", status="running",
        input_file=file.filename or "input.dxf",
    ))
    background_tasks.add_task(
        run_in_threadpool, _run_dxf_job, run_id, file_bytes, file.filename or "input.dxf",
    )
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
