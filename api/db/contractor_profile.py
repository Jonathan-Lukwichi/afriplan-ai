"""
SQLite-backed contractor profile — replaces agent.shared.contractor_io's
~/.afriplan/profile.json for this web app (that module stays as-is; it's
verbatim-ported shared code, and its file-based contract is exactly what a
single local Streamlit session needs, just not what a web server needs).

Single shared demo profile (id=1), per CLAUDE.md decision #4: real per-user
accounts are a deliberate future decision, not implied by this persistence
upgrade.
"""

from __future__ import annotations

from agent.shared import ContractorProfile
from db.connection import get_connection


def load_contractor_profile() -> ContractorProfile:
    with get_connection() as conn:
        row = conn.execute("SELECT profile_json FROM contractor_profile WHERE id = 1").fetchone()
    if row is None:
        return ContractorProfile()
    return ContractorProfile.model_validate_json(row["profile_json"])


def save_contractor_profile(profile: ContractorProfile) -> None:
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO contractor_profile (id, profile_json) VALUES (1, ?)
            ON CONFLICT(id) DO UPDATE SET profile_json = excluded.profile_json
            """,
            (profile.model_dump_json(),),
        )
