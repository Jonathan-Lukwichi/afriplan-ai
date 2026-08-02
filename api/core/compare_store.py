"""
Keyed cache for cross-pipeline comparisons — the same materialized-result
pattern as core/run_store.py, one level up: a CompareRecord tracks the two
underlying run_ids and, once both resolve, the computed PipelineComparison.

SQLite-backed (Phase 11) behind the same get/put interface as run_store.
"""

from __future__ import annotations

import threading
from dataclasses import dataclass
from typing import Literal, Optional

from agent.comparison import PipelineComparison
from db.connection import get_connection

CompareStatus = Literal["running", "passed", "failed"]


@dataclass
class CompareRecord:
    compare_id: str
    dxf_run_id: str
    pdf_run_id: str
    status: CompareStatus
    result: Optional[PipelineComparison] = None
    error: Optional[str] = None


class CompareStore:
    def __init__(self) -> None:
        self._lock = threading.Lock()

    def put(self, record: CompareRecord) -> None:
        result_json = record.result.model_dump_json() if record.result is not None else None
        with self._lock, get_connection() as conn:
            conn.execute(
                """
                INSERT INTO comparisons (compare_id, dxf_run_id, pdf_run_id, status, result_json, error)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(compare_id) DO UPDATE SET
                    dxf_run_id=excluded.dxf_run_id, pdf_run_id=excluded.pdf_run_id,
                    status=excluded.status, result_json=excluded.result_json, error=excluded.error
                """,
                (record.compare_id, record.dxf_run_id, record.pdf_run_id, record.status, result_json, record.error),
            )

    def get(self, compare_id: str) -> Optional[CompareRecord]:
        with self._lock, get_connection() as conn:
            row = conn.execute("SELECT * FROM comparisons WHERE compare_id = ?", (compare_id,)).fetchone()
        if row is None:
            return None
        result = PipelineComparison.model_validate_json(row["result_json"]) if row["result_json"] is not None else None
        return CompareRecord(
            compare_id=row["compare_id"], dxf_run_id=row["dxf_run_id"], pdf_run_id=row["pdf_run_id"],
            status=row["status"], result=result, error=row["error"],
        )


compare_store = CompareStore()
