"""
Reading accuracy — did we read what is DRAWN? Read-only view of a Scorecard; prices play no part.

A bill mixes three kinds of line, and only the first is "reading":
  read      counted symbols and measured runs that appear on the uploaded drawings
            (network method count / length, and the drawing type it needs was uploaded)
  derived   follows from other items by an estimating rule (wire, conduit, boxes, trench)
  provisional  never on any drawing (connection fees, CoC, P&Gs)
Items whose drawing type was not uploaded (a manhole without the site plan) cannot be read either.

Judged on the `read` items only:
  reading_score   Σ w·found·qty_acc / Σ w   (w = the item's value in the REAL bill — what it is
                  worth to get right; our own rates never enter)
  coverage        Σ w·found / Σ w;  qty_accuracy  weighted qty accuracy on found items
  items_*         plain counts: judged, found, within ±5 % / ±10 % of the real quantity
  item_precision  of the read-type items we produced, the share that are in the real bill (by count)
"""

from __future__ import annotations

from typing import Dict, List

from evaluation.metrics import ItemScore, Scorecard
from evaluation.network import NETWORK, Method

READ_METHODS = (Method.COUNT, Method.LENGTH)


def _method(key: str) -> Method:
    node = NETWORK.get(key.split("|", 1)[0])
    return node.method if node else Method.PROVISIONAL


def _in_ref(i: ItemScore) -> bool:
    return i.ref_value > 0 or i.ref_qty > 0


def _verdict(i: ItemScore) -> str:
    if not i.matched:
        return "not read"
    if not i.ref_qty:
        return "read"
    dev = (i.pred_qty - i.ref_qty) / i.ref_qty
    if abs(dev) < 0.005:
        return "exact"
    return f"read {abs(dev):.0%} {'over' if dev > 0 else 'short'}".replace("%", " %")


def _bucket(i: ItemScore) -> str:
    m = _method(i.key)
    if m == Method.DERIVED:
        return "derived"
    if m in (Method.PROVISIONAL, Method.PRELIMS):
        return "provisional"
    return "read" if i.in_scope else "not_on_uploaded_drawings"


def reading_accuracy(card: Scorecard) -> dict:
    ref_items = [i for i in card.items if _in_ref(i)]
    total_value = sum(i.ref_value for i in ref_items)
    groups: Dict[str, List[ItemScore]] = {}
    for i in ref_items:
        groups.setdefault(_bucket(i), []).append(i)
    read = groups.pop("read", [])

    w = sum(i.ref_value for i in read)
    found = [i for i in read if i.matched]
    w_found = sum(i.ref_value for i in found)

    def within(tol: float) -> int:
        return sum(1 for i in found if i.ref_qty and abs(i.pred_qty - i.ref_qty) / i.ref_qty <= tol + 1e-9)

    produced = [i for i in card.items if i.pred_qty > 0 or i.pred_value > 0]
    produced = [i for i in produced if _method(i.key) in READ_METHODS]
    extras = sorted(i.key for i in produced if not _in_ref(i))
    items = sorted(({"building": i.building, "key": i.key, "family": i.key.split("|", 1)[0],
                     "method": _method(i.key).value, "label": i.label,
                     "ref_qty": i.ref_qty, "pred_qty": i.pred_qty, "ref_value": i.ref_value,
                     "weight": i.ref_value / w if w else 0.0, "qty_acc": i.qty_acc if i.matched else 0.0,
                     "points_lost": (i.ref_value * (1 - (i.qty_acc if i.matched else 0.0)) / w) if w else 0.0,
                     "verdict": _verdict(i)} for i in read), key=lambda d: -d["points_lost"])
    return {
        "reading_score": sum(i.ref_value * i.qty_acc for i in found) / w if w else 0.0,
        "coverage": w_found / w if w else 0.0,
        "qty_accuracy": sum(i.ref_value * i.qty_acc for i in found) / w_found if w_found else 0.0,
        "judged_share_of_bill": w / total_value if total_value else 0.0,
        "items_judged": len(read),
        "items_found": len(found),
        "items_within_5pct": within(0.05),
        "items_within_10pct": within(0.10),
        "item_precision": (len(produced) - len(extras)) / len(produced) if produced else 0.0,
        "extras": extras,
        "items": items,
        "excluded": {name: {"share_of_bill": sum(i.ref_value for i in g) / total_value if total_value else 0.0,
                            "families": sorted({i.key.split("|", 1)[0] for i in g})}
                     for name, g in sorted(groups.items())},
    }
