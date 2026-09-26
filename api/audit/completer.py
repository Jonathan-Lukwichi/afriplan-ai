"""
BOQ completer — add the derived items pipelines never calculate.

Pipelines count what is DRAWN (sockets, lights, switches, feeders). A real bill
also carries what an estimator DERIVES from those counts: flush wall boxes,
chasing, conduit, GP wire, terminations, trench… On Wedela those derived items
are a large share of every building bill and were entirely absent from pipeline
output.

For each fitted ratio (evaluation.ratios) whose target family is missing from the
bill and whose leave-one-building-out error is within `max_loo_error`, add an
INFERRED line with the ratio and its error written into the assumption, plus a
low-severity gap. A ratio too unreliable to use becomes a gap, not a number.
The input bill is never mutated.
"""

from __future__ import annotations

import math
from typing import Dict, List

from agent.shared import (
    BillOfQuantities,
    BQLineItem,
    BQSection,
    GapItem,
    ItemConfidence,
    LineKind,
)
from evaluation.metrics import pred_lines_from_boq
from evaluation.ratios import Ratio, RatioModel, input_total

DEFAULT_MAX_LOO_ERROR = 0.35

_SECTION_OF_FAMILY: Dict[str, BQSection] = {
    "wall_box": BQSection.POWER_OUTLETS, "extension_box": BQSection.POWER_OUTLETS,
    "waterproof_box": BQSection.POWER_OUTLETS, "chasing": BQSection.CONTAINMENT,
    "conduit": BQSection.CONTAINMENT, "draw_wire": BQSection.CONTAINMENT,
    "round_box": BQSection.CONTAINMENT, "trunking": BQSection.CONTAINMENT,
    "trunking_cover": BQSection.CONTAINMENT, "gp_wire": BQSection.FINAL_CABLES,
    "bcew": BQSection.EARTHING, "termination": BQSection.SUBMAIN_CABLES,
    "trench": BQSection.UNDERGROUND, "warning_tape": BQSection.UNDERGROUND,
}

_LABELS: Dict[str, str] = {
    "wall_box|100x100": "100x100 flush wall box (outlets)",
    "wall_box|100x50": "100x50 flush wall box (switches)",
    "chasing|*": "Wall chasing for conduit drops",
    "conduit|*": "PVC conduit with accessories",
    "draw_wire|*": "Draw wire (5 kg)",
    "round_box|*": "PVC round looping box",
    "gp_wire|1.5mm2": "1.5mm² GP wire (lighting)",
    "gp_wire|2.5mm2": "2.5mm² GP wire (power)",
    "bcew|1.5mm2": "1.5mm² BCEW circuit earth",
    "trunking|*": "Trunking with mounting accessories",
    "trunking_cover|*": "Trunking covers",
    "termination|*": "Cable terminations (glands, shrouds, lugs)",
    "trench|*": "Cable trench + reinstatement",
    "warning_tape|*": "Warning tape 300 mm above cable",
}

_COUNT_UNITS = {"no", "ea", "each", "nr"}


def _primary_counts(boq: BillOfQuantities, building: str) -> Dict[str, float]:
    counts: Dict[str, float] = {}
    runs = set()
    for p in pred_lines_from_boq(boq, building=building):
        if p.role == "install":
            continue
        key = f"{p.family}|{p.spec}"
        counts[key] = counts.get(key, 0.0) + p.qty
        if p.family == "swa_cable":
            runs.add((p.spec, p.description))
    counts["#swa_cable"] = float(len(runs))
    return counts


def _qty(ratio: Ratio, raw: float) -> float:
    if ratio.unit.strip().lower() in _COUNT_UNITS:
        return float(math.ceil(raw - 1e-9))
    return round(raw, 1)


def complete_boq(
    boq: BillOfQuantities,
    model: RatioModel,
    *,
    building: str = "",
    max_loo_error: float = DEFAULT_MAX_LOO_ERROR,
) -> BillOfQuantities:
    """Return a clone of `boq` with fitted derived items added (INFERRED, gapped)."""
    out = boq.model_copy(deep=True)
    counts = _primary_counts(out, building)
    present = {p.family for p in pred_lines_from_boq(out, building=building)}
    added: List[BQLineItem] = []

    for r in model.ratios:
        if r.target_family in present:
            continue
        x = input_total(counts, r.inputs)
        if x <= 0:
            continue
        label = _LABELS.get(r.target, r.target.replace("_", " "))
        section = _SECTION_OF_FAMILY.get(r.target_family, BQSection.FINAL_CABLES)
        err = "n/a" if r.loo_mape is None else f"{r.loo_mape:.0%}"
        if r.loo_mape is None or r.loo_mape > max_loo_error:
            out.gaps.append(GapItem(
                section=section, building_block=building,
                description=f"{label}: not inferred — fitted ratio too unreliable (LOO error {err})",
                assumption=f"Would be {r.weight:.3g} × {x:g} input items; error above {max_loo_error:.0%}.",
                suggested_action="Measure this item from the drawings.", severity="medium",
            ))
            continue
        qty = _qty(r, r.weight * x)
        if qty <= 0:
            continue
        assumption = (f"Fitted ratio {r.weight:.3g} × {x:g} ({' + '.join(i.rstrip('|*') for i in r.inputs)}); "
                      f"leave-one-building-out error {err}, n={r.n} ({', '.join(model.project_sources)}). Verify.")
        added.append(BQLineItem(
            section=section, description=f"{label} (inferred)", unit=r.unit or "No", qty=qty,
            unit_price_zar=r.rate_zar, total_zar=round(qty * r.rate_zar, 2),
            source=ItemConfidence.INFERRED, line_kind=LineKind.COMBINED,
            building_block=building, assumption=assumption, drawing_ref="ratio model",
        ))
        out.gaps.append(GapItem(
            section=section, building_block=building,
            description=f"{label}: quantity inferred, not measured",
            assumption=assumption, suggested_action="Confirm against the layout drawings.",
            severity="low",
        ))

    out.line_items.extend(added)
    _renumber_and_total(out)
    return out


def _renumber_and_total(boq: BillOfQuantities) -> None:
    boq.line_items.sort(key=lambda l: l.section.section_number)
    counters: Dict[int, int] = {}
    for ln in boq.line_items:
        n = ln.section.section_number
        counters[n] = counters.get(n, 0) + 1
        ln.item_no = counters[n]
    subtotal = round(sum(l.total_zar for l in boq.line_items), 2)
    contingency = round(subtotal * boq.contingency_pct / 100.0, 2)
    excl = round(subtotal + contingency + boq.markup_zar, 2)
    vat = round(excl * boq.vat_pct / 100.0, 2)
    boq.subtotal_zar, boq.contingency_zar = subtotal, contingency
    boq.total_excl_vat_zar, boq.vat_zar = excl, vat
    boq.total_incl_vat_zar = round(excl + vat, 2)
    boq.items_inferred = sum(1 for l in boq.line_items if l.source == ItemConfidence.INFERRED)
