"""
Build a reference project's committed ground-truth artefacts from its raw files.

    python scripts/build_reference.py wedela

Writes data/projects/<project>/reference_boq.json (parsed bill) and, once
evaluation.ratios exists, ratio_model.json (fitted derived-item ratios).
Deterministic: same raw files → byte-identical JSON.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "api"))
sys.stdout.reconfigure(encoding="utf-8")

from evaluation.dataset import load_manifest, project_dir, verify_manifest  # noqa: E402
from evaluation.reference import parse_reference_xlsx  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("project")
    args = ap.parse_args()

    manifest = load_manifest(args.project)
    root = project_dir(args.project)
    problems = verify_manifest(manifest, root)
    if problems:
        print("Raw files do not match the manifest:\n" + "\n".join(problems))
        return 1

    boq_files = manifest.files_for(role="reference_boq")
    if len(boq_files) != 1:
        print(f"Expected exactly one reference_boq file, found {len(boq_files)}")
        return 1
    ref = parse_reference_xlsx(root / boq_files[0].path, project=args.project,
                               buildings=manifest.buildings)
    (root / "reference_boq.json").write_text(ref.model_dump_json(indent=1), encoding="utf-8")
    n = sum(len(b.lines) for b in ref.buildings)
    print(f"reference_boq.json — {len(ref.buildings)} bills, {n} lines, "
          f"summary total R {ref.summary_total_excl_vat:,.2f} excl VAT")

    try:
        from evaluation.ratios import fit_ratios
    except ImportError:
        return 0
    model = fit_ratios(ref)
    (root / "ratio_model.json").write_text(model.model_dump_json(indent=1), encoding="utf-8")
    print(f"ratio_model.json — {len(model.ratios)} fitted ratios")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
