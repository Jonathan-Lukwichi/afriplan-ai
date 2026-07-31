"""
Keyed cache for cross-pipeline comparisons — the same materialized-result
pattern as core/run_store.py, one level up: a CompareRecord tracks the two
underlying run_ids and, once both resolve, the computed PipelineComparison.
"""

from __future__ import annotations

import threading
from dataclasses import dataclass
from typing import Dict, Literal, Optional

from agent.comparison import PipelineComparison

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
        self._compares: Dict[str, CompareRecord] = {}
        self._lock = threading.Lock()

    def put(self, record: CompareRecord) -> None:
        with self._lock:
            self._compares[record.compare_id] = record

    def get(self, compare_id: str) -> Optional[CompareRecord]:
        with self._lock:
            return self._compares.get(compare_id)


compare_store = CompareStore()
