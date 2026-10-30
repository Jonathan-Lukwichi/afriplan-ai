"""sourcing.catalogue: one dated price catalogue (supplier · item · price · date) built from price lists, plus user overrides."""

from __future__ import annotations

import openpyxl
import pytest

from sourcing import catalogue as cat

HEADER = ["Collection", "Sub-collection", "Local Discounting group", "Discount", "Part", "Description",
          "List Price excl VAT", "Activity", "Length", "Height", "Width", "Weight"]


def _row(part, desc, price, group="Miniature Circuit Breakers", disc="MCB"):
    return ["General Purpose", "1 Residential General Purpose", group, disc, part, desc, price, "HSCWD", "", "", "", ""]


@pytest.mark.parametrize("text, value", [
    ("ZAR 12 345,00", 12345.0),
    ("ZAR 9 2,00", 92.0),          # PDF extraction splits digits with a space
    ("ZAR 1 234 567,50", 1234567.5),
    ("249,79", 249.79),
    ("", None),
    ("on request", None),
])
def test_rand_prices_are_parsed_from_the_sa_format(text, value):
    assert cat.parse_zar(text) == value


def test_attributes_are_read_from_the_description():
    assert cat.attributes("C60N MCB 1P 20A C curve 6kA") == {"poles": 1, "amps": 20.0, "ka": 6.0}
    assert cat.attributes("NS1000 N 3P BASIC BREAKER DRAWOUT")["poles"] == 3
    assert cat.attributes("Asfora-dbl socket outlet sideE-16A white")["amps"] == 16.0
    assert cat.attributes("mcb 63a 3p") == {"poles": 3, "amps": 63.0}


@pytest.mark.parametrize("desc, group, family", [
    ("C60N MCB 1P 20A C", "Miniature Circuit Breakers", "mcb"),
    ("NSX100F 36kA 3P TM100D", "PTCCB < 630A", "mccb"),
    ("GEAR MOTOR 200/240 VCA", "Air Circuit breakers - Optimum", "acb"),
    ("Asfora-dbl socket outlet sideE-16A white", "Wiring Device System", "socket"),
    ("Asfora 1 lever 1 way switch 16A", "Wiring Device System", "switch"),
    ("iID RCCB 2P 40A 30mA", "Residual Current Devices", "earth_leakage"),
    ("Kaedra enclosure 24 modules IP65", "Enclosures", "enclosure"),
    ("DOUBLE 1NO+1NC CONTACT", "Control & Signalling - Optimum", "control"),
    ("Connection Cable", "Human Machine Interface", "automation"),   # an HMI cable is not a building cable
    ("Soft starter ATS480 110A 208 to 690V", "Drives & Soft starters", "automation"),
])
def test_items_get_an_afriplan_family(desc, group, family):
    assert cat.classify_family(desc, group) == family


def test_schneider_rows_become_dated_catalogue_items_and_headers_are_skipped():
    rows = [HEADER, _row("A9F74120", "C60N MCB 1P 20A C", "ZAR 185,50"), _row("X1", "no price", "")]
    items, skipped = cat.parse_schneider_rows(rows, source="Schneider Electric Price List 2026.pdf", price_date="2026-09-08")
    assert skipped == 1
    [item] = items
    assert item.item_id == "schneider:A9F74120"
    assert item.supplier == "Schneider Electric"
    assert item.family == "mcb" and item.poles == 1 and item.amps == 20.0
    assert item.list_price_zar_excl_vat == 185.5
    assert item.price_date == "2026-09-08"
    assert item.category == "Miniature Circuit Breakers"
    assert item.price_source == "price list"


EDGES = [53, 161, 306, 496, 548, 599, 813, 919, 974, 1015, 1060, 1101]


def _span(x0, text, step=5.0):
    return (x0, [(x0 + step * k + step / 2, c) for k, c in enumerate(text)])


def test_a_row_is_split_into_cells_by_span_start_and_overflow_stays_in_its_cell():
    spans = [_span(53, "General Purpose"), _span(161, "1 Residential"), _span(306, "Wiring Device System"),
             _span(496, "WDS"), _span(548, "33394"),
             _span(599, "NS 1000 N 4P BASIC BREAKER DRAWOUT ELEC"),  # runs past 813 into the price column
             _span(814, "ZAR"), _span(886, "41 234,00"), _span(919, "PPCCB")]
    cells = cat.row_cells(spans, EDGES)
    assert cells[4:8] == ["33394", "NS 1000 N 4P BASIC BREAKER DRAWOUT ELEC", "ZAR 41 234,00", "PPCCB"]


def test_a_part_number_glued_to_its_description_is_split_at_the_description_column():
    spans = [_span(53, "General Purpose"), _span(548, "EPH280022Asfora-socket outlet", step=51 / 9)]
    cells = cat.row_cells(spans, EDGES)
    assert cells[4] == "EPH280022" and cells[5] == "Asfora-socket outlet"


def test_any_two_glued_cells_are_split_when_the_next_column_has_no_span_of_its_own():
    glued = "2 Small & Med building General PEntry & Medium Meters"   # sub-collection + group printed as one span
    step = (306 - 161) / len("2 Small & Med building General P")
    spans = [_span(53, "General Purpose"), _span(161, glued, step=step), _span(496, "AMT"),
             _span(548, "METSEPM5"), _span(599, "PM5560 POWER METER"), _span(814, "ZAR"), _span(870, "11 111,00")]
    cells = cat.row_cells(spans, EDGES)
    assert cells[1:4] == ["2 Small & Med building General P", "Entry & Medium Meters", "AMT"]


def test_reading_a_price_list_pdf_end_to_end(tmp_path):
    import fitz
    doc = fitz.open()
    page = doc.new_page(width=1200, height=400)
    for x, text in zip(EDGES, HEADER):
        page.insert_text((x, 40), text.split()[0], fontsize=6)
    for y, (part, desc, price) in ((60, ("A9F74120", "C60N MCB 1P 20A C", "185,50")), (75, ("A9F74220", "C60N MCB 2P 20A C", "1 020,00"))):
        for x, text in ((53, "General Purpose"), (306, "Miniature Circuit Breakers"), (496, "MCB"), (548, part),
                        (599, desc), (814, "ZAR"), (870, price), (919, "HSCWD")):
            page.insert_text((x, y), text, fontsize=6)
    path = tmp_path / "list.pdf"
    doc.save(path)
    rows, _ = cat.read_schneider_pdf(path)
    items, skipped = cat.parse_schneider_rows(rows, source="list.pdf", price_date="2026-09-08")
    assert [(i.part_no, i.list_price_zar_excl_vat, i.poles) for i in items] == [("A9F74120", 185.5, 1), ("A9F74220", 1020.0, 2)]
    assert skipped == 0


def test_repeated_part_numbers_never_disappear_silently():
    rows = [_row("A1", "C60N MCB 1P 20A C", "ZAR 185,50"),
            _row("A1", "C60N MCB 1P 20A C", "ZAR 185,50"),                     # exact repeat: dropped, counted
            _row("A1", "C60N MCB 1P 20A C", "ZAR 190,00", group="Other range")]  # same part, other price: kept
    stats: dict = {}
    items, skipped = cat.parse_schneider_rows(rows, source="s.pdf", price_date="2026-09-08", stats=stats)
    assert [(i.item_id, i.list_price_zar_excl_vat) for i in items] == [("schneider:A1", 185.5), ("schneider:A1~2", 190.0)]
    assert stats == {"exact_duplicates": 1, "same_part_other_price": 1}


def test_afriplan_estimate_prices_enter_the_catalogue_with_their_keys():
    items = cat.items_from_constants(price_date="2026-02-01")
    by_id = {i.item_id: i for i in items}
    from core import constants
    key = next(iter(constants.DB_PRICES))
    assert by_id[f"afriplan:{key}"].list_price_zar_excl_vat == constants.DB_PRICES[key]
    assert by_id[f"afriplan:{key}"].afriplan_key == key
    assert all(i.supplier == "AfriPlan estimate" for i in items)
    assert not any(i.afriplan_key in constants.LABOUR_RATES for i in items)  # labour is not a product


def test_overrides_change_price_and_date_and_can_add_a_custom_item():
    items, _ = cat.parse_schneider_rows([_row("A9F74120", "C60N MCB 1P 20A C", "ZAR 185,50")],
                                        source="s.pdf", price_date="2026-09-08")
    overrides = [
        {"item_id": "schneider:A9F74120", "list_price_zar_excl_vat": "199.00", "price_date": "2026-11-01",
         "updated_by": "Herve", "note": "supplier quote"},
        {"item_id": "acdc:XYZ", "supplier": "ACDC Dynamics", "description": "Isolator 30A DP IP66",
         "list_price_zar_excl_vat": "310", "price_date": "2026-11-02", "updated_by": "Jonathan"},
        {"item_id": "schneider:NOPE", "list_price_zar_excl_vat": "1"},  # unknown and no description
    ]
    merged, problems = cat.apply_overrides(items, overrides)
    by_id = {i.item_id: i for i in merged}
    mcb = by_id["schneider:A9F74120"]
    assert (mcb.list_price_zar_excl_vat, mcb.price_date) == (199.0, "2026-11-01")
    assert mcb.price_source == "override: Herve — supplier quote"
    custom = by_id["acdc:XYZ"]
    assert custom.family == "isolator" and custom.amps == 30.0 and custom.supplier == "ACDC Dynamics"
    assert problems == ["schneider:NOPE: not in the catalogue and no description — ignored"]


def test_csv_round_trip_keeps_every_field(tmp_path):
    items, _ = cat.parse_schneider_rows([_row("A9F74120", "C60N MCB 1P 20A C", "ZAR 185,50")],
                                        source="s.pdf", price_date="2026-09-08")
    path = tmp_path / "price_catalogue.csv"
    cat.write_csv(items, path)
    assert cat.load_catalogue(path) == items


def test_excel_has_catalogue_suppliers_sources_and_an_editable_net_price(tmp_path):
    items, _ = cat.parse_schneider_rows([_row("A9F74120", "C60N MCB 1P 20A C", "ZAR 185,50")],
                                        source="s.pdf", price_date="2026-09-08")
    suppliers = [cat.Supplier(name="Schneider Electric", role="manufacturer", source="s.pdf", source_date="2026-09-08")]
    sources = [cat.SourceDoc(document="s.pdf", supplier="Schneider Electric", price_date="2026-09-08", items=1, skipped=0)]
    path = tmp_path / "price_catalogue.xlsx"
    cat.write_xlsx(items, suppliers, sources, path)
    wb = openpyxl.load_workbook(path)
    assert wb.sheetnames == ["README", "Catalogue", "Suppliers", "Sources"]
    ws = wb["Catalogue"]
    head = [c.value for c in ws[1]]
    assert {"item_id", "supplier", "price_date", "list_price_zar_excl_vat", "discount_pct", "net_price_zar_excl_vat"} <= set(head)
    net = ws.cell(row=2, column=head.index("net_price_zar_excl_vat") + 1).value
    assert str(net).startswith("=")  # a formula, so a user's discount updates it


def test_sparks_directory_gives_company_names_and_roles_but_no_people():
    text = "BUYER'S GUIDE\nMANUFACTURERS \nCONTACTS\nPROTECTION\nABB South Africa\nSiemens\nDISTRIBUTORS\nACDC Dynamics\nVoltex\nCONTACT\nABB South Africa\nCustomer contact centre \nACDC Dynamics\nElmari Erasmus\n"
    sup = cat.parse_sparks_directory(text, source="sparks.pdf", source_date="2019-09-01")
    names = {(s.name, s.role) for s in sup}
    assert ("ABB South Africa", "manufacturer") in names and ("Voltex", "distributor") in names
    assert not any("Erasmus" in s.name or "contact" in s.name.lower() for s in sup)
    assert not any(s.name in {"PROTECTION", "CONTACTS"} for s in sup)
