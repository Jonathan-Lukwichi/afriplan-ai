"""Reading accuracy: did we read what is DRAWN — counted symbols and measured runs — independent of any price."""

import pytest

from evaluation.metrics import PredLine, score
from evaluation.network import DrawingType as D
from evaluation.reading import reading_accuracy
from evaluation.reference import RefBuilding, RefLine, ReferenceBoq


def _l(fam, qty, rate, spec=""):
    return RefLine(sheet="H", building="H", description=fam, qty=qty, rate=rate, total=qty * rate,
                   key_family=fam, key_spec=spec)


def _p(fam, qty, rate, spec=""):
    return PredLine(building="H", family=fam, spec=spec, qty=qty, rate=rate, total=qty * rate)


REF = ReferenceBoq(project="t", buildings=[RefBuilding(name="H", sheet="H", in_summary=True, lines=[
    _l("socket_double", 10, 400),            # count, read exactly
    _l("light_panel", 20, 2000),             # count, 18 of 20 read
    _l("swa_cable", 100, 450, "95mm2|4c"),   # length, half read
    _l("db", 2, 3000),                        # count, never read
    _l("conduit", 300, 100),                 # derived — an estimating rule, not reading
    _l("connection_fee", 1, 5000),           # provisional — never on a drawing
    _l("manhole", 3, 1000),                  # needs the site plan, which was not uploaded
])])
PRED = [_p("socket_double", 10, 400), _p("light_panel", 18, 2000), _p("swa_cable", 50, 450, "95mm2|4c"),
        _p("light_pole", 4, 2500)]          # an extra the bill does not have


@pytest.fixture
def card():
    return score(PRED, REF, uploaded={D.SLD, D.LIGHTING, D.PLUGS})


def test_only_items_counted_or_measured_on_uploaded_drawings_are_judged(card):
    r = reading_accuracy(card)
    assert sorted(i["family"] for i in r["items"]) == ["db", "light_panel", "socket_double", "swa_cable"]
    assert set(r["excluded"]) == {"derived", "provisional", "not_on_uploaded_drawings"}
    assert r["excluded"]["derived"]["families"] == ["conduit"]
    assert r["excluded"]["not_on_uploaded_drawings"]["families"] == ["manhole"]


def test_reading_score_is_value_weighted_by_the_real_bill_and_ignores_our_rates(card):
    r = reading_accuracy(card)
    # judged value 4 000 + 40 000 + 45 000 + 6 000 = 95 000; read 4 000·1 + 40 000·0.9 + 45 000·0.5
    assert r["reading_score"] == pytest.approx((4000 + 36000 + 22500) / 95000)
    cheap = score([p.model_copy(update={"rate": 1, "total": p.qty}) for p in PRED], REF,
                  uploaded={D.SLD, D.LIGHTING, D.PLUGS})
    assert reading_accuracy(cheap)["reading_score"] == pytest.approx(r["reading_score"])   # our prices never matter
    assert reading_accuracy(cheap)["item_precision"] == pytest.approx(r["item_precision"])


def test_item_counts_found_within_tolerance_and_precision_by_count(card):
    r = reading_accuracy(card)
    assert (r["items_judged"], r["items_found"]) == (4, 3)
    assert r["items_within_5pct"] == 1 and r["items_within_10pct"] == 2      # sockets exact, panels -10 %
    assert r["item_precision"] == pytest.approx(3 / 4)                       # light_pole is not in the bill
    assert r["extras"] == ["light_pole"]


def test_each_judged_item_says_what_went_wrong(card):
    by = {i["family"]: i for i in reading_accuracy(card)["items"]}
    assert by["db"]["verdict"] == "not read"
    assert by["swa_cable"]["verdict"] == "read 50 % short"
    assert by["light_panel"]["verdict"] == "read 10 % short"
    assert by["socket_double"]["verdict"] == "exact"
