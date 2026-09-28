"""
Remembered names for unnamed CAD symbol shapes (ADR-0007): signature → catalogue item.

Named once — by the AI or by a person — and reused on every later drawing that has the
same shape, so a shape is never paid for twice. A person's name always wins over the AI's.
"""

from __future__ import annotations

from typing import Dict, Tuple

from db.connection import get_connection


def load_symbol_names() -> Dict[str, Tuple[str, str]]:
    """{signature: (item, named_by)} with named_by 'ai' or 'person'."""
    with get_connection() as conn:
        rows = conn.execute("SELECT signature, item, named_by FROM symbol_names").fetchall()
    return {r["signature"]: (r["item"], r["named_by"]) for r in rows}


def save_symbol_name(signature: str, item: str, named_by: str) -> None:
    """Store a name. An AI name never overwrites one a person gave."""
    with get_connection() as conn:
        row = conn.execute("SELECT named_by FROM symbol_names WHERE signature = ?", (signature,)).fetchone()
        if row is not None and row["named_by"] == "person" and named_by != "person":
            return
        conn.execute(
            """
            INSERT INTO symbol_names (signature, item, named_by) VALUES (?, ?, ?)
            ON CONFLICT(signature) DO UPDATE SET item = excluded.item, named_by = excluded.named_by
            """,
            (signature, item, named_by),
        )
