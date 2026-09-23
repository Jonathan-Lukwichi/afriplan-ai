"""
BOQ audit rules — deterministic checks any quantity surveyor would run.

Works on a human reference bill (ReferenceBoq) and on any pipeline output
(BillOfQuantities → adapted to the same line model). Every finding carries a
severity and the rand value at risk so a reviewer can triage by money.

    ARITH           qty × rate ≠ line total
    UNTOTALLED      line has qty and rate but no total → silently excluded from sums
    NO_RATE         line has a quantity but no price
    DUPLICATE       identical line (code, description, qty, rate) repeated
    REPEATED        same item code + description priced more than once, different rates
    ROLLUP          Σ line totals of a section ≠ the stated section total
    CONTINGENCY     contingency ≠ declared % of the section totals
    TOTAL           building total ≠ Σ sections + contingency
    NOT_IN_SUMMARY  a priced/quantified bill sheet is missing from the project summary
    SUMMARY         summary amount ≠ the building sheet's own total
    ERROR_CELL      spreadsheet error cells (#REF!, #VALUE!…)
    COMPANION       feeder cable without its install line / terminations / earth
"""

from __future__ import annotations

import re
import statistics
from typing import Dict, List, Literal, Optional

from pydantic import BaseModel

from agent.shared import BillOfQuantities
from evaluation.reference import RefBuilding, RefLine, ReferenceBoq
from evaluation.taxonomy import BILL_SECTION_OF, classify_item, line_role

Severity = Literal["critical", "high", "medium", "low"]
_TOL = 1.0   # rand tolerance for rounding


class AuditFinding(BaseModel):
    rule: str
    severity: Severity
    building: str
    location: str = ""
    message: str
    value_at_risk_zar: float = 0.0
    suggested_action: str = ""


def _loc(l: RefLine) -> str:
    code = f"{l.code} " if l.code else ""
    row = f" (row {l.raw_row})" if l.raw_row else ""
    return f"{code}{l.label[:60]}{row}"


def _rate_key(l: RefLine) -> str:
    return f"{l.key}#{l.role}"          # supply and install rates differ for the same item


def _rate_lookup(ref: Optional[ReferenceBoq]) -> Dict[str, float]:
    """Median priced rate per (ItemKey, role) across the whole reference (value-at-risk)."""
    if ref is None:
        return {}
    rates: Dict[str, List[float]] = {}
    for l in ref.all_lines():
        if l.rate:
            rates.setdefault(_rate_key(l), []).append(l.rate)
    return {k: statistics.median(v) for k, v in rates.items()}


# ─── line-level rules ────────────────────────────────────────────────

def _line_rules(b: RefBuilding, rates: Dict[str, float]) -> List[AuditFinding]:
    out: List[AuditFinding] = []
    for l in b.lines:
        if l.rate is not None and l.total is not None:
            diff = l.qty * l.rate - l.total
            if abs(diff) > max(_TOL, 0.01 * abs(l.total)):
                out.append(AuditFinding(
                    rule="ARITH", severity="high", building=b.name, location=_loc(l),
                    message=f"{l.qty:g} × R {l.rate:,.2f} = R {l.qty * l.rate:,.2f}, bill shows R {l.total:,.2f}",
                    value_at_risk_zar=abs(diff), suggested_action="Correct the line total formula."))
        elif l.rate and l.total is None:
            out.append(AuditFinding(
                rule="UNTOTALLED", severity="high", building=b.name, location=_loc(l),
                message=f"Priced ({l.qty:g} × R {l.rate:,.2f}) but has no total — excluded from section sums",
                value_at_risk_zar=l.qty * l.rate,
                suggested_action="Add the SUB TOTAL formula; the section total is understated."))
        if l.qty > 0 and not l.rate and not l.total:
            rk = _rate_key(l)
            out.append(AuditFinding(
                rule="NO_RATE", severity="medium", building=b.name, location=_loc(l),
                message=f"Quantity {l.qty:g} {l.unit} has no rate",
                value_at_risk_zar=rates.get(rk, 0.0) * l.qty,
                suggested_action="Price the item" + (f" (median rate elsewhere R {rates[rk]:,.2f})" if rk in rates else "") + "."))
    return out


def _norm(desc: str) -> str:
    return re.sub(r"\s+", " ", desc.lower()).strip()[:60]


def _duplicate_rules(b: RefBuilding) -> List[AuditFinding]:
    out: List[AuditFinding] = []
    exact: Dict[tuple, List[RefLine]] = {}
    by_code: Dict[tuple, List[RefLine]] = {}
    for l in b.lines:
        exact.setdefault((l.code, _norm(l.description), l.qty, l.rate), []).append(l)
        if l.description.strip().lower() not in ("supply", "install"):
            by_code.setdefault((l.code, _norm(l.description)), []).append(l)
    flagged = set()
    for group in exact.values():
        if len(group) > 1:
            flagged.add((group[0].code, _norm(group[0].description)))
            out.append(AuditFinding(
                rule="DUPLICATE", severity="high", building=b.name, location=_loc(group[0]),
                message=f"Identical line appears {len(group)}× (rows {', '.join(str(g.raw_row) for g in group)})",
                value_at_risk_zar=sum(g.value for g in group[1:]),
                suggested_action="Remove the duplicate or confirm the extra quantity is intended."))
    for key, group in by_code.items():
        if len(group) > 1 and key not in flagged and len({g.rate for g in group}) > 1:
            out.append(AuditFinding(
                rule="REPEATED", severity="medium", building=b.name, location=_loc(group[0]),
                message=f"Item priced {len(group)}× at different rates: "
                        + ", ".join(f"R {g.rate:,.0f}" for g in group if g.rate),
                value_at_risk_zar=sum(g.value for g in group) - max(g.value for g in group),
                suggested_action="Confirm whether these are distinct items; renumber or merge."))
    return out


# ─── building-level rules ────────────────────────────────────────────

def _rollup_rules(b: RefBuilding, contingency_pct: float) -> List[AuditFinding]:
    out: List[AuditFinding] = []
    for sec, stated in b.section_totals.items():
        summed = sum(l.total or 0.0 for l in b.lines if l.bill_section == sec)
        if abs(summed - stated) > _TOL:
            out.append(AuditFinding(
                rule="ROLLUP", severity="high", building=b.name, location=f"Section {sec}",
                message=f"Lines sum to R {summed:,.2f}, section total states R {stated:,.2f}",
                value_at_risk_zar=abs(summed - stated),
                suggested_action="Check the section total range covers every line."))
    sections = sum(b.section_totals.values())
    if b.contingency and sections:
        expected = sections * contingency_pct
        if abs(b.contingency - expected) > _TOL:
            out.append(AuditFinding(
                rule="CONTINGENCY", severity="medium", building=b.name, location="Summary",
                message=f"Contingency R {b.contingency:,.2f} ≠ {contingency_pct:.0%} of sections (R {expected:,.2f})",
                value_at_risk_zar=abs(b.contingency - expected),
                suggested_action="Recompute the contingency on the final section totals."))
    if b.total_excl_vat:
        expected = (sections + b.contingency) if b.section_totals else sum(l.value for l in b.lines)
        if abs(b.total_excl_vat - expected) > _TOL:
            out.append(AuditFinding(
                rule="TOTAL", severity="high", building=b.name, location="TOTAL Exl VAT",
                message=f"Total R {b.total_excl_vat:,.2f} ≠ sections + contingency R {expected:,.2f}",
                value_at_risk_zar=abs(b.total_excl_vat - expected),
                suggested_action="Include every section and the contingency in the total."))
    for e in b.errors:
        out.append(AuditFinding(
            rule="ERROR_CELL", severity="high", building=b.name, location=e,
            message=f"Spreadsheet error: {e}",
            suggested_action="Repair the broken reference; totals depending on it are invalid."))
    return out


def _companion_rules(b: RefBuilding) -> List[AuditFinding]:
    out: List[AuditFinding] = []
    specs = sorted({l.key_spec for l in b.lines if l.key_family == "swa_cable" and l.role != "install"})
    has_earth = any(l.key_family == "bcew" and not l.key_spec.startswith("1.5") and
                    not l.key_spec.startswith("2.5") for l in b.lines)
    for spec in specs:
        size = spec.split("|", 1)[0]
        missing = []
        split = any(l.key_family == "swa_cable" and l.key_spec == spec and l.role == "supply" for l in b.lines)
        if split and not any(l.key_family == "swa_cable" and l.key_spec == spec and l.role == "install" for l in b.lines):
            missing.append("install line")
        if not any(l.key_family == "termination" and l.key_spec.split("|")[-1] == size for l in b.lines):
            missing.append("terminations (2 per run)")
        if not has_earth:
            missing.append("BCEW earth conductor")
        if missing:
            value = sum(l.value for l in b.lines if l.key_family == "swa_cable" and l.key_spec == spec)
            out.append(AuditFinding(
                rule="COMPANION", severity="medium", building=b.name, location=f"SWA {spec}",
                message=f"Feeder {spec} has no {', '.join(missing)}".replace("BCEW earth", "earth (BCEW)"),
                value_at_risk_zar=0.0 if value == 0 else value * 0.1,
                suggested_action="Every feeder needs supply+install, an earth and a termination at each end."))
    return out


def _audit_building(b: RefBuilding, rates: Dict[str, float], contingency_pct: float) -> List[AuditFinding]:
    return (_line_rules(b, rates) + _duplicate_rules(b)
            + _rollup_rules(b, contingency_pct) + _companion_rules(b))


# ─── entry points ────────────────────────────────────────────────────

def audit_reference(ref: ReferenceBoq, *, contingency_pct: float = 0.05) -> List[AuditFinding]:
    """Audit a parsed human bill: every building sheet + the project summary."""
    rates = _rate_lookup(ref)
    out: List[AuditFinding] = []
    for b in ref.buildings:
        building_findings = _audit_building(b, rates, contingency_pct)
        if b.in_summary or not (b.lines or b.total_excl_vat):
            out += building_findings
            continue
        # An orphan sheet: one finding carrying its (estimated) value, instead of a
        # NO_RATE line per item restating the same fact.
        unpriced = [f for f in building_findings if f.rule == "NO_RATE"]
        out += [f for f in building_findings if f.rule != "NO_RATE"]
        priced = sum(l.value for l in b.lines)
        estimated = sum(f.value_at_risk_zar for f in unpriced)
        detail = f"{len(b.lines)} quantified lines, priced R {priced:,.2f}"
        if unpriced:
            detail += f"; {len(unpriced)} unpriced lines ≈ R {estimated:,.2f} at median reference rates"
        out.append(AuditFinding(
            rule="NOT_IN_SUMMARY", severity="high", building=b.name, location=f"sheet '{b.sheet.strip()}'",
            message=f"Bill sheet not rolled into the project summary ({detail})",
            value_at_risk_zar=(b.total_excl_vat or priced) + estimated,
            suggested_action="Add it to the summary, or mark it as an excluded alternative / superseded sheet."))
    for name, amount in ref.summary.items():
        b = ref.building(name)
        if b is not None and b.total_excl_vat and abs(b.total_excl_vat - amount) > _TOL:
            out.append(AuditFinding(
                rule="SUMMARY", severity="high", building=b.name, location="Summary sheet",
                message=f"Summary shows R {amount:,.2f}, building sheet totals R {b.total_excl_vat:,.2f}",
                value_at_risk_zar=abs(b.total_excl_vat - amount),
                suggested_action="Link the summary cell to the building total."))
    if ref.summary and ref.summary_total_excl_vat:
        summed = sum(ref.summary.values())
        if abs(summed - ref.summary_total_excl_vat) > _TOL:
            out.append(AuditFinding(
                rule="SUMMARY", severity="high", building="(project)", location="Summary sheet",
                message=f"Summary lines add to R {summed:,.2f}, total states R {ref.summary_total_excl_vat:,.2f}",
                value_at_risk_zar=abs(summed - ref.summary_total_excl_vat),
                suggested_action="Fix the summary total range."))
    order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    return sorted(out, key=lambda f: (order[f.severity], -f.value_at_risk_zar))


def building_from_boq(boq: BillOfQuantities, *, building: str) -> RefBuilding:
    """Adapt a pipeline BillOfQuantities to the audit/reference line model."""
    lines = []
    for ln in boq.line_items:
        key = classify_item(ln.description, unit=ln.unit)
        role = ln.line_kind.value if ln.line_kind.value in ("supply", "install") else line_role(ln.description)
        lines.append(RefLine(
            sheet=boq.pipeline, building=building, bill_section=BILL_SECTION_OF.get(key.family, "X"),
            code=ln.item_number_str, description=ln.description, unit=ln.unit, qty=ln.qty,
            rate=ln.unit_price_zar or None, total=ln.total_zar if ln.unit_price_zar else None,
            key_family=key.family, key_spec=key.spec, role=role,
        ))
    return RefBuilding(name=building, sheet=boq.pipeline, lines=lines, in_summary=True)


def audit_boq(boq: BillOfQuantities, *, building: str = "", reference: Optional[ReferenceBoq] = None,
              contingency_pct: float = 0.05) -> List[AuditFinding]:
    """Audit a pipeline-produced bill (line-level + companion rules)."""
    b = building_from_boq(boq, building=building or boq.project_name or boq.pipeline)
    rates = _rate_lookup(reference)
    return _line_rules(b, rates) + _duplicate_rules(b) + _companion_rules(b)
