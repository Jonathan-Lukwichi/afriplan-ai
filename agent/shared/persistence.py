"""
Run-log persistence — write each pipeline run to runs/<pipeline>/<run_id>.json.

Both pipelines call this from their orchestrator (or via the UI layer).
The function takes any Pydantic model and writes it via model_dump_json,
so the on-disk shape is exactly the public data contract.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

from pydantic import BaseModel

log = logging.getLogger(__name__)


def persist_run(
    run: BaseModel,
    *,
    pipeline: str,                  # "pdf" | "dxf" | "comparison"
    run_id: str,
    runs_root: str = "runs",
) -> Optional[Path]:
    """
    Write `run.model_dump_json()` to `runs/<pipeline>/<run_id>.json`.

    Returns the path, or None on failure (logged but never raises — we
    don't want a disk problem to crash a successful pipeline run).
    """
    try:
        out_dir = Path(runs_root) / pipeline
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / f"{run_id}.json"
        with out_path.open("w", encoding="utf-8") as f:
            f.write(run.model_dump_json(indent=2))
        return out_path
    except OSError as e:
        log.warning("Failed to persist %s run %s: %s", pipeline, run_id, e)
        return None
