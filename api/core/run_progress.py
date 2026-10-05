"""
Live progress of running jobs — in memory, beside the run store.

A run writes its progress here many times a second at peak (every page read, every AI
wait); the SQLite run store only receives the final result. Progress lives in the process
that runs the job, which is the process that answers the polls (off Vercel); on Vercel the
job finishes inside the request, so a poll only ever sees the final status.
"""

from __future__ import annotations

import threading
import time
from typing import Any, Dict, Optional

_lock = threading.Lock()
_progress: Dict[str, Dict[str, Any]] = {}


def set_progress(run_id: str, **fields: Any) -> None:
    """Merge `fields` (stage, done, total, message, note) into the run's progress."""
    with _lock:
        p = _progress.setdefault(run_id, {"started_at": time.time(), "note": ""})
        if "stage" in fields and fields["stage"] != p.get("stage"):
            p["note"] = ""                       # a wait note belongs to the step it was said in
        p.update(fields)
        p["updated_at"] = time.time()


def get_progress(run_id: str) -> Optional[Dict[str, Any]]:
    with _lock:
        p = _progress.get(run_id)
        if p is None:
            return None
        return {**p, "elapsed_s": round(time.time() - p["started_at"], 1)}


def clear_progress(run_id: str) -> None:
    with _lock:
        _progress.pop(run_id, None)
