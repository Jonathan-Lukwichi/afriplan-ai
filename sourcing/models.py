"""
sourcing.models — data shapes for the live-pricing / RFQ layer.

This package is an INDEPENDENT, read-only enrichment layer. It reads a
`BillOfQuantities` (produced by either pipeline) and asks real suppliers for
live prices, availability and lead times, so an engineer can compare 3-4
manufacturers per item without phoning around.

Design rules that mirror the rest of the codebase:
  • It never imports either pipeline, and neither pipeline imports it — it sits
    *after* the deterministic bill, like the comparison layer.
  • It never mutates a BillOfQuantities in place; applying a chosen quote
    returns a cloned bill (see engine.apply_quotes).
  • Live prices are non-deterministic by nature, so they live OUTSIDE the
    determinism contract of the assembler. A sourced price is tagged
    ItemConfidence.MANUAL on the bill, never EXTRACTED/INFERRED.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


# ─── Channels a quote can arrive through ─────────────────────────────────────

class SourcingChannel(str, Enum):
    MOCK = "mock"                # simulated supplier (POC / offline demo)
    WEB_CATALOG = "web_catalog"  # scraped/API'd online store (instant)
    RFQ_EMAIL = "rfq_email"      # request-for-quote email, LLM-parsed reply
    PRICE_LIST = "price_list"    # cached manufacturer price list
    MANUAL = "manual"            # contractor typed it in


# ─── Stock availability ──────────────────────────────────────────────────────

class Availability(str, Enum):
    IN_STOCK = "in_stock"
    LOW_STOCK = "low_stock"
    ON_ORDER = "on_order"        # not held, but can be brought in
    OUT_OF_STOCK = "out_of_stock"
    UNKNOWN = "unknown"

    @property
    def is_obtainable(self) -> bool:
        return self in (Availability.IN_STOCK, Availability.LOW_STOCK, Availability.ON_ORDER)


# ─── Supplier identity ───────────────────────────────────────────────────────

class SupplierInfo(BaseModel):
    supplier_id: str
    name: str
    channel: SourcingChannel = SourcingChannel.MOCK
    contact_email: str = ""
    region: str = "ZA"
    website: str = ""


# ─── What we want priced (one BOQ line, distilled) ───────────────────────────

class QuoteRequestItem(BaseModel):
    """A single line the engineer wants live prices for."""
    item_ref: str                       # BQLineItem.item_number_str, e.g. "5.3"
    description: str
    unit: str = "each"
    qty: float = 1.0
    section: str = ""                   # BQSection.value
    category: str = ""
    manufacturer_hint: str = ""         # optional preferred brand
    # The deterministic BOQ unit price — used as a sanity anchor / fallback.
    anchor_price_zar: float = 0.0


# ─── One supplier's answer for one item ──────────────────────────────────────

class SupplierQuote(BaseModel):
    item_ref: str
    supplier_id: str
    supplier_name: str
    channel: SourcingChannel = SourcingChannel.MOCK

    unit_price_zar: float = 0.0
    currency: str = "ZAR"
    availability: Availability = Availability.UNKNOWN
    stock_qty: Optional[float] = None       # units on hand, if the supplier says
    lead_time_days: int = 0                 # 0 = ex-stock, same/next day
    min_order_qty: float = 1.0

    valid_until: Optional[str] = None       # ISO date the quote expires
    quoted_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    notes: str = ""
    raw_source: str = ""                    # reply text / URL / catalog ref
    parse_confidence: float = 1.0           # 1.0 for structured sources; <1 for LLM-parsed

    @property
    def line_total_zar(self) -> float:
        return round(self.unit_price_zar * max(self.min_order_qty, 1.0), 2)


# ─── All quotes gathered for one item, with a recommendation ─────────────────

class ItemSourcingResult(BaseModel):
    request: QuoteRequestItem
    quotes: List[SupplierQuote] = Field(default_factory=list)
    recommended_supplier_id: str = ""      # filled by the engine's ranking

    def _obtainable(self) -> List[SupplierQuote]:
        return [q for q in self.quotes
                if q.availability.is_obtainable and q.unit_price_zar > 0]

    def cheapest(self) -> Optional[SupplierQuote]:
        obtainable = self._obtainable()
        return min(obtainable, key=lambda q: q.unit_price_zar) if obtainable else None

    def fastest(self) -> Optional[SupplierQuote]:
        obtainable = self._obtainable()
        return min(obtainable, key=lambda q: q.lead_time_days) if obtainable else None

    def recommended(self) -> Optional[SupplierQuote]:
        for q in self.quotes:
            if q.supplier_id == self.recommended_supplier_id:
                return q
        return self.cheapest()


# ─── The whole sourcing exercise for a bill ──────────────────────────────────

class SourcingReport(BaseModel):
    project_name: str = ""
    boq_run_id: str = ""
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    results: List[ItemSourcingResult] = Field(default_factory=list)

    @property
    def items_sourced(self) -> int:
        return len(self.results)

    @property
    def suppliers_contacted(self) -> int:
        ids = set()
        for r in self.results:
            for q in r.quotes:
                ids.add(q.supplier_id)
        return len(ids)

    @property
    def potential_saving_zar(self) -> float:
        """Sum of (anchor − cheapest live) × qty across items where we beat the estimate."""
        saving = 0.0
        for r in self.results:
            cheap = r.cheapest()
            if cheap and r.request.anchor_price_zar > 0:
                delta = (r.request.anchor_price_zar - cheap.unit_price_zar) * r.request.qty
                saving += delta
        return round(saving, 2)
