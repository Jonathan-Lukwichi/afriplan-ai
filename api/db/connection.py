"""
SQLite connection + schema — replaces the original app's local files
(~/.afriplan/profile.json, runs/<pipeline>/<run_id>.json) with a real
multi-session store, per CLAUDE.md's persistence decision. Plain stdlib
sqlite3 (the plan explicitly allows "sqlmodel or plain sqlite3") — every
row here is fundamentally a JSON blob keyed by id, which doesn't benefit
from an ORM's relational mapping.
"""

from __future__ import annotations

import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path

_DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./data/afriplan.db")
_RAW_DB_PATH = _DATABASE_URL.removeprefix("sqlite:///")
# Anchor a relative path to api/ (this file's parent's parent), not the
# process cwd - main.py runs from api/ but pytest's rootdir is the repo
# root, so a bare relative path silently created two different DB files
# depending on which one launched the process (a real bug hit during
# Phase 11 build - a stray top-level data/ appeared from a pytest run).
_DB_PATH = (
    _RAW_DB_PATH if Path(_RAW_DB_PATH).is_absolute()
    else str(Path(__file__).resolve().parent.parent / _RAW_DB_PATH)
)


def _ensure_parent_dir() -> None:
    parent = Path(_DB_PATH).parent
    if str(parent) not in (".", ""):
        parent.mkdir(parents=True, exist_ok=True)


def _ensure_schema(conn: sqlite3.Connection) -> None:
    conn.execute("""
        CREATE TABLE IF NOT EXISTS runs (
            run_id TEXT PRIMARY KEY,
            pipeline TEXT NOT NULL,
            status TEXT NOT NULL,
            input_file TEXT NOT NULL,
            result_json TEXT,
            sourced_boq_json TEXT,
            error TEXT,
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS comparisons (
            compare_id TEXT PRIMARY KEY,
            dxf_run_id TEXT NOT NULL,
            pdf_run_id TEXT NOT NULL,
            status TEXT NOT NULL,
            result_json TEXT,
            error TEXT,
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS contractor_profile (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            profile_json TEXT NOT NULL
        )
    """)


@contextmanager
def get_connection():
    """Every connection ensures the schema exists first (CREATE TABLE IF NOT
    EXISTS is idempotent and cheap) — callers never need to remember to call
    init_db() before using the store. A real bug during Phase 11 build:
    tests that imported run_store/compare_store directly, without ever
    importing main.py, hit "no such table" because nothing had run the
    schema yet."""
    _ensure_parent_dir()
    conn = sqlite3.connect(_DB_PATH)
    conn.row_factory = sqlite3.Row
    _ensure_schema(conn)
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db() -> None:
    """Explicit call at app startup (main.py) — mostly documentation at this
    point, since get_connection() self-initialises, but calling it eagerly
    surfaces a broken DATABASE_URL/permissions issue at boot rather than on
    the first request."""
    with get_connection():
        pass
