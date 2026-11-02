"""The list of things to check: one line per question, however many sheets ask it. Rule 7 still holds:
every assumption stays on the list, grouped, and a lone gap is left exactly as it was written."""

from __future__ import annotations

from agent.shared import BQSection
from agent.shared.boq import GapItem
from agent.shared.gaps import group_gaps


def _gap(description, *, assumption="As read.", action="Check.", severity="medium", section=BQSection.LIGHTING):
    return GapItem(section=section, description=description, assumption=assumption,
                   suggested_action=action, severity=severity, drawing_ref="dxf")


def _legend(item):
    return _gap(f"Legend lists '{item}' but no instances were counted")


def test_a_lone_gap_is_left_as_it_was():
    gap = _legend("Geyser")
    assert group_gaps([gap]) == [gap]


def test_the_same_gap_twice_is_one_gap():
    assert len(group_gaps([_gap("Check this"), _gap("Check this")])) == 1


def test_gaps_unlike_each_other_are_not_merged():
    assert len(group_gaps([_gap("One thing"), _gap("Another thing")])) == 2


def test_the_legend_items_become_one_line_naming_each_once():
    [gap] = group_gaps([_legend("Geyser"), _legend("Exit Sign"), _legend("Geyser")])
    assert "2 legend items" in gap.description
    assert "Geyser" in gap.description and "Exit Sign" in gap.description
    assert gap.description.count("Geyser") == 1


def test_feeders_with_no_route_stay_a_must_check_and_are_all_named():
    [gap] = group_gaps([_gap(f"Feeder DB-PFA→DB-HPS{i} has no drawn route on the site plan", assumption="Assumed 30 m.",
                             action="Draw or confirm the route for this board on the site plan.", severity="high")
                        for i in (1, 2)])
    assert gap.severity == "high" and gap.assumption == "Assumed 30 m."
    assert "2 feeders" in gap.description
    assert "DB-PFA→DB-HPS1" in gap.description and "DB-PFA→DB-HPS2" in gap.description


def test_the_same_question_on_each_building_is_asked_once():
    [gap] = group_gaps([_gap(f"Ceiling height for conduit drops in {b} not on the drawing", assumption="3 m assumed.",
                             severity="low") for b in ("WD-AB-01", "WD-PB-01", "this building")])
    assert "3 buildings" in gap.description and gap.assumption == "3 m assumed." and gap.severity == "low"


def test_measured_feeders_keep_their_lengths_as_one_note():
    [gap] = group_gaps([_gap(f"Feeder {n} length taken from the site-plan route", severity="low",
                             assumption=f"Route measured {m} m on the site plan, +5% and 1.5 m at each end.")
                        for n, m in (("A→B", 10.5), ("B→C", 20.0))])
    assert "2 feeder lengths" in gap.description
    assert "A→B 10.5 m" in gap.assumption and "B→C 20 m" in gap.assumption and "+5%" in gap.assumption


def test_written_and_drawn_lengths_that_differ_keep_both_numbers():
    [gap] = group_gaps([
        _gap("Feeder A→B: lengths written on the site plan add to 60 m, the drawn route scales to 40 m"),
        _gap("Feeder B→C: lengths written on the site plan add to 20 m, the drawn route scales to 14 m")])
    assert "A→B (60 m written, 40 m drawn)" in gap.description and "B→C (20 m written, 14 m drawn)" in gap.description


def test_ai_names_become_one_note():
    [gap] = group_gaps([_gap(f"{n} symbols recognised as '{i}' by AI", severity="low")
                        for n, i in ((153, "Vapour Proof Light"), (9, "Bulkhead Light"))])
    assert gap.severity == "low" and "Vapour Proof Light (153)" in gap.description


def test_a_group_takes_the_place_of_its_first_member():
    out = group_gaps([_gap("First"), _legend("Geyser"), _gap("Second"), _legend("Exit Sign")])
    assert [g.description.split(":")[0] for g in out][0] == "First"
    assert out[1].description.startswith("2 legend items") and out[2].description == "Second"


def test_the_order_of_the_sheets_does_not_change_the_words():
    a, b = _legend("Geyser"), _legend("Exit Sign")
    assert group_gaps([a, b])[0].description == group_gaps([b, a])[0].description
