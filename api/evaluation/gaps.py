"""
Where the Reproduction Score is lost — read-only analysis of a Scorecard.

The frozen scorer (metrics.py) gives the headline; this module explains it. Every
reference item i loses

    points_lost_i = w_i · (1 − matched_i · qty_acc_i) / Σ w        (w = reference value)

so the points lost add up to exactly 1 − RS. Each loss gets a cause —
not_produced / qty_low / qty_high — and the kind of fix it needs, from the BOQ network
(how the item is obtained: counted, measured, derived, or never on a drawing).
Rates do not enter RS, so rate errors are listed separately (they move the bill total).
Nothing here changes what "better" means (ADR-0003).
"""

from __future__ import annotations

from typing import Dict, List

from pydantic import BaseModel, Field

from evaluation.metrics import ItemScore, Scorecard
from evaluation.network import NETWORK, DrawingType, Method, missing_for
from evaluation.taxonomy import BILL_SECTION_OF

RATE_TOLERANCE = 0.9            # rate accuracy below this is listed as a rate error
CAUSES = ("not_produced", "qty_low", "qty_high")


class ItemLoss(BaseModel):
    building: str
    key: str
    family: str
    section: str
    method: str
    label: str = ""
    cause: str                  # exact | not_produced | qty_low | qty_high
    in_scope: bool
    ref_qty: float
    pred_qty: float
    ref_value: float
    pred_value: float
    ref_rate: float
    pred_rate: float
    qty_acc: float
    rate_acc: float
    points_lost: float          # share of the whole score (0..1) lost on this item
    fix: str = ""


class GroupLoss(BaseModel):
    name: str
    ref_share: float = 0.0      # share of the reference value in this group
    points_lost: float = 0.0
    not_produced: float = 0.0
    qty_low: float = 0.0
    qty_high: float = 0.0


class Extra(BaseModel):
    building: str
    key: str
    family: str
    pred_qty: float
    pred_value: float


class GapAnalysis(BaseModel):
    reproduction_score: float
    reference_value: float
    predicted_value: float
    by_cause: Dict[str, float] = Field(default_factory=dict)
    by_family: List[GroupLoss] = Field(default_factory=list)
    by_section: List[GroupLoss] = Field(default_factory=list)
    by_method: List[GroupLoss] = Field(default_factory=list)
    items: List[ItemLoss] = Field(default_factory=list)          # biggest loss first
    rate_errors: List[ItemLoss] = Field(default_factory=list)    # biggest rand effect first
    extras: List[Extra] = Field(default_factory=list)            # biggest value first


def _method(family: str) -> str:
    node = NETWORK.get(family)
    return node.method.value if node else Method.PROVISIONAL.value


def _cause(i: ItemScore) -> str:
    if not i.matched:
        return "not_produced"
    if i.qty_acc >= 1.0 - 1e-9:
        return "exact"
    return "qty_low" if i.pred_qty < i.ref_qty else "qty_high"


def _fix(family: str, method: str, cause: str, in_scope: bool, uploaded: set) -> str:
    if cause == "exact":
        return ""
    hint = _fix_kind(family, method, cause, in_scope, uploaded)
    note = NETWORK[family].note if family in NETWORK else ""
    return f"{hint} ({note})" if note else hint


def _fix_kind(family: str, method: str, cause: str, in_scope: bool, uploaded: set) -> str:
    if method in (Method.PROVISIONAL.value, Method.PRELIMS.value):
        return "never on a drawing — add it as a rule / provisional sum, not by reading harder"
    if not in_scope:
        need = sorted(d.value for d in missing_for([family], uploaded))
        return f"the uploaded drawings cannot show it — needs a {' or '.join(need) or 'further'} drawing"
    if cause == "not_produced":
        return {
            Method.COUNT.value: "drawn but never reported — add a form box / symbol name / taxonomy wording",
            Method.LENGTH.value: "run never read or measured",
            Method.DERIVED.value: "derived item not generated — add a completer rule or ratio",
        }.get(method, "never reported")
    over = cause == "qty_high"
    return {
        Method.COUNT.value: ("count too high — duplicates across sheets / legend glyphs counted"
                             if over else "count too low — symbols missed or sheets not read"),
        Method.LENGTH.value: ("length too long — check scale and route" if over
                              else "length too short — measure the route on the site plan, not an assumed length"),
        Method.DERIVED.value: "derived quantity off — the ratio from its primary items needs refitting",
    }.get(method, "quantity off")


def _group(items: List[ItemLoss], attr: str, ref_total: float) -> List[GroupLoss]:
    groups: Dict[str, GroupLoss] = {}
    for i in items:
        g = groups.setdefault(getattr(i, attr), GroupLoss(name=getattr(i, attr)))
        g.ref_share += i.ref_value / ref_total if ref_total else 0.0
        g.points_lost += i.points_lost
        if i.cause in CAUSES:
            setattr(g, i.cause, getattr(g, i.cause) + i.points_lost)
    return sorted(groups.values(), key=lambda g: -g.points_lost)


def analyse_gaps(card: Scorecard) -> GapAnalysis:
    uploaded_by_b = {b: set(v) for b, v in card.uploaded.items()}
    ref_items = [i for i in card.items if i.ref_value > 0 or i.ref_qty > 0]
    ref_total = sum(i.ref_value for i in ref_items)
    losses: List[ItemLoss] = []
    for i in ref_items:
        family = i.key.split("|", 1)[0]
        method, cause = _method(family), _cause(i)
        uploaded = {DrawingType(v) for v in uploaded_by_b.get(i.building, set())}
        losses.append(ItemLoss(
            building=i.building, key=i.key, family=family, section=BILL_SECTION_OF.get(family, "X"),
            method=method, label=i.label, cause=cause, in_scope=i.in_scope,
            ref_qty=i.ref_qty, pred_qty=i.pred_qty, ref_value=i.ref_value, pred_value=i.pred_value,
            ref_rate=i.ref_rate, pred_rate=i.pred_rate, qty_acc=i.qty_acc, rate_acc=i.rate_acc,
            points_lost=(i.ref_value * (1.0 - (i.qty_acc if i.matched else 0.0)) / ref_total) if ref_total else 0.0,
            fix=_fix(family, method, cause, i.in_scope, uploaded),
        ))
    losses.sort(key=lambda l: -l.points_lost)
    rate_errors = sorted((l for l in losses if l.cause != "not_produced" and l.ref_rate
                          and l.rate_acc < RATE_TOLERANCE),
                         key=lambda l: -abs(l.pred_qty * (l.pred_rate - l.ref_rate)))
    extras = sorted((Extra(building=i.building, key=i.key, family=i.key.split("|", 1)[0],
                           pred_qty=i.pred_qty, pred_value=i.pred_value)
                     for i in card.items if i.pred_value > 0 and not (i.ref_value > 0 or i.ref_qty > 0)),
                    key=lambda e: -e.pred_value)
    by_cause = {c: sum(l.points_lost for l in losses if l.cause == c) for c in CAUSES}
    return GapAnalysis(
        reproduction_score=card.reproduction_score, reference_value=card.reference_value,
        predicted_value=card.predicted_value, by_cause=by_cause,
        by_family=_group(losses, "family", ref_total), by_section=_group(losses, "section", ref_total),
        by_method=_group(losses, "method", ref_total), items=losses, rate_errors=rate_errors, extras=extras,
    )
