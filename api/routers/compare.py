"""
POST /api/compare, GET /api/compare/{compare_id}, GET /api/compare/{compare_id}/pdf

Resurrects the comparison feature as a real, live one (unlike the original
app, where agent/comparison/compare.py was fully tested but never wired to
the wizard) — a "Both" upload launches a DXF run and a PDF run concurrently
via asyncio.gather (matching the blueprint's originally-intended but
never-shipped parallel behaviour, not the sequential wait a naive
BackgroundTasks chain would give), and once both resolve, compare_runs
fires automatically.
"""

from __future__ import annotations

import asyncio
import uuid
from typing import List

from fastapi import APIRouter, BackgroundTasks, File, HTTPException, UploadFile
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import Response

from agent.comparison import compare_runs, export_comparison_to_pdf
from core.compare_store import CompareRecord, compare_store
from core.run_jobs import run_dxf_job, run_pdf_job
from core.run_store import RunRecord, run_store

router = APIRouter(prefix="/api/compare", tags=["compare"])


async def _run_both_then_compare(
    compare_id: str, dxf_run_id: str, pdf_run_id: str,
    dxf_bytes: bytes, dxf_name: str, pdf_pairs: list[tuple[bytes, str]],
) -> None:
    await asyncio.gather(
        run_in_threadpool(run_dxf_job, dxf_run_id, dxf_bytes, dxf_name),
        run_in_threadpool(run_pdf_job, pdf_run_id, pdf_pairs),
    )

    dxf_record = run_store.get(dxf_run_id)
    pdf_record = run_store.get(pdf_run_id)

    if dxf_record.status != "passed" or pdf_record.status != "passed":
        reasons = [r for r in (dxf_record.error, pdf_record.error) if r]
        compare_store.put(CompareRecord(
            compare_id=compare_id, dxf_run_id=dxf_run_id, pdf_run_id=pdf_run_id,
            status="failed", error="; ".join(reasons) or "One or both pipelines failed",
        ))
        return

    result = compare_runs(pdf_run=pdf_record.result, dxf_run=dxf_record.result)
    compare_store.put(CompareRecord(
        compare_id=compare_id, dxf_run_id=dxf_run_id, pdf_run_id=pdf_run_id,
        status="passed", result=result,
    ))


@router.post("")
async def create_comparison(
    background_tasks: BackgroundTasks,
    dxf_file: UploadFile = File(...),
    pdf_files: List[UploadFile] = File(...),
):
    dxf_bytes = await dxf_file.read()
    dxf_name = dxf_file.filename or "input.dxf"
    pdf_pairs = [(await f.read(), f.filename or "input.pdf") for f in pdf_files]

    dxf_run_id = uuid.uuid4().hex[:12]
    pdf_run_id = uuid.uuid4().hex[:12]
    run_store.put(RunRecord(run_id=dxf_run_id, pipeline="dxf", status="running", input_file=dxf_name))
    run_store.put(RunRecord(
        run_id=pdf_run_id, pipeline="pdf", status="running",
        input_file=pdf_pairs[0][1] if len(pdf_pairs) == 1 else f"{len(pdf_pairs)} files",
    ))

    compare_id = uuid.uuid4().hex[:12]
    compare_store.put(CompareRecord(
        compare_id=compare_id, dxf_run_id=dxf_run_id, pdf_run_id=pdf_run_id, status="running",
    ))
    background_tasks.add_task(
        _run_both_then_compare, compare_id, dxf_run_id, pdf_run_id, dxf_bytes, dxf_name, pdf_pairs,
    )

    return {"compare_id": compare_id, "dxf_run_id": dxf_run_id, "pdf_run_id": pdf_run_id, "status": "running"}


@router.get("/{compare_id}")
def get_comparison(compare_id: str):
    record = compare_store.get(compare_id)
    if record is None:
        raise HTTPException(404, "comparison not found")
    return {
        "compare_id": record.compare_id,
        "dxf_run_id": record.dxf_run_id,
        "pdf_run_id": record.pdf_run_id,
        "status": record.status,
        "error": record.error,
        "result": record.result.model_dump(mode="json") if record.result is not None else None,
    }


@router.get("/{compare_id}/pdf")
def get_comparison_pdf(compare_id: str):
    record = compare_store.get(compare_id)
    if record is None:
        raise HTTPException(404, "comparison not found")
    if record.status != "passed" or record.result is None:
        raise HTTPException(409, "comparison is not ready yet")
    pdf_bytes = export_comparison_to_pdf(record.result)
    return Response(
        content=pdf_bytes, media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=comparison_report.pdf"},
    )
