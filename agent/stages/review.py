"""
REVIEW Stage: Manages contractor review state and correction tracking.

This stage happens in the UI between DISCOVER and VALIDATE.
The ReviewManager tracks all corrections made by the contractor.
"""

from datetime import datetime
from typing import Optional, Any

from agent.models import (
    ExtractionResult, CorrectionEntry, CorrectionLog, ItemConfidence,
    StageResult, PipelineStage
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

    def __init__(self, extraction: ExtractionResult, project_name: str = ""):
        """Initialize with extraction result from DISCOVER stage."""
        self.extraction = extraction
        self.project_name = project_name or extraction.metadata.project_name or "Project"
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

    def complete_review(self) -> ExtractionResult:
        """Mark review as complete and attach correction log to extraction."""
        self.extraction.review_completed = True
        self.extraction.corrections = self.get_correction_log()

        # Update confidence for manually corrected items
        self._mark_manual_items()

        return self.extraction

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

    def update_circuit_value(
        self,
        block_name: str,
        db_name: str,
        circuit_id: str,
        field: str,
        new_value: Any,
    ) -> None:
        """
        Log a change to a circuit value.

        Args:
            block_name: Name of the building block
            db_name: Name of the distribution board
            circuit_id: ID of the circuit (empty string for DB-level changes)
            field: Field being changed (e.g., "breaker_a", "cable_size_mm2")
            new_value: New value for the field
        """
        if circuit_id:
            field_path = f"blocks.{block_name}.dbs.{db_name}.circuits.{circuit_id}.{field}"
        else:
            field_path = f"blocks.{block_name}.dbs.{db_name}.{field}"

        # Find original value (simplified - actual implementation would navigate the data structure)
        original_value = None  # Would be fetched from extraction

        self.log_correction(
            field_path=field_path,
            original_value=original_value,
            corrected_value=new_value,
            item_type=f"circuit_{field}",
            building_block=block_name,
        )

    def update_fixture_count(
        self,
        block_name: str,
        room_name: str,
        field: str,
        new_value: int,
    ) -> None:
        """
        Log a change to a fixture count.

        Args:
            block_name: Name of the building block
            room_name: Name of the room
            field: Fixture field being changed (e.g., "vapor_proof_2x18w")
            new_value: New count for the fixture
        """
        field_path = f"blocks.{block_name}.rooms.{room_name}.fixtures.{field}"

        # Find original value (simplified)
        original_value = None

        self.log_correction(
            field_path=field_path,
            original_value=original_value,
            corrected_value=new_value,
            item_type="fixture_count",
            building_block=block_name,
        )

    def update_cable_length(
        self,
        from_point: str,
        to_point: str,
        new_length: float,
    ) -> None:
        """
        Log a change to a cable run length.

        Args:
            from_point: Starting point of the cable run
            to_point: Ending point of the cable run
            new_length: New length in meters
        """
        field_path = f"site_cables.{from_point}_to_{to_point}.length_m"

        # Find original value (simplified)
        original_value = None

        self.log_correction(
            field_path=field_path,
            original_value=original_value,
            corrected_value=new_length,
            item_type="cable_length",
        )

    def get_accuracy_report(self) -> dict:
        """
        Get a summary report of AI accuracy based on corrections made.

        Returns:
            Dict with accuracy metrics
        """
        log = self.get_correction_log()
        return {
            "project_name": self.project_name,
            "total_ai_items": self.total_ai_items,
            "total_corrections": self.num_corrections,
            "corrections_changed": log.total_corrected,
            "corrections_added": log.total_added,
            "corrections_removed": log.total_removed,
            "accuracy_pct": log.accuracy_pct,
            "review_completed": self.extraction.review_completed,
        }


def create_review_manager(extraction: ExtractionResult) -> ReviewManager:
    """Factory function to create a ReviewManager."""
    return ReviewManager(extraction)


def cross_reference_sld_vs_layouts(extraction: ExtractionResult) -> list[dict]:
    """
    Cross-reference SLD circuit point counts against layout fixture counts.

    This validates that the "No Of Point" value from SLD schedules matches
    the actual count of symbols on layout drawings.

    Returns:
        List of discrepancies: {circuit, db, sld_count, layout_count, diff, severity}
    """
    discrepancies = []

    for block in extraction.building_blocks:
        # Build circuit -> point count from SLDs
        sld_counts = {}
        for db in block.distribution_boards:
            for circuit in db.circuits:
                if circuit.is_spare:
                    continue
                key = f"{db.name} {circuit.id}"
                sld_counts[key] = {
                    "db": db.name,
                    "circuit_id": circuit.id,
                    "sld_points": circuit.num_points,
                    "type": circuit.type,
                }

        # Build circuit -> count from room fixtures
        layout_counts = {}
        for room in block.rooms:
            for ref in room.circuit_refs:
                if ref not in layout_counts:
                    layout_counts[ref] = {"count": 0, "rooms": []}
                # Add fixture counts for this circuit
                if "L" in ref.upper():  # Lighting circuit
                    layout_counts[ref]["count"] += room.fixtures.total_lights
                elif "P" in ref.upper():  # Power circuit
                    layout_counts[ref]["count"] += room.fixtures.total_sockets
                layout_counts[ref]["rooms"].append(room.name)

        # Compare SLD vs Layout counts
        for circuit_ref, sld_info in sld_counts.items():
            sld_points = sld_info["sld_points"]
            layout_info = layout_counts.get(circuit_ref, {"count": 0})
            layout_points = layout_info["count"]

            if sld_points != layout_points and sld_points > 0:
                diff = abs(sld_points - layout_points)
                severity = "high" if diff > 3 else "medium" if diff > 1 else "low"

                discrepancies.append({
                    "circuit": circuit_ref,
                    "db": sld_info["db"],
                    "circuit_id": sld_info["circuit_id"],
                    "sld_count": sld_points,
                    "layout_count": layout_points,
                    "diff": diff,
                    "severity": severity,
                    "message": f"SLD shows {sld_points} points, layout count is {layout_points}",
                })

    return discrepancies


def get_items_needing_review(extraction: ExtractionResult) -> list[dict]:
    """
    Get list of items that need contractor review.

    Items with INFERRED or ESTIMATED confidence are flagged for review.
    Also includes cross-reference discrepancies.

    Returns:
        List of dicts with item info: {type, name, confidence, block, path}
    """
    items = []

    # Add cross-reference discrepancies as high-priority review items
    discrepancies = cross_reference_sld_vs_layouts(extraction)
    for disc in discrepancies:
        items.append({
            "type": "cross_reference_mismatch",
            "name": f"{disc['circuit']}: {disc['message']}",
            "confidence": ItemConfidence.ESTIMATED,
            "block": "",
            "path": f"validation.cross_ref.{disc['circuit']}",
            "severity": disc["severity"],
        })

    for block in extraction.building_blocks:
        block_name = block.name

        # Check DBs
        for db_idx, db in enumerate(block.distribution_boards):
            if db.confidence in (ItemConfidence.INFERRED, ItemConfidence.ESTIMATED):
                items.append({
                    "type": "distribution_board",
                    "name": db.name or f"DB {db_idx + 1}",
                    "confidence": db.confidence,
                    "block": block_name,
                    "path": f"blocks.{block_name}.dbs.{db_idx}",
                })

            # Check circuits
            for ckt_idx, circuit in enumerate(db.circuits):
                if circuit.confidence in (ItemConfidence.INFERRED, ItemConfidence.ESTIMATED):
                    items.append({
                        "type": "circuit",
                        "name": circuit.description or f"Circuit {circuit.id}",
                        "confidence": circuit.confidence,
                        "block": block_name,
                        "path": f"blocks.{block_name}.dbs.{db_idx}.circuits.{ckt_idx}",
                    })

        # Check rooms
        for room_idx, room in enumerate(block.rooms):
            if room.confidence in (ItemConfidence.INFERRED, ItemConfidence.ESTIMATED):
                items.append({
                    "type": "room",
                    "name": room.name or f"Room {room_idx + 1}",
                    "confidence": room.confidence,
                    "block": block_name,
                    "path": f"blocks.{block_name}.rooms.{room_idx}",
                })

        # Check heavy equipment
        for eq_idx, equipment in enumerate(block.heavy_equipment):
            if equipment.confidence in (ItemConfidence.INFERRED, ItemConfidence.ESTIMATED):
                items.append({
                    "type": "equipment",
                    "name": equipment.name,
                    "confidence": equipment.confidence,
                    "block": block_name,
                    "path": f"blocks.{block_name}.equipment.{eq_idx}",
                })

    # Check site cable runs
    for run_idx, run in enumerate(extraction.site_cable_runs):
        if run.confidence in (ItemConfidence.INFERRED, ItemConfidence.ESTIMATED):
            items.append({
                "type": "cable_run",
                "name": f"{run.from_point} → {run.to_point}",
                "confidence": run.confidence,
                "block": "",
                "path": f"site_cables.{run_idx}",
            })

    return items


def create_review_stage_result(
    review_manager: ReviewManager,
    processing_time_ms: int = 0,
) -> StageResult:
    """
    Create a StageResult for the REVIEW stage.

    Args:
        review_manager: The completed ReviewManager instance
        processing_time_ms: Time spent in the review stage

    Returns:
        StageResult for the REVIEW pipeline stage
    """
    log = review_manager.get_correction_log()

    return StageResult(
        stage=PipelineStage.REVIEW,
        success=True,
        confidence=review_manager.accuracy_preview / 100.0,  # Convert % to 0-1 scale
        data={
            "total_corrections": review_manager.num_corrections,
            "total_ai_items": review_manager.total_ai_items,
            "accuracy_pct": review_manager.accuracy_preview,
            "corrections_added": log.total_added,
            "corrections_removed": log.total_removed,
            "corrections_changed": log.total_corrected,
        },
        model_used=None,  # No AI model used in review stage
        tokens_used=0,
        cost_zar=0.0,
        processing_time_ms=processing_time_ms,
        errors=[],
        warnings=[],
    )
