"""Heavy runs wait their turn instead of overloading the server: ten testers can press Run at once.

A full CAD set peaks at ~1.1 GB on a 2 GB server, so two at once can crash it and lose every
run in progress. The queue lets only `slots` jobs of a kind run at once; the others wait in line,
in order, and their progress says how many runs are ahead. When the line itself is full, a new
upload is refused with a clear 503 before anything is stored.
"""

from __future__ import annotations

import asyncio
import threading
import time
import uuid

import pytest
from fastapi.testclient import TestClient

from core import run_jobs
from core.run_progress import clear_progress, get_progress
from core.run_queue import QueueFull, RunQueue
from main import app


def _blocking_job(started: list, gate: threading.Event, seen_progress: dict):
    def job(run_id: str) -> None:
        seen_progress[run_id] = get_progress(run_id)     # what the user sees once the job starts
        started.append(run_id)
        gate.wait(5)
    return job


async def _until(cond, timeout=3.0):
    end = time.monotonic() + timeout
    while not cond():
        if time.monotonic() > end:
            raise AssertionError("condition not reached in time")
        await asyncio.sleep(0.01)


def test_one_slot_runs_jobs_one_after_another_in_arrival_order():
    q = RunQueue("dxf", slots=1, max_waiting=10)
    started, gate, seen = [], threading.Event(), {}
    job = _blocking_job(started, gate, seen)
    a, b, c = (f"q-{uuid.uuid4().hex[:6]}" for _ in range(3))

    async def scenario():
        tasks = [asyncio.create_task(q.run(rid, job)) for rid in (a, b, c)]
        await _until(lambda: started == [a])
        await asyncio.sleep(0.1)
        assert started == [a], "a second job started while the only slot was busy"
        gate.set()
        await asyncio.gather(*tasks)

    asyncio.run(scenario())
    assert started == [a, b, c]


def test_a_waiting_run_says_how_many_runs_are_ahead_and_the_note_goes_once_it_starts():
    q = RunQueue("dxf", slots=1, max_waiting=10)
    started, gate, seen = [], threading.Event(), {}
    job = _blocking_job(started, gate, seen)
    a, b, c = (f"q-{uuid.uuid4().hex[:6]}" for _ in range(3))

    async def scenario():
        tasks = [asyncio.create_task(q.run(rid, job)) for rid in (a, b, c)]
        await _until(lambda: started == [a])
        pb, pc = get_progress(b), get_progress(c)
        assert pb["stage"] == "queued" and "1 run ahead" in pb["message"]
        assert pc["stage"] == "queued" and "2 runs ahead" in pc["message"]
        gate.set()
        await asyncio.gather(*tasks)

    try:
        asyncio.run(scenario())
    finally:
        for rid in (a, b, c):
            clear_progress(rid)
    assert seen[b] is None, "the waiting message must not linger once the run has started"


def test_two_slots_run_two_jobs_at_once():
    q = RunQueue("pdf", slots=2, max_waiting=10)
    started, gate, seen = [], threading.Event(), {}
    job = _blocking_job(started, gate, seen)
    ids = [f"q-{uuid.uuid4().hex[:6]}" for _ in range(3)]

    async def scenario():
        tasks = [asyncio.create_task(q.run(rid, job)) for rid in ids]
        await _until(lambda: len(started) == 2)
        await asyncio.sleep(0.1)
        assert len(started) == 2
        gate.set()
        await asyncio.gather(*tasks)

    asyncio.run(scenario())
    assert sorted(started) == sorted(ids)


def test_a_failing_job_frees_its_slot_for_the_next_one():
    q = RunQueue("dxf", slots=1, max_waiting=10)
    ran = []

    def boom(run_id):
        raise RuntimeError("drawing could not be read")

    def ok(run_id):
        ran.append(run_id)

    async def scenario():
        first = asyncio.create_task(q.run("q-boom", boom))
        second = asyncio.create_task(q.run("q-ok", ok))
        with pytest.raises(RuntimeError):
            await first
        await second

    asyncio.run(scenario())
    assert ran == ["q-ok"]


def test_the_line_is_full_only_when_every_slot_is_busy_and_the_waiting_places_are_taken():
    q = RunQueue("dxf", slots=1, max_waiting=1)
    gate, started, seen = threading.Event(), [], {}
    job = _blocking_job(started, gate, seen)

    async def scenario():
        assert not q.is_full()
        t1 = asyncio.create_task(q.run("q-1", job))
        await _until(lambda: started == ["q-1"])
        assert not q.is_full(), "one waiting place is still free"
        t2 = asyncio.create_task(q.run("q-2", job))
        await asyncio.sleep(0.05)
        assert q.is_full()
        with pytest.raises(QueueFull):
            q.check_room()
        gate.set()
        await asyncio.gather(t1, t2)
        assert not q.is_full()

    try:
        asyncio.run(scenario())
    finally:
        clear_progress("q-2")


def test_a_full_line_refuses_the_upload_with_503_and_stores_nothing(monkeypatch):
    full = RunQueue("dxf", slots=1, max_waiting=0)
    monkeypatch.setattr(full, "is_full", lambda: True)
    monkeypatch.setattr(run_jobs, "DXF_QUEUE", full)
    before = _count_runs()

    resp = TestClient(app).post("/api/runs", data={"pipeline": "dxf"},
                                files=[("files", ("a.dxf", b"0\nEOF\n", "application/dxf"))])

    assert resp.status_code == 503
    assert "busy" in resp.json()["detail"].lower()
    assert _count_runs() == before


def _count_runs() -> int:
    from db.connection import get_connection
    with get_connection() as conn:
        return conn.execute("SELECT COUNT(*) AS n FROM runs").fetchone()["n"]


def test_slot_counts_come_from_the_environment(monkeypatch):
    from core.config import run_slots
    monkeypatch.setenv("AFRIPLAN_DXF_SLOTS", "2")
    monkeypatch.setenv("AFRIPLAN_PDF_SLOTS", "3")
    monkeypatch.setenv("AFRIPLAN_QUEUE_MAX", "15")
    assert run_slots() == {"dxf": 2, "pdf": 3, "max_waiting": 15}
    monkeypatch.delenv("AFRIPLAN_DXF_SLOTS")
    monkeypatch.delenv("AFRIPLAN_PDF_SLOTS")
    monkeypatch.delenv("AFRIPLAN_QUEUE_MAX")
    assert run_slots() == {"dxf": 1, "pdf": 2, "max_waiting": 20}
