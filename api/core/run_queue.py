"""
The run queue — heavy jobs take turns so a burst of uploads cannot overload the server.

A full CAD set peaks at ~1.1 GB on a 2 GB server: two at once can run it out of memory, and a
restart loses every run in progress. Each RunQueue lets `slots` jobs of its kind run at once;
the others wait in line in arrival order, and their live progress says how many runs are
ahead. Waiting happens on the event loop (no thread is held while waiting), the job itself
runs in the threadpool as before. When every slot is busy and `max_waiting` runs are already
in line, `check_room()` refuses the next upload before anything is stored.

All bookkeeping runs on the event loop, so it needs no lock; the asyncio.Condition is made
per event loop (tests run each scenario in a fresh loop).
"""

from __future__ import annotations

import asyncio
from typing import Any, Callable, Dict, List

from fastapi.concurrency import run_in_threadpool

from core.run_progress import clear_progress, set_progress


class QueueFull(Exception):
    """Every slot is busy and the line is full."""


class RunQueue:
    def __init__(self, kind: str, slots: int, max_waiting: int) -> None:
        self.kind = kind
        self.slots = max(1, slots)
        self.max_waiting = max(0, max_waiting)
        self._running = 0
        self._waiting: List[str] = []
        self._conds: Dict[int, asyncio.Condition] = {}

    # ── admission ──
    def is_full(self) -> bool:
        return self._running >= self.slots and len(self._waiting) >= self.max_waiting

    def check_room(self) -> None:
        if self.is_full():
            raise QueueFull(
                f"AfriPlan is busy: {self._running} {self.kind.upper()} run(s) in progress and "
                f"{len(self._waiting)} waiting. Please try again in a few minutes.")

    def snapshot(self) -> Dict[str, int]:
        return {"slots": self.slots, "running": self._running, "waiting": len(self._waiting)}

    # ── running ──
    async def run(self, run_id: str, fn: Callable[..., Any], *args: Any) -> Any:
        cond = self._cond()
        self._waiting.append(run_id)
        self._announce()
        try:
            async with cond:
                await cond.wait_for(lambda: self._running < self.slots and self._waiting[0] == run_id)
                self._waiting.pop(0)
                self._running += 1
        except BaseException:                       # cancelled while waiting: leave the line
            if run_id in self._waiting:
                self._waiting.remove(run_id)
            self._announce()
            raise
        self._announce()
        clear_progress(run_id)                      # the waiting note must not outlive the wait
        try:
            return await run_in_threadpool(fn, run_id, *args)
        finally:
            async with cond:
                self._running -= 1
                cond.notify_all()
            self._announce()

    def _cond(self) -> asyncio.Condition:
        loop = asyncio.get_running_loop()
        key = id(loop)
        if key not in self._conds:
            self._conds = {key: asyncio.Condition()}  # one live loop at a time; drop stale ones
        return self._conds[key]

    def _announce(self) -> None:
        """Tell every waiting run where it stands: runs in progress + runs ahead in line."""
        for i, rid in enumerate(self._waiting):
            ahead = self._running + i
            set_progress(rid, stage="queued", done=0, total=0,
                         message=f"Waiting in line: {ahead} run{'s' if ahead != 1 else ''} ahead of yours",
                         note="The server runs a few projects at a time so that no run is lost.")
