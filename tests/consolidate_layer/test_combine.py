"""
Combining the DWG reader's and the PDF reader's findings into one set (ADR-0008).

The rules under test: nothing is counted twice, the stronger evidence wins, what only one
reader saw is kept, disagreements become things to check, and a warning about a finding
that was dropped is dropped with it.
"""

from __future__ import annotations

from agent.shared import BQSection, GapItem, ItemConfidence
from agent.shared.findings import (
    BoardFinding,
    Evidence,
    FeederFinding,
    Findings,
    ItemFinding,
    WireFinding,
)
from consolidate.combine import combine

LIGHT_WORDS = ["ABLUTION", "BLOCK", "LIGHTING", "LAYOUT", "WDAB01"]


def _cad(**kw) -> Findings:
    f = Findings(**kw)
    f.sheet_words.setdefault("WD-AB-01-LIGHTING", LIGHT_WORDS)
    return f


def _pdf(**kw) -> Findings:
    f = Findings(**kw)
    f.sheet_words.setdefault("Set p0", LIGHT_WORDS)
    return f


def _board(name, reader, amps=100, **kw):
    ev = Evidence.WRITTEN if reader == "dxf" else Evidence.SEEN
    return BoardFinding(name=name, reader=reader, main_breaker_a=amps, circuits=[(20, 1)] * 4,
                        evidence=ev, **kw)


def _kept(combined, kind):
    return getattr(combined.findings, kind)


# ─── boards ──────────────────────────────────────────────────────────

def test_same_board_from_both_readers_is_kept_once_from_the_dwg():
    c = combine(_cad(boards=[_board("DB-AB1", "dxf")]), _pdf(boards=[_board("DB AB1", "pdf")]))
    assert [(b.name, b.reader) for b in c.findings.boards] == [("DB-AB1", "dxf")]
    assert any(d.kind == "board" and d.kept == "dxf" for d in c.decisions)


def test_board_disagreement_becomes_a_thing_to_check():
    c = combine(_cad(boards=[_board("DB-AB1", "dxf", amps=100)]),
                _pdf(boards=[_board("DB-AB1", "pdf", amps=125)]))
    gaps = [g.description for g in c.findings.all_gaps()]
    assert any("DB-AB1" in g and "100" in g and "125" in g for g in gaps)


def test_pdf_board_with_contents_beats_a_dwg_tag_only_board():
    c = combine(_cad(boards=[BoardFinding(name="DB-X", contents_known=False)]),
                _pdf(boards=[_board("DB-X", "pdf")]))
    [b] = c.findings.boards
    assert b.reader == "pdf" and b.contents_known and b.name == "DB-X"


def test_board_only_the_pdf_shows_is_kept():
    c = combine(_cad(boards=[_board("DB-A", "dxf")]), _pdf(boards=[_board("DB-POOL", "pdf")]))
    assert {b.name for b in c.findings.boards} == {"DB-A", "DB-POOL"}


# ─── feeders ─────────────────────────────────────────────────────────

def _feeder(frm, to, reader, ev, length, **kw):
    gaps = [GapItem(description=f"{frm}->{to} length assumed")] if ev == Evidence.ASSUMED else []
    return FeederFinding(from_board=frm, to_board=to, reader=reader, evidence=ev, length_m=length,
                         cable_size_mm2=kw.pop("size", 16), gaps=gaps, **kw)


def test_measured_feeder_wins_and_the_assumed_ones_warning_goes_with_it():
    c = combine(_cad(feeders=[_feeder("KIOSK", "DB-A", "dxf", Evidence.MEASURED, 212.0)]),
                _pdf(feeders=[_feeder("KIOSK", "DB-A", "pdf", Evidence.ASSUMED, 30.0)]))
    [f] = c.findings.feeders
    assert f.reader == "dxf" and f.length_m == 212.0
    assert not any("length assumed" in g.description for g in c.findings.all_gaps())


def test_feeder_cable_size_disagreement_is_flagged():
    c = combine(_cad(feeders=[_feeder("KIOSK", "DB-A", "dxf", Evidence.MEASURED, 50, size=16)]),
                _pdf(feeders=[_feeder("KIOSK", "DB-A", "pdf", Evidence.SEEN, 50, size=25)]))
    assert any("16" in g.description and "25" in g.description for g in c.findings.all_gaps())


def test_ai_matched_names_merge_duplicates_that_python_cannot_pair():
    calls = []

    def matcher(kind, cad_names, pdf_names):
        calls.append((kind, sorted(cad_names), sorted(pdf_names)))
        return {n: ("KIOSK", "same", "the kiosk busbar is the kiosk") for n in pdf_names if "KIOSK" in n}

    cad = _cad(feeders=[_feeder("KIOSK", "DB-A", "dxf", Evidence.MEASURED, 200)])
    pdf = _pdf(feeders=[_feeder("KIOSK (WD-KIOSK-01)", "DB-A", "pdf", Evidence.ASSUMED, 30),
                        _feeder("KIOSK busbar", "DB-A", "pdf", Evidence.ASSUMED, 30)])
    c = combine(cad, pdf, match_names=matcher)
    assert [f.reader for f in c.findings.feeders] == ["dxf"]
    # 'KIOSK (WD-KIOSK-01)' pairs exactly (words in brackets are a description);
    # only the name Python could not pair is sent, once
    assert calls == [("equipment", ["DB-A", "KIOSK"], ["KIOSK busbar"])]
    assert c.ai_matched == 1


def test_unsure_match_keeps_both_and_asks_a_person():
    matcher = lambda kind, cad, pdf: {n: ("DB-A", "unsure", "similar names") for n in pdf}   # noqa: E731
    c = combine(_cad(boards=[_board("DB-A", "dxf")]), _pdf(boards=[_board("DB-A2", "pdf")]),
                match_names=matcher)
    assert {b.name for b in c.findings.boards} == {"DB-A", "DB-A2"}
    assert any("DB-A2" in g.description and "DB-A" in g.description and g.severity == "high"
               for g in c.findings.all_gaps())


def test_without_a_matcher_combining_still_runs_on_exact_matches():
    c = combine(_cad(boards=[_board("KIOSK", "dxf")]), _pdf(boards=[_board("KIOSK busbar", "pdf")]))
    assert len(c.findings.boards) == 2 and c.ai_matched == 0


# ─── items and wiring, sheet by sheet ────────────────────────────────

def _item(name, reader, qty, sheet, **kw):
    ev = Evidence.COUNTED if reader == "dxf" else Evidence.SEEN
    return ItemFinding(description=f"{name} x", item=name, reader=reader, qty=qty, sheet=sheet,
                       section=BQSection.LIGHTING, evidence=ev, **kw)


def test_on_the_same_sheet_the_dwg_count_wins_and_a_big_difference_is_flagged():
    cad = _cad(items=[_item("LED Downlight", "dxf", 40, "WD-AB-01-LIGHTING")])
    pdf = _pdf(items=[_item("LED Downlight", "pdf", 52, "Set p0")])
    c = combine(cad, pdf)
    assert [(i.reader, i.qty) for i in c.findings.items] == [("dxf", 40)]
    assert any("40" in g.description and "52" in g.description for g in c.findings.all_gaps())
    assert c.sheet_pairs == {"Set p0": "WD-AB-01-LIGHTING"}


def test_an_item_only_the_pdf_saw_on_that_sheet_is_kept():
    cad = _cad(items=[_item("LED Downlight", "dxf", 40, "WD-AB-01-LIGHTING")])
    pdf = _pdf(items=[_item("Solar Post Light", "pdf", 18, "Set p0")])
    c = combine(cad, pdf)
    assert {(i.item, i.reader) for i in c.findings.items} == {("LED Downlight", "dxf"), ("Solar Post Light", "pdf")}


def test_items_on_a_page_with_no_dwg_are_kept():
    cad = _cad(items=[_item("LED Downlight", "dxf", 40, "WD-AB-01-LIGHTING")])
    pdf = _pdf(items=[_item("LED Downlight", "pdf", 9, "Set p7")])
    pdf.sheet_words["Set p7"] = ["SWIMMING", "POOL", "PUMP", "ROOM"]
    c = combine(cad, pdf)
    assert sorted(i.qty for i in c.findings.items) == [9, 40]


def test_ai_names_a_dwg_item_the_catalogue_does_not_know():
    cad = _cad(items=[ItemFinding(description="DL-12W (template-matched)", reader="dxf", qty=40,
                                  sheet="WD-AB-01-LIGHTING", evidence=Evidence.COUNTED)])
    pdf = _pdf(items=[_item("LED Downlight", "pdf", 41, "Set p0")])
    matcher = lambda kind, cad_names, pdf_names: {"LED Downlight": ("DL-12W (template-matched)", "same", "12W downlight")}  # noqa: E731
    c = combine(cad, pdf, match_names=matcher)
    assert [i.reader for i in c.findings.items] == ["dxf"]


def test_measured_wiring_replaces_the_pdf_allowance_for_that_sheet():
    cad = _cad(wires=[WireFinding(description="L1", metres=80, sheet="WD-AB-01-LIGHTING",
                                  evidence=Evidence.MEASURED)])
    pdf = _pdf(wires=[WireFinding(description="Tuck shop", metres=64, sheet="Set p0", reader="pdf",
                                  evidence=Evidence.ASSUMED, confidence=ItemConfidence.ASSUMED,
                                  gaps=[GapItem(description="Tuck shop wiring not dimensioned")])])
    c = combine(cad, pdf)
    assert [w.reader for w in c.findings.wires] == ["dxf"]
    assert not any("not dimensioned" in g.description for g in c.findings.all_gaps())


def test_pdf_kiosk_allowance_is_dropped_when_the_dwg_has_the_main_kiosk():
    cad = _cad(boards=[_board("KIOSK", "dxf", main_kiosk=True)])
    pdf = _pdf(items=[ItemFinding(description="Mini-substation / LV kiosk supply & install", item="Main LV kiosk",
                                  reader="pdf", qty=1, section=BQSection.INCOMING, price_zar=45000)])
    c = combine(cad, pdf)
    assert not c.findings.items


def test_a_pdf_warning_about_a_board_goes_only_if_the_dwg_replaced_that_board():
    pdf = _pdf(boards=[_board("DB-A", "pdf"), _board("DB-B", "pdf")],
               gaps=[GapItem(section=BQSection.DISTRIBUTION, building_block="DB-A", description="A: samples disagree"),
                     GapItem(section=BQSection.DISTRIBUTION, building_block="DB-B", description="B: samples disagree")])
    c = combine(_cad(boards=[_board("DB-A", "dxf")]), pdf)
    left = [g.description for g in c.findings.all_gaps()]
    assert "B: samples disagree" in left and "A: samples disagree" not in left


def test_words_in_brackets_describe_the_equipment_and_do_not_stop_an_exact_match():
    cad = _cad(boards=[_board("KIOSK", "dxf")],
               feeders=[_feeder("MINI-SUB", "KIOSK", "dxf", Evidence.MEASURED, 120)])
    pdf = _pdf(boards=[_board("KIOSK (WD-KIOSK-01)", "pdf")],
               feeders=[_feeder("Existing Mini Sub", "KIOSK (WD-KIOSK-01)", "pdf", Evidence.ASSUMED, 30)])
    c = combine(cad, pdf)
    assert [b.reader for b in c.findings.boards] == ["dxf"]
    assert [f.reader for f in c.findings.feeders] == ["dxf"]
