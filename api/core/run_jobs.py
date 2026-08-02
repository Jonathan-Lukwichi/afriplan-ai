"""
Shared job-launching helpers for both /api/runs and /api/compare — a single
place that creates a RunRecord and schedules its background threadpool job,
so the comparison endpoint (which needs to launch one of each pipeline) and
the plain single-pipeline endpoint don't duplicate this wiring.
"""

from __future__ import annotations

import uuid

from fastapi import BackgroundTasks
from fastapi.concurrency import run_in_threadpool

from agent.dxf_pipeline.passes.run import run_dxf_estimator
from agent.pdf_pipeline.passes.run import run_pdf_estimator
from core.run_store import RunRecord, run_store


def run_dxf_job(run_id: str, file_bytes: bytes, file_name: str) -> None:
    try:
        result = run_dxf_estimator(file_bytes, file_name)
        record = run_store.get(run_id)
        record.result = result
        record.status = "passed" if result.success else "failed"
        record.error = result.error
        run_store.put(record)
    except Exception as e:  # noqa: BLE001 — a crashed job must still resolve the poll
        record = run_store.get(run_id)
        record.status = "failed"
        record.error = str(e)
        run_store.put(record)


def run_pdf_job(run_id: str, files: list[tuple[bytes, str]]) -> None:
    try:
        result = run_pdf_estimator(files)
        record = run_store.get(run_id)
        record.result = result
        record.status = "passed" if result.success else "failed"
        record.error = result.error
        run_store.put(record)
    except Exception as e:  # noqa: BLE001 — a crashed job must still resolve the poll
        record = run_store.get(run_id)
        record.status = "failed"
        record.error = str(e)
        run_store.put(record)


def launch_dxf_run(background_tasks: BackgroundTasks, file_bytes: bytes, file_name: str) -> str:
    run_id = uuid.uuid4().hex[:12]
    run_store.put(RunRecord(
        run_id=run_id, pipeline="dxf", status="running", input_file=file_name or "input.dxf",
    ))
    background_tasks.add_task(run_in_threadpool, run_dxf_job, run_id, file_bytes, file_name or "input.dxf")
    return run_id


def launch_pdf_run(background_tasks: BackgroundTasks, pairs: list[tuple[bytes, str]]) -> str:
    run_id = uuid.uuid4().hex[:12]
    label = pairs[0][1] if len(pairs) == 1 else f"{len(pairs)} files"
    run_store.put(RunRecord(run_id=run_id, pipeline="pdf", status="running", input_file=label))
    background_tasks.add_task(run_in_threadpool, run_pdf_job, run_id, pairs)
    return run_id
