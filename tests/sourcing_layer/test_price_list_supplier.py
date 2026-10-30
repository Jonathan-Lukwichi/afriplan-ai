"""sourcing.suppliers.price_list: the price catalogue as one more supplier beside each BoQ line (compare, never auto-apply)."""

from __future__ import annotations

from sourcing import SourcingEngine
from sourcing import catalogue as cat
from sourcing.models import Availability, QuoteRequestItem, SourcingChannel
from sourcing.suppliers.mock import default_mock_suppliers
from sourcing.suppliers.price_list import PriceListSupplier, default_price_list_suppliers


def _item(part, desc, price, supplier="Schneider Electric", date="2026-09-08", **kw):
    return cat._item(item_id=f"x:{part}", supplier=supplier, brand=supplier, part_no=part, description=desc,
                     list_price_zar_excl_vat=price, price_date=date, source_document="list.pdf", **kw)


ITEMS = [
    _item("M1", "C60N MCB 1P 20A C 6kA", 100.0),
    _item("M2", "iC60H MCB 1P 20A C 10kA", 140.0),
    _item("M3", "Easy9 MCB 1P 20A C 4.5kA", 120.0),
    _item("M4", "C60N MCB 2P 20A C 6kA", 300.0),           # wrong poles
    _item("M5", "C60N MCB 1P 32A C 6kA", 110.0),           # wrong amps
    _item("A1", "Auxiliary contact for MCB 1P 20A", 50.0),  # an accessory, not the breaker
    _item("S1", "Double switched socket outlet 16A white", 90.0),
    _item("S2", "Single switched socket outlet 16A white", 60.0),
]


def _req(desc, ref="5.1", section="SECTION 2: DISTRIBUTION"):
    return QuoteRequestItem(item_ref=ref, description=desc, section=section, qty=4, anchor_price_zar=85.0)


def test_a_breaker_line_is_priced_from_matching_list_items_only_median_of_the_matches():
    [q] = PriceListSupplier("Schneider Electric", ITEMS).quote([_req("20A 1P MCB")])
    assert q.unit_price_zar == 120.0                     # median of M1, M2, M3; M4, M5, A1 excluded
    assert q.raw_source == "x:M3"
    assert "median of 3 matching" in q.notes


def test_a_line_too_vague_to_match_gets_no_quote():
    assert PriceListSupplier("Schneider Electric", ITEMS).quote([_req("Distribution board 24 way")]) == []
    assert PriceListSupplier("Schneider Electric", ITEMS).quote([_req("MCB")]) == []   # no amps, no poles


def test_wiring_devices_get_no_list_quote_until_product_ranges_are_mapped():
    # Against the real list a "1-Lever Switch" matched a control selector head and a "Data Socket"
    # a 16 A power socket: sockets and switches need range knowledge (SANS 164 vs industrial CEE).
    sup = PriceListSupplier("Schneider Electric", ITEMS)
    for line in ("16A Double Switched Socket", "Data Socket (CAT6)", "1-Lever Switch", "Floor Box Socket"):
        assert sup.quote([_req(line, section="SECTION 6: POWER OUTLETS")]) == [], line


def test_a_list_price_quote_shows_its_date_uses_the_trade_discount_and_is_never_obtainable():
    items = [_item("M1", "C60N MCB 1P 20A C 6kA", 100.0, discount_pct=10.0)]
    [q] = PriceListSupplier("Schneider Electric", items).quote([_req("20A 1P MCB")])
    assert q.channel == SourcingChannel.PRICE_LIST
    assert q.availability == Availability.UNKNOWN
    assert q.unit_price_zar == 90.0
    assert "2026-09-08" in q.supplier_name


def test_the_engine_never_recommends_a_list_price_over_a_real_quote():
    engine = SourcingEngine(default_mock_suppliers() + [PriceListSupplier("Schneider Electric", ITEMS)])
    [res] = engine.request_quotes([_req("20A 1P MCB")]).results
    assert any(q.channel == SourcingChannel.PRICE_LIST for q in res.quotes)
    assert res.recommended_supplier_id and not res.recommended_supplier_id.startswith("pricelist:")


def test_one_price_list_supplier_per_catalogue_supplier_but_not_the_afriplan_estimates(tmp_path):
    path = tmp_path / "price_catalogue.csv"
    cat.write_csv(ITEMS + [_item("V1", "Isolator 30A DP IP66", 310.0, supplier="Voltex", date="2026-10-29"),
                           _item("mcb_20a_1p", "mcb 20a 1p", 85.0, supplier=cat.AFRIPLAN)], path)
    names = sorted(s.info.name for s in default_price_list_suppliers(path))
    assert names == ["Schneider Electric list price (2026-09-08)", "Voltex list price (2026-10-29)"]
    assert default_price_list_suppliers(tmp_path / "missing.csv") == []
