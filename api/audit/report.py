"""Render audit findings (shared by scripts/audit_boq.py and the Streamlit Audit page)."""

from __future__ import annotations

from typing import Dict, List

from audit.boq_rules import AuditFinding


def summarise_findings(findings: List[AuditFinding]) -> Dict:
    """Count, total value at risk, and (rule, count, value) rows sorted by value."""
    by: Dict[str, List[AuditFinding]] = {}
    for f in findings:
        by.setdefault(f.rule, []).append(f)
    rows = sorted(((r, len(fs), sum(f.value_at_risk_zar for f in fs)) for r, fs in by.items()),
                  key=lambda row: -row[2])
    return {
        "count": len(findings),
        "value_at_risk_zar": sum(f.value_at_risk_zar for f in findings),
        "by_rule": rows,
        "high": sum(1 for f in findings if f.severity in ("critical", "high")),
    }


def render_findings(findings: List[AuditFinding], title: str) -> str:
    s = summarise_findings(findings)
    out = [f"# {title}", "",
           f"**{s['count']} findings · R {s['value_at_risk_zar']:,.0f} value at risk**", "",
           "| Rule | Findings | Value at risk |", "|---|---:|---:|"]
    out += [f"| {rule} | {n} | R {v:,.0f} |" for rule, n, v in s["by_rule"]]
    out += ["", "## Findings (by severity, then value)", "",
            "| Sev | Rule | Building | Location | Finding | Value at risk | Action |",
            "|---|---|---|---|---|---:|---|"]
    for f in findings:
        out.append(f"| {f.severity} | {f.rule} | {f.building} | {f.location} | {f.message} | "
                   f"R {f.value_at_risk_zar:,.0f} | {f.suggested_action} |")
    return "\n".join(out) + "\n"
