"""
sourcing.suppliers.mock — deterministic simulated suppliers.

The mock channel proves the whole flow end-to-end with no network: given a BOQ
line, four SA-flavoured wholesalers each return a price, availability and lead
time that VARY per supplier and per item but are STABLE across runs (seeded by a
SHA-256 of supplier_id + item_ref, so a demo is reproducible and testable).

Each supplier has a personality:
  • ACDC Dynamics   — big stockist, keen prices, mostly ex-stock
  • Voltex          — national, mid prices, reliable but some lead time
  • Waco Industries — cheaper on fittings, thinner stock (more on-order)
  • ARB Electrical  — premium, best availability, priced a touch higher
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import timedelta
from typing import List

from sourcing.models import (
    Availability,
    QuoteRequestItem,
    SourcingChannel,
    SupplierInfo,
    SupplierQuote,
)
from sourcing.pricing_ref import reference_price
from sourcing.suppliers.base import SupplierConnector


@dataclass(frozen=True)
class _Personality:
    price_factor: float          # multiplier on the reference material price
    price_jitter: float          # ± spread applied deterministically per item
    stock_bias: float            # 0..1, higher = more likely in stock
    max_lead_days: int           # cap on lead time when not in stock


_PERSONALITIES = {
    "acdc": _Personality(price_factor=0.94, price_jitter=0.06, stock_bias=0.80, max_lead_days=10),
    "voltex": _Personality(price_factor=1.00, price_jitter=0.05, stock_bias=0.70, max_lead_days=21),
    "waco": _Personality(price_factor=0.88, price_jitter=0.10, stock_bias=0.55, max_lead_days=35),
    "arb": _Personality(price_factor=1.08, price_jitter=0.04, stock_bias=0.90, max_lead_days=14),
}


def _unit_interval(*parts: str) -> float:
    """Deterministic 0..1 float from the given strings (process-independent)."""
    h = hashlib.sha256("::".join(parts).encode("utf-8")).hexdigest()
    return int(h[:8], 16) / 0xFFFFFFFF


class MockSupplier(SupplierConnector):
    """A reproducible fake supplier with a fixed personality."""

    def __init__(self, info: SupplierInfo, personality: _Personality):
        super().__init__(info)
        self._p = personality

    def quote(self, items: List[QuoteRequestItem]) -> List[SupplierQuote]:
        return [self._quote_one(it) for it in items]

    def _quote_one(self, item: QuoteRequestItem) -> SupplierQuote:
        sid = self.info.supplier_id
        base = reference_price(item.section, item.description, item.anchor_price_zar)
        if base <= 0:
            base = 100.0  # nominal so the demo always shows a number

        # Deterministic price around the reference.
        r_price = _unit_interval(sid, item.item_ref, "price")
        jitter = (r_price * 2 - 1) * self._p.price_jitter        # −jitter..+jitter
        unit_price = round(base * self._p.price_factor * (1 + jitter), 2)

        # Deterministic availability + lead time.
        r_stock = _unit_interval(sid, item.item_ref, "stock")
        availability, lead_days, stock_qty = self._availability(r_stock, item.qty)

        # Quote validity is stamped with a real date by the UI layer; core logic
        # stays clock-free so tests are deterministic.
        valid_until = None
        note = f"{self.info.name}: quote held 14 days from issue."

        return SupplierQuote(
            item_ref=item.item_ref,
            supplier_id=sid,
            supplier_name=self.info.name,
            channel=SourcingChannel.MOCK,
            unit_price_zar=unit_price,
            availability=availability,
            stock_qty=stock_qty,
            lead_time_days=lead_days,
            min_order_qty=1.0,
            valid_until=valid_until,
            notes=note,
            raw_source=f"mock://{sid}/{item.item_ref}",
            parse_confidence=1.0,
        )

    def _availability(self, r_stock: float, qty: float):
        p = self._p
        if r_stock < p.stock_bias:
            # In stock — but 'low' if demand is close to a thin holding.
            holding = round(qty * (1.2 + r_stock * 3), 0)
            if holding < qty * 1.3:
                return Availability.LOW_STOCK, max(1, int(p.max_lead_days * 0.2)), holding
            return Availability.IN_STOCK, 0, holding
        # Not held — bring it in.
        lead = 3 + int((r_stock - p.stock_bias) / max(1e-6, 1 - p.stock_bias) * p.max_lead_days)
        return Availability.ON_ORDER, lead, 0.0


# ─── Factory: the standard 4-supplier panel ──────────────────────────────────

def default_mock_suppliers() -> List[MockSupplier]:
    """The four wholesalers used in the POC comparison panel."""
    specs = [
        ("acdc", "ACDC Dynamics", "sales@acdc.co.za", "https://acdc.co.za"),
        ("voltex", "Voltex", "quotes@voltex.co.za", "https://voltex.co.za"),
        ("waco", "Waco Industries", "info@waco.co.za", "https://waco.co.za"),
        ("arb", "ARB Electrical", "rfq@arb.co.za", "https://arb.co.za"),
    ]
    out: List[MockSupplier] = []
    for sid, name, email, site in specs:
        info = SupplierInfo(
            supplier_id=sid, name=name, channel=SourcingChannel.MOCK,
            contact_email=email, website=site, region="ZA",
        )
        out.append(MockSupplier(info, _PERSONALITIES[sid]))
    return out
