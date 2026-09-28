"""
Connection + schema — supports two backends behind one get_connection()
interface:

  - sqlite:// (default) — plain stdlib sqlite3, used for local dev and the
    existing Docker/Render deployment. Every row here is fundamentally a
    JSON blob keyed by id, which doesn't benefit from an ORM's relational
    mapping.
  - postgresql:// (Vercel deployment) — psycopg3, since Vercel's serverless
    filesystem is ephemeral and doesn't survive between invocations, so
    SQLite-on-disk can't be the store there. Vercel Postgres injects this
    as DATABASE_URL automatically.

Callers never need to know which backend is active: get_connection() always
yields something with the same .execute(sql, params)/.commit()/.close()
shape, using sqlite-style '?' placeholders (translated to psycopg's '%s' by
_PgConnection when Postgres is active) and dict-like rows either way
(sqlite3.Row / psycopg dict_row both support row["col"]).
"""

from __future__ import annotations

import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path

_DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./data/afriplan.db")
IS_POSTGRES = _DATABASE_URL.startswith("postgres://") or _DATABASE_URL.startswith("postgresql://")

if not IS_POSTGRES:
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


def _schema_statements(is_postgres: bool) -> list[str]:
    created_at = "TIMESTAMPTZ NOT NULL DEFAULT now()" if is_postgres else "TEXT NOT NULL DEFAULT (datetime('now'))"
    return [
        f"""
        CREATE TABLE IF NOT EXISTS runs (
            run_id TEXT PRIMARY KEY,
            pipeline TEXT NOT NULL,
            status TEXT NOT NULL,
            input_file TEXT NOT NULL,
            result_json TEXT,
            sourced_boq_json TEXT,
            error TEXT,
            created_at {created_at}
        )
        """,
        f"""
        CREATE TABLE IF NOT EXISTS comparisons (
            compare_id TEXT PRIMARY KEY,
            dxf_run_id TEXT NOT NULL,
            pdf_run_id TEXT NOT NULL,
            status TEXT NOT NULL,
            result_json TEXT,
            error TEXT,
            created_at {created_at}
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS contractor_profile (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            profile_json TEXT NOT NULL
        )
        """,
        # ADR-0007: what each unnamed CAD symbol shape is — named once (by the AI or a
        # person), then reused so it is never paid for again. 'person' beats 'ai'.
        """
        CREATE TABLE IF NOT EXISTS symbol_names (
            signature TEXT PRIMARY KEY,
            item TEXT NOT NULL,
            named_by TEXT NOT NULL
        )
        """,
    ]


def _ensure_schema_sqlite(conn: sqlite3.Connection) -> None:
    for stmt in _schema_statements(is_postgres=False):
        conn.execute(stmt)


def _ensure_schema_postgres(conn) -> None:
    cur = conn.cursor()
    for stmt in _schema_statements(is_postgres=True):
        cur.execute(stmt)


class _PgConnection:
    """Adapts a psycopg connection to the sqlite3.Connection shape the
    store files already use: conn.execute(sql, params) with '?'
    placeholders, returning a cursor whose fetchone()/fetchall() give
    dict-like rows (psycopg's dict_row), exactly like sqlite3.Row."""

    def __init__(self, conn) -> None:
        self._conn = conn

    def execute(self, sql: str, params=()):
        cur = self._conn.cursor()
        cur.execute(sql.replace("?", "%s"), params)
        return cur

    def commit(self) -> None:
        self._conn.commit()

    def close(self) -> None:
        self._conn.close()


@contextmanager
def get_connection():
    """Every connection ensures the schema exists first (CREATE TABLE IF NOT
    EXISTS is idempotent and cheap on either backend) — callers never need
    to remember to call init_db() before using the store. A real bug during
    Phase 11 build: tests that imported run_store/compare_store directly,
    without ever importing main.py, hit "no such table" because nothing had
    run the schema yet."""
    if IS_POSTGRES:
        import psycopg
        from psycopg.rows import dict_row

        conn = psycopg.connect(_DATABASE_URL, row_factory=dict_row)
        _ensure_schema_postgres(conn)
        wrapped = _PgConnection(conn)
        try:
            yield wrapped
            conn.commit()
        finally:
            conn.close()
    else:
        _ensure_parent_dir()
        conn = sqlite3.connect(_DB_PATH)
        conn.row_factory = sqlite3.Row
        _ensure_schema_sqlite(conn)
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
