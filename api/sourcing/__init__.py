"""
sourcing — live supplier price / quotation enrichment for a Bill of Quantities.

An INDEPENDENT, read-only layer (like `scoring/` and `agent/comparison/`): it
reads a finished BillOfQuantities, asks 3-4 suppliers for live price,
availability and lead time per item, and lets an engineer pick a supplier per
line. Neither pipeline imports it; it never mutates the pipelines' output.

Channels are pluggable SupplierConnectors:
  • mock            — deterministic simulated suppliers (POC / offline)
  • web_catalog     — online-store suppliers (future adapter)
  • price_list      — cached manufacturer price lists (future adapter)
  • rfq_email       — LLM-drafted RFQ + LLM-parsed reply (sourcing.rfq)

Typical use:
    from sourcing import SourcingEngine, build_requests, apply_quotes
    from sourcing.suppliers.mock import default_mock_suppliers

    reqs = build_requests(boq)
    report = SourcingEngine(default_mock_suppliers()).request_quotes(reqs)
    chosen = {r.request.item_ref: r.recommended() for r in report.results}
    priced = apply_quotes(boq, {k: v for k, v in chosen.items() if v})
"""

from sourcing.models import (
    Availability,
    ItemSourcingResult,
    QuoteRequestItem,
    SourcingChannel,
    SourcingReport,
    SupplierInfo,
    SupplierQuote,
)
from sourcing.engine import (
    DEFAULT_WEIGHTS,
    RankWeights,
    SourcingEngine,
    apply_quotes,
    build_requests,
)

__all__ = [
    "Availability",
    "SourcingChannel",
    "SupplierInfo",
    "QuoteRequestItem",
    "SupplierQuote",
    "ItemSourcingResult",
    "SourcingReport",
    "SourcingEngine",
    "RankWeights",
    "DEFAULT_WEIGHTS",
    "build_requests",
    "apply_quotes",
]
