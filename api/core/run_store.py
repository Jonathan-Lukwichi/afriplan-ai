"""
Keyed materialized-result cache for pipeline runs.

Adapts the original app's singleton "/last" pattern for a multi-tenant web
app: every run is addressed by its own run_id instead of one shared slot, so
concurrent contractors' uploads never clobber each other. Every consumer
(the Extraction page, exports, comparison) reads the same cached RunRecord —
nothing re-triggers its own private recompute.

Backed by SQLite (Phase 11) behind this same get/put interface, replacing
the Phase 4-10 in-memory dict — callers still just call get()/put(), but
put() is now the ONLY way a mutation persists (an in-memory dict let
callers mutate a fetched record in place and have it "just work"; a real
store can't do that, so every mutation site now re-calls put() explicitly
after changing a field — see core/run_jobs.py, routers/compare.py,
routers/pricing.py).
"""

from __future__ import annotations

import threading
from dataclasses import dataclass
from typing import Any, Literal, Optional

from db.connection import get_connection

RunStatus = Literal["running", "passed", "failed"]


@dataclass
class RunRecord:
    run_id: str
    pipeline: Literal["pdf", "dxf"]
    status: RunStatus
    input_file: str
    result: Optional[Any] = None   # DxfEstimatorRun / EstimatorRun once done
    error: Optional[str] = None
    # Set once live-sourced supplier prices are applied (sourcing.apply_quotes)
    # - overrides result.boq as the export/pricing basis, mirroring the
    # original app's session_state.priced_boq override semantics.
    sourced_boq: Optional[Any] = None


def _result_class(pipeline: str):
    if pipeline == "dxf":
        from agent.dxf_pipeline.passes.run import DxfEstimatorRun
        return DxfEstimatorRun
    from agent.pdf_pipeline.passes.run import EstimatorRun
    return EstimatorRun


def _boq_class():
    from agent.shared import BillOfQuantities
    return BillOfQuantities


class RunStore:
    """SQLite-backed; a lock only serialises this process's own read-then-write
    sequences (SQLite itself handles cross-connection safety)."""

    def __init__(self) -> None:
        self._lock = threading.Lock()

    def put(self, record: RunRecord) -> None:
        result_json = record.result.model_dump_json() if record.result is not None else None
        sourced_boq_json = record.sourced_boq.model_dump_json() if record.sourced_boq is not None else None
        with self._lock, get_connection() as conn:
            conn.execute(
                """
                INSERT INTO runs (run_id, pipeline, status, input_file, result_json, sourced_boq_json, error)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(run_id) DO UPDATE SET
                    pipeline=excluded.pipeline, status=excluded.status, input_file=excluded.input_file,
                    result_json=excluded.result_json, sourced_boq_json=excluded.sourced_boq_json, error=excluded.error
                """,
                (record.run_id, record.pipeline, record.status, record.input_file,
                 result_json, sourced_boq_json, record.error),
            )

    def fail_interrupted(self, reason: str) -> int:
        """Jobs run inside this process: at start-up, any run still 'running' died with the
        previous process. Mark them failed with the reason instead of leaving them spinning."""
        with self._lock, get_connection() as conn:
            cur = conn.execute("UPDATE runs SET status = 'failed', error = ? WHERE status = 'running'", (reason,))
            return cur.rowcount or 0

    def get(self, run_id: str) -> Optional[RunRecord]:
        with self._lock, get_connection() as conn:
            row = conn.execute("SELECT * FROM runs WHERE run_id = ?", (run_id,)).fetchone()
        if row is None:
            return None
        result = None
        if row["result_json"] is not None:
            result = _result_class(row["pipeline"]).model_validate_json(row["result_json"])
        sourced_boq = None
        if row["sourced_boq_json"] is not None:
            sourced_boq = _boq_class().model_validate_json(row["sourced_boq_json"])
        return RunRecord(
            run_id=row["run_id"], pipeline=row["pipeline"], status=row["status"],
            input_file=row["input_file"], result=result, error=row["error"], sourced_boq=sourced_boq,
        )


run_store = RunStore()
