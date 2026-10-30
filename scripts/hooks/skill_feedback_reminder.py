"""
Claude Code PostToolUse hook (Bash|PowerShell): close the skills' learning loop.

After a scored run (`doe/execution/project.py finish` or `scripts/evaluate.py`), tell Claude
to run the `improving-boq-skills` skill, so every test iteration feeds back into the BoQ
skills' FEEDBACK.md logs. Never blocks: it only adds context.
Portable: needs only Python (no jq).
"""

from __future__ import annotations

import json
import re
import sys

# The interpreter must run the script (so a commit message or grep that only mentions it stays quiet).
_SCORED_RUN = re.compile(
    r"(?:python3?(?:\.exe)?|\$PY|\$\{PY\})[\"']?\s+(?:-\S+\s+)*[\"']?\S*?"
    r"(?:project\.py[\"']?\s+finish\b|scripts[\\/]evaluate\.py\b)"
)

MESSAGE = (
    "A scored BoQ run just finished. Before reporting done, use the `improving-boq-skills` "
    "skill: log what this run showed (accuracy_report gaps, wrong or missing items, the "
    "user's corrections) in the FEEDBACK.md of the skill whose rule was involved, then "
    "apply any rule change the evidence now supports. No client rand figures or quantities."
)


def reminder(payload: dict) -> str | None:
    """The reminder text when the tool call was a scored run, else None."""
    if payload.get("tool_name") not in ("Bash", "PowerShell"):
        return None
    command = str((payload.get("tool_input") or {}).get("command") or "")
    return MESSAGE if _SCORED_RUN.search(command) else None


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except Exception:  # noqa: BLE001 — never break the session on a malformed payload
        return 0
    msg = reminder(payload)
    if msg:
        print(json.dumps({"hookSpecificOutput": {"hookEventName": "PostToolUse", "additionalContext": msg}}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
