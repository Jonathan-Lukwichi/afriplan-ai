"""
Score a BOQ against a reference project with the frozen scorer.

    python scripts/evaluate.py --project wedela --self-test
    python scripts/evaluate.py --project wedela --run runs/dxf/<id>.json --building "Small Guard House"
    python scripts/evaluate.py --project wedela --boq my_boq.json --building "Storage" --source pdf

--run    a persisted pipeline run (EstimatorRun / DxfEstimatorRun JSON with a 'boq')
--boq    a BillOfQuantities JSON (e.g. the 'Raw BOQ (.json)' download from page 3)
--building  the reference building the prediction belongs to (required for --run/--boq)
--source    which inputs count as 'uploaded' for scoped metrics: dwg | pdf | all
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.stdout.reconfigure(encoding="utf-8")

from agent.shared import BillOfQuantities  # noqa: E402
from evaluation.dataset import load_manifest, uploaded_from_manifest  # noqa: E402
from evaluation.metrics import pred_lines_from_boq, pred_lines_from_reference, score  # noqa: E402
from evaluation.network import DrawingType  # noqa: E402
from evaluation.reference import load_reference  # noqa: E402
from evaluation.report import render_markdown  # noqa: E402


def _load_boq(path: Path) -> BillOfQuantities:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if "boq" in raw and "line_items" not in raw:
        raw = raw["boq"]
    if raw is None:
        raise SystemExit(f"{path} has no BOQ (the run failed?)")
    return BillOfQuantities.model_validate(raw)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--project", required=True)
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--run", type=Path)
    g.add_argument("--boq", type=Path)
    g.add_argument("--self-test", action="store_true")
    ap.add_argument("--building", default="")
    ap.add_argument("--source", choices=["dwg", "pdf", "all"], default="all")
    ap.add_argument("--out", type=Path)
    args = ap.parse_args()

    ref = load_reference(args.project)
    manifest = load_manifest(args.project)

    if args.self_test:
        card = score(pred_lines_from_reference(ref), ref, uploaded=set(DrawingType), pipeline="self-test")
        print(f"RS {card.reproduction_score:.1%}  coverage {card.coverage:.1%}  "
              f"precision {card.precision:.1%}  (reference R {card.reference_value:,.0f})")
        return 0 if abs(card.reproduction_score - 1.0) < 1e-9 else 1

    if not args.building or ref.building(args.building) is None:
        names = ", ".join(b.name for b in ref.billed_buildings())
        raise SystemExit(f"--building must be one of: {names}")
    building = ref.building(args.building).name
    boq = _load_boq(args.run or args.boq)
    uploaded = uploaded_from_manifest(manifest, building, source=args.source)
    card = score(pred_lines_from_boq(boq, building=building), ref, uploaded={building: uploaded},
                 pipeline=boq.pipeline, buildings=[building])
    md = render_markdown(card)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(md, encoding="utf-8")
        print(f"Wrote {args.out}")
    else:
        print(md)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
