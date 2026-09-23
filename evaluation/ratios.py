"""
Fitted derived-item ratios — the "weights" of the layered BOQ network.

Items like wall boxes, chasing, conduit, GP wire and terminations are never drawn
as symbols; an estimator derives them from the things that ARE drawn (sockets,
switches, lights, feeder runs). We learn those relationships from a priced
reference bill instead of hard-coding them:

    qty(target)  ≈  weight × Σ qty(inputs)          least squares through the origin

and report the leave-one-building-out (LOO) mean absolute percentage error, so
every fitted ratio carries an honest "how well does this generalise to a building
it has not seen" number. With one project that is the only defensible form of
learning (a neural net on ~6 buildings would memorise, not learn — ADR-0004).

Keys:  "family|spec"  exact item        "family|*"  all specs of a family
       "#family"      number of distinct lines (e.g. cable runs → terminations)
"""

from __future__ import annotations

import statistics
from typing import Dict, List, Optional, Sequence, Tuple

from pydantic import BaseModel, Field

from evaluation.reference import RefBuilding, ReferenceBoq
from evaluation.taxonomy import BILL_SECTION_OF

_LIGHTS = ["light_panel|*", "light_flood|*", "light_vapour_proof|*", "light_bulkhead|*",
           "light_downlight|*", "light_other|*"]
_SOCKETS = ["socket_double|*", "socket_single|*"]
_SWITCHES = ["switch|*", "day_night_switch|*"]

# (target, inputs) — the derived items the pipelines never emit today.
DEFAULT_RATIO_SPECS: List[Tuple[str, List[str]]] = [
    ("wall_box|100x100", _SOCKETS + ["isolator|*"]),
    ("wall_box|100x50", _SWITCHES),
    ("chasing|*", _SOCKETS + ["isolator|*"] + _SWITCHES),
    ("conduit|*", _LIGHTS + _SOCKETS + _SWITCHES),
    ("draw_wire|*", _SOCKETS),
    ("round_box|*", _LIGHTS),
    ("gp_wire|1.5mm2", _LIGHTS),
    ("gp_wire|2.5mm2", _SOCKETS),
    ("bcew|1.5mm2", _LIGHTS),
    ("trunking|*", _LIGHTS),
    ("trunking_cover|*", _LIGHTS),
    ("termination|*", ["#swa_cable"]),
    ("trench|*", ["swa_cable|*"]),
    ("warning_tape|*", ["swa_cable|*"]),
]


class Ratio(BaseModel):
    target: str
    inputs: List[str]
    weight: float
    n: int                              # buildings used in the fit
    loo_mape: Optional[float] = None    # None when n < 3 (no honest hold-out possible)
    unit: str = ""
    rate_zar: float = 0.0               # median reference rate of the target (for the completer)
    bill_section: str = ""

    @property
    def target_family(self) -> str:
        return self.target.split("|", 1)[0]


class RatioModel(BaseModel):
    project_sources: List[str] = Field(default_factory=list)
    ratios: List[Ratio] = Field(default_factory=list)

    def predict(self, primary_counts: Dict[str, float]) -> Dict[str, float]:
        """primary_counts: 'family|spec' -> qty (as produced by building_quantities)."""
        return {r.target: r.weight * input_total(primary_counts, r.inputs) for r in self.ratios}


# ─── quantities per building ─────────────────────────────────────────

def building_quantities(b: RefBuilding) -> Dict[str, float]:
    """
    'family|spec' -> qty, plus 'family|*' family totals and '#family' line counts.
    Install rows are skipped: a Supply/Install pair is ONE physical quantity.
    """
    q: Dict[str, float] = {}
    runs: Dict[str, set] = {}
    for l in b.lines:
        if l.role == "install":
            continue
        exact = f"{l.key_family}|{l.key_spec}"
        q[exact] = q.get(exact, 0.0) + l.qty
        fam = f"{l.key_family}|*"
        q[fam] = q.get(fam, 0.0) + l.qty
        runs.setdefault(l.key_family, set()).add((l.key_spec, l.code, l.raw_row))
    for fam, members in runs.items():
        q[f"#{fam}"] = float(len(members))
    return q


def input_total(counts: Dict[str, float], inputs: Sequence[str]) -> float:
    """Σ over input patterns; 'family|*' sums every spec of the family."""
    total = 0.0
    for pat in inputs:
        if pat.startswith("#"):
            total += counts.get(pat, 0.0)
        elif pat.endswith("|*"):
            fam = pat[:-2]
            if pat in counts:
                total += counts[pat]
            else:
                total += sum(v for k, v in counts.items()
                             if k.split("|", 1)[0] == fam and not k.endswith("|*"))
        else:
            total += counts.get(pat, 0.0)
    return total


def _target_qty(q: Dict[str, float], target: str) -> float:
    return q.get(target, 0.0)


# ─── fitting ─────────────────────────────────────────────────────────

def _fit(xs: List[float], ys: List[float]) -> float:
    sxx = sum(x * x for x in xs)
    return sum(x * y for x, y in zip(xs, ys)) / sxx if sxx else 0.0


def _loo_mape(xs: List[float], ys: List[float]) -> Optional[float]:
    if len(xs) < 3:
        return None
    errs = []
    for i in range(len(xs)):
        w = _fit(xs[:i] + xs[i + 1:], ys[:i] + ys[i + 1:])
        pred, actual = w * xs[i], ys[i]
        errs.append(abs(pred - actual) / actual if actual else (1.0 if pred else 0.0))
    return round(sum(errs) / len(errs), 4)


def _target_meta(ref: ReferenceBoq, target: str) -> Tuple[str, float]:
    fam, _, spec = target.partition("|")
    lines = [l for b in ref.billed_buildings() for l in b.lines
             if l.key_family == fam and (spec in ("*", "") or l.key_spec == spec)
             and l.role != "install"]
    rates = [l.rate for l in lines if l.rate]
    unit = statistics.mode([l.unit for l in lines]) if lines else ""
    return unit, (round(statistics.median(rates), 2) if rates else 0.0)


def fit_ratios(ref: ReferenceBoq, specs: Sequence[Tuple[str, List[str]]] = DEFAULT_RATIO_SPECS) -> RatioModel:
    """Fit every (target ← inputs) ratio across the reference's billed buildings."""
    per_building = [building_quantities(b) for b in ref.billed_buildings()]
    ratios: List[Ratio] = []
    for target, inputs in specs:
        xs, ys = [], []
        for q in per_building:
            x = input_total(q, inputs)
            if x > 0:
                xs.append(x)
                ys.append(_target_qty(q, target))
        if not xs:
            continue
        unit, rate = _target_meta(ref, target)
        ratios.append(Ratio(
            target=target, inputs=list(inputs), weight=round(_fit(xs, ys), 4), n=len(xs),
            loo_mape=_loo_mape(xs, ys), unit=unit, rate_zar=rate,
            bill_section=BILL_SECTION_OF.get(target.split("|", 1)[0], ""),
        ))
    return RatioModel(project_sources=[ref.project], ratios=ratios)


def load_ratio_model(project: str) -> RatioModel:
    from evaluation.dataset import project_dir
    return RatioModel.model_validate_json(
        (project_dir(project) / "ratio_model.json").read_text(encoding="utf-8")
    )
