"""Issue 011 — merging facts across pages must not double-count what two sheets both show."""
from agent.pdf_pipeline.passes.facts import (
    Feeder, LayoutTakeoff, PowerSpine, SpineCircuit, SpineDB, TakeoffRoom,
)
from agent.pdf_pipeline.passes.orchestrator import _merge_spine, _merge_takeoff, _site_lighting_gaps


def _db(name, amps=100, circuits=2):
    return SpineDB(name=name, main_breaker_a=amps, circuits=[SpineCircuit(breaker_a=20)] * circuits)


def test_a_board_on_two_sheets_is_one_board():
    dst, gaps = PowerSpine(), []
    _merge_spine(dst, PowerSpine(distribution_boards=[_db("DB-1", circuits=2)]), page=1, gaps=gaps)
    _merge_spine(dst, PowerSpine(distribution_boards=[_db("DB1", circuits=5)]), page=4, gaps=gaps)
    assert len(dst.distribution_boards) == 1
    assert len(dst.distribution_boards[0].circuits) == 5          # the fuller reading wins
    assert dst.distribution_boards[0].name == "DB-1"              # first spelling kept
    assert not gaps


def test_conflicting_board_rating_is_a_gap_not_a_silent_pick():
    dst, gaps = PowerSpine(), []
    _merge_spine(dst, PowerSpine(distribution_boards=[_db("DB-CR", amps=250)]), page=2, gaps=gaps)
    _merge_spine(dst, PowerSpine(distribution_boards=[_db("DB-CR", amps=300)]), page=3, gaps=gaps)
    assert len(dst.distribution_boards) == 1
    assert len(gaps) == 1 and "250" in gaps[0].description and "300" in gaps[0].description
    assert "p2" in gaps[0].description and "p3" in gaps[0].description


def test_missing_rating_is_filled_from_the_other_sheet():
    dst, gaps = PowerSpine(), []
    _merge_spine(dst, PowerSpine(distribution_boards=[_db("DB-ST", amps=0, circuits=4)]), page=1, gaps=gaps)
    _merge_spine(dst, PowerSpine(distribution_boards=[_db("DB-ST", amps=63, circuits=1)]), page=2, gaps=gaps)
    assert dst.distribution_boards[0].main_breaker_a == 63 and not gaps


def test_the_same_feeder_on_two_sheets_is_one_feeder():
    dst, gaps = PowerSpine(), []
    f1 = Feeder(from_source="DB-CR", to_db="DB-SGH", cable_size_mm2=6)
    f2 = Feeder(from_source="DB CR", to_db="DB-SGH", cable_size_mm2=6, length_m=30, length_annotated=True)
    _merge_spine(dst, PowerSpine(feeders=[f1]), page=1, gaps=gaps)
    _merge_spine(dst, PowerSpine(feeders=[f2]), page=2, gaps=gaps)
    assert len(dst.feeders) == 1
    assert dst.feeders[0].length_annotated and dst.feeders[0].length_m == 30   # the written length kept


def test_feeder_size_conflict_is_a_gap():
    dst, gaps = PowerSpine(), []
    _merge_spine(dst, PowerSpine(feeders=[Feeder(from_source="DB-CR", to_db="DB-1", cable_size_mm2=50)]), page=1, gaps=gaps)
    _merge_spine(dst, PowerSpine(feeders=[Feeder(from_source="DB-CR", to_db="DB1", cable_size_mm2=35)]), page=2, gaps=gaps)
    assert len(dst.feeders) == 1 and len(gaps) == 1 and "50" in gaps[0].description


def test_a_room_on_the_lighting_and_the_plug_sheet_is_one_room():
    dst, gaps = LayoutTakeoff(), []
    _merge_takeoff(dst, LayoutTakeoff(rooms=[TakeoffRoom(room_name="Kitchen / Scullery", served_by_db="DB-1",
                                                         downlights=6)]), page=3, gaps=gaps)
    _merge_takeoff(dst, LayoutTakeoff(rooms=[TakeoffRoom(room_name="kitchen /  scullery", served_by_db="DB1",
                                                         double_sockets=4)]), page=5, gaps=gaps)
    assert len(dst.rooms) == 1
    room = dst.rooms[0]
    assert (room.downlights, room.double_sockets) == (6, 4)
    assert room.source_pages == [3, 5]
    assert not gaps


def test_the_same_room_counted_differently_on_two_sheets_takes_the_higher_count_and_says_so():
    dst, gaps = LayoutTakeoff(), []
    _merge_takeoff(dst, LayoutTakeoff(rooms=[TakeoffRoom(room_name="Hall", downlights=12)]), page=3, gaps=gaps)
    _merge_takeoff(dst, LayoutTakeoff(rooms=[TakeoffRoom(room_name="Hall", downlights=10)]), page=4, gaps=gaps)
    assert dst.rooms[0].downlights == 12
    assert len(gaps) == 1 and "12" in gaps[0].description and "10" in gaps[0].description


def test_two_rooms_with_the_same_name_on_one_sheet_stay_separate():
    dst, gaps = LayoutTakeoff(), []
    _merge_takeoff(dst, LayoutTakeoff(rooms=[TakeoffRoom(room_name="Store", downlights=1),
                                             TakeoffRoom(room_name="Store", downlights=2)]), page=3, gaps=gaps)
    assert len(dst.rooms) == 2


def test_site_lighting_on_several_sheets_is_flagged():
    dst, gaps = LayoutTakeoff(), []
    _merge_takeoff(dst, LayoutTakeoff(rooms=[TakeoffRoom(room_name="Site / external", pole_lights=14)]), page=2, gaps=gaps)
    _merge_takeoff(dst, LayoutTakeoff(rooms=[TakeoffRoom(room_name="North perimeter", pole_lights=35)]), page=6, gaps=gaps)
    flagged = _site_lighting_gaps(dst)
    assert len(flagged) == 1 and "p2" in flagged[0].description and "p6" in flagged[0].description
    assert flagged[0].severity == "medium"
    single = LayoutTakeoff(rooms=[TakeoffRoom(room_name="Site", pole_lights=14, source_pages=[2])])
    assert not _site_lighting_gaps(single)


def test_merge_bookkeeping_is_not_serialised():
    dst = PowerSpine()
    _merge_spine(dst, PowerSpine(distribution_boards=[_db("DB-1")]), page=1, gaps=[])
    _merge_spine(dst, PowerSpine(distribution_boards=[_db("DB-1")]), page=2, gaps=[])
    dumped = dst.model_dump_json()
    assert "_pages" not in dumped and "DB-1" in dumped
