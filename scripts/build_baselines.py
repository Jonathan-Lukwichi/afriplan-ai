#!/usr/bin/env python3
"""
Build / inspect a baseline ground-truth file for a project.

Usage:
  # Inspect an existing baseline against current pipeline outputs
  python scripts/build_baselines.py inspect <project_name>

  # Interactively author a new baseline (prompts for counts)
  python scripts/build_baselines.py interactive <project_name>

  # Bootstrap a baseline from a current DXF run (deterministic; needs hand-correction)
  python scripts/build_baselines.py from-dxf <project_name> <path/to/file.dxf>

The output file is `baselines/<project_name>.json`.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))


BASELINES_DIR = REPO_ROOT / "baselines"


def _interactive(project: str) -> None:
    print(f"\nBuilding baseline for project: {project}")
    print("Press Enter to skip a field; values are integers.\n")

    pdf_counts = {}
    for k in (
        "downlights", "panel_lights", "bulkheads", "floodlights",
        "emergency_lights", "exit_signs", "double_sockets", "single_sockets",
        "waterproof_sockets", "data_outlets", "switches_1lever",
        "switches_2lever", "switches_3lever", "isolators",
    ):
        v = input(f"  PDF {k:24s}: ").strip()
        if v:
            pdf_counts[k] = int(v)

    print("\nDXF block counts (use canonical names from agent/dxf_pipeline/patterns.py):")
    dxf_counts = {}
    while True:
        name = input("  Block canonical_name (blank to stop): ").strip()
        if not name:
            break
        qty = input(f"    Qty for {name!r}: ").strip()
        if qty:
            dxf_counts[name] = int(qty)

    notes = input("\nValidation notes: ").strip()
    validated_by = input("Validated by: ").strip() or "unknown"

    baseline = {
        "project_name": project,
        "validated_by": validated_by,
        "validated_at": date.today().isoformat(),
        "notes": notes,
        "pdf_fixture_counts": pdf_counts,
        "dxf_block_counts_by_type": dxf_counts,
    }

    _write(project, baseline)


def _from_dxf(project: str, dxf_path: str) -> None:
    from agent.dxf_pipeline import run_dxf_pipeline

    p = Path(dxf_path)
    print(f"Running DXF pipeline against {p} ...")
    result = run_dxf_pipeline(p.read_bytes(), file_name=p.name)
    if not result.success:
        print(f"WARNING: DXF run did not pass its gate ({result.error}). "
              "Counts saved anyway — review and correct before using as baseline.")

    baseline = {
        "project_name": project,
        "source_dxf": p.name,
        "validated_by": "auto from-dxf (HAND-CORRECT BEFORE USE)",
        "validated_at": date.today().isoformat(),
        "notes": (
            "Auto-bootstrapped from a deterministic DXF run. "
            "Review every count, fix mis-classifications, then commit."
        ),
        "pdf_fixture_counts": {},   # left empty — author by hand or via PDF run
        "dxf_block_counts_by_type": dict(result.extraction.block_counts_by_type),
        "total_polyline_length_m": round(result.extraction.total_polyline_length_m, 2),
    }
    _write(project, baseline)


def _inspect(project: str) -> None:
    path = BASELINES_DIR / f"{project}.json"
    if not path.exists():
        print(f"No baseline at {path}")
        sys.exit(1)
    with path.open() as f:
        baseline = json.load(f)
    print(f"\nBaseline: {path}")
    print(json.dumps(baseline, indent=2))


def _write(project: str, baseline: dict) -> None:
    BASELINES_DIR.mkdir(exist_ok=True)
    path = BASELINES_DIR / f"{project}.json"
    if path.exists():
        confirm = input(f"\n{path} exists. Overwrite? [y/N]: ").strip().lower()
        if confirm != "y":
            print("Aborted.")
            return
    with path.open("w", encoding="utf-8") as f:
        json.dump(baseline, f, indent=2, sort_keys=False)
        f.write("\n")
    print(f"\n✓ Wrote {path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Build / inspect baseline JSON files.")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_int = sub.add_parser("interactive", help="Build a baseline interactively")
    p_int.add_argument("project", help="Project name, e.g. 'wedela'")

    p_dxf = sub.add_parser("from-dxf", help="Bootstrap a baseline from a DXF run")
    p_dxf.add_argument("project", help="Project name, e.g. 'wedela'")
    p_dxf.add_argument("dxf_path", help="Path to the DXF file")

    p_ins = sub.add_parser("inspect", help="Print an existing baseline")
    p_ins.add_argument("project", help="Project name")

    args = parser.parse_args()

    if args.cmd == "interactive":
        _interactive(args.project)
    elif args.cmd == "from-dxf":
        _from_dxf(args.project, args.dxf_path)
    elif args.cmd == "inspect":
        _inspect(args.project)


if __name__ == "__main__":
    main()
