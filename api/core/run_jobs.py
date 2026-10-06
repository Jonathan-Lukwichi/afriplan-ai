"""
Shared job-launching helpers for both /api/runs and /api/compare — a single
place that creates a RunRecord and runs its threadpool job, so the
comparison endpoint (which needs to launch one of each pipeline) and the
plain single-pipeline endpoint don't duplicate this wiring.

Two execution modes, chosen by ON_VERCEL (Vercel sets VERCEL=1 in every
deployment automatically — no config needed):
  - Off Vercel (local dev, Docker/Render): schedule via BackgroundTasks, so
    the HTTP response returns instantly with status="running" and the
    frontend polls GET /api/runs/{id} for completion — the original,
    nicer-feeling UX, safe here because the process keeps running after the
    response is sent.
  - On Vercel: BackgroundTasks work is not guaranteed to keep running once
    a serverless function has sent its response (Python Vercel functions
    have no post-response execution primitive), so the job is awaited
    directly instead — the request just stays open until the job resolves.
    The frontend needs no changes either way: it polls the same endpoint,
    and on Vercel that first poll simply already sees the final status.
"""

from __future__ import annotations

import os
import uuid

from typing import Optional

from fastapi import BackgroundTasks, HTTPException

from agent.dxf_pipeline.passes.run import run_dxf_project
from agent.pdf_pipeline.llm import build_default_pdf_llm
from agent.pdf_pipeline.passes.run import run_pdf_estimator
from core.config import ai_providers_ready, run_slots
from core.run_progress import clear_progress, set_progress
from core.run_queue import QueueFull, RunQueue
from core.run_store import RunRecord, run_store

ON_VERCEL = bool(os.environ.get("VERCEL"))

# Heavy runs take turns (core/run_queue.py): a burst of uploads waits in line instead of
# running the server out of memory. CAD and PDF have separate lines — a CAD set is
# memory-heavy, a PDF run mostly waits on the AI.
_SLOTS = run_slots()
DXF_QUEUE = RunQueue("dxf", _SLOTS["dxf"], _SLOTS["max_waiting"])
PDF_QUEUE = RunQueue("pdf", _SLOTS["pdf"], _SLOTS["max_waiting"])


def check_room(*queues: RunQueue) -> None:
    """Refuse an upload with 503 when its line is full — before any run record is stored."""
    try:
        for q in queues:
            q.check_room()
    except QueueFull as e:
        raise HTTPException(503, str(e))


def checked_ai_provider(choice: str) -> Optional[str]:
    """The user's AI reader for a PDF run: "" means the server default (None); a pick must be a
    provider whose key this server holds, so a wrong choice fails at upload, not mid-run."""
    choice = (choice or "").strip().lower()
    if not choice:
        return None
    if choice not in ai_providers_ready():
        raise HTTPException(400, f"AI provider '{choice}' is not available on this server "
                                 f"(available: {', '.join(ai_providers_ready()) or 'none'})")
    return choice


def _shape_namer():
    """ADR-0007: the optional AI step that names unnamed CAD symbols — built here, handed to
    the DXF pipeline as a plain callable. None without an API key (the run stays free)."""
    from core.config import ai_available
    if not ai_available():
        return None
    from agent.pdf_pipeline.llm import make_ai_client
    from assist.symbol_namer import make_shape_namer
    from db.symbol_names import load_symbol_names, save_symbol_name
    return make_shape_namer(client=make_ai_client(), remembered=load_symbol_names(),
                            on_named=lambda sig, item: save_symbol_name(sig, item, "ai"))


def run_dxf_job(run_id: str, files: list[tuple[bytes, str]], ai_symbols: bool = False) -> None:
    """One drawing or a whole drawing set (SLDs + layouts + site plan) as one project;
    with `ai_symbols`, unnamed symbol shapes are named by the AI (ADR-0007)."""
    try:
        result = run_dxf_project(files, name_shapes=_shape_namer() if ai_symbols else None)
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


def run_pdf_job(run_id: str, files: list[tuple[bytes, str]], provider: Optional[str] = None) -> None:
    set_progress(run_id, stage="start", done=0, total=0, message="Opening the drawings")
    try:
        picked = {"llm": build_default_pdf_llm(provider=provider)} if provider else {}
        result = run_pdf_estimator(files, on_progress=lambda **p: set_progress(run_id, **p), **picked)
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
    finally:
        clear_progress(run_id)


async def launch_dxf_run(background_tasks: BackgroundTasks, pairs: list[tuple[bytes, str]],
                         ai_symbols: bool = False) -> str:
    check_room(DXF_QUEUE)
    run_id = uuid.uuid4().hex[:12]
    label = pairs[0][1] if len(pairs) == 1 else f"{len(pairs)} files"
    run_store.put(RunRecord(run_id=run_id, pipeline="dxf", status="running", input_file=label))
    if ON_VERCEL:
        await DXF_QUEUE.run(run_id, run_dxf_job, pairs, ai_symbols)
    else:
        background_tasks.add_task(DXF_QUEUE.run, run_id, run_dxf_job, pairs, ai_symbols)
    return run_id


async def launch_pdf_run(background_tasks: BackgroundTasks, pairs: list[tuple[bytes, str]],
                         provider: Optional[str] = None) -> str:
    check_room(PDF_QUEUE)
    run_id = uuid.uuid4().hex[:12]
    label = pairs[0][1] if len(pairs) == 1 else f"{len(pairs)} files"
    run_store.put(RunRecord(run_id=run_id, pipeline="pdf", status="running", input_file=label))
    if ON_VERCEL:
        await PDF_QUEUE.run(run_id, run_pdf_job, pairs, provider)
    else:
        background_tasks.add_task(PDF_QUEUE.run, run_id, run_pdf_job, pairs, provider)
    return run_id
