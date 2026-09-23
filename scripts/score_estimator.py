"""
Score the PDF estimator against a reference baseline.

Usage:
    # Score a persisted run's BOQ against a baseline
    python scripts/score_estimator.py --run runs/pdf/<run_id>.json --baseline wedela

    # Score a saved BOQ JSON directly
    python scripts/score_estimator.py --boq path/to/boq.json --baseline trichard

    # Run the estimator live over a drawing set, then score (needs API key)
    python scripts/score_estimator.py --pdf "Electrical plan/Wedela SLD 260525.pdf" \
        "Electrical plan/Wedela Lighting&Plugs 260525.pdf" --baseline wedela

Deterministic except for the optional --pdf live-run path.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from agent.shared import BillOfQuantities
from scoring import load_baseline, score_boq


def _boq_from_run(path: str) -> BillOfQuantities:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    boq = data.get("boq", data)
    return BillOfQuantities.model_validate(boq)


def _boq_from_boq_json(path: str) -> BillOfQuantities:
    return BillOfQuantities.model_validate_json(Path(path).read_text(encoding="utf-8"))


def _boq_from_live(pdf_paths, baseline_name) -> BillOfQuantities:
    from agent.pdf_pipeline.passes.run import run_pdf_estimator
    files = [(Path(p).read_bytes(), Path(p).name) for p in pdf_paths]
    run = run_pdf_estimator(files, persist=True)
    if not run.boq:
        print(f"Estimator produced no BOQ: {run.error}", file=sys.stderr)
        sys.exit(2)
    return run.boq


def main() -> None:
    ap = argparse.ArgumentParser(description="Score the estimator against a baseline")
    ap.add_argument("--baseline", required=True, help="Baseline name (e.g. wedela) or path")
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--run", help="Persisted EstimatorRun JSON")
    src.add_argument("--boq", help="Saved BillOfQuantities JSON")
    src.add_argument("--pdf", nargs="+", help="PDF drawing set to run live then score")
    args = ap.parse_args()

    baseline = load_baseline(args.baseline)
    if args.run:
        boq = _boq_from_run(args.run)
    elif args.boq:
        boq = _boq_from_boq_json(args.boq)
    else:
        boq = _boq_from_live(args.pdf, args.baseline)

    report = score_boq(boq, baseline)
    print(report.render())


if __name__ == "__main__":
    main()
