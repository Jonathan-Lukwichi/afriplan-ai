"""
A person's answers to a project's things to check.

One row per project and question: who answered, when, and on which drawings. The run itself is
never changed, so an answer can be undone and accuracy stays a measure of the reader alone.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Dict

from db.connection import get_connection


def load_answers(project_key: str) -> Dict[str, dict]:
    """{question_id: {values, by, at, drawings}}."""
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT question_id, values_json, answered_by, answered_at, drawings FROM review_answers "
            "WHERE project_key = ?", (project_key,)).fetchall()
    return {r["question_id"]: {"values": json.loads(r["values_json"]), "by": r["answered_by"],
                               "at": r["answered_at"], "drawings": r["drawings"]} for r in rows}


def save_answer(project_key: str, question_id: str, values: dict, by: str, drawings: str) -> None:
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO review_answers (project_key, question_id, values_json, answered_by, answered_at, drawings)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(project_key, question_id) DO UPDATE SET values_json = excluded.values_json,
                answered_by = excluded.answered_by, answered_at = excluded.answered_at, drawings = excluded.drawings
            """,
            (project_key, question_id, json.dumps(values), by,
             datetime.now(timezone.utc).isoformat(timespec="seconds"), drawings),
        )


def delete_answer(project_key: str, question_id: str) -> None:
    with get_connection() as conn:
        conn.execute("DELETE FROM review_answers WHERE project_key = ? AND question_id = ?",
                     (project_key, question_id))
