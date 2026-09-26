"""
Claude Code PostToolUse hook (Edit|Write): enforce the architecture rules by tool,
not by prose (ADR-0001, ADR-0006).

Reads the hook JSON on stdin; if a .py file was edited, runs tests/architecture.
On violation, exits 2 so the failure output is fed back to Claude immediately.
Portable: needs only Python (no jq).
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except Exception:  # noqa: BLE001 — never break the session on a malformed payload
        return 0
    path = (payload.get("tool_input") or {}).get("file_path") or \
        (payload.get("tool_response") or {}).get("filePath") or ""
    if not str(path).endswith(".py"):
        return 0
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", "tests/architecture", "-q", "-p", "no:warnings"],
        cwd=ROOT, capture_output=True, text=True,
    )
    if proc.returncode == 0:
        return 0
    tail = "\n".join((proc.stdout + proc.stderr).strip().splitlines()[-25:])
    print("Architecture rules violated (pipeline independence / read-only layers). "
          "See CLAUDE.md hard rules 1-3.\n" + tail, file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
