"""
REVIEW Stage: Manages contractor review state and correction tracking.

This stage happens in the UI between DISCOVER and VALIDATE.
The ReviewManager tracks all corrections made by the contractor.
"""

from datetime import datetime
from typing import Optional, Any

from agent.models import (
    ExtractionResult, CorrectionEntry, CorrectionLog, ItemConfidence
)


class ReviewManager:
    """
    Tracks changes made during contractor review.

    Usage:
        manager = ReviewManager(extraction)
        # ... contractor makes edits in UI ...
        manager.log_correction("blocks.Pool.rooms.Office.fixtures.lights", 10, 12, "fixture_count")
        # ... more edits ...
        log = manager.get_correction_log()
        manager.complete_review()
    """

    def __init__(self, extraction: ExtractionResult):
        """Initialize with extraction result from DISCOVER stage."""
        self.extraction = extraction
        self.corrections: list[CorrectionEntry] = []
        self._count_ai_items()

    def _count_ai_items(self) -> None:
        """Count total items the AI extracted (for accuracy calculation)."""
        count = 0

        for block in self.extraction.building_blocks:
            # Count DBs
            count += len(block.distribution_boards)

            # Count circuits
            for db in block.distribution_boards:
                count += len(db.circuits)

            # Count rooms and fixtures
            for room in block.rooms:
                count += 1  # Room itself
                fixtures = room.fixtures
                # Count non-zero fixture fields
                fixture_fields = [
                    'recessed_led_600x1200', 'surface_mount_led_18w', 'flood_light_30w',
                    'flood_light_200w', 'downlight_led_6w', 'vapor_proof_2x24w',
                    'vapor_proof_2x18w', 'prismatic_2x18w', 'bulkhead_26w', 'bulkhead_24w',
                    'fluorescent_50w_5ft', 'pole_light_60w', 'double_socket_300',
                    'single_socket_300', 'double_socket_1100', 'single_socket_1100',
                    'double_socket_waterproof', 'double_socket_ceiling', 'data_points_cat6',
                    'floor_box', 'switch_1lever_1way', 'switch_2lever_1way',
                    'switch_1lever_2way', 'day_night_switch', 'isolator_30a',
                    'isolator_20a', 'master_switch'
                ]
                for field_name in fixture_fields:
                    val = getattr(fixtures, field_name, 0)
                    if isinstance(val, int) and val > 0:
                        count += 1

            # Count heavy equipment
            count += len(block.heavy_equipment)

        # Count site cable runs
        count += len(self.extraction.site_cable_runs)

        self.total_ai_items = count

    def log_correction(
        self,
        field_path: str,
        original_value: Any,
        corrected_value: Any,
        item_type: str,
        building_block: str = "",
        page_source: str = "",
    ) -> None:
        """
        Log a contractor correction.

        Args:
            field_path: Dot-notation path to the field (e.g., "blocks.Pool.rooms.0.fixtures.lights")
            original_value: What the AI extracted
            corrected_value: What the contractor changed it to
            item_type: Type of item ("fixture_count", "cable_size", "breaker_rating", etc.)
            building_block: Name of the building block
            page_source: Which drawing page the data came from
        """
        entry = CorrectionEntry(
            field_path=field_path,
            original_value=original_value,
            corrected_value=corrected_value,
            item_type=item_type,
            building_block=building_block,
            page_source=page_source,
            timestamp=datetime.now().isoformat(),
        )
        self.corrections.append(entry)

    def remove_last_correction(self) -> Optional[CorrectionEntry]:
        """Remove and return the last correction (undo)."""
        if self.corrections:
            return self.corrections.pop()
        return None

    def get_corrections_for_block(self, block_name: str) -> list[CorrectionEntry]:
        """Get all corrections for a specific building block."""
        return [c for c in self.corrections if c.building_block == block_name]

    def get_corrections_by_type(self, item_type: str) -> list[CorrectionEntry]:
        """Get all corrections of a specific type."""
        return [c for c in self.corrections if c.item_type == item_type]

    def get_correction_log(self) -> CorrectionLog:
        """Build final correction log after review is complete."""
        # Count additions (original was 0 or None/empty)
        added = sum(
            1 for c in self.corrections
            if c.original_value in (0, None, "", [])
            and c.corrected_value not in (0, None, "", [])
        )

        # Count removals (corrected to 0 or None/empty)
        removed = sum(
            1 for c in self.corrections
            if c.corrected_value in (0, None, "", [])
            and c.original_value not in (0, None, "", [])
        )

        # Count changes (both values non-empty)
        changed = len(self.corrections) - added - removed

        return CorrectionLog(
            project_name=self.extraction.metadata.project_name,
            corrections=self.corrections.copy(),
            total_ai_items=self.total_ai_items,
            total_corrected=changed,
            total_added=added,
            total_removed=removed,
        )

    def complete_review(self) -> None:
        """Mark review as complete and attach correction log to extraction."""
        self.extraction.review_completed = True
        self.extraction.corrections = self.get_correction_log()

        # Update confidence for manually corrected items
        self._mark_manual_items()

    def _mark_manual_items(self) -> None:
        """Mark items that were manually corrected with MANUAL confidence."""
        # This would iterate through corrections and update the corresponding
        # items in the extraction to have confidence=MANUAL
        # For now, this is a placeholder - full implementation would parse
        # field_path and update the appropriate model
        pass

    @property
    def num_corrections(self) -> int:
        """Total number of corrections made."""
        return len(self.corrections)

    @property
    def has_corrections(self) -> bool:
        """Whether any corrections have been made."""
        return len(self.corrections) > 0

    @property
    def accuracy_preview(self) -> float:
        """Preview of AI accuracy based on current corrections."""
        if self.total_ai_items == 0:
            return 0.0
        log = self.get_correction_log()
        correct = self.total_ai_items - log.total_corrected - log.total_removed
        return round(max(0, correct) / self.total_ai_items * 100, 1)


def create_review_manager(extraction: ExtractionResult) -> ReviewManager:
    """Factory function to create a ReviewManager."""
    return ReviewManager(extraction)
