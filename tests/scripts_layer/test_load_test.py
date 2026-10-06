"""scripts/load_test.py: the summary counts every user and measures waiting only for runs that finished."""

from __future__ import annotations

import importlib.util
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
_spec = importlib.util.spec_from_file_location("load_test", ROOT / "scripts" / "load_test.py")
load_test = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(load_test)


def test_summary_counts_outcomes_and_times():
    rows = [
        {"user": 1, "status": "passed", "wait_s": 0.0, "total_s": 70.0},
        {"user": 2, "status": "passed", "wait_s": 70.0, "total_s": 140.0},
        {"user": 3, "status": "failed", "wait_s": 140.0, "total_s": 150.0},
        {"user": 4, "status": "busy"},
        {"user": 5, "status": "error"},
    ]
    s = load_test.summarise(rows, 1123.6)
    assert (s["users"], s["passed"], s["failed"], s["refused_busy"], s["errors"]) == (5, 2, 1, 1, 1)
    assert (s["wait_s_max"], s["wait_s_median"], s["total_s_max"]) == (140.0, 70.0, 150.0)
    assert s["server_peak_mb"] == 1124


def test_memory_of_this_process_is_readable():
    mb = load_test.rss_mb(os.getpid())
    assert mb is not None and mb > 1
