"""Where the Reproduction Score is lost — every missing point traced to an item and a cause."""

import pytest

from evaluation.gaps import analyse_gaps
from evaluation.metrics import PredLine, score
from evaluation.network import DrawingType as D
from evaluation.reference import RefBuilding, RefLine, ReferenceBoq


def _l(fam, qty, rate, spec="", bld="H"):
    return RefLine(sheet=bld, building=bld, description=fam, qty=qty, rate=rate,
                   total=qty * rate, key_family=fam, key_spec=spec)


def _p(fam, qty, rate, spec="", bld="H"):
    return PredLine(building=bld, family=fam, spec=spec, qty=qty, rate=rate, total=qty * rate)


@pytest.fixture
def card():
    ref = ReferenceBoq(project="t", buildings=[RefBuilding(name="H", sheet="H", in_summary=True, lines=[
        _l("socket_double", 10, 400),             #   4 000  exact
        _l("light_panel", 20, 2000),              #  40 000  never produced
        _l("swa_cable", 100, 450, "50mm2|4c"),    #  45 000  half the length
        _l("db", 2, 3000),                        #   6 000  three times too many
        _l("connection_fee", 1, 5000),            #   5 000  provisional sum, never on a drawing
    ])])                                          # 100 000
    pred = [
        _p("socket_double", 10, 400),
        _p("swa_cable", 50, 450, "50mm2|4c"),
        _p("db", 6, 1500),
        _p("light_pole", 4, 2500),                # not in the bill at all
    ]
    return score(pred, ref, uploaded={D.SLD, D.LIGHTING, D.PLUGS})


def test_points_lost_add_up_to_exactly_what_the_score_misses(card):
    gaps = analyse_gaps(card)
    assert gaps.reproduction_score == pytest.approx(card.reproduction_score)
    assert sum(i.points_lost for i in gaps.items) == pytest.approx(1 - card.reproduction_score)
    assert sum(gaps.by_cause.values()) == pytest.approx(1 - card.reproduction_score)


def test_each_reference_item_gets_the_cause_of_its_loss(card):
    cause = {i.family: i.cause for i in analyse_gaps(card).items}
    assert cause == {"socket_double": "exact", "light_panel": "not_produced", "swa_cable": "qty_low",
                     "db": "qty_high", "connection_fee": "not_produced"}


def test_losses_are_grouped_by_family_bill_section_and_method(card):
    gaps = analyse_gaps(card)
    fam = {g.name: g for g in gaps.by_family}
    assert fam["light_panel"].points_lost == pytest.approx(0.40)
    assert fam["light_panel"].not_produced == pytest.approx(0.40)
    assert fam["swa_cable"].qty_low == pytest.approx(0.225)       # 45 % of value × half the qty
    assert gaps.by_family[0].name == "light_panel"                # biggest loss first
    sections = {g.name: g.points_lost for g in gaps.by_section}
    assert sections["D"] == pytest.approx(0.40)                   # lighting section
    methods = {g.name: g.points_lost for g in gaps.by_method}
    assert methods["provisional"] == pytest.approx(0.05)


def test_items_priced_that_the_real_bill_does_not_have_are_listed(card):
    extras = analyse_gaps(card).extras
    assert [(e.family, e.pred_value) for e in extras] == [("light_pole", 10_000)]


def test_rate_errors_are_reported_separately_because_rs_ignores_rates(card):
    rates = {i.family: i for i in analyse_gaps(card).rate_errors}
    assert set(rates) == {"db"}                                   # only the DB rate is off
    assert rates["db"].ref_rate == pytest.approx(3000) and rates["db"].pred_rate == pytest.approx(1500)


def test_every_lost_item_says_what_kind_of_fix_it_needs(card):
    hint = {i.family: i.fix for i in analyse_gaps(card).items}
    assert "never on a drawing" in hint["connection_fee"]
    assert "length" in hint["swa_cable"]
    assert "never reported" in hint["light_panel"]
    assert hint["socket_double"] == ""


def test_an_item_the_uploaded_drawings_cannot_show_is_blamed_on_the_missing_drawing():
    ref = ReferenceBoq(project="t", buildings=[RefBuilding(name="H", sheet="H", in_summary=True,
                                                           lines=[_l("manhole", 3, 1000)])])
    item = analyse_gaps(score([], ref, uploaded={D.SLD})).items[0]
    assert not item.in_scope
    assert "site_plan" in item.fix
