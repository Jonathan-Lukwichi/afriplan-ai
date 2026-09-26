"""Render a Scorecard as a markdown evaluation report."""

from __future__ import annotations

from evaluation.metrics import Scorecard

_ROWS = [
    ("Reproduction Score", "reproduction_score"),
    ("Coverage", "coverage"),
    ("Coverage (items)", "coverage_items"),
    ("Precision", "precision"),
    ("Quantity accuracy", "qty_accuracy"),
    ("Rate accuracy", "rate_accuracy"),
    ("Total accuracy", "total_accuracy"),
]


def _pct(v: float) -> str:
    return f"{v * 100:.1f}%"


def render_markdown(card: Scorecard, *, top_n: int = 25, title: str = "") -> str:
    full = card.model_dump()
    out = [
        f"# {title or f'BOQ evaluation — {card.project} · {card.pipeline or 'prediction'}'}",
        "",
        f"**Reproduction Score: {_pct(card.reproduction_score)}** "
        f"(scoped to uploaded drawings: {_pct(card.scoped.get('reproduction_score', 0))})",
        "",
        "Reference value = Σ priced bill lines of the scored buildings (excl. contingency, VAT, P&Gs).",
        "",
        "| Metric | Full reference | Scoped to uploaded drawings |",
        "|---|---:|---:|",
    ]
    for label, key in _ROWS:
        out.append(f"| {label} | {_pct(full[key])} | {_pct(card.scoped.get(key, 0.0))} |")
    out += [
        f"| Reference value | R {card.reference_value:,.0f} | R {card.scoped.get('reference_value', 0):,.0f} |",
        f"| Predicted value | R {card.predicted_value:,.0f} | R {card.scoped.get('predicted_value', 0):,.0f} |",
        "",
        "## Per building",
        "",
        "| Building | Uploaded drawings | RS | Coverage | Qty acc | Ref value | Pred value |",
        "|---|---|---:|---:|---:|---:|---:|",
    ]
    for b, m in card.per_building.items():
        up = ", ".join(card.uploaded.get(b, [])) or "—"
        out.append(
            f"| {b} | {up} | {_pct(m['reproduction_score'])} | {_pct(m['coverage'])} | "
            f"{_pct(m['qty_accuracy'])} | R {m['reference_value']:,.0f} | R {m['predicted_value']:,.0f} |"
        )

    missing = [i for i in sorted(card.items, key=lambda i: -i.ref_value) if not i.matched and i.ref_value > 0]
    out += ["", f"## Not produced by the pipeline (top {top_n} by value)", "",
            "| Building | Item | In scope? | Ref qty | Ref value |", "|---|---|:---:|---:|---:|"]
    for i in missing[:top_n]:
        out.append(f"| {i.building} | `{i.key}` {i.label[:50]} | {'yes' if i.in_scope else 'no'} | "
                   f"{i.ref_qty:g} | R {i.ref_value:,.0f} |")
    if len(missing) > top_n:
        out.append(f"| … | {len(missing) - top_n} more | | | |")

    matched = [i for i in card.items if i.matched]
    worst = sorted(matched, key=lambda i: -(1 - i.qty_acc) * i.ref_value)[:top_n]
    out += ["", "## Largest quantity errors on matched items", "",
            "| Building | Item | Ref qty | Pred qty | Qty acc | Ref rate | Pred rate |",
            "|---|---|---:|---:|---:|---:|---:|"]
    for i in worst:
        out.append(f"| {i.building} | `{i.key}` | {i.ref_qty:g} | {i.pred_qty:g} | {_pct(i.qty_acc)} | "
                   f"R {i.ref_rate:,.2f} | R {i.pred_rate:,.2f} |")

    if card.unmatched_predicted:
        out += ["", "## Predicted but not in the reference", ""]
        out += [f"- {s}" for s in card.unmatched_predicted[:top_n]]
    return "\n".join(out) + "\n"
