"""
Audit a BOQ (and the drawings behind it).

    python scripts/audit_boq.py --project wedela                       # audit the reference bill
    python scripts/audit_boq.py --project wedela --sufficiency         # drawings → complete/partial BOQ
    python scripts/audit_boq.py --project wedela --boq out.json --building "Storage"   # audit a pipeline bill
    ... --out reports/audits/wedela-reference-audit.md
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "api"))
sys.stdout.reconfigure(encoding="utf-8")

from agent.shared import BillOfQuantities  # noqa: E402
from audit.boq_rules import audit_boq, audit_reference  # noqa: E402
from audit.report import render_findings  # noqa: E402
from evaluation.reference import load_reference  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--project", required=True)
    ap.add_argument("--boq", type=Path)
    ap.add_argument("--building", default="")
    ap.add_argument("--sufficiency", action="store_true")
    ap.add_argument("--out", type=Path)
    args = ap.parse_args()

    ref = load_reference(args.project)
    if args.sufficiency:
        from audit.sufficiency import render_sufficiency, sufficiency_for_project
        md = render_sufficiency(sufficiency_for_project(args.project, ref))
    elif args.boq:
        raw = json.loads(args.boq.read_text(encoding="utf-8"))
        boq = BillOfQuantities.model_validate(raw.get("boq", raw) if "line_items" not in raw else raw)
        md = render_findings(audit_boq(boq, building=args.building, reference=ref),
                             f"BOQ audit — {boq.pipeline} bill for {args.building or boq.project_name}")
    else:
        md = render_findings(audit_reference(ref), f"Reference BOQ audit — {args.project}")

    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(md, encoding="utf-8")
        print(f"Wrote {args.out}")
    else:
        print(md)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
