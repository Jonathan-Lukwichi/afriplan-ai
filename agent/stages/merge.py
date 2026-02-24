"""
AfriPlan Electrical - Merge Stage

Aggregates page-level extraction results into a project-level result.
Performs:
- Cross-page deduplication
- Register vs uploaded drawings comparison
- Coverage diagnostics
- Warning aggregation

No AI/cloud APIs used.
"""

from __future__ import annotations

import logging
from typing import List, Dict, Set, Optional, Any
from collections import defaultdict

from agent.models import (
    ProjectExtractionResult, MergeStatistics,
    RegisterExtraction, SLDExtraction, LayoutExtraction,
    PageExtractionResult, ExtractionWarning, Severity, PageType
)
from agent.extractors.common import dedupe_strings, merge_similar_strings
from agent.parsers.drawing_number_parser import (
    parse_drawing_number, match_drawing_to_register
)

logger = logging.getLogger(__name__)


def merge_page_results(
    page_results: List[PageExtractionResult],
    document_filenames: Optional[List[str]] = None,
) -> ProjectExtractionResult:
    """
    Merge page-level extraction results into a project-level result.

    Args:
        page_results: List of page extraction results
        document_filenames: Source document filenames

    Returns:
        ProjectExtractionResult with aggregated data
    """
    result = ProjectExtractionResult()

    # Separate by page type
    register_pages = []
    sld_pages = []
    lighting_pages = []
    plugs_pages = []

    for pr in page_results:
        if pr.page_type == PageType.REGISTER and pr.register_data:
            register_pages.append(pr.register_data)
        elif pr.page_type == PageType.SLD and pr.sld_data:
            sld_pages.append(pr.sld_data)
        elif pr.page_type == PageType.LAYOUT_LIGHTING and pr.layout_data:
            lighting_pages.append(pr.layout_data)
        elif pr.page_type == PageType.LAYOUT_PLUGS and pr.layout_data:
            plugs_pages.append(pr.layout_data)

    # Store page lists
    result.register_pages = register_pages
    result.sld_pages = sld_pages
    result.lighting_pages = lighting_pages
    result.plugs_pages = plugs_pages

    # Merge register data
    if register_pages:
        result.register_combined = _merge_register_pages(register_pages)
        result.project_name = result.register_combined.project_name
        result.client_name = result.register_combined.client_name
        result.consultant_name = result.register_combined.consultant_name

    # Aggregate DB names from all SLD pages
    all_dbs = set()
    for sld in sld_pages:
        if sld.db_name:
            all_dbs.add(sld.db_name)
        all_dbs.update(sld.db_refs)
    result.all_db_names = sorted(list(all_dbs))

    # Aggregate circuit refs
    all_circuit_refs = set()
    for sld in sld_pages:
        for circuit in sld.circuits:
            if circuit.circuit_id:
                all_circuit_refs.add(f"{sld.db_name} {circuit.circuit_id}")
    for layout in lighting_pages + plugs_pages:
        all_circuit_refs.update(layout.circuit_refs)
    result.all_circuit_refs = sorted(list(all_circuit_refs))

    # Aggregate room labels
    all_rooms = set()
    for layout in lighting_pages + plugs_pages:
        all_rooms.update(layout.room_labels)
    result.all_room_labels = merge_similar_strings(sorted(list(all_rooms)))

    # Aggregate cable sizes
    all_cables = set()
    for sld in sld_pages:
        all_cables.update(sld.cable_refs)
    for layout in lighting_pages + plugs_pages:
        all_cables.update(layout.cable_sizes)
    result.all_cable_sizes = sorted(list(all_cables))

    # Aggregate equipment
    all_equipment = set()
    for layout in lighting_pages + plugs_pages:
        all_equipment.update(layout.equipment_labels)
    result.all_equipment = sorted(list(all_equipment))

    # Build drawing number map
    for pr in page_results:
        if pr.drawing_number:
            result.drawing_number_to_page[pr.drawing_number] = pr.page_number
            result.page_to_drawing_number[pr.page_number] = pr.drawing_number

    # Calculate statistics
    result.statistics = _calculate_statistics(
        page_results, result, register_pages
    )

    # Collect all warnings
    for pr in page_results:
        result.all_warnings.extend(pr.warnings)

    result.critical_warnings = len([
        w for w in result.all_warnings if w.severity == Severity.CRITICAL
    ])
    result.total_warnings = len(result.all_warnings)

    # Processing metadata
    result.pages_processed = len(page_results)
    result.pages_successful = len([pr for pr in page_results if pr.success])

    return result


def _merge_register_pages(
    register_pages: List[RegisterExtraction]
) -> RegisterExtraction:
    """
    Merge multiple register pages into one.
    (Some projects split register across pages)
    """
    merged = RegisterExtraction()

    # Take project info from first page with it
    for rp in register_pages:
        if rp.project_name and not merged.project_name:
            merged.project_name = rp.project_name
        if rp.client_name and not merged.client_name:
            merged.client_name = rp.client_name
        if rp.consultant_name and not merged.consultant_name:
            merged.consultant_name = rp.consultant_name

    # Merge all rows, deduplicate by drawing number
    seen_dwg = set()
    for rp in register_pages:
        for row in rp.rows:
            key = row.drawing_number.upper()
            if key not in seen_dwg:
                seen_dwg.add(key)
                merged.rows.append(row)

    merged.total_drawings = len(merged.rows)

    # Merge warnings
    for rp in register_pages:
        merged.parse_warnings.extend(rp.parse_warnings)

    return merged


def _calculate_statistics(
    page_results: List[PageExtractionResult],
    merged: ProjectExtractionResult,
    register_pages: List[RegisterExtraction],
) -> MergeStatistics:
    """Calculate merge statistics."""
    stats = MergeStatistics()

    # Page counts by type
    stats.total_pages = len(page_results)
    for pr in page_results:
        if pr.page_type == PageType.REGISTER:
            stats.register_pages += 1
        elif pr.page_type == PageType.SLD:
            stats.sld_pages += 1
        elif pr.page_type == PageType.LAYOUT_LIGHTING:
            stats.lighting_pages += 1
        elif pr.page_type == PageType.LAYOUT_PLUGS:
            stats.plugs_pages += 1
        elif pr.page_type == PageType.UNKNOWN:
            stats.unknown_pages += 1

    # Extraction counts
    stats.total_dbs = len(merged.all_db_names)
    stats.total_circuits = len(merged.all_circuit_refs)
    stats.total_rooms = len(merged.all_room_labels)

    # Coverage analysis: compare register vs uploaded
    if merged.register_combined:
        register_drawings = set(
            row.drawing_number.upper()
            for row in merged.register_combined.rows
            if row.drawing_number
        )
        uploaded_drawings = set(
            pr.drawing_number.upper()
            for pr in page_results
            if pr.drawing_number
        )

        stats.drawings_in_register = len(register_drawings)
        stats.drawings_uploaded = len(uploaded_drawings)

        # Match drawings
        matched = register_drawings & uploaded_drawings
        stats.drawings_matched = len(matched)

        # Missing = in register but not uploaded
        stats.drawings_missing = sorted(list(register_drawings - uploaded_drawings))

        # Extra = uploaded but not in register
        stats.drawings_extra = sorted(list(uploaded_drawings - register_drawings))

    # Deduplicated sets
    stats.unique_db_refs = merged.all_db_names
    stats.unique_cable_sizes = merged.all_cable_sizes
    stats.unique_circuit_refs = merged.all_circuit_refs

    return stats


def validate_coverage(result: ProjectExtractionResult) -> List[ExtractionWarning]:
    """
    Validate coverage and return diagnostic warnings.
    """
    warnings = []

    stats = result.statistics

    # Missing drawings warning
    if stats.drawings_missing:
        warnings.append(ExtractionWarning(
            code="MISSING_DRAWINGS",
            message=f"{len(stats.drawings_missing)} drawings in register but not uploaded",
            severity=Severity.WARNING,
            source_stage="merge",
            details={"missing": stats.drawings_missing[:10]},  # First 10
        ))

    # Extra drawings warning (uploaded but not in register)
    if stats.drawings_extra:
        warnings.append(ExtractionWarning(
            code="EXTRA_DRAWINGS",
            message=f"{len(stats.drawings_extra)} uploaded drawings not in register",
            severity=Severity.INFO,
            source_stage="merge",
            details={"extra": stats.drawings_extra[:10]},
        ))

    # No register warning
    if stats.register_pages == 0:
        warnings.append(ExtractionWarning(
            code="NO_REGISTER",
            message="No drawing register found - cannot verify completeness",
            severity=Severity.INFO,
            source_stage="merge",
        ))

    # No SLD warning
    if stats.sld_pages == 0:
        warnings.append(ExtractionWarning(
            code="NO_SLD",
            message="No SLD pages found - circuit data unavailable",
            severity=Severity.WARNING,
            source_stage="merge",
        ))

    # No layout pages warning
    if stats.lighting_pages == 0 and stats.plugs_pages == 0:
        warnings.append(ExtractionWarning(
            code="NO_LAYOUTS",
            message="No layout pages found - room/fixture data unavailable",
            severity=Severity.WARNING,
            source_stage="merge",
        ))

    # High unknown page ratio
    if stats.total_pages > 0:
        unknown_ratio = stats.unknown_pages / stats.total_pages
        if unknown_ratio > 0.3:
            warnings.append(ExtractionWarning(
                code="HIGH_UNKNOWN_RATIO",
                message=f"{stats.unknown_pages}/{stats.total_pages} pages could not be classified",
                severity=Severity.WARNING,
                source_stage="merge",
            ))

    return warnings


def generate_coverage_report(result: ProjectExtractionResult) -> str:
    """
    Generate a text coverage report.
    """
    lines = []
    stats = result.statistics

    lines.append("=" * 60)
    lines.append("EXTRACTION COVERAGE REPORT")
    lines.append("=" * 60)

    lines.append(f"\nProject: {result.project_name or 'Unknown'}")
    lines.append(f"Client: {result.client_name or 'Unknown'}")
    lines.append(f"Consultant: {result.consultant_name or 'Unknown'}")

    lines.append("\n--- PAGE SUMMARY ---")
    lines.append(f"Total pages processed: {stats.total_pages}")
    lines.append(f"  Register pages: {stats.register_pages}")
    lines.append(f"  SLD pages: {stats.sld_pages}")
    lines.append(f"  Lighting pages: {stats.lighting_pages}")
    lines.append(f"  Plugs pages: {stats.plugs_pages}")
    lines.append(f"  Unknown pages: {stats.unknown_pages}")

    lines.append("\n--- EXTRACTION SUMMARY ---")
    lines.append(f"Distribution boards: {stats.total_dbs}")
    lines.append(f"Circuit references: {stats.total_circuits}")
    lines.append(f"Room labels: {stats.total_rooms}")
    lines.append(f"Cable sizes found: {len(stats.unique_cable_sizes)}")

    if stats.drawings_in_register > 0:
        lines.append("\n--- COVERAGE ANALYSIS ---")
        lines.append(f"Drawings in register: {stats.drawings_in_register}")
        lines.append(f"Drawings uploaded: {stats.drawings_uploaded}")
        lines.append(f"Matched: {stats.drawings_matched}")

        if stats.drawings_missing:
            lines.append(f"\nMissing drawings ({len(stats.drawings_missing)}):")
            for dwg in stats.drawings_missing[:10]:
                lines.append(f"  - {dwg}")
            if len(stats.drawings_missing) > 10:
                lines.append(f"  ... and {len(stats.drawings_missing) - 10} more")

    lines.append("\n--- WARNINGS ---")
    lines.append(f"Total: {result.total_warnings}")
    lines.append(f"Critical: {result.critical_warnings}")

    lines.append("\n" + "=" * 60)

    return "\n".join(lines)
