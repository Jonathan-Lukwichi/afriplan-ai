"""
Unit tests for the sourcing (live-pricing) layer.

All offline: the mock suppliers are deterministic and the RFQ parser is fed a
fake LLM client, so nothing here touches the network.
"""

from __future__ import annotations

import pytest

from agent.shared import BillOfQuantities, BQLineItem, BQSection, ItemConfidence
from sourcing import (
    Availability,
    SourcingEngine,
    apply_quotes,
    build_requests,
)
from sourcing.models import QuoteRequestItem, SourcingChannel, SupplierInfo
from sourcing.rfq import QuoteParser, draft_rfq
from sourcing.suppliers.mock import default_mock_suppliers


# ─── Fixtures ────────────────────────────────────────────────────────────────

def _boq() -> BillOfQuantities:
    items = [
        BQLineItem(section=BQSection.LIGHTING, description="6W LED downlight — Office",
                   unit="No", qty=40, unit_price_zar=260.0),
        BQLineItem(section=BQSection.POWER_OUTLETS, description="16A double switched socket",
                   unit="No", qty=55, unit_price_zar=175.0),
        BQLineItem(section=BQSection.SUBMAIN_CABLES, description="Install 25mm² SWA feeder DB-A",
                   unit="m", qty=45, unit_price_zar=95.0),
    ]
    boq = BillOfQuantities(pipeline="pdf", line_items=items)
    for it in boq.line_items:
        it.total_zar = round(it.qty * it.unit_price_zar, 2)
    boq.subtotal_zar = round(sum(i.total_zar for i in boq.line_items), 2)
    return boq


# ─── build_requests ──────────────────────────────────────────────────────────

def test_build_requests_skips_labour_lines():
    reqs = build_requests(_boq())
    descs = [r.description for r in reqs]
    assert any("downlight" in d for d in descs)
    assert not any(d.lower().startswith("install") for d in descs), \
        "material_only must drop pure-labour 'Install …' lines"


def test_build_requests_filters_by_ref():
    boq = _boq()
    ref = boq.line_items[0].item_number_str
    reqs = build_requests(boq, item_refs=[ref], material_only=False)
    assert len(reqs) == 1 and reqs[0].item_ref == ref


# ─── Mock suppliers ──────────────────────────────────────────────────────────

def test_mock_suppliers_are_deterministic():
    reqs = build_requests(_boq())
    a = default_mock_suppliers()[0].quote(reqs)
    b = default_mock_suppliers()[0].quote(reqs)
    # quoted_at is a wall-clock default; the priced facts are what must be stable.
    dump = lambda qs: [q.model_dump(exclude={"quoted_at"}) for q in qs]
    assert dump(a) == dump(b)


def test_each_supplier_prices_every_item():
    reqs = build_requests(_boq())
    for sup in default_mock_suppliers():
        quotes = sup.quote(reqs)
        assert len(quotes) == len(reqs)
        assert all(q.unit_price_zar > 0 for q in quotes)


def test_suppliers_differ():
    reqs = build_requests(_boq())
    sups = default_mock_suppliers()
    first_item_prices = {s.info.supplier_id: s.quote(reqs)[0].unit_price_zar for s in sups}
    assert len(set(first_item_prices.values())) > 1, "suppliers should not all quote the same"


# ─── Engine ranking ──────────────────────────────────────────────────────────

def test_engine_produces_a_report_with_recommendations():
    reqs = build_requests(_boq())
    report = SourcingEngine(default_mock_suppliers()).request_quotes(reqs)
    assert report.items_sourced == len(reqs)
    assert report.suppliers_contacted == 4
    for res in report.results:
        assert len(res.quotes) == 4
        rec = res.recommended()
        assert rec is not None
        assert rec.availability.is_obtainable


def test_recommended_is_never_out_of_stock():
    reqs = build_requests(_boq())
    report = SourcingEngine(default_mock_suppliers()).request_quotes(reqs)
    for res in report.results:
        rec = res.recommended()
        assert rec.availability != Availability.OUT_OF_STOCK


def test_engine_requires_a_connector():
    with pytest.raises(ValueError):
        SourcingEngine([])


# ─── apply_quotes ────────────────────────────────────────────────────────────

def test_apply_quotes_clones_and_reprices():
    boq = _boq()
    reqs = build_requests(boq)
    report = SourcingEngine(default_mock_suppliers()).request_quotes(reqs)
    chosen = {r.request.item_ref: r.recommended() for r in report.results}
    chosen = {k: v for k, v in chosen.items() if v}

    original_subtotal = boq.subtotal_zar
    priced = apply_quotes(boq, chosen)

    # original untouched
    assert boq.subtotal_zar == original_subtotal
    assert all(l.source != ItemConfidence.MANUAL for l in boq.line_items)
    # clone repriced + tagged
    touched = [l for l in priced.line_items if l.item_number_str in chosen]
    assert touched and all(l.source == ItemConfidence.MANUAL for l in touched)
    assert all("Live price" in l.notes for l in touched)
    for l in touched:
        assert l.total_zar == round(l.qty * l.unit_price_zar, 2)


# ─── RFQ email drafting (deterministic template) ─────────────────────────────

def test_draft_rfq_contains_items_and_contact():
    reqs = build_requests(_boq())
    sup = default_mock_suppliers()[0].info
    email = draft_rfq(sup, reqs, contractor_name="ACME Electrical", project_name="Job 12")
    assert email["to"] == sup.contact_email
    assert "Request for Quotation" in email["subject"]
    assert "downlight" in email["body"]
    assert "ACME Electrical" in email["body"]


# ─── RFQ reply parsing (LLM, with a fake client) ─────────────────────────────

class _FakeBlock:
    type = "tool_use"
    def __init__(self, data):
        self.input = data


class _FakeResponse:
    def __init__(self, data):
        self.content = [_FakeBlock(data)]


class _FakeClient:
    """Stands in for anthropic.Anthropic — returns a canned tool_use block."""
    def __init__(self, data):
        self._data = data
        self.messages = self

    def create(self, **kwargs):
        return _FakeResponse(self._data)


def test_quote_parser_maps_reply_to_structured_quotes():
    sup = SupplierInfo(supplier_id="voltex", name="Voltex",
                       channel=SourcingChannel.RFQ_EMAIL, contact_email="q@voltex.co.za")
    items = [QuoteRequestItem(item_ref="5.1", description="6W LED downlight", unit="No", qty=40)]
    fake = _FakeClient({"quotes": [{
        "item_ref": "5.1", "unit_price_zar": 210.5, "availability": "in_stock",
        "lead_time_days": 0, "min_order_qty": 1, "confidence": 0.9,
    }]})
    parser = QuoteParser(client=fake)
    quotes = parser.parse_reply(sup, items, "Downlights R210.50 each, ex stock.")
    assert len(quotes) == 1
    q = quotes[0]
    assert q.item_ref == "5.1"
    assert q.unit_price_zar == 210.5
    assert q.availability == Availability.IN_STOCK
    assert q.channel == SourcingChannel.RFQ_EMAIL
    assert q.supplier_id == "voltex"


def test_quote_parser_handles_bad_availability_gracefully():
    sup = SupplierInfo(supplier_id="arb", name="ARB")
    items = [QuoteRequestItem(item_ref="6.1", description="socket", qty=1)]
    fake = _FakeClient({"quotes": [{
        "item_ref": "6.1", "unit_price_zar": 150, "availability": "nonsense",
        "lead_time_days": 5,
    }]})
    quotes = QuoteParser(client=fake).parse_reply(sup, items, "…")
    assert quotes[0].availability == Availability.UNKNOWN
