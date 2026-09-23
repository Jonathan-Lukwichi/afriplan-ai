"""
FROZEN SCORER — do not edit inside an optimisation loop (autoresearch/program.md).

Scores a predicted BOQ against a reference BOQ. Changing this file changes what
"better" means; any change needs a new ADR and a re-run of every baseline.

Matching
    Lines are matched on (building, ItemKey). Roles are collapsed: a reference
    Supply+Install pair and a predicted combined line are the same item.
      physical qty = Σ qty of supply + combined lines (install rows repeat the qty)
      value        = Σ value of all roles

Metrics (all in [0, 1]; value-weighted by the REFERENCE value of each item)
    coverage            share of reference value whose item was predicted at all
    precision           share of predicted value that lands on a reference item
    qty_accuracy        Σ w·max(0, 1-|q̂-q|/q) over matched items / Σ w matched
    rate_accuracy       same on the unit rate (value / qty)
    total_accuracy      max(0, 1-|T̂-T|/T) on the scored buildings' line totals
    reproduction_score  Σ w·matched·qty_acc / Σ w      ← the headline number

Every metric is also reported "scoped": restricted to reference items that are
reproducible from the drawing types actually uploaded (evaluation.network). The
gap between full and scoped coverage is what the missing drawings cost.
"""

from __future__ import annotations

from typing import Dict, Iterable, List, Mapping, Optional, Set, Tuple, Union

from pydantic import BaseModel, Field

from agent.shared import BillOfQuantities
from evaluation.network import DrawingType, reproducible
from evaluation.reference import RefLine, ReferenceBoq
from evaluation.taxonomy import classify_item, line_role


class PredLine(BaseModel):
    building: str
    family: str
    spec: str = ""
    role: str = "combined"
    qty: float = 0.0
    rate: float = 0.0
    total: float = 0.0
    description: str = ""


class ItemScore(BaseModel):
    building: str
    key: str
    ref_qty: float = 0.0
    pred_qty: float = 0.0
    ref_value: float = 0.0
    pred_value: float = 0.0
    matched: bool = False
    qty_acc: float = 0.0
    rate_acc: float = 0.0
    in_scope: bool = False
    label: str = ""

    @property
    def ref_rate(self) -> float:
        return self.ref_value / self.ref_qty if self.ref_qty else 0.0

    @property
    def pred_rate(self) -> float:
        return self.pred_value / self.pred_qty if self.pred_qty else 0.0


class Scorecard(BaseModel):
    project: str
    pipeline: str = ""
    buildings: List[str] = Field(default_factory=list)
    uploaded: Dict[str, List[str]] = Field(default_factory=dict)
    items: List[ItemScore] = Field(default_factory=list)
    coverage: float = 0.0
    coverage_items: float = 0.0          # unweighted: share of reference items predicted
    precision: float = 0.0
    qty_accuracy: float = 0.0
    rate_accuracy: float = 0.0
    total_accuracy: float = 0.0
    reproduction_score: float = 0.0
    reference_value: float = 0.0
    predicted_value: float = 0.0
    scoped: Dict[str, float] = Field(default_factory=dict)
    per_building: Dict[str, Dict[str, float]] = Field(default_factory=dict)
    unmatched_reference: List[str] = Field(default_factory=list)
    unmatched_predicted: List[str] = Field(default_factory=list)


# ─── adapters ────────────────────────────────────────────────────────

def pred_lines_from_boq(boq: BillOfQuantities, *, building: str) -> List[PredLine]:
    """Any pipeline's BillOfQuantities → PredLines attributed to one building."""
    out: List[PredLine] = []
    for ln in boq.line_items:
        key = classify_item(ln.description, unit=ln.unit)
        role = ln.line_kind.value if ln.line_kind.value in ("supply", "install") else line_role(ln.description)
        out.append(PredLine(
            building=building, family=key.family, spec=key.spec, role=role, qty=ln.qty,
            rate=ln.unit_price_zar, total=ln.total_zar or ln.qty * ln.unit_price_zar,
            description=ln.description,
        ))
    return out


def pred_lines_from_reference(ref: ReferenceBoq, buildings: Optional[Iterable[str]] = None) -> List[PredLine]:
    """The reference as if it were a prediction — the scorer's self-test."""
    want = set(buildings) if buildings is not None else None
    return [
        PredLine(building=l.building, family=l.key_family, spec=l.key_spec, role=l.role,
                 qty=l.qty, rate=l.rate or 0.0, total=l.value, description=l.description)
        for b in ref.billed_buildings() if want is None or b.name in want
        for l in b.lines
    ]


# ─── aggregation ─────────────────────────────────────────────────────

_Agg = Dict[Tuple[str, str], Dict[str, float]]


def _key(family: str, spec: str) -> str:
    return f"{family}|{spec}" if spec else family


def _aggregate(rows: Iterable[Tuple[str, str, str, float, float]]) -> _Agg:
    """rows: (building, key, role, qty, value) → {(building,key): {qty, value}}"""
    agg: _Agg = {}
    for bld, key, role, qty, value in rows:
        slot = agg.setdefault((bld, key), {"qty": 0.0, "value": 0.0})
        if role != "install":
            slot["qty"] += qty
        slot["value"] += value
    return agg


def _acc(pred: float, actual: float) -> float:
    if actual <= 0:
        return 1.0 if pred <= 0 else 0.0
    return max(0.0, 1.0 - abs(pred - actual) / actual)


def _metrics(items: List[ItemScore]) -> Dict[str, float]:
    ref_items = [i for i in items if i.ref_value > 0 or i.ref_qty > 0]
    ref_value = sum(i.ref_value for i in ref_items)
    pred_value = sum(i.pred_value for i in items)
    matched = [i for i in ref_items if i.matched]
    w_matched = sum(i.ref_value for i in matched)

    def wmean(attr: str) -> float:
        if not matched:
            return 0.0
        if w_matched <= 0:
            return sum(getattr(i, attr) for i in matched) / len(matched)
        return sum(i.ref_value * getattr(i, attr) for i in matched) / w_matched

    rs = (sum(i.ref_value * i.qty_acc for i in matched) / ref_value) if ref_value else 0.0
    return {
        "coverage": (w_matched / ref_value) if ref_value else 0.0,
        "coverage_items": (len(matched) / len(ref_items)) if ref_items else 0.0,
        "precision": (sum(i.pred_value for i in items if i.matched) / pred_value) if pred_value else 0.0,
        "qty_accuracy": wmean("qty_acc"),
        "rate_accuracy": wmean("rate_acc"),
        "total_accuracy": _acc(pred_value, ref_value),
        "reproduction_score": rs,
        "reference_value": ref_value,
        "predicted_value": pred_value,
    }


# ─── the scorer ──────────────────────────────────────────────────────

Uploaded = Union[Set[DrawingType], Mapping[str, Set[DrawingType]]]


def score(
    pred: List[PredLine],
    ref: ReferenceBoq,
    *,
    uploaded: Uploaded,
    pipeline: str = "",
    buildings: Optional[Iterable[str]] = None,
) -> Scorecard:
    """
    Score predicted lines against the reference's billed buildings (or the
    `buildings` subset). `uploaded` is the set of drawing types available —
    one set for all buildings, or a {building: set} mapping.
    """
    names = list(buildings) if buildings is not None else [b.name for b in ref.billed_buildings()]
    wanted = set(names)
    ref_lines: List[RefLine] = [l for b in ref.buildings if b.name in wanted for l in b.lines]
    labels = {(l.building, l.key): l.label for l in ref_lines}

    ref_agg = _aggregate((l.building, l.key, l.role, l.qty, l.value) for l in ref_lines)
    pred_agg = _aggregate((p.building, _key(p.family, p.spec), p.role, p.qty, p.total)
                          for p in pred if p.building in wanted)

    def up_for(bld: str) -> Set[DrawingType]:
        return set(uploaded.get(bld, set())) if isinstance(uploaded, Mapping) else set(uploaded)

    items: List[ItemScore] = []
    for (bld, key) in sorted(set(ref_agg) | set(pred_agg)):
        r = ref_agg.get((bld, key), {"qty": 0.0, "value": 0.0})
        p = pred_agg.get((bld, key), {"qty": 0.0, "value": 0.0})
        in_ref = (bld, key) in ref_agg
        matched = in_ref and (bld, key) in pred_agg
        r_rate = r["value"] / r["qty"] if r["qty"] else 0.0
        p_rate = p["value"] / p["qty"] if p["qty"] else 0.0
        items.append(ItemScore(
            building=bld, key=key, ref_qty=r["qty"], pred_qty=p["qty"],
            ref_value=r["value"], pred_value=p["value"], matched=matched,
            qty_acc=_acc(p["qty"], r["qty"]) if matched else 0.0,
            rate_acc=_acc(p_rate, r_rate) if matched and r_rate else 0.0,
            in_scope=reproducible(key.split("|", 1)[0], up_for(bld)),
            label=labels.get((bld, key), ""),
        ))

    full = _metrics(items)
    scoped = _metrics([i for i in items if i.in_scope])
    card = Scorecard(
        project=ref.project, pipeline=pipeline, buildings=names,
        uploaded={b: sorted(d.value for d in up_for(b)) for b in names},
        items=items, scoped=scoped,
        **{k: v for k, v in full.items() if k in Scorecard.model_fields},
    )
    card.per_building = {b: _metrics([i for i in items if i.building == b]) for b in names}
    card.unmatched_reference = [
        f"{i.building} | {i.key} | R {i.ref_value:,.0f}"
        for i in sorted(items, key=lambda i: -i.ref_value) if not i.matched and i.ref_value > 0
    ]
    card.unmatched_predicted = [
        f"{i.building} | {i.key} | R {i.pred_value:,.0f}"
        for i in sorted(items, key=lambda i: -i.pred_value)
        if i.pred_value > 0 and not (i.ref_value > 0 or i.ref_qty > 0)
    ]
    return card
