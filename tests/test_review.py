"""
AfriPlan Electrical v4.1 — Review Manager Tests

Tests for the contractor review functionality.
"""

import pytest
from datetime import datetime

from agent.models import (
    ExtractionResult,
    BuildingBlock,
    Room,
    DBBoard,
    Circuit,
    Fixture,
    PlugPoint,
    SiteCableRun,
    ItemConfidence,
    CorrectionType,
)
from agent.stages.review import ReviewManager


@pytest.fixture
def sample_extraction():
    """Create a sample extraction result for testing."""
    fixture1 = Fixture(
        fixture_type="downlight",
        quantity=4,
        wattage_w=9,
        confidence=ItemConfidence.EXTRACTED,
    )
    fixture2 = Fixture(
        fixture_type="batten",
        quantity=2,
        wattage_w=18,
        confidence=ItemConfidence.INFERRED,
    )

    room1 = Room(
        room_name="Bedroom 1",
        room_type="bedroom",
        area_m2=12.0,
        fixtures=[fixture1],
        plugs=[PlugPoint(socket_type="double", quantity=2)],
        confidence=ItemConfidence.EXTRACTED,
    )
    room2 = Room(
        room_name="Kitchen",
        room_type="kitchen",
        area_m2=15.0,
        fixtures=[fixture2],
        plugs=[PlugPoint(socket_type="double", quantity=4)],
        confidence=ItemConfidence.INFERRED,
    )

    circuit1 = Circuit(
        circuit_number="C1",
        circuit_type="lighting",
        breaker_a=10,
        point_count=6,
        confidence=ItemConfidence.EXTRACTED,
    )

    db1 = DBBoard(
        db_name="Main DB",
        db_type="distribution",
        ways=12,
        main_breaker_a=60,
        circuits=[circuit1],
        confidence=ItemConfidence.EXTRACTED,
    )

    cable1 = SiteCableRun(
        from_point="Meter",
        to_point="Main DB",
        cable_type="16mm² 4-core",
        length_m=25.0,
        confidence=ItemConfidence.INFERRED,
    )

    block = BuildingBlock(
        block_name="House",
        block_type="residential",
        floors=1,
        db_boards=[db1],
        rooms=[room1, room2],
        site_cable_runs=[cable1],
    )

    return ExtractionResult(
        building_blocks=[block],
        overall_confidence=0.75,
    )


class TestReviewManager:
    """Test ReviewManager functionality."""

    def test_init(self, sample_extraction):
        manager = ReviewManager(sample_extraction, "Test Project")
        assert manager.project_name == "Test Project"
        assert manager.original_extraction == sample_extraction
        assert len(manager.corrections) == 0

    def test_update_fixture_count(self, sample_extraction):
        manager = ReviewManager(sample_extraction)

        # Update fixture quantity
        manager.update_fixture_count(
            block_idx=0,
            room_idx=0,
            fixture_idx=0,
            new_quantity=6,
        )

        # Check correction logged
        assert len(manager.corrections) == 1
        assert manager.corrections[0].original_value == 4
        assert manager.corrections[0].corrected_value == 6
        assert manager.corrections[0].correction_type == CorrectionType.QUANTITY_CHANGE

        # Check fixture updated
        fixture = sample_extraction.building_blocks[0].rooms[0].fixtures[0]
        assert fixture.quantity == 6
        assert fixture.confidence == ItemConfidence.MANUAL

    def test_update_circuit_value(self, sample_extraction):
        manager = ReviewManager(sample_extraction)

        manager.update_circuit_value(
            block_idx=0,
            db_idx=0,
            circuit_idx=0,
            field="breaker_a",
            new_value=16,
        )

        assert len(manager.corrections) == 1
        circuit = sample_extraction.building_blocks[0].db_boards[0].circuits[0]
        assert circuit.breaker_a == 16
        assert circuit.confidence == ItemConfidence.MANUAL

    def test_update_cable_length(self, sample_extraction):
        manager = ReviewManager(sample_extraction)

        manager.update_cable_length(
            block_idx=0,
            cable_idx=0,
            new_length=30.0,
        )

        cable = sample_extraction.building_blocks[0].site_cable_runs[0]
        assert cable.length_m == 30.0
        assert cable.confidence == ItemConfidence.MANUAL

    def test_add_room(self, sample_extraction):
        manager = ReviewManager(sample_extraction)

        new_room = Room(
            room_name="Bathroom 1",
            room_type="bathroom",
            area_m2=6.0,
            confidence=ItemConfidence.MANUAL,
        )
        manager.add_room(block_idx=0, room=new_room)

        assert len(sample_extraction.building_blocks[0].rooms) == 3
        assert sample_extraction.building_blocks[0].rooms[2].room_name == "Bathroom 1"

    def test_remove_room(self, sample_extraction):
        manager = ReviewManager(sample_extraction)

        manager.remove_room(block_idx=0, room_idx=1)

        assert len(sample_extraction.building_blocks[0].rooms) == 1
        assert sample_extraction.building_blocks[0].rooms[0].room_name == "Bedroom 1"

    def test_get_items_needing_review(self, sample_extraction):
        manager = ReviewManager(sample_extraction)

        items = manager.get_items_needing_review()

        # Should return items with INFERRED or ESTIMATED confidence
        assert len(items) > 0
        for item in items:
            assert item["confidence"] in [ItemConfidence.INFERRED, ItemConfidence.ESTIMATED]

    def test_complete_review(self, sample_extraction):
        manager = ReviewManager(sample_extraction)

        # Make some changes
        manager.update_fixture_count(0, 0, 0, 8)

        result = manager.complete_review()

        assert result.review_completed
        assert result.review_timestamp is not None
        assert len(result.correction_log) == 1

    def test_get_correction_summary(self, sample_extraction):
        manager = ReviewManager(sample_extraction)

        # Make several changes
        manager.update_fixture_count(0, 0, 0, 8)
        manager.update_cable_length(0, 0, 35.0)

        summary = manager.get_correction_summary()

        assert summary["total_corrections"] == 2
        assert CorrectionType.QUANTITY_CHANGE in summary["by_type"]
        assert CorrectionType.CABLE_CHANGE in summary["by_type"]


class TestReviewManagerEdgeCases:
    """Test edge cases and error handling."""

    def test_invalid_block_index(self, sample_extraction):
        manager = ReviewManager(sample_extraction)

        with pytest.raises(IndexError):
            manager.update_fixture_count(
                block_idx=99,  # Invalid
                room_idx=0,
                fixture_idx=0,
                new_quantity=5,
            )

    def test_invalid_room_index(self, sample_extraction):
        manager = ReviewManager(sample_extraction)

        with pytest.raises(IndexError):
            manager.update_fixture_count(
                block_idx=0,
                room_idx=99,  # Invalid
                fixture_idx=0,
                new_quantity=5,
            )

    def test_empty_extraction(self):
        empty = ExtractionResult()
        manager = ReviewManager(empty)

        items = manager.get_items_needing_review()
        assert items == []


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
