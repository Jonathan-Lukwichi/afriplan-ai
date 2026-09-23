"""
scripts/sourcing_demo.py — prove the live-pricing concept end-to-end, offline.

Builds a tiny sample BOQ, asks the 4 mock suppliers for quotes on every
material line, prints the per-item comparison (price / availability / lead
time / recommended), then applies the recommended supplier to each line and
shows the before/after bill total.

    python scripts/sourcing_demo.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agent.shared import BillOfQuantities, BQLineItem, BQSection, ItemConfidence
from sourcing import SourcingEngine, apply_quotes, build_requests
from sourcing.suppliers.mock import default_mock_suppliers


def _sample_boq() -> BillOfQuantities:
    items = [
        BQLineItem(item_no=1, section=BQSection.LIGHTING, description="6W LED downlight — Office",
                   unit="No", qty=40, unit_price_zar=260.0, source=ItemConfidence.EXTRACTED),
        BQLineItem(item_no=2, section=BQSection.LIGHTING, description="2x24W vapour-proof LED — Plant",
                   unit="No", qty=12, unit_price_zar=890.0, source=ItemConfidence.EXTRACTED),
        BQLineItem(item_no=1, section=BQSection.POWER_OUTLETS, description="16A double switched socket — Office",
                   unit="No", qty=55, unit_price_zar=175.0, source=ItemConfidence.EXTRACTED),
        BQLineItem(item_no=1, section=BQSection.DISTRIBUTION, description="DB-A: 3ph 100A, 24-way, surface mount",
                   unit="Sum", qty=1, unit_price_zar=2200.0, source=ItemConfidence.EXTRACTED),
        BQLineItem(item_no=1, section=BQSection.SUBMAIN_CABLES, description="Install 25mm² x4C SWA feeder DB-A",
                   unit="m", qty=45, unit_price_zar=95.0, source=ItemConfidence.EXTRACTED),
    ]
    boq = BillOfQuantities(pipeline="pdf", project_name="Demo Project", line_items=items)
    boq.subtotal_zar = round(sum(i.total_zar for i in items), 2)
    return boq


def main() -> None:
    boq = _sample_boq()
    # recompute line totals
    for it in boq.line_items:
        it.total_zar = round(it.qty * it.unit_price_zar, 2)
    boq.subtotal_zar = round(sum(i.total_zar for i in boq.line_items), 2)

    reqs = build_requests(boq)  # material lines only (skips the 'Install …' feeder)
    engine = SourcingEngine(default_mock_suppliers())
    report = engine.request_quotes(reqs, project_name=boq.project_name)

    print(f"\n=== Live sourcing - {report.items_sourced} items x "
          f"{report.suppliers_contacted} suppliers ===\n")
    for res in report.results:
        print(f"• {res.request.item_ref}  {res.request.description}  "
              f"(BOQ est R{res.request.anchor_price_zar:,.2f})")
        for q in res.quotes:
            star = " -> " if q.supplier_id == res.recommended_supplier_id else "    "
            print(f"{star} {q.supplier_name:<16} R{q.unit_price_zar:>9,.2f}  "
                  f"{q.availability.value:<12} lead {q.lead_time_days:>2}d")
        print()

    chosen = {r.request.item_ref: r.recommended() for r in report.results}
    chosen = {k: v for k, v in chosen.items() if v is not None}
    priced = apply_quotes(boq, chosen)

    print("=== Effect on the bill ===")
    print(f"  Subtotal (BOQ estimate) : R {boq.subtotal_zar:,.2f}")
    print(f"  Subtotal (live sourced) : R {priced.subtotal_zar:,.2f}")
    print(f"  Potential saving        : R {report.potential_saving_zar:,.2f}")


if __name__ == "__main__":
    main()
