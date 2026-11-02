"""Things to check as questions: each answer changes the bill through the one pricer, and what the
reader found is never touched. Synthetic findings, no client data."""

from __future__ import annotations

import pytest

from agent.shared.boq import BQSection, GapItem, ItemConfidence
from agent.shared.findings import Evidence, FeederFinding, Findings, ItemFinding, WireFinding
from agent.shared.pricing import price_findings
from review.questions import apply_answers, build_questions, group_questions

BY = "Thandi"


def _gap(description, severity="medium"):
    return GapItem(section=BQSection.LIGHTING, description=description, assumption="As read.",
                   suggested_action="Check.", severity=severity, drawing_ref="dxf")


def _findings() -> Findings:
    measured = FeederFinding(from_board="DB-A", to_board="DB-B", cable_size_mm2=16, length_m=76.7, trench_m=70,
                             evidence=Evidence.MEASURED, confidence=ItemConfidence.INFERRED,
                             length_options={"As the site plan draws it": 76.7, "Written on the site plan": 46.0},
                             gaps=[_gap("Feeder DB-A→DB-B: lengths written on the site plan add to 46 m, "
                                        "the drawn route scales to 70 m")])
    guessed = FeederFinding(from_board="DB-A", to_board="DB-C", cable_size_mm2=35, length_m=30, trench_m=30,
                            evidence=Evidence.ASSUMED, confidence=ItemConfidence.ASSUMED,
                            gaps=[_gap("Feeder DB-A→DB-C has no drawn route on the site plan", "high")])
    plain = FeederFinding(from_board="DB-A", to_board="DB-D", cable_size_mm2=10, length_m=20, trench_m=20,
                          evidence=Evidence.MEASURED, confidence=ItemConfidence.INFERRED)
    return Findings(
        feeders=[measured, guessed, plain],
        items=[ItemFinding(description="Switch — Office", qty=4, building="WD-A", material_zar=50, install_zar=85)],
        wires=[WireFinding(description="wire L1", metres=50, route_m=40, building="WD-A", evidence=Evidence.MEASURED)],
        gaps=[_gap("Legend lists 'Geyser' but no instances were counted"),
              _gap("Legend lists 'Exit Sign' but no instances were counted"),
              _gap("A.dwg is an older revision of B.dwg — not read, so nothing is counted twice"),
              _gap("Feeder lengths noted", "low")],
    )


def _ask(findings=None):
    f = findings or _findings()
    return {q.id: q for q in build_questions(f, f)}


def _bill(findings):
    return price_findings(findings, pipeline="dxf")


def _feeder(answered, to):
    return next(f for f in answered.feeders if f.to_board == to)


def test_a_feeder_with_no_route_asks_its_cable_and_its_trench():
    q = _ask()["feeder:DBA>DBC"]
    assert q.group == "no_route" and q.severity == "high"
    assert [(f.name, f.value) for f in q.fields] == [("length_m", 30), ("trench_m", 30)]


def test_a_feeder_with_two_lengths_offers_both_with_their_rand_change():
    q = _ask()["feeder:DBA>DBB"]
    assert q.group == "lengths"
    written = next(o for o in q.options if o.label == "Written on the site plan")
    assert written.value == 46 and written.change_zar < 0


def test_a_feeder_nobody_doubts_asks_nothing():
    assert "feeder:DBA>DBD" not in _ask()


def test_every_question_says_what_is_at_stake():
    q = _ask()["feeder:DBA>DBC"]
    assert q.on_bill_zar > 0 and q.per_unit_zar > 0 and q.per_unit == "metre"


def test_a_notes_only_gap_asks_nothing():
    assert not any("Feeder lengths noted" in q.title for q in _ask().values())


def test_answering_a_length_changes_the_bill_and_clears_the_question():
    original = _findings()
    answered = apply_answers(original, {"feeder:DBA>DBC": {"length_m": 55, "trench_m": 0}}, by=BY)
    f = _feeder(answered, "DB-C")
    assert f.length_m == 55 and f.trench_m == 0 and BY in f.assumption
    assert f.source_label == "Answered"
    assert not any("no drawn route" in g.description for g in _bill(answered).gaps)
    assert _bill(answered).subtotal_zar != _bill(original).subtotal_zar


def test_what_the_reader_found_is_never_touched():
    original = _findings()
    before = original.model_dump_json()
    apply_answers(original, {"feeder:DBA>DBC": {"length_m": 55, "trench_m": 0}, "conduit_labour": {"rate": 40}}, by=BY)
    assert original.model_dump_json() == before


def test_no_answers_reprices_to_the_same_bill():
    assert _bill(apply_answers(_findings(), {}, by=BY)).subtotal_zar == _bill(_findings()).subtotal_zar


def test_a_ceiling_answer_moves_the_conduit_and_clears_its_flag():
    original = _findings()
    answered = apply_answers(original, {"ceiling:WD-A": {"ceiling_m": 4.0}}, by=BY)
    conduit = lambda b: next(l for l in b.line_items if "conduit" in l.description)     # noqa: E731
    assert conduit(_bill(answered)).qty == pytest.approx(conduit(_bill(original)).qty + 4)   # 4 switches × 1 m
    assert not any("Ceiling height" in g.description for g in _bill(answered).gaps)


def test_conduit_labour_is_added_and_stops_being_flagged():
    original = _findings()
    answered = apply_answers(original, {"conduit_labour": {"rate": 40}}, by=BY)
    assert _bill(answered).subtotal_zar > _bill(original).subtotal_zar
    assert not any("Conduit install labour" in g.description for g in _bill(answered).gaps)


def test_conduit_shows_what_it_rests_on_until_the_ceiling_is_answered():
    conduit = lambda b: next(l for l in b.line_items if "conduit" in l.description)     # noqa: E731
    assert conduit(_bill(_findings())).source_label == "Measured, ceiling assumed"
    answered = apply_answers(_findings(), {"ceiling:WD-A": {"ceiling_m": 3.0}}, by=BY)
    assert conduit(_bill(answered)).source_label == "Measured"


def test_a_legend_item_answered_none_clears_and_adds_nothing():
    original = _findings()
    answered = apply_answers(original, {"legend:Geyser": {"qty": 0}}, by=BY)
    assert not any("Geyser" in g.description for g in _bill(answered).gaps)
    assert len(_bill(answered).line_items) == len(_bill(original).line_items)


def test_a_legend_item_with_a_count_and_price_becomes_a_line():
    answered = apply_answers(_findings(), {"legend:Geyser": {"qty": 2, "rate": 1500}}, by=BY)
    [line] = [l for l in _bill(answered).line_items if l.description.startswith("Geyser")]
    assert line.qty == 2 and line.unit_price_zar == 1500 and line.source_label == "Answered"


def test_a_counted_item_with_no_price_says_so():
    answered = apply_answers(_findings(), {"legend:Geyser": {"qty": 2}}, by=BY)
    assert any("No rate" in g.description and "Geyser" in g.description for g in _bill(answered).gaps)


def test_a_counted_catalogue_item_takes_its_catalogue_rate():
    original = _findings()
    original.gaps.append(_gap("Legend lists 'LED Floodlight' but no instances were counted"))
    answered = apply_answers(original, {"legend:LED Floodlight": {"qty": 3}}, by=BY)
    [line] = [l for l in _bill(answered).line_items if l.description.startswith("LED Floodlight")]
    assert line.unit_price_zar > 0


def test_a_gap_with_nothing_to_measure_is_confirmed_and_clears():
    questions = _ask()
    [q] = [q for q in questions.values() if "older revision" in q.title]
    assert q.group == "confirm" and q.fields == []
    answered = apply_answers(_findings(), {q.id: {}}, by=BY)
    assert not any("older revision" in g.description for g in _bill(answered).gaps)


def test_question_ids_do_not_depend_on_the_order_of_the_findings():
    a, b = _findings(), _findings()
    b.gaps.reverse()
    assert set(_ask(a)) == set(_ask(b))


def test_questions_gather_into_a_few_groups_with_a_one_click_answer():
    f = _findings()
    groups = {g.key: g for g in group_questions(build_questions(f, f))}
    assert list(groups)[0] == "no_route"                      # most urgent first
    assert groups["legend"].bulk.values == {"qty": 0}
    assert groups["ceiling"].bulk.values == {"ceiling_m": 3.0}
    assert groups["confirm"].bulk is not None and groups["no_route"].bulk is None
    assert len(groups) <= 6
