"""
AfriPlan Electrical - Lighting Layout Extractor

Extract information from lighting layout pages.
Focuses on text-based extraction (deterministic):
- Room labels
- Circuit references
- Fixture labels from legend
- Notes and specifications

Does NOT attempt symbol counting (requires AI vision).

No AI/cloud APIs used.
"""

from __future__ import annotations

import logging
import re
from typing import List, Optional, Dict, Any
from dataclasses import dataclass

from agent.models import LayoutExtraction, ExtractionWarning, Severity
from agent.extractors.common import (
    normalize_text, clean_text_for_display,
    extract_room_labels, extract_circuit_ids, extract_db_refs,
    extract_cable_sizes, parse_height, dedupe_strings
)

logger = logging.getLogger(__name__)


class LightingLayoutExtractor:
    """
    Deterministic extractor for lighting layout pages.

    Extracts text-based information only.
    Symbol counting requires AI vision and is not implemented here.

    Usage:
        extractor = LightingLayoutExtractor()
        result = extractor.extract(page_text, page_number=1)
    """

    def __init__(self):
        """Initialize the lighting layout extractor."""
        # Fixture patterns for legend detection
        self.fixture_patterns = [
            (r'LED\s*DOWNLIGHT', "downlight"),
            (r'DOWNLIGHT', "downlight"),
            (r'LED\s*PANEL', "led_panel"),
            (r'RECESSED\s*(?:LED)?', "recessed"),
            (r'SURFACE\s*(?:MOUNT|LED)', "surface_mount"),
            (r'VAPOR\s*PROOF', "vapor_proof"),
            (r'BULKHEAD', "bulkhead"),
            (r'FLOOD\s*LIGHT', "flood_light"),
            (r'POLE\s*LIGHT', "pole_light"),
            (r'EMERGENCY\s*(?:LIGHT)?', "emergency"),
            (r'EXIT\s*SIGN', "exit_sign"),
        ]

        # Switch patterns
        self.switch_patterns = [
            (r'1[-\s]?LEVER\s*1[-\s]?WAY', "1L1W"),
            (r'2[-\s]?LEVER\s*1[-\s]?WAY', "2L1W"),
            (r'1[-\s]?LEVER\s*2[-\s]?WAY', "1L2W"),
            (r'DAY/?NIGHT\s*SWITCH', "D/N"),
            (r'MASTER\s*SWITCH', "MS"),
        ]

    def extract(
        self,
        text: str,
        text_blocks: Optional[List[Any]] = None,
        page_number: int = 0,
        legend_region_text: str = "",
        title_block_text: str = "",
    ) -> LayoutExtraction:
        """
        Extract lighting layout information from page text.

        Args:
            text: Raw page text
            text_blocks: Positioned text blocks (optional)
            page_number: Source page number
            legend_region_text: Text from detected legend region
            title_block_text: Text from title block region

        Returns:
            LayoutExtraction with parsed data
        """
        result = LayoutExtraction(
            source_page=page_number,
            layout_type="lighting",
        )

        # Extract drawing info from title block
        if title_block_text:
            result.drawing_number = self._extract_drawing_number(title_block_text)
            result.drawing_title = self._extract_drawing_title(title_block_text)

        # Fallback to main text
        if not result.drawing_number:
            result.drawing_number = self._extract_drawing_number(text)

        # Extract room labels
        result.room_labels = extract_room_labels(text)

        # Extract circuit references
        all_circuit_refs = []
        db_refs = extract_db_refs(text)

        for db in db_refs:
            circuits = extract_circuit_ids(text)
            for cid in circuits:
                if cid.startswith('L'):  # Lighting circuits
                    all_circuit_refs.append(f"{db} {cid}")

        # Also find direct circuit references like "DB-S1 L1"
        direct_refs = re.findall(
            r'(DB[-\s]?[A-Z0-9]+\s+L\d+)',
            text,
            re.IGNORECASE
        )
        for ref in direct_refs:
            all_circuit_refs.append(ref.upper())

        result.circuit_refs = dedupe_strings(all_circuit_refs)

        # Extract legend items
        legend_text = legend_region_text or text
        result.legend_items = self._extract_legend_items(legend_text)

        # Extract notes
        result.notes = self._extract_notes(text)

        # Extract mounting heights
        result.mounting_heights = self._extract_mounting_heights(text)

        # Extract cable sizes
        cable_specs = extract_cable_sizes(text)
        result.cable_sizes = [cs.raw_text for cs in cable_specs]

        # Extract equipment labels
        result.equipment_labels = self._extract_equipment_labels(text)

        # Extract containment references
        result.containment_refs = self._extract_containment(text)

        return result

    def _extract_drawing_number(self, text: str) -> str:
        """Extract drawing number from text."""
        patterns = [
            r'([A-Z]{2,4}-[A-Z]{1,4}-\d{1,3}-(?:LIGHTING|LT))',
            r'([A-Z]{2,4}-\d{1,3}-(?:LIGHTING|LT))',
            r'DWG\s*(?:NO)?[\s:\.]+([A-Z0-9\-]+)',
        ]

        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1).upper()

        return ""

    def _extract_drawing_title(self, text: str) -> str:
        """Extract drawing title from text."""
        patterns = [
            r'TITLE[\s:]+(.+?)(?:\n|$)',
            r'LIGHTING\s+(?:LAYOUT|PLAN)\s+[-–]\s+(.+?)(?:\n|$)',
        ]

        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return clean_text_for_display(match.group(1))

        return ""

    def _extract_legend_items(self, text: str) -> List[str]:
        """Extract fixture types from legend."""
        items = []

        # Look for LEGEND section
        legend_match = re.search(
            r'LEGEND[\s:]*(.+?)(?:\n\n|\Z)',
            text,
            re.IGNORECASE | re.DOTALL
        )

        search_text = legend_match.group(1) if legend_match else text

        # Find fixture types
        for pattern, fixture_type in self.fixture_patterns:
            if re.search(pattern, search_text, re.IGNORECASE):
                # Try to get full description
                match = re.search(
                    pattern + r'[^A-Z]*([A-Z0-9\s\-]+)',
                    search_text,
                    re.IGNORECASE
                )
                if match:
                    items.append(clean_text_for_display(match.group(0)))
                else:
                    items.append(fixture_type)

        # Find switch types
        for pattern, switch_type in self.switch_patterns:
            if re.search(pattern, search_text, re.IGNORECASE):
                match = re.search(pattern, search_text, re.IGNORECASE)
                if match:
                    items.append(clean_text_for_display(match.group(0)))

        return dedupe_strings(items)

    def _extract_notes(self, text: str) -> List[str]:
        """Extract notes from text."""
        notes = []

        # Find NOTE/NOTES sections
        note_patterns = [
            r'NOTE[S]?[\s:]+(.+?)(?:\n\n|\Z)',
            r'N\.B\.[\s:]+(.+?)(?:\n|$)',
            r'(?:^|\n)(\d+\.\s+.+?)(?:\n|$)',  # Numbered notes
        ]

        for pattern in note_patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE | re.MULTILINE):
                note = clean_text_for_display(match.group(1))
                if len(note) > 10:  # Skip very short matches
                    notes.append(note)

        return notes[:10]  # Limit to 10 notes

    def _extract_mounting_heights(self, text: str) -> List[str]:
        """Extract mounting height specifications."""
        heights = []

        patterns = [
            r'@\s*(\d+)\s*mm',
            r'(\d+)\s*mm\s+(?:AFF|AFFL|above\s+floor)',
            r'height[\s:]+(\d+)\s*mm',
        ]

        for pattern in patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                heights.append(f"{match.group(1)}mm")

        return dedupe_strings(heights)

    def _extract_equipment_labels(self, text: str) -> List[str]:
        """Extract equipment labels from text."""
        labels = []

        patterns = [
            r'\b(A/?C\s*UNIT)\b',
            r'\b(GEYSER\s*\d*)\b',
            r'\b(EXTRACTOR\s*FAN)\b',
            r'\b(EXHAUST\s*FAN)\b',
        ]

        for pattern in patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                labels.append(match.group(1).upper())

        return dedupe_strings(labels)

    def _extract_containment(self, text: str) -> List[str]:
        """Extract containment references."""
        refs = []

        patterns = [
            r'(\d+mm\s*(?:PVC\s*)?CONDUIT)',
            r'(CABLE\s*TRAY\s*\d*)',
            r'(TRUNKING\s*\d*x\d*)',
            r'(SKIRTING\s*TRUNKING)',
        ]

        for pattern in patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                refs.append(clean_text_for_display(match.group(1)))

        return dedupe_strings(refs)

    def validate(self, result: LayoutExtraction) -> List[ExtractionWarning]:
        """Validate extraction result and return warnings."""
        warnings = []

        if not result.room_labels:
            warnings.append(ExtractionWarning(
                code="NO_ROOMS",
                message="No room labels found in lighting layout",
                severity=Severity.INFO,
                source_stage="extract_lighting_layout",
            ))

        if not result.circuit_refs:
            warnings.append(ExtractionWarning(
                code="NO_CIRCUIT_REFS",
                message="No lighting circuit references found",
                severity=Severity.INFO,
                source_stage="extract_lighting_layout",
            ))

        if not result.legend_items:
            warnings.append(ExtractionWarning(
                code="NO_LEGEND",
                message="No legend/fixture types found",
                severity=Severity.INFO,
                source_stage="extract_lighting_layout",
            ))

        return warnings
