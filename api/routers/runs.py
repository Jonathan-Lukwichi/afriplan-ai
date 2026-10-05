"""
POST /api/runs, GET /api/runs/{run_id} — the keyed run-cache pattern.

DXF is a no-LLM job over one drawing or a whole drawing set (run as one project). PDF is a multi-file, LLM-backed
job that can take up to ~60s (vision calls with retry/escalation inside
PdfLLM.call_with_tool) - both run as threadpool jobs behind the same
create/poll contract so the frontend doesn't need to know which. Off Vercel
that threadpool job is scheduled as a BackgroundTask (instant response,
frontend polls); on Vercel it's awaited directly before responding, since
Vercel's Python runtime gives no guarantee background work continues after
a response is sent (see core.run_jobs.ON_VERCEL). The "both, compare" option
lives at /api/compare (routers/compare.py), which launches one of each via
the same core.run_jobs helpers.
"""

from __future__ import annotations

from typing import List

from fastapi import APIRouter, BackgroundTasks, File, Form, HTTPException, UploadFile

from core.run_jobs import launch_dxf_run, launch_pdf_run
from core.run_progress import get_progress
from core.run_store import run_store

router = APIRouter(prefix="/api/runs", tags=["runs"])


@router.post("")
async def create_run(
    background_tasks: BackgroundTasks,
    files: List[UploadFile] = File(...),
    pipeline: str = Form("dxf"),
    ai_symbols: bool = Form(False),     # DXF: name unnamed symbol shapes with AI (ADR-0007)
):
    if pipeline not in ("dxf", "pdf"):
        raise HTTPException(400, f"pipeline '{pipeline}' not supported")
    if not files:
        raise HTTPException(400, "no files uploaded")

    if pipeline == "dxf":
        # one drawing, or the whole set (SLDs + layouts + site plan) run as one project
        pairs = [(await f.read(), f.filename or "input.dxf") for f in files]
        run_id = await launch_dxf_run(background_tasks, pairs, ai_symbols=ai_symbols)
    else:
        pairs = [(await f.read(), f.filename or "input.pdf") for f in files]
        run_id = await launch_pdf_run(background_tasks, pairs)

    # Off Vercel this is always "running" (the job is still in the
    # threadpool queue). On Vercel the job has already been awaited above,
    # so the record may already be "passed"/"failed" by the time we
    # respond — report the real status rather than a stale hardcoded one.
    return {"run_id": run_id, "status": run_store.get(run_id).status}


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
        "progress": get_progress(record.run_id) if record.status == "running" else None,
        "result": record.result.model_dump(mode="json") if record.result is not None else None,
    }
