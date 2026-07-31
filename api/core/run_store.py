"""
Keyed materialized-result cache for pipeline runs.

Adapts the original app's singleton "/last" pattern for a multi-tenant web
app: every run is addressed by its own run_id instead of one shared slot, so
concurrent contractors' uploads never clobber each other. Every consumer
(the Extraction page, exports, comparison) reads the same cached RunRecord —
nothing re-triggers its own private recompute.

In-memory for now (Phase 4-10); Phase 11 swaps the dict for SQLite behind
this same get/put interface so callers don't change.
"""

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from typing import Any, Dict, Literal, Optional

RunStatus = Literal["running", "passed", "failed"]


@dataclass
class RunRecord:
    run_id: str
    pipeline: Literal["pdf", "dxf"]
    status: RunStatus
    input_file: str
    result: Optional[Any] = None   # DxfEstimatorRun / PdfEstimatorRun once done
    error: Optional[str] = None


class RunStore:
    def __init__(self) -> None:
        self._runs: Dict[str, RunRecord] = {}
        self._lock = threading.Lock()

    def put(self, record: RunRecord) -> None:
        with self._lock:
            self._runs[record.run_id] = record

    def get(self, run_id: str) -> Optional[RunRecord]:
        with self._lock:
            return self._runs.get(run_id)


run_store = RunStore()
