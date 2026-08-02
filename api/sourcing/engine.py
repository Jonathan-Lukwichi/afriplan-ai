"""
sourcing.engine — fan quote requests out across suppliers, rank, apply.

This is the orchestration heart of the sourcing layer:

  • build_requests()  — distil BOQ lines into QuoteRequestItems
  • SourcingEngine.request_quotes() — ask every instant connector, collect
    quotes, rank them, produce a SourcingReport
  • apply_quotes()    — return a CLONED BillOfQuantities with chosen supplier
    prices written onto their lines (tagged MANUAL, original never mutated)

Ranking (best_value): normalise price and lead time across the obtainable
quotes for an item and combine, so "recommended" balances cost against how soon
it can actually be delivered — an out-of-stock bargain is not a win.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional

from agent.shared import BillOfQuantities, BQLineItem, ItemConfidence
from sourcing.models import (
    ItemSourcingResult,
    QuoteRequestItem,
    SourcingReport,
    SupplierQuote,
)
from sourcing.suppliers.base import SupplierConnector


# ─── Ranking weights ─────────────────────────────────────────────────────────

@dataclass(frozen=True)
class RankWeights:
    price: float = 0.6
    lead_time: float = 0.35
    confidence: float = 0.05


DEFAULT_WEIGHTS = RankWeights()


# ─── BOQ → requests ──────────────────────────────────────────────────────────

def build_requests(
    boq: BillOfQuantities,
    *,
    item_refs: Optional[Iterable[str]] = None,
    material_only: bool = True,
) -> List[QuoteRequestItem]:
    """Turn BOQ lines into quote requests.

    material_only skips pure-labour 'Install …' split lines — suppliers price
    material, not the contractor's labour. item_refs (item_number_str values)
    filters to a chosen subset; None means every eligible line.
    """
    wanted = set(item_refs) if item_refs is not None else None
    out: List[QuoteRequestItem] = []
    for ln in boq.line_items:
        ref = ln.item_number_str
        if wanted is not None and ref not in wanted:
            continue
        if material_only and _is_labour_line(ln):
            continue
        out.append(QuoteRequestItem(
            item_ref=ref,
            description=ln.description,
            unit=ln.unit,
            qty=ln.qty,
            section=ln.section.value,
            category=ln.category,
            anchor_price_zar=ln.unit_price_zar,
        ))
    return out


def _is_labour_line(ln: BQLineItem) -> bool:
    d = ln.description.lower()
    return d.startswith("install ") or d.startswith("terminate ") or d.startswith("trench")


# ─── Engine ──────────────────────────────────────────────────────────────────

class SourcingEngine:
    def __init__(
        self,
        connectors: List[SupplierConnector],
        *,
        weights: RankWeights = DEFAULT_WEIGHTS,
    ):
        if not connectors:
            raise ValueError("SourcingEngine needs at least one supplier connector.")
        self._connectors = connectors
        self._weights = weights

    def request_quotes(
        self,
        items: List[QuoteRequestItem],
        *,
        project_name: str = "",
        boq_run_id: str = "",
    ) -> SourcingReport:
        # ref → result (preserve request order)
        results: Dict[str, ItemSourcingResult] = {
            it.item_ref: ItemSourcingResult(request=it) for it in items
        }

        for connector in self._connectors:
            try:
                quotes = connector.quote(items)
            except Exception:  # noqa: BLE001 — one bad supplier must not sink the run
                continue
            for q in quotes:
                if q.item_ref in results:
                    results[q.item_ref].quotes.append(q)

        for res in results.values():
            res.recommended_supplier_id = self._rank(res.quotes)

        return SourcingReport(
            project_name=project_name,
            boq_run_id=boq_run_id,
            results=[results[it.item_ref] for it in items],
        )

    def _rank(self, quotes: List[SupplierQuote]) -> str:
        """Return the supplier_id of the best-value obtainable quote."""
        obtainable = [q for q in quotes
                      if q.availability.is_obtainable and q.unit_price_zar > 0]
        if not obtainable:
            return ""
        if len(obtainable) == 1:
            return obtainable[0].supplier_id

        prices = [q.unit_price_zar for q in obtainable]
        leads = [q.lead_time_days for q in obtainable]
        p_min, p_max = min(prices), max(prices)
        l_min, l_max = min(leads), max(leads)
        w = self._weights

        def score(q: SupplierQuote) -> float:
            p_norm = 0.0 if p_max == p_min else (q.unit_price_zar - p_min) / (p_max - p_min)
            l_norm = 0.0 if l_max == l_min else (q.lead_time_days - l_min) / (l_max - l_min)
            conf_penalty = 1.0 - q.parse_confidence
            return w.price * p_norm + w.lead_time * l_norm + w.confidence * conf_penalty

        return min(obtainable, key=score).supplier_id


# ─── Apply chosen quotes back onto a (cloned) BOQ ────────────────────────────

def apply_quotes(
    boq: BillOfQuantities,
    chosen: Dict[str, SupplierQuote],
) -> BillOfQuantities:
    """Return a CLONED bill with `chosen` supplier prices written onto lines.

    `chosen` maps item_number_str → the SupplierQuote the engineer accepted.
    The line's unit price becomes the live supplier price, tagged MANUAL, with a
    note recording supplier, availability and lead time. The input bill is never
    mutated; totals are recomputed on the copy.
    """
    cloned = boq.model_copy(deep=True)
    for ln in cloned.line_items:
        q = chosen.get(ln.item_number_str)
        if q is None:
            continue
        ln.unit_price_zar = round(q.unit_price_zar, 2)
        ln.total_zar = round(ln.qty * ln.unit_price_zar, 2)
        ln.source = ItemConfidence.MANUAL
        lead = "ex-stock" if q.lead_time_days == 0 else f"{q.lead_time_days}d lead"
        ln.notes = (
            f"Live price — {q.supplier_name} ({q.availability.value}, {lead})."
            + (f" {ln.notes}" if ln.notes else "")
        )

    _recompute_totals(cloned)
    _recount_provenance(cloned)
    return cloned


def _recompute_totals(boq: BillOfQuantities) -> None:
    subtotal = round(sum(l.total_zar for l in boq.line_items), 2)
    contingency = round(subtotal * (boq.contingency_pct / 100.0), 2)
    markup = round(subtotal * (boq.contractor_markup_pct / 100.0), 2)
    excl_vat = round(subtotal + contingency + markup, 2)
    vat = round(excl_vat * (boq.vat_pct / 100.0), 2)
    boq.subtotal_zar = subtotal
    boq.contingency_zar = contingency
    boq.markup_zar = markup
    boq.total_excl_vat_zar = excl_vat
    boq.vat_zar = vat
    boq.total_incl_vat_zar = round(excl_vat + vat, 2)


def _recount_provenance(boq: BillOfQuantities) -> None:
    boq.items_extracted = sum(1 for l in boq.line_items if l.source == ItemConfidence.EXTRACTED)
    boq.items_inferred = sum(1 for l in boq.line_items if l.source == ItemConfidence.INFERRED)
    boq.items_assumed = sum(1 for l in boq.line_items if l.source == ItemConfidence.ASSUMED)
    boq.items_provisional = sum(1 for l in boq.line_items if l.source == ItemConfidence.PROVISIONAL)
    boq.items_estimated = sum(1 for l in boq.line_items if l.source == ItemConfidence.ESTIMATED)
