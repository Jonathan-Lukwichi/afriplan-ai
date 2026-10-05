"""
Accuracy report — how close a produced BoQ is to the real, human-priced bill, and why not closer.

`build_accuracy_report` turns the frozen scorer's Scorecards (one per reader: CAD alone,
PDF alone, Combined) into a plain-JSON dict; `render_accuracy_markdown` writes it for people.
The JSON is the record to compare runs over time; the markdown is the one to read.
Both quote the reference's items and rand values — client data: keep them out of git.
Metric definitions: docs/accuracy-metrics.md.
"""

from __future__ import annotations

from typing import Dict

from evaluation.gaps import analyse_gaps
from evaluation.metrics import Scorecard
from evaluation.reading import reading_accuracy

METRICS_EXPLAINED = {
    "reproduction_score": "HEADLINE. Share of the real bill's value we reproduced with the right quantity: "
                          "Σ value·matched·qty_accuracy / Σ value. 100 % = every item present with the exact quantity.",
    "coverage": "Share of the real bill's value whose item we produced at all (quantity ignored).",
    "precision": "Share of OUR priced value that is a real-bill item (the rest is extra / wrong items).",
    "qty_accuracy": "On items we produced: how close the quantities are, 1 − |ours − real| / real, value-weighted.",
    "rate_accuracy": "On items we produced: how close our unit rates are to the real rates, value-weighted. "
                     "Not part of the headline; it moves the bill total.",
    "total_accuracy": "How close our bill total is to the real total, 1 − |ours − real| / real. "
                      "Can look good by luck (misses and extras cancel) — never judge on it alone.",
}
CAUSE_EXPLAINED = {
    "not_produced": "item in the real bill, absent from ours",
    "qty_low": "item present, quantity too low",
    "qty_high": "item present, quantity too high",
}
_HEADLINE = ("reproduction_score", "coverage", "precision", "qty_accuracy", "rate_accuracy", "total_accuracy")


def build_accuracy_report(cards: Dict[str, Scorecard], *, project: str, run: str, delivered: str,
                          top_n: int = 30) -> dict:
    readers = {label: {**{m: getattr(c, m) for m in _HEADLINE},
                       "scoped_reproduction_score": c.scoped.get("reproduction_score", 0.0),
                       "reference_value": c.reference_value, "predicted_value": c.predicted_value,
                       "reading": reading_accuracy(c)}
               for label, c in cards.items()}
    g = analyse_gaps(cards[delivered])
    return {
        "project": project, "run": run, "delivered": delivered,
        "metrics_explained": METRICS_EXPLAINED, "causes_explained": CAUSE_EXPLAINED,
        "readers": readers,
        "delivered_gaps": {
            "by_cause": g.by_cause,
            "by_section": [s.model_dump() for s in g.by_section],
            "by_method": [s.model_dump() for s in g.by_method],
            "by_family": [s.model_dump() for s in g.by_family],
            "items": [i.model_dump() for i in g.items if i.points_lost > 0][:top_n],
            "rate_errors": [i.model_dump() for i in g.rate_errors][:top_n],
            "extras": [e.model_dump() for e in g.extras][:top_n],
        },
    }


def _pct(v: float) -> str:
    return f"{v * 100:.1f} %"


def _pts(v: float) -> str:
    return f"{v * 100:.1f}"


def _reading_section(rep: dict) -> list:
    """Reading accuracy first: only what is counted or measured on the uploaded drawings; no prices."""
    rd = rep["readers"][rep["delivered"]]["reading"]
    out = ["## Reading accuracy — did we read what is drawn? (prices play no part)", "",
           "Judged only on items that are **counted or measured on the uploaded drawings** "
           f"({_pct(rd['judged_share_of_bill'])} of the real bill's value). Each item weighs what it is worth "
           "in the real bill; our own rates never enter.", "",
           "| Reader | **Reading score** | Coverage | Qty accuracy | Items found | Within ±5 % | Within ±10 % | Item precision |",
           "|---|---:|---:|---:|---:|---:|---:|---:|"]
    for label, r in rep["readers"].items():
        g = r["reading"]
        out.append(f"| {label} | **{_pct(g['reading_score'])}** | {_pct(g['coverage'])} | {_pct(g['qty_accuracy'])} | "
                   f"{g['items_found']} / {g['items_judged']} | {g['items_within_5pct']} | {g['items_within_10pct']} | "
                   f"{_pct(g['item_precision'])} |")
    out += ["", "Not judged as reading (they are not counted or measured on the uploaded drawings):", ""]
    why = {"derived": "follow from other items by an estimating rule",
           "provisional": "never on any drawing (sums, fees, P&Gs)",
           "not_on_uploaded_drawings": "the drawing that shows them was not uploaded"}
    out += [f"- **{name}** ({_pct(x['share_of_bill'])} of the bill) — {why.get(name, name)}: "
            f"{', '.join(x['families'])}" for name, x in rd["excluded"].items()]
    out += ["", f"### Reading losses, {rep['delivered']} (biggest first)", "",
            "| Building | Item | Method | Real qty | Our qty | Verdict | Points lost |", "|---|---|---|---:|---:|---|---:|"]
    out += [f"| {i['building']} | `{i['key']}` {i['label'][:40]} | {i['method']} | {i['ref_qty']:g} | {i['pred_qty']:g} | "
            f"{i['verdict']} | {_pts(i['points_lost'])} |" for i in rd["items"] if i["points_lost"] > 0.0005][:30]
    if rd["extras"]:
        out += ["", "Read by us but not in the real bill: " + ", ".join(f"`{e}`" for e in rd["extras"])]
    return out + [""]


def render_accuracy_markdown(rep: dict) -> str:
    g = rep["delivered_gaps"]
    d = rep["readers"][rep["delivered"]]
    out = [f"# Accuracy report — {rep['project']} — {rep['run']}", "",
           f"**{rep['delivered']}: Reproduction Score {_pct(d['reproduction_score'])}** — "
           f"{_pct(1 - d['reproduction_score'])} of the real bill's value is still missing or mis-quantified.", ""]
    out += _reading_section(rep)
    out += ["## What we measure", "",
           "Our BoQ is compared line by line with the real, human-priced bill (its priced building lines; "
           "contingency, VAT and P&Gs excluded). Lines are matched by building and item type (ItemKey). "
           "Every item is weighted by its value in the real bill, so a big feeder cable counts far more than a "
           "socket. Details: `docs/accuracy-metrics.md`.", "",
           "| Metric | Meaning |", "|---|---|"]
    out += [f"| {k} | {v} |" for k, v in rep["metrics_explained"].items()]
    out += ["", "## Every reader", "",
            "| Reader | **RS** | Coverage | Precision | Qty acc | Rate acc | Total acc | RS scoped to drawings |",
            "|---|---:|---:|---:|---:|---:|---:|---:|"]
    for label, r in rep["readers"].items():
        out.append(f"| {label} | **{_pct(r['reproduction_score'])}** | {_pct(r['coverage'])} | {_pct(r['precision'])} | "
                   f"{_pct(r['qty_accuracy'])} | {_pct(r['rate_accuracy'])} | {_pct(r['total_accuracy'])} | "
                   f"{_pct(r['scoped_reproduction_score'])} |")
    out += ["", "## Where the missing points are", "",
            "Points = percentage points of the Reproduction Score. They add up to 100 − RS.", "",
            "| Cause | Points lost | Meaning |", "|---|---:|---|"]
    out += [f"| {c} | {_pts(v)} | {rep['causes_explained'][c]} |" for c, v in g["by_cause"].items()]
    for title, key in (("By bill section", "by_section"), ("By how the item is obtained", "by_method"),
                       ("By item family (top 15)", "by_family")):
        out += ["", f"### {title}", "", "| Group | Share of real bill | Points lost | not produced | qty low | qty high |",
                "|---|---:|---:|---:|---:|---:|"]
        out += [f"| {s['name']} | {_pct(s['ref_share'])} | **{_pts(s['points_lost'])}** | {_pts(s['not_produced'])} | "
                f"{_pts(s['qty_low'])} | {_pts(s['qty_high'])} |" for s in g[key][:15]]
    out += ["", "## Biggest losses, item by item — and the kind of fix each needs", "",
            "| Building | Item | Cause | Real qty | Our qty | Real value | Points lost | Fix |",
            "|---|---|---|---:|---:|---:|---:|---|"]
    out += [f"| {i['building']} | `{i['key']}` {i['label'][:40]} | {i['cause']} | {i['ref_qty']:g} | {i['pred_qty']:g} | "
            f"R {i['ref_value']:,.0f} | **{_pts(i['points_lost'])}** | {i['fix']} |" for i in g["items"]]
    out += ["", "## Rates — not in the headline, but they move the bill total", "",
            "| Building | Item | Real rate | Our rate | Rate acc | Effect on our total |", "|---|---|---:|---:|---:|---:|"]
    out += [f"| {i['building']} | `{i['key']}` | R {i['ref_rate']:,.2f} | R {i['pred_rate']:,.2f} | {_pct(i['rate_acc'])} | "
            f"R {i['pred_qty'] * (i['pred_rate'] - i['ref_rate']):+,.0f} |" for i in g["rate_errors"]]
    out += ["", "## Priced by us, absent from the real bill (lowers precision)", "",
            "| Building | Item | Our qty | Our value |", "|---|---|---:|---:|"]
    out += [f"| {e['building']} | `{e['key']}` | {e['pred_qty']:g} | R {e['pred_value']:,.0f} |" for e in g["extras"]]
    return "\n".join(out) + "\n"
