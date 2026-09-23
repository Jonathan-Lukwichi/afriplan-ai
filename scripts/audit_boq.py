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
from typing import List

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.stdout.reconfigure(encoding="utf-8")

from agent.shared import BillOfQuantities  # noqa: E402
from audit.boq_rules import AuditFinding, audit_boq, audit_reference  # noqa: E402
from evaluation.reference import load_reference  # noqa: E402


def render_findings(findings: List[AuditFinding], title: str) -> str:
    total = sum(f.value_at_risk_zar for f in findings)
    by_rule = {}
    for f in findings:
        by_rule.setdefault(f.rule, []).append(f)
    out = [f"# {title}", "",
           f"**{len(findings)} findings · R {total:,.0f} value at risk**", "",
           "| Rule | Findings | Value at risk |", "|---|---:|---:|"]
    for rule, fs in sorted(by_rule.items(), key=lambda kv: -sum(f.value_at_risk_zar for f in kv[1])):
        out.append(f"| {rule} | {len(fs)} | R {sum(f.value_at_risk_zar for f in fs):,.0f} |")
    out += ["", "## Findings (by severity, then value)", "",
            "| Sev | Rule | Building | Location | Finding | Value at risk | Action |",
            "|---|---|---|---|---|---:|---|"]
    for f in findings:
        out.append(f"| {f.severity} | {f.rule} | {f.building} | {f.location} | {f.message} | "
                   f"R {f.value_at_risk_zar:,.0f} | {f.suggested_action} |")
    return "\n".join(out) + "\n"


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
