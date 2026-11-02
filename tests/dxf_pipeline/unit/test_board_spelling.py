"""A layout can spell a board differently from its SLD. On the building's own sheet, one letter apart
is the same board: never billed a second time, and never silent. Synthetic sheets, no client data."""

from __future__ import annotations

from agent.dxf_pipeline.passes.assemble import findings_from_recognition, same_board
from agent.dxf_pipeline.passes.recognize import DxfRecognition


class _Tagged(DxfRecognition):
    def __init__(self, *tags):
        super().__init__()
        self._tags = list(tags)

    def db_refs(self):
        return self._tags


def test_one_letter_apart_on_the_buildings_own_sheet_is_the_same_board():
    assert same_board("DB-SGR", ["DB-SGH", "DB-CR"], sheet_code="SGH") == "DB-SGH"


def test_a_sheet_of_another_building_proves_nothing():
    assert same_board("DB-SGR", ["DB-SGH"], sheet_code="LGH") is None


def test_two_letters_apart_are_two_boards():
    assert same_board("DB-XYR", ["DB-SGH"], sheet_code="SGH") is None


def test_boards_numbered_in_a_row_stay_apart():
    assert same_board("DB-AB2", ["DB-AB1"], sheet_code="AB") is None


def test_the_sld_board_is_not_billed_again_under_the_layouts_spelling():
    found = findings_from_recognition(_Tagged("DB-SGR"), known_boards=["DB-SGH"], sheet_code="SGH")
    assert found.boards == []
    assert any("DB-SGR" in g.description and "DB-SGH" in g.description for g in found.all_gaps())


def test_an_unknown_board_is_still_billed_and_flagged():
    found = findings_from_recognition(_Tagged("DB-XY"), known_boards=["DB-SGH"], sheet_code="SGH")
    assert [b.name for b in found.boards] == ["DB-XY"]
