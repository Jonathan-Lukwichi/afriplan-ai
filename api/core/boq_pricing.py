"""
Reprice a BillOfQuantities with new markup/contingency/VAT parameters.

Ported (as a pure function, framework stripped) from the original app's
pages/3_BOQ_Generation.py::_reprice — same math, no Streamlit dependency.
"""

from __future__ import annotations

from agent.shared import BillOfQuantities


def reprice_boq(boq: BillOfQuantities, markup: float, contingency: float, vat: float) -> BillOfQuantities:
    """Recompute totals on a cloned BOQ with new pricing parameters."""
    cloned_items = [it.model_copy() for it in boq.line_items]
    subtotal = round(sum(it.total_zar for it in cloned_items), 2)
    contingency_zar = round(subtotal * (contingency / 100.0), 2)
    markup_zar = round(subtotal * (markup / 100.0), 2)
    total_excl = round(subtotal + contingency_zar + markup_zar, 2)
    vat_zar = round(total_excl * (vat / 100.0), 2)
    total_incl = round(total_excl + vat_zar, 2)

    return boq.model_copy(update={
        "line_items": cloned_items,
        "contractor_markup_pct": markup,
        "contingency_pct": contingency,
        "vat_pct": vat,
        "subtotal_zar": subtotal,
        "contingency_zar": contingency_zar,
        "markup_zar": markup_zar,
        "total_excl_vat_zar": total_excl,
        "vat_zar": vat_zar,
        "total_incl_vat_zar": total_incl,
    })
